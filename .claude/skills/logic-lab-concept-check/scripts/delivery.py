"""Stage, check, and publish one concept check without rebuilding its lab pack."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

import _paths
import blind
import build
from content import DATA, SRC_NAME, ContentError, experiment_number, folder_name, json_file, quiz_name, read_pack, write_json
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.manifest import VENDOR_DIR

EXPECTED_BROWSER_RUNS = {f"{size} {theme}" for size in ("1280x900", "375x812") for theme in ("light", "dark")}
EVIDENCE_FILES = ("objectives.json", "items.json", "blind-ledger.json", "browser.json")


def paths(root, number, run):
    target = Path(root).resolve() / "복습노트" / folder_name(number)
    stage = Path(run).resolve() / "복습노트" / target.name
    if stage.is_relative_to(target) or target.is_relative_to(stage):
        raise ContentError("학습팩과 다른 임시 실행 폴더를 지정하세요")
    return target, stage


def source_dir(folder):
    return folder / DATA / SRC_NAME


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def basis(pack):
    return {p.relative_to(pack.folder).as_posix(): digest(p)
            for p in (pack.folder / DATA / "manifest.json", pack.note, pack.note_md, pack.questions)}


def prepare(root, number, run):
    target, stage = paths(root, number, run)
    pack = read_pack(target)
    vendor = target.parent / VENDOR_DIR
    if not vendor.is_dir():
        raise ContentError(f"학습팩의 오프라인 자원이 없어요: {vendor}")
    run = Path(run).resolve()
    run.mkdir(parents=True, exist_ok=False)
    shutil.copytree(vendor, stage.parent / VENDOR_DIR)
    shutil.copytree(target, stage, ignore=lambda path, names: {
        name for name in names
        if (Path(path) == target and name == quiz_name(number))
        or (Path(path) == target / DATA and name == SRC_NAME)
    })
    if basis(read_pack(stage)) != basis(pack):
        raise ContentError("복사 중 학습팩 근거가 바뀌었어요. 새 실행 폴더에서 다시 시작하세요")
    src = source_dir(stage)
    src.mkdir()
    write_json(run / "basis.json", basis(pack))
    return src


def verify_candidate(stage):
    src = source_dir(stage)
    html, expected = build.render_page(src)
    if not html.is_file() or html.read_bytes() != expected.encode("utf-8"):
        raise ContentError("현재 원고로 HTML을 다시 빌드하세요")
    problems = blind.status(src, src / "blind-ledger.json")
    if problems:
        raise ContentError("블라인드 풀이 미통과\n" + "\n".join(problems))
    browser = json_file(src / "browser.json")
    runs = browser.get("runs", [])
    count = len(json_file(src / "items.json")["items"])
    if (browser.get("status") != "pass" or browser.get("sha256") != digest(html)
            or browser.get("failures") != [] or len(runs) != len(EXPECTED_BROWSER_RUNS)
            or {row.get("label") for row in runs} != EXPECTED_BROWSER_RUNS
            or any(row.get("failures") != [] or row.get("external_blocked") != []
                   or row.get("detail") != dict(items=count, items_checked=count, hints_checked=count)
                   for row in runs)):
        raise ContentError("현재 HTML의 오프라인 브라우저 검사 네 조합이 필요해요")
    errors = check_pack(stage)
    if errors:
        raise ContentError("학습팩 검사 미통과\n" + "\n".join(errors))
    return src


def publish(root, number, run):
    target, stage = paths(root, number, run)
    staged_src = verify_candidate(stage)
    staged_pack = read_pack(stage)
    current = read_pack(target)
    if basis(staged_pack) != basis(current) or basis(current) != json_file(Path(run) / "basis.json"):
        raise ContentError("검토 중 학습팩 근거가 바뀌었어요. 새 원고를 검증하세요")
    for relative in ("pretendard/pretendard.css", "katex/katex.min.css",
                     "katex/katex.min.js", "katex/auto-render.min.js"):
        if digest(stage.parent / VENDOR_DIR / relative) != digest(target.parent / VENDOR_DIR / relative):
            raise ContentError(f"검토 중 오프라인 자원이 바뀌었어요: {relative}")
    destination = target / quiz_name(number)
    final_src = source_dir(target)
    if any(p.is_symlink() for p in (target, target / DATA, destination, final_src)):
        raise ContentError("확인문제 대상에 심볼릭 링크가 있어요")
    if final_src.exists() and not final_src.is_dir():
        raise ContentError(f"자료 위치가 폴더가 아니에요: {final_src}")
    if destination.exists() and not destination.is_file():
        raise ContentError(f"확인문제 위치가 파일이 아니에요: {destination}")

    backup = None
    with tempfile.TemporaryDirectory(prefix=".concept-check-", dir=target) as temporary:
        pending = Path(temporary)
        previous = pending / "previous"
        new_src = pending / SRC_NAME
        if final_src.exists():
            backup = Path(tempfile.mkdtemp(prefix="previous-", dir=run))
            shutil.copytree(final_src, backup / SRC_NAME)
        if destination.exists():
            if backup is None:
                backup = Path(tempfile.mkdtemp(prefix="previous-", dir=run))
            shutil.copy2(destination, backup / destination.name)
        new_src.mkdir()
        for name in EVIDENCE_FILES:
            shutil.copy2(staged_src / name, new_src / name)
        pending_html = pending / destination.name
        shutil.copy2(stage / destination.name, pending_html)
        if final_src.exists():
            os.replace(final_src, previous)
        installed_src = False
        try:
            os.replace(new_src, final_src)
            installed_src = True
            os.replace(pending_html, destination)
        except OSError:
            if installed_src:
                os.replace(final_src, new_src)
            if previous.exists():
                os.replace(previous, final_src)
            raise
    return destination, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "build", "publish"))
    parser.add_argument("experiment")
    parser.add_argument("--root", type=Path, default=_paths.REPO)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    try:
        number = experiment_number(args.experiment)
        _, stage = paths(args.root, number, args.run)
        if args.action == "prepare":
            print(prepare(args.root, number, args.run))
        elif args.action == "check":
            source = build.load_source(source_dir(stage))
            print(f"OK · 확인 목표 {len(source['objectives'])}개 · 문항 {len(source['items'])}개")
        elif args.action == "build":
            print(build.build(source_dir(stage)))
        else:
            destination, backup = publish(args.root, number, args.run)
            print(destination)
            if backup:
                print(f"이전 확인문제 백업 {backup}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
