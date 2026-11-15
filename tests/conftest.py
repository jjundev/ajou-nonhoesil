"""xdist 를 `--dist loadgroup` 으로 돌릴 때 그룹을 정한다(`pytest.ini`).

- `tests/_boards.py` 의 `per_builder`·`per_experiment` 가 만든 클래스는 자기
  `render_group` 으로 묶는다 — 같은 회로를 보는 테스트가 한 워커에 모여 렌더 캐시를
  한 번만 채운다.
- `xdist_per_test = True` 인 클래스는 테스트마다 따로 흩는다 — `setUp` 이 매번 새로
  만들어 나눠 쓰는 것이 없고, 한 클래스가 한 워커를 1분 넘게 잡던 자리다.
- 나머지는 파일::클래스 단위로 묶는다. 마크 없는 테스트를 loadgroup 은 낱개로 흩는데,
  그러면 `setUpClass` 준비를 테스트마다 다시 한다.

`--affected[=기준]` 은 `tests/_affected.py` 가 고른 테스트 파일만 남긴다 — 기준 커밋 뒤 바뀐
파일을 읽는 테스트만 돌고, 고른 게 없으면 "돌릴 것 없음" 으로 종료 코드 0 이다. 옵션이 없으면
아무것도 하지 않는다. 워커는 컨트롤러가 정한 목록을 `workerinput` 으로 받는다(워커마다 git 을
다시 부르지 않는다). 기준은 `--affected=BASE` 로 붙여 쓴다 — `--affected 경로` 는 경로를 기준으로
삼켜 버리므로 기준이 커밋이 아니면 사용법 오류로 멈춘다.
"""
import re

import pytest

from tests import _affected

AFFECTED = pytest.StashKey[tuple]()      # (Selection, 요약 줄) — 컨트롤러에서만 채워진다


def pytest_addoption(parser):
    parser.addoption("--explanation-pack-root", default="복습노트", help="Root of six staged explanation packs")
    parser.addoption(
        '--affected', nargs='?', const='auto', default=None, metavar='BASE',
        help='기준 커밋 이후 바뀐 파일을 읽는 테스트 파일만 돈다(tests/_affected.py)')


def _base_error(opt, root=_affected.ROOT):
    """`--affected` 값이 기준으로 쓸 수 없으면 사용법 오류 문구, 쓸 수 있으면 `None`.

    `nargs='?'` 라 `pytest --affected tests/x.py` 는 경로를 기준으로 삼킨다 — 그대로 두면 git 이
    경로를 pathspec 으로 읽어 "바뀐 파일 없음" 으로 아무것도 안 돌고 0 으로 끝난다.
    """
    if opt is None or opt == 'auto' or _affected.resolve(opt, root) is not None:
        return None
    return (f"--affected 의 기준 '{opt}' 은(는) 커밋이 아니다 — 기준은 --affected=BASE 로 붙여 쓴다. "
            '맨 --affected 바로 뒤에 경로를 두면 기준으로 읽힌다(경로를 앞에 두거나 --affected=BASE 로 쓴다)')


def pytest_configure(config):
    opt = config.getoption('--affected')
    if opt is not None and not hasattr(config, 'workerinput'):
        msg = _base_error(opt)
        if msg is not None:
            raise pytest.UsageError(msg)
        config.stash[AFFECTED] = _affected.plan(None if opt == 'auto' else opt)


def pytest_report_header(config):
    return config.stash[AFFECTED][1] if AFFECTED in config.stash else []


@pytest.hookimpl(trylast=True)
def pytest_sessionstart(session):
    """`-q` 는 보고서 머리를 감춘다 — 그래도 요약 줄은 보여야 "왜 이것만 도는지" 를 알 수 있다."""
    config = session.config
    if AFFECTED not in config.stash:
        return
    reporter = config.pluginmanager.get_plugin('terminalreporter')
    if reporter is not None and reporter.verbosity < 0:
        for line in config.stash[AFFECTED][1]:
            reporter.write_line(line)


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node):
    """xdist 컨트롤러가 워커를 띄울 때 — 고른 목록(전체면 None)을 실어 보낸다."""
    if AFFECTED not in node.config.stash:       # --affected 를 안 줬다
        return
    sel = node.config.stash[AFFECTED][0]
    node.workerinput['affected'] = None if sel.files is None else sorted(sel.files)


def _chosen(config):
    """고른 테스트 파일 목록. `--affected` 가 없거나 전체 실행이면 `None`."""
    if config.getoption('--affected') is None:
        return None
    if hasattr(config, 'workerinput'):
        return config.workerinput.get('affected')
    sel = config.stash[AFFECTED][0]
    return None if sel.files is None else sorted(sel.files)


_ROUTED = re.compile(r'tests/test_[^/]*\.py')     # 라우터가 고르는 파일 — 그 밖에서 모인 항목은 늘 남긴다


def _routed_rel(path, root=_affected.ROOT):
    """`path` 가 라우터가 고르는 `tests/test_*.py` 면 그 저장소 상대 경로, 아니면 `None`.

    양쪽을 `norm` 으로 맞춘 뒤 자른다 — 저장소 경로 앞부분이 NFD 로 와도 같은 문자열이 된다.
    """
    base = _affected.norm(str(root)).rstrip('/') + '/'
    full = _affected.norm(str(path))
    if not full.startswith(base):
        return None             # 저장소 밖 — 라우터가 판단할 수 없다
    rel = full[len(base):]
    return rel if _ROUTED.fullmatch(rel) else None


def _deselect(config, items):
    chosen = _chosen(config)
    if chosen is None:
        return
    keep = set(chosen)
    kept, gone = [], []
    for it in items:
        rel = _routed_rel(it.path)
        (kept if rel is None or rel in keep else gone).append(it)
    if gone:
        config.hook.pytest_deselected(items=gone)
        items[:] = kept


def pytest_sessionfinish(session, exitstatus):
    """고른 게 0개라 xdist 가 "수집된 테스트 없음"(5)으로 끝내도 이건 정상이다."""
    chosen = _chosen(session.config)
    if chosen is not None and not chosen and exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK


@pytest.hookimpl(tryfirst=True)   # xdist 가 마크를 읽어 nodeid 에 `@그룹` 을 붙이기 전에
def pytest_collection_modifyitems(config, items):
    _group(items)
    _deselect(config, items)


def _group(items):
    for item in items:
        if item.get_closest_marker("xdist_group"):
            continue
        cls = item.cls
        if getattr(cls, "xdist_per_test", False):
            group = item.nodeid
        else:
            group = getattr(cls, "render_group", None) or f"{item.path.name}::{cls.__name__ if cls else ''}"
        item.add_marker(pytest.mark.xdist_group(group))


@pytest.fixture
def published_workbook_preview(tmp_path):
    """Render the published payload into an isolated browser-test workspace."""
    from pathlib import Path
    from scripts.lab.review_pack.manifest import DATA, load_manifest
    from scripts.lab.workbook_pdf import _temporary_html

    root = Path('복습노트')
    def preview(experiment, key):
        folder = root / experiment
        manifest = load_manifest(folder / DATA / 'manifest.json')
        scratch = tmp_path / experiment
        scratch.mkdir(exist_ok=True)
        return _temporary_html(folder, manifest, key, scratch)
    return preview
