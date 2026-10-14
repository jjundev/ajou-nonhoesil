"""변경 기반 테스트 라우터(`tests/_affected.py`)의 고르기 검사 — 변경 집합과 `select`."""

import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from tests._affected import (
    EXTRA_DEPS, ROOT, Selection, changed_files, default_base, explain, header_lines, load_map,
    main, map_path, plan, rebuild, save_map, select, trace_file,
)
from tests._affected import test_files as list_test_files  # `test_` 로 시작해 pytest 가 줍지 않게 이름을 바꾼다

M = {
    'version': 1,
    'tests': {
        'tests/test_a.py': {
            'files': ['tests/test_a.py', 'scripts/lab/md.py', '보고서/실험05/명세.md'],
            'dirs': ['보고서'],
            'opaque': False,
        },
        'tests/test_b.py': {
            'files': ['tests/test_b.py', 'scripts/lab/notion.py'],
            'dirs': [],
            'opaque': False,
        },
    },
}
T = ['tests/test_a.py', 'tests/test_b.py']


def test_읽은_파일이_바뀌면_그_테스트만():
    s = select({'scripts/lab/md.py': 'M'}, M, T)
    assert s.files == {'tests/test_a.py'} and s.reasons['tests/test_a.py'] == ('scripts/lab/md.py',)


def test_테스트_파일_자신이_바뀌면_고른다():
    assert select({'tests/test_b.py': 'M'}, M, T).files == {'tests/test_b.py'}


def test_훑은_디렉터리_아래_새_파일은_조상까지_본다():
    assert select({'보고서/실험07/결선도/배치.py': 'A'}, M, T).files == {'tests/test_a.py'}


def test_훑은_디렉터리_아래라도_수정은_파일로만_본다():
    s = select({'보고서/실험06/명세.md': 'M'}, M, T)
    assert s.files == frozenset() and s.unread == ('보고서/실험06/명세.md',)


def test_전체_트리거():
    assert select({'tests/conftest.py': 'M'}, M, T).files is None


def test_추적기_사이트_폴더_아래도_전체_트리거():
    s = select({'tests/_trace_site/extra.py': 'A'}, M, T)
    assert s.files is None and '설정·라우터 변경' in s.full_reason


def test_맵이_없으면_전체():
    s = select({'scripts/lab/md.py': 'M'}, None, T)
    assert s.files is None and 'rebuild' in s.full_reason


def test_맵_버전이_다르면_전체():
    s = select({'scripts/lab/md.py': 'M'}, {'version': 2, 'tests': {}}, T)
    assert s.files is None and 'rebuild' in s.full_reason


def test_아무도_안_읽는_코드는_전체_비코드는_보고만():
    assert select({'scripts/lab/new.py': 'A'}, M, T).files is None
    s = select({'보고서/실험05/output/메모.md': 'M'}, M, T)
    assert s.files == frozenset() and s.unread == ('보고서/실험05/output/메모.md',)


def test_IGNORE_아래_코드는_보고만():
    assert select({'docs/x.py': 'M'}, M, T).files == frozenset()


def test_맵에_없는_테스트는_늘_고른다():
    s = select({'보고서/x.md': 'M'}, M, T + ['tests/test_c.py'])
    assert 'tests/test_c.py' in s.files and s.reasons['tests/test_c.py'] == ('맵에 없음',)


def test_맵에_없는_테스트_파일_자신이_바뀌면_전체를_부르지_않는다():
    s = select({'tests/test_new.py': 'A'}, M, T + ['tests/test_new.py'])
    assert s.files == {'tests/test_new.py'} and s.full_reason is None


def test_지운_테스트_파일은_전체를_부르지_않는다():
    assert select({'tests/test_gone.py': 'D'}, M, T).files == frozenset()


def test_EXTRA_glob_으로_고른다():
    s = select({'복습노트/실험05/a.html': 'M'}, M, T, extra={'tests/test_b.py': ('복습노트/**',)})
    assert s.files == {'tests/test_b.py'}


def test_바뀐_것이_없으면_빈_선택():
    s = select({}, M, T)
    assert s.files == frozenset() and s.full_reason is None


