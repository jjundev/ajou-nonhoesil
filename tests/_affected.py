"""변경 기반 테스트 라우터 — 바뀐 경로로 돌릴 테스트 파일을 고른다. 표준 라이브러리만 쓴다.

흐름(한 파일에 다 둔다)::

    변경 집합   changed_files(base)  git 기준 커밋과 지금 작업 트리의 차이 → {경로: 'A'|'D'|'M'}
    의존 맵     <git 공용 폴더>/pytest-affected/map.json   테스트 파일마다 읽은 파일·훑은 디렉터리 기록(`tests/_trace.py` 가 남긴 것)
    고르기      select(...)          변경 집합 × 맵 → Selection(돌릴 파일, 이유, 전체 사유, 안 읽힌 경로)

맵 형식(version 1)::

    {"version": 1, "commit": "<sha>", "built": "<시각>",
     "tests": {"tests/test_x.py": {"files": [...], "dirs": [...], "opaque": bool, ...}}}

경로는 모두 저장소 상대·NFC·posix 문자열이다. macOS 도구가 NFD 로 주거나 Windows 가 역슬래시로
줘도 `norm` 이 같은 문자열로 맞춘다.

명령줄::

    python -m tests._affected rebuild [-j N] [--timeout S]   테스트 파일마다 격리해 돌려 맵을 만든다
    python -m tests._affected explain [--base REF]           지금 변경으로 무엇을 왜 고르는지 보인다

판정은 보수적이다 — 확실히 상관없다고 말할 수 있을 때만 건너뛴다. 아무 테스트도 안 읽는 코드가
바뀌면 전체를 돌리고, 맵이 없거나 라우터 자신이 바뀌어도 전체를 돌린다.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from tests._trace import ENV_DIR, ENV_ROOT

ROOT = Path(__file__).resolve().parents[1]

MAP_VERSION = 1

# 이 파일들이 바뀌면 어느 테스트에 닿는지 알 수 없다 — 전체를 돌린다(`tests/_trace_site/` 아래도 같다).
FULL_TRIGGERS = (
    'pytest.ini', 'tests/conftest.py', 'requirements-dev.txt',
    'tests/_affected.py', 'tests/_trace.py', 'tests/_trace_site/sitecustomize.py',
)
_TRIGGER_DIR = 'tests/_trace_site/'

# 이 확장자의 파일이 어느 테스트에도 안 읽히면 "아무도 모르는 코드" 로 보고 전체를 돌린다.
CODE_SUFFIXES = frozenset({'.py', '.js', '.mjs', '.cjs', '.css', '.html', '.json', '.toml'})
# 코드 확장자라도 테스트와 상관없는 곳 — 안 읽힌 경로로 보고만 한다.
IGNORE = ('docs/**', 'tmp/**', '.claude/worktrees/**', '문제풀이영상/**', '.claude/skills/logic-lab-solution-video/**')

_PACK = ('복습노트/**', '.claude/skills/logic-lab-review-pack/**')
# 감사 훅이 못 보는 의존 — 테스트 파일 → 그 테스트가 바뀐 경로에 반응해야 하는 glob.
# 빈 튜플은 "직접 읽는 게 파이썬 쪽 기록에 다 남는다" 는 뜻이다(적어 두어야 가드가 통과한다).
EXTRA_DEPS: dict[str, tuple[str, ...]] = {
    # playwright·Chrome·node 가 팩 HTML 과 그것이 부르는 자산을 직접 연다 — 파이썬 쪽 기록에 안 남는다.
    'tests/test_review_pack_explanation_browser.py': _PACK,
    'tests/test_review_pack_navigation_browser.py': _PACK,
    'tests/test_review_pack_workbook_browser.py': _PACK,
    'tests/test_workbook_equations.py': _PACK,
    'tests/test_workbook_clip_gate.py': _PACK,
    'tests/test_review_pack_print.py': _PACK,
    # `git show :<경로>` 로 인덱스 사본을 읽는다.
    'tests/test_review_pack_workbook_render.py': ('.claude/skills/logic-lab-review-pack/assets/workbook/**',),
    # Chrome 은 파이썬이 tmp 에 쓴 HTML 만 연다 — 그 재료는 파이썬 쪽에 기록된다.
    'tests/test_lab_html2pdf.py': (), 'tests/test_lab_fit_pages.py': (),
    'tests/test_lab_figure_export.py': (), 'tests/test_trace_guide.py': (), 'tests/test_lab_config.py': (),
    # git 을 임시 저장소나 인자로 준 경로에만 쓴다.
    'tests/test_lab_isolate.py': (), 'tests/test_lab_schematic.py': (),
    # 가드 정규식 자신의 글자(`sync_playwright`·`chromium`)와 tmp 저장소용 git 호출에 걸린 것일 뿐이다.
    'tests/test_affected.py': (),
    # 가드 정규식이 `stages[0]["node"]` 같은 사전 키를 node 실행으로 오인한 것이다 — 파서는 외부 도구를 안 부른다.
    'tests/test_lab_netlist_parser.py': (),
}


def norm(p: str) -> str:
    """NFC 로 맞추고 역슬래시를 `/` 로 — 맵의 경로와 같은 표기."""
    return unicodedata.normalize('NFC', p).replace('\\', '/')


# --- 변경 집합 ----------------------------------------------------------------

def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['git', '-c', 'core.quotepath=off', *args],
        cwd=root, capture_output=True, check=False,
    )


def _git_text(root: Path, *args: str) -> str | None:
    """git 이 성공하면 표준출력 한 줄(공백 제거), 실패하면 `None`."""
    done = _git(root, *args)
    if done.returncode != 0:
        return None
    return done.stdout.decode('utf-8').strip()


def changed_files(base: str, root: Path = ROOT) -> dict[str, str]:
    """`base` 커밋 뒤 바뀐 경로 → 'A'|'D'|'M'. 커밋·스테이지·작업 트리·untracked 를 다 합친다.

    이름 바꾸기는 합치지 않아(`--no-renames`) 옛 경로는 'D', 새 경로는 'A' 로 둘 다 나온다.
    """
    out: dict[str, str] = {}
    diff = _git(root, 'diff', '--name-status', '-z', '--no-renames', base)
    if diff.returncode != 0:
        raise RuntimeError(f'git diff 실패: {diff.stderr.decode("utf-8", "replace").strip()}')
    parts = diff.stdout.decode('utf-8').split('\0')
    for status, path in zip(parts[0::2], parts[1::2]):
        if status:
            out[norm(path)] = status[0] if status[0] in 'AD' else 'M'
    others = _git(root, 'ls-files', '--others', '--exclude-standard', '-z')
    if others.returncode != 0:
        raise RuntimeError(f'git ls-files 실패: {others.stderr.decode("utf-8", "replace").strip()}')
    for path in others.stdout.decode('utf-8').split('\0'):
        if path:
            out[norm(path)] = 'A'
    return out


def default_base(root: Path = ROOT) -> str:
    """기준 커밋 — `origin/main` 과의 merge-base, 없으면 `main` 과의 merge-base, 그것도 없으면 HEAD.

    ref 가 있는데 merge-base 가 실패하면(공통 조상이 없는 역사 등) 다음 후보로 넘어가지 않고
    `RuntimeError` — 넘어가면 이 브랜치의 커밋이 변경 집합에서 빠진다.
    """
    for ref in ('refs/remotes/origin/main', 'refs/heads/main'):
        if _git_text(root, 'rev-parse', '--verify', '-q', ref) is None:
            continue
        base = _git_text(root, 'merge-base', 'HEAD', ref)
        if not base:
            raise RuntimeError(f'git merge-base HEAD {ref} 실패 — 기준 커밋을 정할 수 없다')
        return base
    head = _git_text(root, 'rev-parse', 'HEAD')
    if head is None:
        raise RuntimeError('git rev-parse HEAD 실패 — 커밋이 없는 저장소')
    return head


# --- 고르기 -------------------------------------------------------------------

@dataclass(frozen=True)
class Selection:
    """`select` 의 결과.

    files        돌릴 테스트 파일. `None` 이면 전체
    reasons      고른 테스트 → 걸린 변경 경로(또는 `'맵에 없음'`)
    full_reason  전체를 돌리는 사유(전체가 아니면 `None`)
    unread       어느 테스트도 안 읽었지만 코드는 아니라 보고만 하는 경로(정렬)
    """

    files: frozenset[str] | None
    reasons: dict[str, tuple[str, ...]]
    full_reason: str | None
    unread: tuple[str, ...]


def _match_any(path: str, globs: Iterable[str]) -> bool:
    pure = PurePosixPath(path)
    return any(pure.full_match(g) for g in globs)


def _ancestors(path: str) -> list[str]:
    """`path` 의 조상 디렉터리들(저장소 루트 `''` 는 뺀다)."""
    return [str(a) for a in PurePosixPath(path).parents if str(a) != '.']


def select(changed: dict[str, str], depmap: dict | None, test_files: Iterable[str],
           extra: dict[str, tuple[str, ...]] = EXTRA_DEPS) -> Selection:
    """변경 집합 × 의존 맵 → 돌릴 테스트 파일. 판정 순서는 앞이 이긴다.

    1. 바뀐 게 없으면 빈 선택.
    2. 라우터·설정 파일이 바뀌었으면 전체.
    3. 맵이 없거나 버전이 다르면 전체.
    4. 테스트마다 — 맵에 없으면 늘 고른다. 있으면 자기 자신·읽은 파일이 바뀌었거나,
       훑은 디렉터리 아래 파일이 새로 생기거나 지워졌거나(수정은 파일로만 본다),
       `extra` glob 에 걸리면 고른다.
    5. 어느 테스트도 고르지 않은 경로 — 지운 테스트 파일은 버리고, 코드 확장자면 전체,
       나머지는 `unread` 로 보고만 한다.
    """
    norm_changed = {norm(p): s for p, s in changed.items()}
    if not norm_changed:
        return Selection(frozenset(), {}, None, ())

    for p in sorted(norm_changed):
        if p in FULL_TRIGGERS or p.startswith(_TRIGGER_DIR):
            return Selection(None, {}, f'설정·라우터 변경: {p}', ())

    if depmap is None or depmap.get('version') != MAP_VERSION:
        return Selection(None, {}, '맵 없음 — python -m tests._affected rebuild', ())

    maps = depmap.get('tests', {})
    reasons: dict[str, tuple[str, ...]] = {}
    claimed: set[str] = set()
    for t in (norm(f) for f in test_files):
        rec = maps.get(t)
        if rec is None:
            reasons[t] = ('맵에 없음',)
            if t in norm_changed:       # 새 테스트 파일 자신의 변경도 이 테스트가 받는다(전체 실행 사유가 아니다)
                claimed.add(t)
            continue
        files = set(rec.get('files', ()))
        dirs = set(rec.get('dirs', ()))
        globs = extra.get(t, ())
        hits = []
        for p, status in norm_changed.items():
            if (p == t or p in files
                    or (status in 'AD' and any(a in dirs for a in _ancestors(p)))
                    or _match_any(p, globs)):
                hits.append(p)
        if hits:
            reasons[t] = tuple(sorted(hits))
            claimed.update(hits)

    unread = []
    full_reason = None
    for p in sorted(set(norm_changed) - claimed):
        pure = PurePosixPath(p)
        if pure.match('tests/test_*.py') and len(pure.parts) == 2 and norm_changed[p] == 'D':
            continue
        if pure.suffix in CODE_SUFFIXES and not _match_any(p, IGNORE):
            full_reason = full_reason or f'테스트가 읽지 않는 코드: {p}'
        else:
            unread.append(p)
    return Selection(None if full_reason else frozenset(reasons), reasons, full_reason, tuple(unread))


# --- 맵 입출력 ----------------------------------------------------------------

def map_path(root: Path = ROOT) -> Path:
    """맵 파일 — git 공용 폴더 아래라 worktree 들이 한 맵을 나눠 쓰고 커밋에는 안 섞인다."""
    common = _git_text(root, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if not common:
        raise RuntimeError('git rev-parse --git-common-dir 실패 — git 저장소가 아니다')
    return Path(common) / 'pytest-affected' / 'map.json'


def load_map(path: Path) -> dict | None:
    """맵을 읽는다. 없거나 JSON 이 깨졌으면 `None`(→ 전체 실행)."""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save_map(path: Path, data: dict) -> None:
    """부모 폴더를 만들고, 같은 폴더의 임시 파일에 쓴 뒤 `os.replace` 로 바꿔 끼운다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.map-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def test_files(root: Path = ROOT) -> list[str]:
    """`tests/test_*.py` 를 정렬해 저장소 상대 경로로."""
    return sorted(norm(p.relative_to(root).as_posix()) for p in (root / 'tests').glob('test_*.py'))


