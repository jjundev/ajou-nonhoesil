"""Journaled, verified uploads to new Notion report pages.

A failed operation is resumed, never replaced with another page. The journal
contains IDs, hashes and source text, but never raw remote responses or signed URLs.
"""
import argparse
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

from . import config, md, notion, notion_images as ni, validate

SCHEMA = "notion-image-sync/v1"


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as f:
            name = f.name
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def save(j):
    atomic_text(Path(j["journal"]), json.dumps(j, ensure_ascii=False, indent=2) + "\n")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@contextmanager
def kind_lock(output_dir, kind):
    """Kernel-released process lock; a dead owner cannot leave a stale lock."""
    folder = Path(output_dir).resolve() / ".notion-sync"
    folder.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(kind.encode()).hexdigest()[:16]
    with (folder / f"{name}.lock").open("a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise notion.NotionError("같은 output/종류의 업로드가 이미 실행 중입니다") from None
        try:
            yield folder / f"{name}.active.json"
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _body(source, title):
    _, body = md.split_frontmatter(source.read_text(encoding="utf-8"))
    if body.startswith(f"# {title}\n"):
        body = body[len(f"# {title}\n"):].lstrip("\n")
    return body


def _fingerprint(tree, excluded):
    """Hash only immutable body content, hierarchy and ordering; omit volatile fields."""
    def stable(value):
        if isinstance(value, list):
            return [stable(v) for v in value]
        if isinstance(value, dict):
            return {k: stable(v) for k, v in value.items()
                    if k not in {"expiry_time", "created_time", "last_edited_time",
                                 "created_by", "last_edited_by", "request_id"}}
        if isinstance(value, str):
            return notion.strip_asset_signatures(value)
        return value
    def project(blocks):
        return [{"id": b["id"], "type": b["type"], "body": stable(b.get(b["type"], {})),
                 "children": project(b.get("_children", []))}
                for b in blocks if b["id"] not in excluded]
    return hashlib.sha256(json.dumps(project(tree), sort_keys=True,
                         ensure_ascii=False).encode()).hexdigest()


def _check_body(j, tree):
    excluded = {p["marker_id"] for p in j["placements"]}
    excluded.update(p["block_id"] for p in j["placements"] if p["block_id"])
    if _fingerprint(tree, excluded) != j["body_fingerprint"]:
        raise notion.NotionError("원격 본문이 작업 도중 변경되었습니다; 자동 변경을 중단합니다")


def _content(image, block, token):
    for attempt in range(2):
        try:
            value = block["image"]
            url = value.get("file", value.get("external", {})).get("url")
            if not url:
                raise notion.NotionError("이미지 다운로드 URL이 없습니다")
            return ni.verify_image_content(image.path, url)
        except notion.NotionError:
            if attempt:
                raise
            block = notion._request("GET", f"/blocks/{block['id']}", token)


def _assert_content(image, block, token):
    result = _content(image, block, token)
    if not result["ok"]:
        raise notion.NotionError(f"이미지 {image.index}: 원본 내용과 다릅니다")
    return result


def _intent(j, name):
    j["intent"] = name
    save(j)


def _page_title(j, temporary=False):
    title = f"{j['title']} v{j['version']}"
    return title + f" [sync:{j['operation_id']}]" if temporary else title


def _find_page(j, token):
    candidates = [b for b in notion.list_children(j["parent_id"], token)
                  if b["type"] == "child_page" and
                  b["child_page"].get("title") == _page_title(j, temporary=True)]
    if len(candidates) != 1:
        raise notion.NotionError("생성 응답이 불명확합니다; 고유한 작업 페이지를 찾지 못했습니다")
    page_id = candidates[0]["id"]
    tree = notion.read_block_tree(page_id, token)
    witnesses = [b for b in tree if b["type"] == "paragraph"
                 and ni.block_text(b) == j["witness"]]
    if len(witnesses) != 1:
        raise notion.NotionError("작업 페이지의 본문 소유권 표식을 확인하지 못했습니다")
    return {"page_id": page_id, "url": f"https://www.notion.so/{page_id.replace('-', '')}"}


def _upload(j, index, image, token):
    item = j["images"][index]
    uid = item.get("upload_id")
    if uid:
        remote = notion.retrieve_file_upload(uid, token)
        if remote.get("status") == "uploaded" and not remote.get("archived"):
            return uid
        if remote.get("status") == "expired" or remote.get("archived"):
            uid = None
        elif remote.get("status") != "pending":
            raise notion.NotionError("알 수 없는 파일 업로드 상태")
    if not uid:
        _intent(j, f"create_upload:{index}")
        remote = notion.create_file_upload(image.path, token)
        uid = item["upload_id"] = remote["id"]
        save(j)
    _intent(j, f"send_upload:{index}")
    notion.send_file_upload(uid, image.path, token)
    save(j)
    return uid


def _reconcile_insert(j, index, image, tree, token):
    """Only adopt a unique image between this marker and its original successor."""
    p = j["placements"][index]
    ids = [b["id"] for b in tree]
    if p["marker_id"] not in ids:
        raise notion.NotionError("미확정 이미지의 표식이 사라졌습니다")
    start = ids.index(p["marker_id"]) + 1
    successor = p["successor_id"]
    if successor is not None and successor not in ids:
        raise notion.NotionError("이미지 다음 본문 경계가 사라졌습니다")
    end = ids.index(successor) if successor else len(ids)
    candidates = tree[start:end]
    if not candidates:
        return
    if len(candidates) != 1 or candidates[0]["type"] != "image":
        raise notion.NotionError("삽입 응답 유실 후 후보가 모호합니다")
    candidate = candidates[0]
    if ni.plain_text(candidate["image"].get("caption", [])) != image.caption:
        raise notion.NotionError("삽입 후보의 캡션이 다릅니다")
    j["images"][index]["verification"] = _assert_content(image, candidate, token)
    p["block_id"] = candidate["id"]
    save(j)


def _verify(j, plan, tree, token):
    positions = [ni.ImagePlacement(**{k: p[k] for k in ni.ImagePlacement.__dataclass_fields__})
                 for p in j["placements"]]
    findings = ni.verify_placements(plan, positions, tree)
    if findings:
        raise notion.NotionError("; ".join(f.message for f in findings))
    _check_body(j, tree)
    blocks = {b["id"]: b for b in ni.walk(tree)}
    for image, position in zip(plan.images, positions):
        j["images"][image.index]["verification"] = _assert_content(
            image, blocks[position.block_id], token)


def _run(j, token):
    if j["status"] == "complete":
        return _result(j)
    try:
        source = Path(j["source"])
        plan = ni.plan_images(source, operation_id=j["operation_id"], body=_body(source, j["title"]))
        if (plan.source_sha256 != j["source_sha256"] or
                [i.sha256 for i in plan.images] != [i["sha256"] for i in j["images"]]):
            raise notion.NotionError("로컬 보고서/이미지가 작업 도중 변경되었습니다")
        if not j.get("page_id"):
            if j.get("intent") == "create_page":
                page = _find_page(j, token)
            else:
                _intent(j, "create_page")
                page = notion.push_markdown(
                    plan.markdown + "\n\n" + j["witness"], j["parent_id"], token,
                    title=_page_title(j, temporary=True))
            j.update(page)
            j["status"] = "page_created"
            save(j)
        tree = notion.read_block_tree(j["page_id"], token)
        # The operation witness is needed for uncertain page creation, then removed
        # before recording boundaries, including document-first/document-last images.
        witnesses = [b for b in tree if ni.block_text(b) == j["witness"]]
        if witnesses:
            if len(witnesses) != 1 or witnesses[0]["type"] != "paragraph":
                raise notion.NotionError("소유권 표식이 잘못되었습니다")
            _intent(j, "archive_witness")
            notion.archive_block(witnesses[0]["id"], token)
            tree = notion.read_block_tree(j["page_id"], token)
        if "placements" not in j:
            positions = ni.locate_markers(plan, tree)
            ids = [b["id"] for b in tree]
            j["placements"] = []
            for p in positions:
                obj = asdict(p)
                k = ids.index(p.marker_id) + 1
                obj["successor_id"] = ids[k] if k < len(ids) else None
                j["placements"].append(obj)
            j["body_fingerprint"] = _fingerprint(tree, {p.marker_id for p in positions})
            j["status"] = "markers_located"
            save(j)
        # Adopt writes whose successful response was never journaled.
        for image, p in zip(plan.images, j["placements"]):
            if not p["block_id"] and j["images"][image.index].get("insert_intended"):
                _reconcile_insert(j, image.index, image, tree, token)
        _check_body(j, tree)
        j["status"] = "inserting"
        save(j)
        for image, p in zip(plan.images, j["placements"]):
            tree = notion.read_block_tree(j["page_id"], token)
            _check_body(j, tree)
            blocks = {b["id"]: b for b in ni.walk(tree)}
            if not p["block_id"]:
                uid = _upload(j, image.index, image, token)
                j["images"][image.index]["insert_intended"] = True
                _intent(j, f"insert:{image.index}")
                inserted = notion.append_after(p["parent_id"], p["marker_id"], [{
                    "object": "block", "type": "image", "image": {"type": "file_upload",
                        "file_upload": {"id": uid}, "caption": notion.rich_text(image.caption)}
                }], token)
                if len(inserted) != 1:
                    raise notion.NotionError("삽입 응답에 이미지가 정확히 하나가 아닙니다")
                p["block_id"] = inserted[0]["id"]
                save(j)
                tree = notion.read_block_tree(j["page_id"], token)
                blocks = {b["id"]: b for b in ni.walk(tree)}
            block = blocks.get(p["block_id"])
            if not block or block["type"] != "image":
                raise notion.NotionError("작업 이미지 블록이 사라졌습니다")
            if ni.plain_text(block["image"].get("caption", [])) != image.caption:
                raise notion.NotionError("작업 이미지 캡션이 변경되었습니다")
            j["images"][image.index]["verification"] = _assert_content(image, block, token)
            # Check exact immediate location before deleting the source marker.
            ids = [b["id"] for b in tree]
            if p["marker_id"] in ids:
                marker_pos = ids.index(p["marker_id"])
                if ids[marker_pos + 1:marker_pos + 2] != [p["block_id"]]:
                    raise notion.NotionError("표식 바로 뒤에 이미지가 없습니다")
                _intent(j, f"archive_marker:{image.index}")
                notion.archive_block(p["marker_id"], token)
            save(j)
        tree = notion.read_block_tree(j["page_id"], token)
        _verify(j, plan, tree, token)
        pulled = notion.pull_markdown(j["page_id"], token)
        # Supply the explicit page title on both sides: the legacy checker
        # exempts an absorbed first heading, which must not exempt a body section.
        heading = f"# {j['title']}\n\n"
        findings = validate.check_notion_roundtrip(
            heading + _body(source, j["title"]), heading + pulled)
        if any(f.level == "error" for f in findings):
            raise notion.NotionError("본문 왕복 구조 검사 실패")
        j["status"] = "verified"
        save(j)
        # No baseline or completed record is written until all checks above pass.
        record = {"source": source.name, "version": j["version"]}
        baseline = notion.history_path(j["output_dir"], record)
        j["baseline"] = str(baseline)
        _intent(j, "write_baseline")
        if baseline.exists() and baseline.read_text(encoding="utf-8") != pulled:
            raise notion.NotionError("기존 baseline과 검증 결과가 다릅니다")
        atomic_text(baseline, pulled)
        j["status"] = "baseline_written"
        save(j)
        _intent(j, "finalize_title")
        notion._request("PATCH", f"/pages/{j['page_id']}", token, {
            "properties": {"title": {"type": "title", "title": notion.rich_text(_page_title(j))}}})
        # Different report kinds share one history file: serialize its read/append.
        with kind_lock(j["output_dir"], "__records__"):
            records = notion.load_records(j["output_dir"])
            found = [r for r in records if r["page_id"] == j["page_id"]]
            if found:
                if len(found) != 1 or found[0]["version"] != j["version"]:
                    raise notion.NotionError("완료 레코드 충돌")
            else:
                if notion.next_version(j["output_dir"], j["kind"]) != j["version"]:
                    raise notion.NotionError("예약된 버전과 이력이 다릅니다")
                _intent(j, "append_record")
                notion.append_record(j["output_dir"], j["kind"], j["page_id"], j["url"],
                                     source.name, datetime.now().astimezone().isoformat())
        j["status"] = "record_written"
        save(j)
        j["status"] = "complete"
        j["intent"] = None
        save(j)
        return _result(j)
    except Exception as e:
        # Raw HTTP responses and signed URLs must never be persisted in the journal.
        detail = str(e) if isinstance(e, notion.NotionError) else type(e).__name__
        detail = notion.strip_asset_signatures(detail).replace(token, "[redacted]")
        raise notion.NotionError(
            f"{detail}; 상태={j['status']}; resume --journal {j['journal']}") from None


def _result(j):
    return {k: j[k] for k in ("operation_id", "page_id", "url", "version", "status", "baseline")} | {
        "image_count": len(j["images"]), "verification": "position/caption/content/roundtrip passed"}


def sync_report(source, parent_id, token, *, kind, title, work_dir, output_dir):
    source, work_dir, output_dir = Path(source).resolve(), Path(work_dir).resolve(), Path(output_dir).resolve()
    if kind not in ("예비보고서", "결과보고서"):
        raise notion.NotionError("예비·결과보고서만 업로드할 수 있습니다")
    with kind_lock(output_dir, kind) as active:
        if active.exists():
            previous = load(active)["journal"]
            if not Path(previous).exists() or load(previous)["status"] != "complete":
                raise notion.NotionError(f"미완료 업로드를 먼저 재개하세요: resume --journal {previous}")
        if (work_dir / "journal.json").exists():
            raise notion.NotionError("기존 journal을 덮어쓰지 않습니다; resume을 사용하세요")
        findings = validate.check_notion_markdown(source)
        errors = [f.message for f in findings if f.level == "error"]
        if errors:
            raise notion.NotionError("; ".join(errors))
        op = uuid.uuid4().hex
        plan = ni.plan_images(source, operation_id=op, body=_body(source, title))
        j = {"schema": SCHEMA, "journal": str(work_dir / "journal.json"), "operation_id": op,
             "source": str(source), "source_sha256": plan.source_sha256, "parent_id": parent_id,
             "kind": kind, "title": title, "output_dir": str(output_dir),
             "version": notion.next_version(output_dir, kind), "status": "planned",
             "intent": None, "witness": f"NOTIONSYNC-{op}",
             "images": [{"index": i.index, "sha256": i.sha256, "caption": i.caption,
                         "path": str(i.path), "marker": i.marker} for i in plan.images]}
        save(j)
        atomic_text(active, json.dumps({"journal": j["journal"]}))
        return _run(j, token)


def resume_report(journal_path, token):
    j = load(Path(journal_path).resolve())
    if j.get("schema") != SCHEMA or Path(j["journal"]).resolve() != Path(journal_path).resolve():
        raise notion.NotionError("지원하지 않거나 위치가 달라진 journal입니다")
    with kind_lock(j["output_dir"], j["kind"]) as active:
        if active.exists() and load(active)["journal"] != j["journal"] and j["status"] != "complete":
            raise notion.NotionError("다른 작업이 해당 output/종류를 소유합니다")
        return _run(j, token)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    push = commands.add_parser("push")
    push.add_argument("--source", type=Path, required=True)
    push.add_argument("--kind", choices=["예비보고서", "결과보고서"], required=True)
    resume = commands.add_parser("resume")
    resume.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    try:
        token = notion.load_token()
        if args.command == "resume":
            result = resume_report(args.journal, token)
        else:
            from .spec_parser import parse_spec
            source = args.source.resolve()
            exp_dir = source.parent.parent
            expected = config.artifact_path(exp_dir, args.kind, ".md").resolve()
            if source != expected:
                raise notion.NotionError(f"보고서 표준 경로가 아닙니다: {expected}")
            spec = parse_spec(exp_dir / "체크리스트/명세.md")
            title = config.document_title(spec.experiment, spec.title, args.kind)
            info = config.load_course_info(config.find_project_root(source))
            parent = info.get("notion_parent_page_id")
            if not parent:
                raise notion.NotionError("과목정보의 notion_parent_page_id가 비어 있습니다")
            result = sync_report(source, parent, token, kind=args.kind, title=title,
                work_dir=source.parent / ".notion-sync" / uuid.uuid4().hex,
                output_dir=source.parent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (notion.NotionError, OSError, ValueError) as e:
        parser.exit(1, f"{e}\n")


if __name__ == "__main__":
    main()