def test_NFD_경로도_같은_파일로_본다():
    nfd = unicodedata.normalize('NFD', '보고서/실험05/명세.md')
    assert select({nfd: 'M'}, M, T).files == {'tests/test_a.py'}


def test_역슬래시_경로():
    assert select({'scripts\\lab\\md.py': 'M'}, M, T).files == {'tests/test_a.py'}


# --- 변경 집합: 임시 git 저장소 ------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', *args],
        cwd=repo, check=True, capture_output=True, text=True, encoding='utf-8',
    )
    return out.stdout.strip()


def _repo(tmp_path: Path, branch: str = 'main', name: str = 'repo') -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, 'init', '-q', '-b', branch)
    return repo


def _commit_all(repo: Path, msg: str) -> str:
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-q', '-m', msg)
    return _git(repo, 'rev-parse', 'HEAD')


def test_변경_집합은_커밋_작업트리_untracked_를_합친다(tmp_path):
    repo = _repo(tmp_path)
    for name in 'abd':
        (repo / f'{name}.txt').write_text('0\n', encoding='utf-8')
    base = _commit_all(repo, 'base')
    (repo / 'a.txt').write_text('1\n', encoding='utf-8')
    _commit_all(repo, 'a 수정')
    (repo / 'b.txt').write_text('1\n', encoding='utf-8')     # 스테이지 안 한 수정
    (repo / 'c.txt').write_text('1\n', encoding='utf-8')     # untracked
    (repo / 'd.txt').unlink()                                 # 삭제
    assert changed_files(base, repo) == {'a.txt': 'M', 'b.txt': 'M', 'c.txt': 'A', 'd.txt': 'D'}


def test_이름_바꾸면_두_경로가_다_나온다(tmp_path):
    repo = _repo(tmp_path)
    (repo / 'old.txt').write_text('내용이 어느 정도 있어야 이름 바꾸기로 잡힌다\n' * 5, encoding='utf-8')
    base = _commit_all(repo, 'base')
    _git(repo, 'mv', 'old.txt', 'new.txt')
    assert changed_files(base, repo) == {'old.txt': 'D', 'new.txt': 'A'}


def test_한글_경로는_NFC_로_나온다(tmp_path):
    repo = _repo(tmp_path)
    (repo / 'x.txt').write_text('0\n', encoding='utf-8')
    base = _commit_all(repo, 'base')
    name = unicodedata.normalize('NFD', '보고서') + '.txt'
    (repo / name).write_text('1\n', encoding='utf-8')
    assert list(changed_files(base, repo)) == ['보고서.txt']


def test_기준은_origin_main_다음_main_다음_HEAD(tmp_path):
    # origin 없음·main 없음(브랜치 이름 trunk) → HEAD
    repo = _repo(tmp_path, 'trunk')
    (repo / 'a.txt').write_text('0\n', encoding='utf-8')
    first = _commit_all(repo, 'first')
    assert default_base(repo) == first

    # main 만 있음 → merge-base(HEAD, main)
    repo2 = _repo(tmp_path, name='m')
    (repo2 / 'a.txt').write_text('0\n', encoding='utf-8')
    fork = _commit_all(repo2, 'fork')
    _git(repo2, 'switch', '-q', '-c', 'feat')
    (repo2 / 'a.txt').write_text('1\n', encoding='utf-8')
    f1 = _commit_all(repo2, 'feat 1')
    (repo2 / 'a.txt').write_text('2\n', encoding='utf-8')
    _commit_all(repo2, 'feat 2')
    assert default_base(repo2) == fork

    # origin/main 도 있으면 그쪽이 먼저다 — main 과 merge-base 가 달라지게 f1 에 건다
    _git(repo2, 'update-ref', 'refs/remotes/origin/main', f1)
    assert default_base(repo2) == f1


def test_origin_main_이_있는데_merge_base_가_실패하면_조용히_넘어가지_않는다(tmp_path):
    repo = _repo(tmp_path)
    (repo / 'a.txt').write_text('0\n', encoding='utf-8')
    _commit_all(repo, 'main 쪽')
    # 공통 조상이 없는 역사 — origin/main 은 있지만 HEAD 와 merge-base 가 없다
    _git(repo, 'switch', '-q', '--orphan', 'other')
    (repo / 'b.txt').write_text('0\n', encoding='utf-8')
    other = _commit_all(repo, '고아')
    _git(repo, 'switch', '-q', 'main')
    _git(repo, 'switch', '-q', '-c', 'feat')
    _git(repo, 'update-ref', 'refs/remotes/origin/main', other)
    with pytest.raises(RuntimeError, match='merge-base'):
        default_base(repo)