# --- 맵 만들기 ----------------------------------------------------------------

def _run_group(cmd: list[str], *, cwd: Path, env: dict, timeout: int) -> int | None:
    """`cmd` 를 새 프로세스 그룹으로 돌려 종료 코드를 준다. 시간이 넘으면 그룹째 죽이고 `None`."""
    posix = os.name == 'posix'
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=posix)
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if posix:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        proc.wait()
        return None


def trace_file(test: str, root: Path = ROOT, timeout: int = 900) -> dict | None:
    """테스트 파일 하나를 추적기(`tests._trace`)를 켜고 따로 돌려 맵 항목을 만든다.

    `{'files', 'dirs', 'opaque', 'seconds', 'outcome'}` — outcome 은 종료 코드 0 → passed,
    1 → failed, 그 밖 → error. 실패한 테스트도 읽은 기록은 남는다. 시간이 넘거나 기록이
    하나도 안 남으면 `None`.
    """
    with tempfile.TemporaryDirectory(prefix='affected-trace-') as out:
        pypath = os.pathsep.join(
            [str(ROOT / 'tests' / '_trace_site'), str(ROOT)]
            + ([os.environ['PYTHONPATH']] if os.environ.get('PYTHONPATH') else []))
        env = {**os.environ, ENV_DIR: out, ENV_ROOT: str(root), 'PYTHONPATH': pypath}
        start = time.monotonic()
        code = _run_group(
            [sys.executable, '-m', 'pytest', '-n0', '-p', 'tests._trace', '-p', 'no:cacheprovider', '-q', test],
            cwd=root, env=env, timeout=timeout)
        seconds = round(time.monotonic() - start, 2)
        if code is None:
            return None
        files: set[str] = set()
        dirs: set[str] = set()
        opaque = False
        found = False
        for jf in sorted(Path(out).glob('*.json')):
            try:
                one = json.loads(jf.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            found = True
            files.update(one.get('files', ()))
            dirs.update(one.get('dirs', ()))
            opaque = opaque or bool(one.get('opaque'))
    if not found:
        return None
    return {'files': sorted(files), 'dirs': sorted(dirs), 'opaque': opaque, 'seconds': seconds,
            'outcome': {0: 'passed', 1: 'failed'}.get(code, 'error')}


def rebuild(jobs: int | None = None, root: Path = ROOT, timeout: int = 900) -> dict:
    """테스트 파일마다 `trace_file` 을 돌려 맵을 저장하고 돌려준다. 끝에 보고를 찍는다.

    직전 맵에서 오래 걸린 파일부터 시작해(처음 보는 파일은 맨 앞) 병렬 꼬리를 줄인다.
    시간 초과·기록 없음(`None`)은 맵에서 뺀다 — 맵에 없는 테스트는 `select` 가 늘 고른다.
    """
    path = map_path(root)
    head = _git_text(root, 'rev-parse', 'HEAD')
    if head is None:
        raise RuntimeError('git rev-parse HEAD 실패 — 커밋이 없는 저장소')
    previous = (load_map(path) or {}).get('tests', {})
    tests = sorted(test_files(root), key=lambda t: -previous.get(t, {}).get('seconds', float('inf')))
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, jobs or os.cpu_count() or 1)) as pool:
        entries = list(pool.map(lambda t: trace_file(t, root, timeout), tests))
    data = {
        'version': MAP_VERSION, 'commit': head, 'built': datetime.now().isoformat(timespec='seconds'),
        'python': platform.python_version(), 'platform': sys.platform,
        'tests': {t: e for t, e in zip(tests, entries) if e is not None},
    }
    save_map(path, data)
    _report(data, [t for t, e in zip(tests, entries) if e is None], time.monotonic() - started, root)
    return data


