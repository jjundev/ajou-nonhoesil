#!/usr/bin/env python3
"""
_원천_아카이브 정리기.

원천 덤프에서 정리/ 와 중복되거나 쓸모없는 파일을 제거하고,
정리/ 에 없는 편집 가능 원본(퀴즈 예상문제 문서, 강의노트 PPT)을 정리/ 로 승격한다.

삭제 규칙은 모두 술어(predicate)로 표현한다. 술어가 성립하지 않으면 그 파일은
삭제하지 않고 건너뛴다 — 파일이 나중에 바뀌어도 조용히 잘못 지우지 않기 위함이다.
기본 동작은 dry-run이며, 실제 변경은 --apply 를 줄 때만 일어난다.
"""

from __future__ import annotations
import argparse
import hashlib
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path

ARCHIVE = Path("from_the_past/_원천_아카이브")
CURATED = Path("from_the_past/정리")

JUNK_PATTERNS = (
    re.compile(r"^~\$"),            # 한글/워드 임시 잠금 파일
    re.compile(r"\.partial\.pdf$"),  # 다운로드 중단본
)
LECTURE_PPT = re.compile(r"^실험(\d{1,2})\.pptx?$")
REPORT_DOC = re.compile(r"^실험\s?(\d{1,2}).*(예비|결과)보고서")
QUIZ_DOC = re.compile(r"^(?:실험\s?(\d{1,2})|quiz_0?(\d{1,2}))")
QUIZ_EXT = {".doc", ".docx", ".hwp"}


def digest(path: Path) -> str:
    m = hashlib.md5()
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            m.update(chunk)
    return m.hexdigest()


def manifest(root: Path) -> dict[str, list[Path]]:
    """root 아래 모든 파일의 md5 -> 경로 목록."""
    out: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[digest(path)].append(path)
    return out


def plan(archive: Path = ARCHIVE, curated: Path = CURATED) -> dict[str, list]:
    """삭제/승격 계획을 세운다. 파일시스템은 건드리지 않는다."""
    curated_hashes = set(manifest(curated)) if curated.exists() else set()
    arc = manifest(archive) if archive.exists() else {}

    deletions: list[tuple[Path, str, int]] = []
    promotions: list[tuple[Path, Path, str]] = []
    seen_internal: set[str] = set()

    for h, paths in sorted(arc.items(), key=lambda kv: str(kv[1][0])):
        for i, p in enumerate(sorted(paths, key=lambda q: (len(q.parts), str(q)))):
            size = p.stat().st_size
            if any(pat.search(p.name) for pat in JUNK_PATTERNS):
                deletions.append((p, "쓰레기(임시/중단 파일)", size))
            elif h in curated_hashes:
                deletions.append((p, "정리/ 안에 바이트 동일본 존재", size))
            elif i > 0 or h in seen_internal:
                deletions.append((p, "아카이브 내부 중복", size))
            else:
                seen_internal.add(h)
                dest = promotion_target(p, curated)
                if dest is not None:
                    promotions.append((p, dest, dest.parent.name))
    return {"deletions": deletions, "promotions": promotions}


def promotion_target(p: Path, curated: Path) -> Path | None:
    """정리/ 로 승격할 위치. 승격 대상이 아니면 None."""
    if LECTURE_PPT.match(p.name):
        return curated / "강의노트" / "원본_PPT" / p.name
    m = REPORT_DOC.match(p.name)
    if m:
        # 보고서는 퀴즈보다 먼저 판정한다 (파일명이 둘 다 "실험N"으로 시작하므로)
        kind = "예비보고서" if m.group(2) == "예비" else "결과보고서"
        return curated / kind / f"실험{int(m.group(1))}" / "원본_hwp" / p.name
    if p.suffix.lower() in QUIZ_EXT:
        m = QUIZ_DOC.match(p.name)
        if m:
            n = int(m.group(1) or m.group(2))
            if 1 <= n <= 10:
                return curated / "퀴즈" / f"실험{n}" / "원본_docx" / p.name
    return None


def verify(before: dict[str, list[Path]], after_root: Path,
           intended: set[str] | None = None) -> list[str]:
    """before 에 있던 고유 내용이 after 에 남아 있는지 확인.

    intended 는 의도적으로 버린 내용의 해시(쓰레기 파일). 그 외의 소실만 실패로 본다.
    """
    after = set(manifest(after_root))
    intended = intended or set()
    return [h for h in before if h not in after and h not in intended]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="실제로 삭제/이동한다 (기본은 dry-run)")
    ap.add_argument("--root", default=".", help="저장소 루트")
    args = ap.parse_args()

    os.chdir(args.root)
    before = manifest(Path("from_the_past"))
    p = plan()

    freed = sum(s for _, _, s in p["deletions"])
    print(f"삭제 {len(p['deletions'])}개 ({freed/1048576:.1f} MB) / 승격 {len(p['promotions'])}개\n")
    by_reason: dict[str, int] = defaultdict(int)
    for _, reason, _ in p["deletions"]:
        by_reason[reason] += 1
    for reason, n in sorted(by_reason.items(), key=lambda kv: -kv[1]):
        print(f"  삭제 {n:4d}개  {reason}")
    print()
    for src, dest, _ in p["promotions"]:
        print(f"  승격  {src.name}  ->  {dest.parent}")

    if not args.apply:
        print("\n[dry-run] 실제 변경 없음. 적용하려면 --apply")
        return 0

    for src, dest, _ in p["promotions"]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
    for path, _, _ in p["deletions"]:
        if path.exists():
            path.unlink()
    for d in sorted(Path("from_the_past").rglob("*"), key=lambda q: -len(q.parts)):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    junk_hashes = {h for h, paths in before.items()
                   if all(any(pat.search(q.name) for pat in JUNK_PATTERNS) for q in paths)}
    lost = verify(before, Path("from_the_past"), intended=junk_hashes)
    if lost:
        print(f"\n검증 실패: 고유 내용 {len(lost)}개 소실")
        return 1
    print(f"\n검증 통과: 고유 내용 {len(before)}개 중 {len(before)-len(junk_hashes)}개 보존, "
          f"쓰레기 {len(junk_hashes)}개만 의도적으로 소실")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
