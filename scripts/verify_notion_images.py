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
            "$$Q=A+B$$\n\n" + markers[1] + "\n\n" + markers[2] +
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


class DropAfter:
    """Lose exactly one successful response; the actual server write happens first."""
    def __init__(self, transport, predicate):
        self.transport, self.predicate, self.fired = transport, predicate, False

    def __call__(self, req, token, timeout=120):
        result = self.transport(req, token, timeout)
        if not self.fired and self.predicate(req):
            self.fired = True
            import urllib.error
            raise urllib.error.URLError("injected response loss after remote success")
        return result


def _case_source(work, large=False):
    work.mkdir(parents=True, exist_ok=True)
    fixtures(work)
    source = work / "source.md"
    if not source.exists():
        body = "![](한 글 (1).png)\n\n# 본문\n\n"
        if large:
            body += "\n\n".join(f"페이지네이션 확인 문단 {i:03d}" for i in range(105)) + "\n\n"
            body += "| A | B |\n|---|---|\n| 0 | 1 |\n\n$$Q=A+B$$\n\n"
            body += f"![{'한글 긴 캡션 ' * 300}](다른 그림.jpg)\n\n"
        body += "끝 경계\n\n![반복 캡션](한 글 (1).png)\n![반복 캡션](한 글 (1).png)"
        source.write_text(body)
    return source


def _execute_case(case, scenario, token):
    from contextlib import ExitStack
    from unittest.mock import patch
    from .lab import notion_sync as ns
    journal = case / "output/.notion-sync/operation/journal.json"
    if journal.exists():
        return ns.resume_report(journal, token), {"resumed_existing_journal": True}
    source = _case_source(case, large=scenario == "happy_path")
    real_transport = notion._open_request
    evidence = {}
    def is_target(req):
        from urllib.parse import urlsplit
        path = urlsplit(req.full_url).path
        if scenario == "page_create_response_lost":
            return req.method == "POST" and path.endswith("/pages")
        if scenario == "insert_response_lost":
            return req.method == "PATCH" and path.endswith("/children")
        if scenario == "archive_response_lost":
            return req.method == "DELETE" and journal.exists() and ns.load(journal)["status"] == "inserting"
        return False
    drop = DropAfter(real_transport, is_target)
    atomic = ns.atomic_text
    baseline_failed = False
    def failing_baseline(path, text):
        nonlocal baseline_failed
        if "baseline" in Path(path).name and not baseline_failed:
            baseline_failed = True
            raise OSError("injected baseline storage failure")
        return atomic(path, text)
    with ExitStack() as stack:
        if "response_lost" in scenario:
            stack.enter_context(patch.object(notion, "_open_request", drop))
        if scenario == "baseline_failure":
            stack.enter_context(patch.object(ns, "atomic_text", failing_baseline))
        try:
            result = ns.sync_report(source, parent_id(), token, kind="예비보고서",
                title=f"[이미지 검증 완료] {scenario} {case.parent.name}",
                work_dir=journal.parent, output_dir=case / "output")
        except notion.NotionError:
            if scenario == "happy_path" or not (drop.fired or baseline_failed):
                raise
            evidence["failure_observed"] = True
        else:
            if scenario != "happy_path":
                raise AssertionError("failure injection did not trigger")
            return result, evidence
    assert drop.fired or baseline_failed
    before = ns.load(journal)
    evidence.update(before_page_id=before.get("page_id"), before_version=before["version"],
                    before_status=before["status"], response_dropped=drop.fired,
                    baseline_failed=baseline_failed)
    result = ns.resume_report(journal, token)
    if before.get("page_id"):
        assert result["page_id"] == before["page_id"]
    assert result["version"] == before["version"]
    return result, evidence


def _crash_worker(case):
    import os
    from unittest.mock import patch
    from urllib.parse import urlsplit
    from .lab import notion_sync as ns
    source = _case_source(case)
    token = notion.load_token()
    real = notion._open_request
    def crash(req, token, timeout=120):
        result = real(req, token, timeout)
        if req.method == "PATCH" and urlsplit(req.full_url).path.endswith("/children"):
            os._exit(73)  # Successful server insert, no response/journal/lock cleanup.
        return result
    with patch.object(notion, "_open_request", crash):
        ns.sync_report(source, parent_id(), token, kind="예비보고서",
            title=f"[이미지 검증 완료] process_crash {case.parent.name}",
            work_dir=case / "output/.notion-sync/operation", output_dir=case / "output")
    raise AssertionError("crash point not reached")