def _report(data: dict, dropped: list[str], seconds: float, root: Path) -> None:
    """rebuild 가 끝난 뒤 맵의 빈틈을 찍는다."""
    entries = data['tests']
    failed = sorted(t for t, e in entries.items() if e['outcome'] != 'passed')
    opaque = sorted(t for t, e in entries.items() if e['opaque'] and t not in EXTRA_DEPS)
    read: set[str] = set()
    for e in entries.values():
        read.update(e['files'])
    listed = _git(root, 'ls-files', '-z')
    unread = []
    if listed.returncode == 0:
        for p in (norm(x) for x in listed.stdout.decode('utf-8').split('\0') if x):
            if (PurePosixPath(p).suffix in CODE_SUFFIXES and not _match_any(p, IGNORE)
                    and p not in FULL_TRIGGERS and not p.startswith(_TRIGGER_DIR)
                    and p not in read and (root / p).is_file()):
                unread.append(p)
    print(f'라우터 맵: 테스트 파일 {len(entries)}개 기록 · {seconds:.0f}초 · {data["commit"][:7]}')
    if failed:
        print(f'  실패·오류로 끝난 파일 {len(failed)}개(읽은 기록은 남김): ' + ', '.join(failed))
    if dropped:
        print(f'  시간 초과·기록 없음으로 맵에서 뺀 파일 {len(dropped)}개(늘 고름): ' + ', '.join(dropped))
    if opaque:
        print(f'  추적이 끊긴 자식을 띄우는데 EXTRA_DEPS 에 없는 파일 {len(opaque)}개: ' + ', '.join(opaque))
    if unread:
        print(f'  어느 테스트도 읽지 않은 코드 파일 {len(unread)}개(앞 20개):')
        for p in unread[:20]:
            print(f'    {p}')


