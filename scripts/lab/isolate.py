"""격리 재생성용 작업 트리.

`git worktree` 를 쓰지 않는다 — worktree 는 이력을 통째로 들고 가서 답안지를
지워도 `git status` 에 삭제 목록이 뜨고 `git show HEAD:...` 로 되살릴 수 있다.
`git archive HEAD` 로 풀고 답안지를 지운 뒤 **새 저장소로 `git init` 해 커밋
하나**를 만든다. 그러면 `git status` 도 `git log` 도 아무것도 말하지 않는다.

답안지 **목록은 여기 없다.** 정본은 스킬 문서(`verify-draft-lab-spec/SKILL.md`)
이고 이 모듈은 받은 목록을 지울 뿐이다 — 목록을 코드에 두면 스킬 문서와
둘이 되어 표류한다.
"""

import io
import os
import re
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path

from . import config
from .regen_compare import _sentences
from .spec_parser import parse_spec

# 기본값 — `draft-lab-spec` 검증용. 명세·결선도·output 을 통째로 비운다.
# 결과보고서 검증은 `clear_subdirs=("output",)` 에 `keep` 으로 예비보고서 md 를
# 되살린다 — 명세·기록·결선도·사진은 ④ 의 입력이지 답안이 아니다.
_CLEARED = ("체크리스트", "결선도", "output")
_GLOB_CHARS = ("*", "?", "[")


def _git(cwd, *args) -> str:
    return subprocess.run(["git", "-c", "user.name=ws", "-c", "user.email=ws@local", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def _guard(dest_real: Path, p: Path, key: str) -> Path:
    """`dest / key` 가 격리 트리 밖을 가리키면 예외. 절대경로 키·`..` 키가 그렇다."""
    p_real = p.resolve()
    if p_real == dest_real or not p_real.is_relative_to(dest_real):
        # `dest / key` 는 key 가 절대경로처럼 보이면 dest 를 버리고 key 그대로가
        # 된다(Path.__truediv__ 의 규칙) — 답안지 키에 실수로든 스킬 문서 오염으로든
        # 앞에 `/` 가 붙으면 격리 임시 폴더 밖 임의 경로를 rmtree/unlink 하게 된다.
        raise ValueError(f"답안지 키가 격리 트리 밖을 가리킨다: {key!r}")
    return p


def _expand_keys(dest: Path, dest_real: Path, answer_keys) -> list:
    out = []
    for key in answer_keys:
        if any(ch in key for ch in _GLOB_CHARS):
            if Path(key).is_absolute() or key.startswith(("/", "\\")) or ".." in Path(key).parts:
                raise ValueError(f"답안지 키가 격리 트리 밖을 가리킨다: {key!r}")
            out += [_guard(dest_real, p, key) for p in sorted(dest.glob(key))]
        else:
            out.append(_guard(dest_real, dest / key, key))
    return out


def _rmtree(path: Path) -> None:
    """지난 회차의 격리 트리를 지운다. Windows 에서 `.git/objects/` 는 읽기 전용이라
    `shutil.rmtree` 가 PermissionError 로 죽는다(2026-09-12 2회차) — 쓰기 권한을
    주고 다시 지운다."""
    def _onerror(func, p, exc_info):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=_onerror)


def _restore(archive: bytes, dest: Path, rel: str) -> None:
    """아카이브에서 `rel` 하나를 다시 꺼낸다. 없으면 KeyError — 조용히 넘기면
    '예비보고서 없이 돌았다' 가 판정에서 '④ 가 예보를 안 읽었다' 로 보인다."""
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
        member = tf.getmember(rel)
        tf.extract(member, dest, filter="data")


def build_isolated_tree(root, dest, experiment: int, answer_keys,
                        clear_subdirs=_CLEARED, keep=(), edit=None) -> Path:
    """…(기존 docstring 유지)…

    `edit(dest)` 는 답안 삭제·`keep` 복원 뒤, `git init` **전**에 한 번 불린다.
    답안이 파일 하나의 일부일 때(결선도 빌더 구간) 파일을 지우지 않고 고치는
    자리다 — 커밋 뒤에 고치면 `git show HEAD:…` 로 원문이 되살아난다.
    """
    root, dest = Path(root), Path(dest)
    if dest.exists():
        _rmtree(dest)
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=root,
                             check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
        tf.extractall(dest, filter="data")

    dest_real = dest.resolve()
    for p in _expand_keys(dest, dest_real, answer_keys):
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    exp = dest / config.experiment_dir(experiment)
    for sub in clear_subdirs:
        d = exp / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    for rel in keep:
        _restore(archive, dest, rel)
    if edit is not None:
        edit(dest)

    _git(dest, "init", "-q")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-qm", "workspace")
    return dest


_DERIVED = re.compile(r"derived\s*\((.*)\)\s*$", re.S)


def leak_tokens(spec_path) -> list:
    """승인본 명세에서 트리에 남아 있으면 안 되는 문자열을 뽑는다."""
    spec = parse_spec(Path(spec_path))
    toks = []
    for it in spec.items:
        toks += [it.id, it.title]
    for t in spec.tables:
        m = _DERIVED.search(t.source or "")
        if m:
            toks += [part.strip() for part in m.group(1).split(";") if part.strip()]
    return toks


def leak_scan(dest, tokens, exts=(".md", ".py", ".html", ".txt", ".json")) -> list:
    dest = Path(dest)
    hits = []
    for p in sorted(dest.rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix not in exts:
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(lines, 1):
            for tok in tokens:
                if tok in line:
                    hits.append(f"{p.relative_to(dest).as_posix()}:{n}: {tok}")
    return hits


def leak_sentences(approved_md, tree, min_len=25, exts=(".md", ".py", ".txt")) -> list:
    """승인본 보고서의 문장(25자 이상)이 트리 어딘가에 그대로 남아 있는지 본다.

    명세 토큰(`leak_tokens`)은 결과보고서에 맞지 않는다 — 결보의 답은 항목 id 가
    아니라 문장이다. `regen_compare.shared_sentences` 와 같은 자름 규칙을 쓴다.
    """
    tree = Path(tree)
    wanted = _sentences(Path(approved_md), min_len)
    hits = []
    for p in sorted(tree.rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix not in exts:
            continue
        try:
            found = _sentences(p, min_len)
        except UnicodeDecodeError:
            continue
        for s in sorted(wanted & found, key=len, reverse=True):
            hits.append(f"{p.relative_to(tree).as_posix()}: {s[:120]}")
    return hits
