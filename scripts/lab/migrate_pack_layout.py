"""복습노트 실험 폴더의 문서 외 파일을 `자료/` 한 곳으로 옮기고 문서 안 링크를 맞춘다 (1회성).

    python -m scripts.lab.migrate_pack_layout            # 계획만 출력 (dry-run)
    python -m scripts.lab.migrate_pack_layout --apply    # 실제로 옮긴다
    python -m scripts.lab.migrate_pack_layout --apply 실험03 실험05

옮기는 것: assets/ evidence/ figures/ manifest.json authoring-index.json.
문서(.md·.html·.pdf)는 제자리에 둔다. PDF 는 다시 만들지 않는다 — 내용이 같다.
실행 전후로 옮긴 파일의 개수와 SHA256 을 비교하고, 다르면 실패한다.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from scripts.lab import config
from scripts.lab.review_pack.manifest import DATA, data_url, link_data, load_manifest
from scripts.lab.review_pack.workbook_rerender import rerender_workbook
from scripts.lab.review_pack.workbook_render import read_workbook_payload, render_workbook_html
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.html2md import convert_pack

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "복습노트"
MOVE = ("assets", "evidence", "figures", "manifest.json", "authoring-index.json")
_ATTR = re.compile(r"""((?:src|href)=["'])(assets|figures|evidence)/""")
_MD = re.compile(r"""(\]\()(assets|figures|evidence)/""")


def _digests(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file() and p.name != ".DS_Store"}


def _moved_before(folder):
    return {name: digest for name, digest in _digests(folder).items() if name.split("/")[0] in MOVE}


def _relink_text(path, pattern):
    text = path.read_text(encoding="utf-8")
    new = pattern.sub(lambda m: m.group(1) + DATA + "/" + m.group(2) + "/", text)
    if new != text:
        path.write_text(new, encoding="utf-8")
    return new != text


def _relink_payload(path, assets):
    """문제지·해설지 JSON 슬롯 속 그림 링크를 자료/ 기준으로. 이미 그렇다면 아무것도 하지 않는다."""
    data = read_workbook_payload(path)
    for p in data["problems"]:
        for key, value in p["html"].items():
            p["html"][key] = link_data(value)
        for f in p["figures"]:
            if not f["src"].startswith(DATA + "/"):
                f["src"] = data_url(f["src"])
        for h in p["hints"]:
            for key in ("label", "html"):
                h[key] = link_data(h[key])
        if "solution" in p:
            for s in p["solution"]["steps"]:
                s["label"], s["html"] = link_data(s["label"]), link_data(s["html"])
            p["solution"]["answer"] = link_data(p["solution"]["answer"])
    path.write_text(render_workbook_html(data, assets), encoding="utf-8")


def plan(folder):
    return [name for name in MOVE if (folder / name).exists()]


def migrate(folder, apply):
    folder = Path(folder)
    todo = plan(folder)
    if (folder / DATA).exists():
        return [f"{folder.name}: 이미 {DATA}/ 가 있다 — 건너뜀"]
    lines = [f"{folder.name}: 옮길 것 {', '.join(todo) or '없음'}"]
    if not apply or not todo:
        return lines
    before = _moved_before(folder)
    (folder / DATA).mkdir()
    for name in todo:
        (folder / name).rename(folder / DATA / name)
    after = _digests(folder / DATA)
    if before != after:
        raise RuntimeError(f"{folder.name}: 옮긴 뒤 파일 목록·해시가 다르다")
    manifest_path = folder / DATA / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generated_files"] = [
        DATA + "/" + p if p.split("/")[0] in MOVE else p for p in manifest.get("generated_files", [])]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    m = load_manifest(manifest_path)
    base = config.experiment_folder_name(m["experiment"])
    _relink_text(folder / f"{base}_실험설명.html", _ATTR)
    convert_pack(folder / f"{base}_실험설명.html", folder / f"{base}_기출풀이.html", manifest=m)   # 실험설명.md 를 HTML 에서 다시 낸다
    guide = folder / "원문과_저작안내.md"
    if guide.is_file():
        _relink_text(guide, _MD)
    if m.get("review_presentation_version") == 2:
        for kind in ("기출문제", "기출풀이"):
            _relink_payload(folder / f"{base}_{kind}.html", folder / DATA / "assets")
        errors = rerender_workbook(folder)
    else:
        errors = []
    errors += check_pack(folder)
    if errors:
        raise RuntimeError(f"{folder.name}: 검사 실패\n" + "\n".join(errors))
    lines.append(f"{folder.name}: 옮김 {len(before)}개 파일, 검사 통과")
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
