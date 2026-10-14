"""변경 기반 테스트 라우터 — 바뀐 경로로 돌릴 테스트 파일을 고른다. 표준 라이브러리만 쓴다.

흐름(한 파일에 다 둔다)::

    변경 집합   changed_files(base)  git 기준 커밋과 지금 작업 트리의 차이 → {경로: 'A'|'D'|'M'}
    의존 맵     tests/.depmap.json   테스트 파일마다 읽은 파일·훑은 디렉터리 기록(`tests/_trace.py` 가 남긴 것)
    고르기      select(...)          변경 집합 × 맵 → Selection(돌릴 파일, 이유, 전체 사유, 안 읽힌 경로)

맵 형식(version 1)::

    {"version": 1, "commit": "<sha>", "built": "<시각>",
     "tests": {"tests/test_x.py": {"files": [...], "dirs": [...], "opaque": bool, ...}}}

경로는 모두 저장소 상대·NFC·posix 문자열이다. macOS 도구가 NFD 로 주거나 Windows 가 역슬래시로
줘도 `norm` 이 같은 문자열로 맞춘다.

이 파일에는 고르기(변경 집합·`select`)가 있다. 맵을 만들고 읽고 계획을 세우는 쪽(`map_path`·
`load_map`·`rebuild`·`plan`·`header_lines`·`main`)은 같은 파일에 이어 붙는다.

판정은 보수적이다 — 확실히 상관없다고 말할 수 있을 때만 건너뛴다. 아무 테스트도 안 읽는 코드가
바뀌면 전체를 돌리고, 맵이 없거나 라우터 자신이 바뀌어도 전체를 돌린다.
"""

from __future__ import annotations

import subprocess
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

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
    """기준 커밋 — `origin/main` 과의 merge-base, 없으면 `main` 과의 merge-base, 그것도 없으면 HEAD."""
    for ref in ('refs/remotes/origin/main', 'refs/heads/main'):
        if _git_text(root, 'rev-parse', '--verify', '-q', ref) is None:
            continue
        base = _git_text(root, 'merge-base', 'HEAD', ref)
        if base:
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
