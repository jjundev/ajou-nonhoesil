"""Exercise the actual CLI prescribed by the skill, including resumption."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from PIL import Image

from scripts.lab import notion, notion_sync as ns
from tests.notion_fake import FakeNotion


def test_skill_cli_push_and_resume(tmp_path, monkeypatch, capsys):
    fake = FakeNotion()
    monkeypatch.setattr("urllib.request.urlopen", fake)
    monkeypatch.setenv("NOTION_TOKEN", "test-token")
    source = tmp_path / "실험07/output/실험07_Test_예비보고서.md"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (3, 2), "red").save(source.parent / "x.png")
    source.write_text("# 실험7 Test 예비보고서\n\n![정상](x.png)")
    monkeypatch.setattr(ns.config, "artifact_path", lambda *a, **k: source)
    monkeypatch.setattr(ns.config, "find_project_root", lambda *a: tmp_path)
    monkeypatch.setattr(ns.config, "load_course_info", lambda *a: {"notion_parent_page_id": "P"})
    monkeypatch.setattr("scripts.lab.spec_parser.parse_spec", lambda *a: SimpleNamespace(experiment=7, title="Test"))
    monkeypatch.setattr(sys, "argv", ["sync", "push", "--source", str(source), "--kind", "예비보고서"])
    fake.fail_after = "insert"
    with pytest.raises(SystemExit) as err:
        ns.main()
    assert err.value.code == 1
    journal = next(source.parent.glob(".notion-sync/*/journal.json"))
    assert not notion.load_records(source.parent)
    monkeypatch.setattr(sys, "argv", ["sync", "resume", "--journal", str(journal)])
    ns.main()
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "complete"
    assert result["image_count"] == 1
    assert next(iter(fake.pages.values()))["title"] == "실험7 Test 예비보고서 v1"
    assert len(fake.pages) == 1
    assert len(notion.load_records(source.parent)) == 1


def test_skill_alias_and_legacy_missing_image_check():
    root = Path(__file__).resolve().parents[1]
    assert (root / ".agents/skills/sync-report-to-notion/SKILL.md").resolve() == (
        root / ".claude/skills/sync-report-to-notion/SKILL.md").resolve()
    from scripts.lab import validate
    assert validate.check_pulled_images("![그림]()")[0].level == "error"
