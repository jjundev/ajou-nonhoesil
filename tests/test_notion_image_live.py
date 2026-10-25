import os
from pathlib import Path
import urllib.error

import pytest


def test_harness_drops_response_after_remote_success():
    from scripts.verify_notion_images import DropAfter
    writes = []
    def remote(req, token, timeout=120):
        writes.append(req)
        return {"id": "inserted-on-server"}
    drop = DropAfter(remote, lambda req: True)
    with pytest.raises(urllib.error.URLError):
        drop("request", "token")
    assert writes == ["request"]
    assert drop.fired
    assert drop("read", "token") == {"id": "inserted-on-server"}


@pytest.mark.skipif(os.environ.get("NOTION_IMAGE_LIVE") != "1" or not os.environ.get("NOTION_IMAGE_LIVE_WORKDIR"),
                    reason="explicit live Notion opt-in and separate work-dir required")
def test_live_acceptance():
    from scripts.verify_notion_images import acceptance
    results = acceptance(Path(os.environ["NOTION_IMAGE_LIVE_WORKDIR"]))
    for name in ("happy_path", "insert_response_lost", "archive_response_lost",
                 "process_crash", "baseline_failure", "wrong_location_detected",
                 "caption_mismatch_detected", "content_mismatch_detected",
                 "page_create_response_lost", "no_duplicate_pages_or_images",
                 "no_secret_persistence"):
        assert results["checks"].get(name) == "pass", (name, results["checks"])