def _assert_completed_case(case, result, token):
    from .lab import notion_sync as ns, notion_images as ni
    j = ns.load(case / "output/.notion-sync/operation/journal.json")
    plan = ni.plan_images(Path(j["source"]), operation_id=j["operation_id"])
    tree = notion.read_block_tree(result["page_id"], token)
    ns._verify(j, plan, tree, token)
    assert len([b for b in tree if b["type"] == "image"]) == len(plan.images)
    assert len(notion.load_records(case / "output")) == 1
    assert len(list((case / "output").glob("*notion_baseline*"))) == 1
    candidates = [b for b in notion.list_children(j["parent_id"], token)
                  if b["type"] == "child_page" and b["child_page"]["title"] in
                  [ns._page_title(j), ns._page_title(j, temporary=True)]]
    assert len(candidates) == 1 and candidates[0]["id"].replace("-", "") == j["page_id"].replace("-", "")
    return j, plan, tree


def _restore_trial_first_image(j, token):
    """Test-only repair: unarchiving restores at end, so recreate at start instead."""
    from .lab import notion_sync as ns, notion_images as ni
    first = j["placements"][0]
    tree = notion.read_block_tree(j["page_id"], token)
    if any(b["id"] == first["block_id"] for b in tree):
        notion.archive_block(first["block_id"], token)
    known = {b["id"] for b in notion.read_block_tree(j["page_id"], token)}
    notion._request("PATCH", f"/blocks/{j['page_id']}/children", token, {
        "children": [{"object": "block", "type": "image", "image": {
            "type": "file_upload", "file_upload": {"id": j["images"][0]["upload_id"]},
            "caption": notion.rich_text(j["images"][0]["caption"])}}],
        "position": {"type": "start"}})
    current = notion.read_block_tree(j["page_id"], token)
    added = [b for b in current if b["id"] not in known]
    assert len(added) == 1 and added[0]["type"] == "image"
    first["block_id"] = added[0]["id"]
    ns.save(j)


def _corruption_checks(case, result, token):
    from dataclasses import replace
    from .lab import notion_sync as ns, notion_images as ni
    j, plan, tree = _assert_completed_case(case, result, token)
    first = j["placements"][0]
    original_id = first["block_id"]
    caption = plan.images[0].caption
    def verify_rejects(expected):
        try:
            ns._verify(j, plan, notion.read_block_tree(j["page_id"], token), token)
        except notion.NotionError as error:
            assert expected in str(error), f"unexpected verification failure: {type(error).__name__}"
            return
        raise AssertionError("corruption was accepted")
    # Caption mutation on an operation-owned image, then restore.
    notion._request("PATCH", f"/blocks/{original_id}", token,
                    {"image": {"caption": notion.rich_text("잘못된 캡션")}})
    verify_rejects("캡션 불일치")
    notion._request("PATCH", f"/blocks/{original_id}", token,
                    {"image": {"caption": notion.rich_text(caption)}})
    # Replace content using a known different uploaded JPEG, then restore.
    wrong_uid = j["images"][1]["upload_id"]
    original_uid = j["images"][0]["upload_id"]
    notion._request("PATCH", f"/blocks/{original_id}", token, {
        "image": {"file_upload": {"id": wrong_uid}}})
    verify_rejects("원본 내용과 다릅니다")
    notion._request("PATCH", f"/blocks/{original_id}", token, {
        "image": {"file_upload": {"id": original_uid}}})
    # Preserve count/caption/content but move occurrence 0 to another section.
    wrong_after = next(b["id"] for b in tree if b["type"] == "heading_1")
    notion.append_after(j["page_id"], wrong_after, [{
        "object": "block", "type": "image", "image": {"type": "file_upload",
        "file_upload": {"id": original_uid}, "caption": notion.rich_text(caption)}}], token)
    known = {b["id"] for b in tree}
    moved_candidates = [b for b in notion.read_block_tree(j["page_id"], token) if b["id"] not in known]
    assert len(moved_candidates) == 1 and moved_candidates[0]["type"] == "image"
    moved = moved_candidates[0]
    notion.archive_block(original_id, token)
    first["block_id"] = moved["id"]
    current = notion.read_block_tree(j["page_id"], token)
    assert len([b for b in current if b["type"] == "image"]) == len(plan.images)
    verify_rejects("본문 경계/순서")
    notion.archive_block(moved["id"], token)
    first["block_id"] = original_id
    _restore_trial_first_image(j, token)
    ns._verify(j, plan, notion.read_block_tree(j["page_id"], token), token)
    return {"wrong_location_detected": "pass", "caption_mismatch_detected": "pass",
            "content_mismatch_detected": "pass"}