# --- 정적 가드 ----------------------------------------------------------------

def test_브라우저_Chrome_git_node_를_부르는_테스트는_EXTRA_DEPS_에_있다():
    pat = re.compile(r"sync_playwright|chromium|_chrome\(|html2pdf|\[\s*['\"]git['\"]|\[\s*['\"]?node\b")
    need = {f'tests/{p.name}' for p in (ROOT / 'tests').glob('test_*.py') if pat.search(p.read_text(encoding='utf-8'))}
    assert need - set(EXTRA_DEPS) == set()


def test_EXTRA_DEPS_의_테스트_파일은_있다():
    assert [t for t in EXTRA_DEPS if not (ROOT / t).is_file()] == []


# --- 맵 입출력 ----------------------------------------------------------------

def test_map_path_는_공용_git_폴더_아래(tmp_path):
    repo = _repo(tmp_path)
    assert map_path(repo).resolve() == (repo / '.git' / 'pytest-affected' / 'map.json').resolve()


def test_load_map_은_없거나_깨졌으면_None(tmp_path):
    assert load_map(tmp_path / '없음.json') is None
    broken = tmp_path / 'broken.json'
    broken.write_text('{깨짐', encoding='utf-8')
    assert load_map(broken) is None


def test_save_map_은_부모_폴더를_만들고_임시_파일을_남기지_않는다(tmp_path):
    path = tmp_path / 'a' / 'b' / 'map.json'
    save_map(path, {'version': 1, 'tests': {'tests/test_가.py': {'files': ['보고서/x.md']}}})
    assert load_map(path) == {'version': 1, 'tests': {'tests/test_가.py': {'files': ['보고서/x.md']}}}
    assert [p.name for p in path.parent.iterdir()] == ['map.json']


def test_test_files_는_tests_아래_test_py_를_정렬한다(tmp_path):
    (tmp_path / 'tests').mkdir()
    for name in ('test_b.py', 'test_a.py', 'helper.py', 'conftest.py'):
        (tmp_path / 'tests' / name).write_text('', encoding='utf-8')
    (tmp_path / 'tests' / 'sub').mkdir()
    (tmp_path / 'tests' / 'sub' / 'test_c.py').write_text('', encoding='utf-8')
    assert list_test_files(tmp_path) == ['tests/test_a.py', 'tests/test_b.py']


# --- trace_file ---------------------------------------------------------------

def _trace_proj(tmp_path: Path, body: str) -> Path:
    """tests/ 에 `__init__.py` 가 없는 임시 프로젝트 — 저장소의 `tests` 패키지가 이겨야 한다."""
    proj = tmp_path / 'proj'
    (proj / 'sub').mkdir(parents=True)
    (proj / 'data.txt').write_text('d', encoding='utf-8')
    (proj / 'sub' / 'a.txt').write_text('a', encoding='utf-8')
    (proj / 'child.txt').write_text('c', encoding='utf-8')
    (proj / 'test_x.py').write_text(body, encoding='utf-8')
    return proj


def test_trace_file_은_한_파일의_기록을_합친다(tmp_path):
    proj = _trace_proj(tmp_path, '''
import subprocess, sys
from pathlib import Path
def test_x():
    Path('data.txt').read_text()
    list(Path('sub').glob('*.txt'))
    subprocess.run([sys.executable, '-c', "open('child.txt').read()"], check=True)
''')
    e = trace_file('test_x.py', root=proj, timeout=120)
    assert 'data.txt' in e['files'] and 'child.txt' in e['files'] and 'test_x.py' in e['files']
    assert 'sub' in e['dirs'] and e['outcome'] == 'passed' and e['opaque'] is False
    assert e['seconds'] > 0 and e['files'] == sorted(e['files'])


