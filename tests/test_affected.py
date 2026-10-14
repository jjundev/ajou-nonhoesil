"""변경 기반 테스트 라우터(`tests/_affected.py`)의 고르기 검사 — 변경 집합과 `select`."""

import re
import subprocess
import unicodedata
from pathlib import Path

from tests._affected import EXTRA_DEPS, ROOT, changed_files, default_base, select

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


# --- 정적 가드 ----------------------------------------------------------------

def test_브라우저_Chrome_git_node_를_부르는_테스트는_EXTRA_DEPS_에_있다():
    pat = re.compile(r"sync_playwright|chromium|_chrome\(|html2pdf|\[\s*['\"]git['\"]|\[\s*node\b")
    need = {f'tests/{p.name}' for p in (ROOT / 'tests').glob('test_*.py') if pat.search(p.read_text(encoding='utf-8'))}
    assert need - set(EXTRA_DEPS) == set()


def test_EXTRA_DEPS_의_테스트_파일은_있다():
    assert [t for t in EXTRA_DEPS if not (ROOT / t).is_file()] == []