def _image_evidence(j):
    return [{"block_id": p["block_id"], "parent_id": p["parent_id"],
             "before_id": p["before_id"], "after_id": p["after_id"],
             "caption": im["caption"], "verification": im["verification"]}
            for p, im in zip(j["placements"], j["images"])]


def acceptance(work):
    import os
    import subprocess
    import sys
    from datetime import datetime
    from .lab import notion_sync as ns
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    token = notion.load_token()
    result_file = work / "results.json"
    summary = ns.load(result_file) if result_file.exists() else {
        "started_at": datetime.now().astimezone().isoformat(), "checks": {}, "cases": {}}
    write_json(result_file, summary)
    for scenario in ["happy_path", "insert_response_lost", "archive_response_lost",
                     "process_crash", "baseline_failure", "page_create_response_lost"]:
        if summary["checks"].get(scenario) == "pass":
            result = summary["cases"][scenario]["result"]
            if scenario == "happy_path":
                summary["checks"].update(_corruption_checks(work / scenario, result, token))
            j, _, _ = _assert_completed_case(work / scenario, result, token)
            summary["cases"][scenario]["images"] = _image_evidence(j)
            write_json(result_file, summary)
            continue
        case = work / scenario
        if scenario == "process_crash":
            journal = case / "output/.notion-sync/operation/journal.json"
            if not journal.exists():
                child = subprocess.run([sys.executable, "-m", "scripts.verify_notion_images",
                    "_worker", "--work-dir", str(case)], capture_output=True, text=True)
                assert child.returncode == 73, f"crash worker exited {child.returncode}"
            before = ns.load(journal)
            result = ns.resume_report(journal, token)
            assert result["page_id"] == before["page_id"] and result["version"] == before["version"]
            evidence = {"exit_code": 73, "before_page_id": before["page_id"],
                        "before_version": before["version"], "before_status": before["status"]}
        else:
            result, evidence = _execute_case(case, scenario, token)
        j, plan, tree = _assert_completed_case(case, result, token)
        if scenario == "happy_path":
            assert len(tree) > 100
            summary["checks"].update(_corruption_checks(case, result, token))
        summary["cases"][scenario] = {"result": result, "evidence": evidence,
            "block_count": len(tree), "images": _image_evidence(
                ns.load(case / "output/.notion-sync/operation/journal.json"))}
        summary["checks"][scenario] = "pass"
        write_json(result_file, summary)
        print(f"{scenario}: pass — {result['url']}", flush=True)
    # Check only artifacts produced by this harness; never persist the token or URLs.
    for path in work.rglob("*"):
        if path.is_file() and path.suffix in (".json", ".md"):
            content = path.read_text()
            assert token not in content
            assert "X-Amz-Signature=" not in content and "X-Amz-Security-Token=" not in content
    summary["checks"].update(no_duplicate_pages_or_images="pass", no_secret_persistence="pass")
    summary["completed_at"] = datetime.now().astimezone().isoformat()
    write_json(result_file, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["probe", "acceptance", "_worker"])
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.work_dir.is_absolute():
        parser.error("--work-dir must be absolute")
    {"probe": probe, "acceptance": acceptance, "_worker": _crash_worker}[args.command](args.work_dir)


if __name__ == "__main__":
    main()