def test_시간_초과는_None(tmp_path):
    proj = _trace_proj(tmp_path, 'import time\ndef test_x():\n    time.sleep(5)\n')
    assert trace_file('test_x.py', root=proj, timeout=1) is None


def test_실패한_테스트도_기록은_남는다(tmp_path):
    proj = _trace_proj(tmp_path, '''
from pathlib import Path
def test_x():
    Path('data.txt').read_text()
    assert False
''')
    e = trace_file('test_x.py', root=proj, timeout=120)
    assert e['outcome'] == 'failed' and 'data.txt' in e['files']


def test_추적_변수_없이_띄운_자식이_있으면_opaque(tmp_path):
    proj = _trace_proj(tmp_path, '''
import os, subprocess, sys
def test_x():
    subprocess.run([sys.executable, '-c', 'pass'], env={'PATH': os.environ['PATH']}, check=True)
''')
    assert trace_file('test_x.py', root=proj, timeout=120)['opaque'] is True


# --- rebuild ------------------------------------------------------------------

def _git_proj(tmp_path: Path, tests: dict[str, str]) -> Path:
    proj = _repo(tmp_path, name='proj')
    (proj / 'tests').mkdir()
    (proj / 'data.txt').write_text('d', encoding='utf-8')
    for name, text in tests.items():
        (proj / 'tests' / name).write_text(text, encoding='utf-8')
    _commit_all(proj, 'init')
    return proj


OK_BODY = 'from pathlib import Path\ndef test_ok():\n    Path(__file__).parents[1].joinpath("data.txt").read_text()\n'
HANG_BODY = 'import time\ndef test_hang():\n    time.sleep(30)\n'


def test_rebuild_는_맵에_빠진_파일을_적지_않는다(tmp_path, capsys):
    proj = _git_proj(tmp_path, {'test_ok.py': OK_BODY, 'test_hang.py': HANG_BODY})
    rebuild(jobs=2, root=proj, timeout=5)
    m = load_map(map_path(proj))
    assert set(m['tests']) == {'tests/test_ok.py'} and m['version'] == 1 and m['commit']
    assert m['commit'] == _git(proj, 'rev-parse', 'HEAD')
    assert {'built', 'python', 'platform'} <= set(m)
    ok = m['tests']['tests/test_ok.py']
    assert 'data.txt' in ok['files'] and ok['outcome'] == 'passed'
    out = capsys.readouterr().out
    assert 'tests/test_hang.py' in out and '시간 초과' in out


def test_rebuild_는_실제_저장소_맵을_건드리지_않는다(tmp_path):
    real = map_path(ROOT)
    before = real.stat().st_mtime_ns if real.exists() else None
    proj = _git_proj(tmp_path, {'test_ok.py': OK_BODY})
    rebuild(jobs=1, root=proj, timeout=60)
    assert (real.stat().st_mtime_ns if real.exists() else None) == before


def test_rebuild_보고는_읽히지_않은_코드_파일을_센다(tmp_path, capsys):
    proj = _git_proj(tmp_path, {'test_ok.py': OK_BODY})
    (proj / 'lonely.py').write_text('x = 1\n', encoding='utf-8')
    _commit_all(proj, 'lonely')
    rebuild(jobs=1, root=proj, timeout=60)
    out = capsys.readouterr().out
    assert 'lonely.py' in out and 'data.txt' not in out


# --- plan / explain -----------------------------------------------------------

def test_plan_요약_첫_줄():
    sel = Selection(files=frozenset({'tests/test_a.py'}), reasons={}, full_reason=None, unread=())
    lines = header_lines(sel, base='abc1234def', changed=3, total=103, map_commit='8553b66aa', built='2026-10-14T10:00')
    assert lines == ['라우터: 기준 abc1234 · 바뀐 파일 3 · 선택 1/103 · 맵 2026-10-14(8553b66)']


def test_전체_실행_문구():
    sel = Selection(files=None, reasons={}, full_reason='맵 없음 — python -m tests._affected rebuild', unread=())
    assert header_lines(sel, 'abc1234', 2, 50, None, None) == [
        '라우터: 전체 실행 — 맵 없음 — python -m tests._affected rebuild']