# --- 계획 ---------------------------------------------------------------------

def header_lines(sel: Selection, base: str, changed: int, total: int,
                 map_commit: str | None, built: str | None, stale: bool = False) -> list[str]:
    """요약 줄 — 고름·전체·빈 선택 셋 중 하나, 맵이 오래됐으면 한 줄 더."""
    if sel.full_reason is not None or sel.files is None:
        lines = [f'라우터: 전체 실행 — {sel.full_reason}']
    elif not sel.files:
        lines = ['라우터: 바뀐 파일 없음 — 돌릴 것 없음' if changed == 0
                 else f'라우터: 바뀐 파일 {changed} 개를 읽는 테스트 없음 — 돌릴 것 없음']
    else:
        lines = [f'라우터: 기준 {base[:7]} · 바뀐 파일 {changed} · 선택 {len(sel.files)}/{total}'
                 f' · 맵 {(built or "")[:10]}({(map_commit or "")[:7]})']
    if stale:
        lines.append('라우터: 맵이 기준보다 오래됐다 — python -m tests._affected rebuild')
    return lines


def _resolve(root: Path, ref: str) -> str | None:
    return _git_text(root, 'rev-parse', '--verify', '-q', f'{ref}^{{commit}}')


def plan(base: str | None = None, root: Path = ROOT) -> tuple[Selection, list[str]]:
    """기준 → 변경 집합 → 맵 → 고르기, 그리고 요약 줄. git 이 실패하면 전체 실행으로 돌린다."""
    tests = test_files(root)
    try:
        base = base or default_base(root)
        changed = changed_files(base, root)
        path = map_path(root)
    except RuntimeError as exc:
        sel = Selection(None, {}, f'git 실패 — {str(exc).splitlines()[0]}', ())
        return sel, header_lines(sel, base or '', 0, len(tests), None, None)
    depmap = load_map(path)
    sel = select(changed, depmap, tests)
    map_commit = built = None
    stale = False
    resolved = _resolve(root, base)
    base = resolved or base       # 요약 줄에는 ref 이름이 아니라 커밋 해시를 보인다
    if depmap is not None:
        map_commit, built = depmap.get('commit'), depmap.get('built')
        if map_commit and resolved and map_commit != resolved:
            stale = _git(root, 'merge-base', '--is-ancestor', map_commit, resolved).returncode == 0
    return sel, header_lines(sel, base, len(changed), len(tests), map_commit, built, stale)


def explain(base: str | None = None, root: Path = ROOT) -> list[str]:
    """`plan` 의 요약 줄 + 고른 테스트마다 걸린 경로 + 아무도 안 읽는 경로."""
    sel, lines = plan(base, root)
    for t in sorted(sel.files or ()):
        lines.append(f'  {t} ← {", ".join(sel.reasons.get(t, ()))}')
    lines.extend(f'  (읽는 테스트 없음) {p}' for p in sel.unread)
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='python -m tests._affected', description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    rb = sub.add_parser('rebuild', help='테스트 파일마다 격리해 돌려 의존 맵을 만든다')
    rb.add_argument('-j', '--jobs', type=int, default=None, help='동시에 돌릴 수(기본: CPU 수)')
    rb.add_argument('--timeout', type=int, default=900, help='파일마다 제한 시간(초)')
    ex = sub.add_parser('explain', help='지금 변경에서 무엇을 왜 고르는지 보인다')
    ex.add_argument('--base', default=None, help='기준 커밋(기본: origin/main 과의 merge-base)')
    args = ap.parse_args(argv)
    if args.cmd == 'rebuild':
        rebuild(jobs=args.jobs, timeout=args.timeout)
    else:
        print('\n'.join(explain(args.base)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
