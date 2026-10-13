"""복습노트 실험 폴더를 "루트에는 .html·.pdf 만, 나머지는 숨김 `.pack/`" 배치로 옮긴다 (1회성).

    python -m scripts.lab.migrate_pack_layout            # 계획만 출력 (dry-run)
    python -m scripts.lab.migrate_pack_layout --apply    # 실제로 옮긴다
    python -m scripts.lab.migrate_pack_layout --apply 실험03 실험05

하는 일 (팩마다):
1. `자료/` 를 `.pack/` 으로 이름만 바꾼다.
2. 루트 HTML 과 `.pack/problem-explanations/` HTML 조각 속 `자료/` 경로를 `.pack/` 으로 바꾼다.
3. 루트의 md 를 `.pack/` 으로 옮기며 링크를 그 폴더 기준으로 바꾼다(pack_md.to_data_frame).
4. manifest.generated_files 를 새 경로로 고친다.

PDF 는 다시 만들지 않는다 — 내용이 같다. HTML·md·manifest 밖의 파일은 전후 SHA256 이 같아야 하고,
md 는 되돌린 텍스트가 원본(옛 접두만 `.pack/` 으로 바꾼 꼴)과 같아야 한다. 끝에 check_pack 을 돌린다.
옛 단계(2026-10-09, 문서 외 파일을 `자료/` 로)는 git 3b7902f 에 있다.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.manifest import DATA
from scripts.lab.review_pack.pack_md import _TARGET, to_data_frame, to_root_frame

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "복습노트"
OLD = "자료"
OLD_ENCODED = "%EC%9E%90%EB%A3%8C"
_HTML_PREFIX = re.compile(r"""(?<=["'(])(?:%s|%s)/""" % (OLD, OLD_ENCODED))


def _digests(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file() and p.name != ".DS_Store"}


def _relink_html(path):
    text = path.read_text(encoding="utf-8")
    new, n = _HTML_PREFIX.subn(DATA + "/", text)
    if OLD + "/" in new or OLD_ENCODED + "/" in new:
        raise RuntimeError(f"{path}: 경로가 아닌 자리에 {OLD}/ 가 남았다")
    if n:
        path.write_text(new, encoding="utf-8")
    return n


def _old_prefix_to_new(text):
    """md 링크 대상의 옛 접두만 `.pack/` 으로 — 왕복 검사의 기준."""
    def one(m):
        target = m.group(2)
        for old in (OLD + "/", OLD_ENCODED + "/"):
            if target.startswith(old):
                target = DATA + "/" + target[len(old):]
        return m.group(1) + target + m.group(3)
    return _TARGET.sub(one, text)


def plan(folder):
    if (folder / DATA).exists():
        return None
    if not (folder / OLD).is_dir():
        raise RuntimeError(f"{folder.name}: {OLD}/ 도 {DATA}/ 도 없다")
    return sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix == ".md")


def migrate(folder, apply):
    folder = Path(folder)
    mds = plan(folder)
    if mds is None:
        return [f"{folder.name}: 이미 {DATA}/ 가 있다 — 건너뜀"]
    lines = [f"{folder.name}: {OLD}/ → {DATA}/, md {len(mds)}개 이동 ({', '.join(mds)})"]
    if not apply:
        return lines
    before = _digests(folder)
    (folder / OLD).rename(folder / DATA)
    htmls = sorted(folder.glob("*.html")) + sorted((folder / DATA / "problem-explanations").rglob("*.html"))
    relinked = sum(_relink_html(p) for p in htmls)
    for name in mds:
        source = folder / name
        text = source.read_text(encoding="utf-8")
        new = to_data_frame(text, prefixes=(OLD + "/",))
        if to_root_frame(new) != _old_prefix_to_new(text):
            raise RuntimeError(f"{folder.name}/{name}: 링크 왕복이 원본과 다르다")
        target = folder / DATA / name
        if target.exists():
            raise RuntimeError(f"{folder.name}/{name}: {DATA}/ 에 같은 이름이 있다")
        target.write_text(new, encoding="utf-8")
        source.unlink()
    manifest_path = folder / DATA / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    def moved(p):
        if p.startswith(OLD + "/"):
            return DATA + p[len(OLD):]
        return DATA + "/" + p if p in mds else p
    manifest["generated_files"] = sorted(moved(p) for p in manifest.get("generated_files", []))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    after = _digests(folder)
    renamed = {(DATA + k[len(OLD):] if k.startswith(OLD + "/") else DATA + "/" + k if k in mds else k): v
               for k, v in before.items()}
    if set(renamed) != set(after):
        raise RuntimeError(f"{folder.name}: 옮긴 뒤 파일 목록이 다르다: {sorted(set(renamed) ^ set(after))[:5]}")
    text_kinds = {".html", ".md"}
    changed = [k for k in after if renamed[k] != after[k]
               and Path(k).suffix not in text_kinds and k != DATA + "/manifest.json"]
    if changed:
        raise RuntimeError(f"{folder.name}: 내용이 바뀌면 안 되는 파일이 바뀌었다: {changed[:5]}")
    errors = check_pack(folder)
    if errors:
        raise RuntimeError(f"{folder.name}: 검사 실패\n" + "\n".join(errors))
    lines.append(f"{folder.name}: HTML 경로 {relinked}곳, 파일 {len(after)}개, 검사 통과")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("experiments", nargs="*", help="실험05 처럼. 비우면 복습노트의 실험 폴더 전부")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    names = a.experiments or sorted(p.name for p in NOTES.iterdir() if p.is_dir() and re.fullmatch(r"실험\d{2}", p.name))
    for name in names:
        for line in migrate(NOTES / name, a.apply):
            print(line)
    if not a.apply:
        print("dry-run — 실제로 옮기려면 --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
