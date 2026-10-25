import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from scripts.lab import notion
from tests.notion_fake import FakeNotion


@pytest.fixture
def setup(tmp_path, monkeypatch):
    fake = FakeNotion()
    monkeypatch.setattr("urllib.request.urlopen", fake)
    source = tmp_path / "report.md"
    Image.new("RGB", (3, 2), "red").save(tmp_path / "a.png")
    source.write_text("# 제목\n\n![](a.png)\n\n본문\n\n![같은 캡션](a.png)\n![같은 캡션](a.png)")
    return fake, source, tmp_path / "out", tmp_path / "out/.notion-sync/op"


def start(setup):
    from scripts.lab.notion_sync import sync_report
    fake, source, out, work = setup
    return sync_report(source, "PARENT", "token", kind="예비보고서", title="제목",
                       work_dir=work, output_dir=out)


def resume(setup):
    from scripts.lab.notion_sync import resume_report
    return resume_report(setup[3] / "journal.json", "token")


def assert_complete(setup, result):
    fake, source, out, work = setup
    assert result["status"] == "complete"
    assert len(fake.pages) == 1
    assert len([b for b in fake.pages[result["page_id"]]["blocks"] if b["type"] == "image"]) == 3
    assert len(notion.load_records(out)) == 1
    assert Path(result["baseline"]).is_file()
    assert "token" not in (work / "journal.json").read_text()


def test_sync_finalizes_only_after_all_checks(setup):
    from scripts.lab import notion_images as ni
    with patch.object(ni, "verify_image_content", return_value={"ok": False}):
        with pytest.raises(notion.NotionError):
            start(setup)
    assert notion.load_records(setup[2]) == []
    assert not list(setup[2].glob("*baseline*"))
    assert_complete(setup, resume(setup))


@pytest.mark.parametrize("event", ["insert", "archive", "page", "send", "upload"])
def test_resume_after_successful_write_lost_response(setup, event):
    setup[0].fail_after = event
    with pytest.raises(notion.NotionError):
        start(setup)
    assert_complete(setup, resume(setup))
    assert setup[0].events.count("page") == 1
    assert setup[0].events.count("insert") == 3


def test_resume_baseline_failure(setup):
    from scripts.lab import notion_sync as ns
    real = ns.atomic_text
    def failure(path, text):
        if "baseline" in Path(path).name:
            raise OSError("disk full")
        return real(path, text)
    with patch.object(ns, "atomic_text", side_effect=failure):
        with pytest.raises(notion.NotionError):
            start(setup)
    assert not notion.load_records(setup[2])
    assert_complete(setup, resume(setup))


def test_resume_record_written_before_journal(setup):
    real = notion.append_record
    def lost(*args, **kwargs):
        real(*args, **kwargs)
        raise OSError("crash after record")
    with patch.object(notion, "append_record", side_effect=lost):
        with pytest.raises(notion.NotionError):
            start(setup)
    assert len(notion.load_records(setup[2])) == 1
    assert_complete(setup, resume(setup))


@pytest.mark.parametrize("target", ["source", "image", "remote"])
def test_source_or_remote_edit_conflict(setup, target):
    setup[0].fail_after = "insert"
    with pytest.raises(notion.NotionError):
        start(setup)
    if target == "source":
        setup[1].write_text(setup[1].read_text() + "\nchanged")
    elif target == "image":
        Image.new("RGB", (3, 2), "blue").save(setup[1].parent / "a.png")
    else:
        blocks = next(iter(setup[0].pages.values()))["blocks"]
        next(b for b in blocks if b["type"] == "paragraph" and
             b["paragraph"]["rich_text"][0]["plain_text"] == "본문")["paragraph"]["rich_text"][0]["plain_text"] = "changed"
    with pytest.raises(notion.NotionError):
        resume(setup)
    assert not notion.load_records(setup[2])