def test_빈_선택_문구_둘():
    sel = Selection(files=frozenset(), reasons={}, full_reason=None, unread=())
    assert header_lines(sel, 'abc1234', 0, 50, 'm' * 9, '2026-10-14T10:00') == [
        '라우터: 바뀐 파일 없음 — 돌릴 것 없음']
    assert header_lines(sel, 'abc1234', 4, 50, 'm' * 9, '2026-10-14T10:00') == [
        '라우터: 바뀐 파일 4 개를 읽는 테스트 없음 — 돌릴 것 없음']


def test_맵이_오래됐으면_둘째_줄이_붙는다():
    sel = Selection(files=None, reasons={}, full_reason='x', unread=())
    lines = header_lines(sel, 'abc1234', 1, 50, 'm' * 9, '2026-10-14T10:00', stale=True)
    assert lines[1] == '라우터: 맵이 기준보다 오래됐다 — python -m tests._affected rebuild'


def _map_for(proj: Path, commit: str) -> None:
    save_map(map_path(proj), {
        'version': 1, 'commit': commit, 'built': '2026-10-14T10:00:00', 'tests': {
            'tests/test_a.py': {'files': ['tests/test_a.py', 'lib.py'], 'dirs': [], 'opaque': False},
        }})


def test_explain_은_걸린_경로를_보인다(tmp_path):
    proj = _git_proj(tmp_path, {'test_a.py': 'def test_a():\n    pass\n'})
    (proj / 'lib.py').write_text('1\n', encoding='utf-8')
    (proj / 'notes.md').write_text('1\n', encoding='utf-8')
    head = _commit_all(proj, 'lib')
    _map_for(proj, head)
    (proj / 'lib.py').write_text('2\n', encoding='utf-8')
    (proj / 'notes.md').write_text('2\n', encoding='utf-8')
    lines = explain('HEAD', proj)
    assert lines[0] == f'라우터: 기준 {head[:7]} · 바뀐 파일 2 · 선택 1/1 · 맵 2026-10-14({head[:7]})'
    assert '  tests/test_a.py ← lib.py' in lines
    assert '  (읽는 테스트 없음) notes.md' in lines
    assert len(lines) == 3


def test_맵이_기준의_조상이면_오래됐다고_알린다(tmp_path):
    proj = _git_proj(tmp_path, {'test_a.py': 'def test_a():\n    pass\n'})
    old = _git(proj, 'rev-parse', 'HEAD')
    _map_for(proj, old)
    (proj / 'lib.py').write_text('2\n', encoding='utf-8')
    _commit_all(proj, '다음')
    sel, lines = plan('HEAD', proj)
    assert lines[-1].startswith('라우터: 맵이 기준보다 오래됐다')


def test_plan_은_맵이_없으면_전체(tmp_path):
    proj = _git_proj(tmp_path, {'test_a.py': 'def test_a():\n    pass\n'})
    (proj / 'x.txt').write_text('1\n', encoding='utf-8')
    sel, lines = plan('HEAD', proj)
    assert sel.files is None and lines == [f'라우터: 전체 실행 — {sel.full_reason}'] and 'rebuild' in sel.full_reason


def test_plan_은_git_실패를_전체_실행으로_바꾼다(tmp_path):
    proj = _git_proj(tmp_path, {'test_a.py': 'def test_a():\n    pass\n'})
    sel, lines = plan('없는-기준', proj)
    assert sel.files is None and 'git' in sel.full_reason and lines[0].startswith('라우터: 전체 실행')
    # origin/main 이 있는데 merge-base 가 안 되는 경우도 기준을 못 정한 것이다
    _git(proj, 'switch', '-q', '--orphan', 'other')
    (proj / 'b.txt').write_text('0\n', encoding='utf-8')
    other = _commit_all(proj, '고아')
    _git(proj, 'switch', '-q', 'main')
    _git(proj, 'update-ref', 'refs/remotes/origin/main', other)
    sel, _ = plan(None, proj)
    assert sel.files is None and 'git' in sel.full_reason


def test_main_explain_은_종료_코드_0(capsys):
    assert main(['explain', '--base', 'HEAD']) == 0
    assert capsys.readouterr().out.startswith('라우터:')
