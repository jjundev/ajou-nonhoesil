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
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from . import config
from .spec_parser import parse_spec

_CLEARED = ("체크리스트", "결선도", "output")


def _git(cwd, *args) -> str:
    return subprocess.run(["git", "-c", "user.name=ws", "-c", "user.email=ws@local", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def build_isolated_tree(root, dest, experiment: int, answer_keys) -> Path:
    root, dest = Path(root), Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=root,
                             check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
        tf.extractall(dest, filter="data")

    dest_real = dest.resolve()
    for key in answer_keys:
        p = dest / key
        p_real = p.resolve()
        if p_real == dest_real or not p_real.is_relative_to(dest_real):
            # `dest / key` 는 key 가 절대경로처럼 보이면 dest 를 버리고
            # key 그대로가 된다(Path.__truediv__ 의 규칙) — 답안지 키에
            # 실수로든 스킬 문서 오염으로든 앞에 `/` 가 붙으면 격리
            # 임시 폴더 밖 임의 경로를 rmtree/unlink 하게 된다.
            raise ValueError(f"답안지 키가 격리 트리 밖을 가리킨다: {key!r}")
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    exp = dest / config.experiment_dir(experiment)
    for sub in _CLEARED:
        d = exp / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

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
                    hits.append(f"{p.relative_to(dest)}:{n}: {tok}")
    return hits
