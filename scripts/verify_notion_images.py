"""Explicit live Notion probes. Writes only dedicated test pages and work-dir files."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import uuid

from .lab import config, notion


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def parent_id():
    return config.load_course_info(config.find_project_root(Path(__file__)))["notion_parent_page_id"]


def text_of(block):
    return "".join(x.get("plain_text", x.get("text", {}).get("content", ""))
                   for x in block.get(block["type"], {}).get("rich_text", []))


def fixtures(work):
    from PIL import Image
    for name, color in [("한 글 (1).png", "red"), ("다른 그림.jpg", "blue")]:
        Image.new("RGB", (24, 16), color).save(work / name)


def probe(work):
    work.mkdir(parents=True, exist_ok=False)
    fixtures(work)
    token, op = notion.load_token(), uuid.uuid4().hex
    state = {"operation_id": op, "intent": "create_page", "checks": {}}
    path = work / "probe.json"
    write_json(path, state)
    markers = [f"NOTIONIMAGE-{op}-{i:04d}" for i in range(4)]
    body = (f"{markers[0]}\n\n# 한글 시험\n\n| A | B |\n|---|---|\n| 0 | 1 |\n\n"
            "$$\nQ=A+B\n$$\n\n" + markers[1] + "\n\n" + markers[2] +
            "\n\n끝 경계\n\n" + markers[3])
    page = notion.push_markdown(body, parent_id(), token,
                               title=f"[이미지 API 시험] {op}")
    state.update(page)
    write_json(path, state)
    blocks = notion.list_children(page["page_id"], token)
    found = {m: [b for b in blocks if b["type"] == "paragraph" and text_of(b) == m]
             for m in markers}
    assert all(len(bs) == 1 for bs in found.values()), "marker not a unique standalone paragraph"
    state["checks"]["standalone_markers"] = "pass"
    state["checks"]["table"] = "pass" if any(b["type"] == "table" for b in blocks) else "fail"
    state["checks"]["equation"] = "pass" if any(b["type"] == "equation" for b in blocks) else "fail"
    original_ids = [b["id"] for b in blocks if text_of(b) not in markers]
    image_ids = []
    for i, marker in enumerate(markers):
        state["intent"] = f"upload_and_insert_{i}"
        write_json(path, state)
        local = work / "한 글 (1).png"
        upload = notion.create_file_upload(local, token)
        state["upload_id"] = upload["id"]
        write_json(path, state)
        notion.send_file_upload(upload["id"], local, token)
        caption = f"한글 캡션 ({i})"
        inserted = notion.append_after(page["page_id"], found[marker][0]["id"], [{
            "object": "block", "type": "image", "image": {"type": "file_upload",
            "file_upload": {"id": upload["id"]}, "caption": notion.rich_text(caption)}}], token)
        block_id = inserted[0]["id"]
        image_ids.append(block_id)
        state["image_ids"] = image_ids
        state["intent"] = f"verify_then_archive_{i}"
        write_json(path, state)
        remote = notion._request("GET", f"/blocks/{block_id}", token)
        assert "".join(x.get("plain_text", "") for x in remote["image"]["caption"]) == caption
        with urllib.request.urlopen(remote["image"]["file"]["url"], timeout=120) as r:
            actual = r.read()
        assert actual == local.read_bytes()
        notion.archive_block(found[marker][0]["id"], token)
    final = notion.list_children(page["page_id"], token)
    expected = []
    for block in blocks:
        if text_of(block) in markers:
            expected.append(image_ids[markers.index(text_of(block))])
        else:
            expected.append(block["id"])
    assert [b["id"] for b in final] == expected
    assert [b["id"] for b in final if b["type"] != "image"] == original_ids
    state["checks"].update(position="pass", captions="pass", content_sha256="pass", marker_removal="pass")
    assert all(v == "pass" for v in state["checks"].values())
    state["intent"] = "complete"
    write_json(path, state)
    print(json.dumps({"url": page["url"], "checks": state["checks"]}, ensure_ascii=False))
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["probe"])
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.work_dir.is_absolute():
        parser.error("--work-dir must be absolute")
    probe(args.work_dir)


if __name__ == "__main__":
    main()