def test_concurrent_kind_rejected(setup):
    from scripts.lab.notion_sync import kind_lock
    with kind_lock(setup[2], "예비보고서"):
        with pytest.raises(notion.NotionError):
            start(setup)
    assert not setup[0].pages


def test_pending_operation_blocks_new_push(setup):
    setup[0].fail_after = "insert"
    with pytest.raises(notion.NotionError):
        start(setup)
    from scripts.lab.notion_sync import sync_report
    with pytest.raises(notion.NotionError):
        sync_report(setup[1], "PARENT", "token", kind="예비보고서", title="제목",
                    work_dir=setup[2] / ".notion-sync/other", output_dir=setup[2])
    assert len(setup[0].pages) == 1


def test_ambiguous_create_no_match_never_recreates(setup):
    setup[0].fail_before = "page"
    with pytest.raises(notion.NotionError):
        start(setup)
    with pytest.raises(notion.NotionError):
        resume(setup)
    assert not setup[0].pages


def test_expired_unattached_upload_replaced(setup):
    setup[0].fail_after = "send"
    with pytest.raises(notion.NotionError):
        start(setup)
    for upload in setup[0].uploads.values():
        upload["status"] = "expired"
    assert_complete(setup, resume(setup))


def test_image_free_legacy_history(setup):
    setup[1].write_text("# 제목\n\n본문")
    result = start(setup)
    assert result["status"] == "complete" and result["image_count"] == 0
    assert notion.load_records(setup[2])[0]["source"] == "report.md"


def test_resume_after_marker_archive(setup):
    real = notion.archive_block
    def lost(id, token):
        real(id, token)
        block = setup[0].blocks[id]
        if "NOTIONIMAGE-" in block["paragraph"]["rich_text"][0]["plain_text"]:
            raise notion.NotionError("lost marker archive response")
    with patch.object(notion, "archive_block", side_effect=lost):
        with pytest.raises(notion.NotionError):
            start(setup)
    assert_complete(setup, resume(setup))
    assert setup[0].events.count("insert") == 3


def test_expired_download_url_refreshed_once(setup):
    from scripts.lab import notion_images as ni
    real = ni.verify_image_content
    calls = 0
    def download(path, url):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise notion.NotionError("expired URL")
        return real(path, url)
    with patch.object(ni, "verify_image_content", side_effect=download):
        assert_complete(setup, start(setup))
    assert calls >= 2


def test_multiple_page_candidates_stop_without_creating(setup):
    setup[0].fail_after = "page"
    with pytest.raises(notion.NotionError):
        start(setup)
    page = next(iter(setup[0].pages.values()))
    import copy
    setup[0].pages["duplicate"] = copy.deepcopy(page)
    with pytest.raises(notion.NotionError):
        resume(setup)
    assert setup[0].events.count("page") == 1


def test_body_loss_prevents_baseline_and_record(setup):
    real = notion.pull_markdown
    setup[1].write_text("# 제목\n\n# 필수 절\n\n![](a.png)")
    with patch.object(notion, "pull_markdown", return_value=""):
        with pytest.raises(notion.NotionError):
            start(setup)
    assert not notion.load_records(setup[2])
    assert not list(setup[2].glob("*baseline*"))


def test_append_response_includes_other_siblings(setup):
    setup[0].append_returns_all = True
    assert_complete(setup, start(setup))
    assert setup[0].events.count("insert") == 3


def test_remote_marker_edit_is_not_deleted_on_resume(setup):
    setup[0].fail_after = "send"
    with pytest.raises(notion.NotionError):
        start(setup)
    journal = json.loads((setup[3] / "journal.json").read_text())
    marker = setup[0].blocks[journal["placements"][0]["marker_id"]]
    marker["paragraph"]["rich_text"] = [{"plain_text": "사용자가 새로 쓴 문장"}]
    with pytest.raises(notion.NotionError):
        resume(setup)
    assert not marker.get("archived")
    assert not notion.load_records(setup[2])
