"""Naming boundary and real producer/consumer paths, without rewriting artifacts."""
from pathlib import Path

import pytest

from scripts.lab import config, hand_sim, trace_guide, merge_report, report_compare
from scripts.lab import notion


def test_report_filename_boundary():
    assert merge_report.output_filename(6, "Latch & Flip-Flop", "결과보고서") == "실험6_Latch_&_Flip-Flop_결과보고서.pdf"
    assert merge_report.output_filename(7, "Shift Register", "예비보고서") == "실험07_Shift_Register_예비보고서.pdf"
    assert merge_report.output_filename(10, "Counter", "결과보고서") == "실험10_Counter_결과보고서.pdf"


def test_artifact_paths_share_spec_title(tmp_path):
    exp = tmp_path / "실험07"
    (exp / "체크리스트").mkdir(parents=True)
    (exp / "체크리스트/명세.md").write_text("---\nexperiment: 7\ntitle: Shift Register\n---\n", encoding="utf-8")
    assert config.artifact_path(exp, "체크리스트", ".html") == exp / "체크리스트/실험07_Shift_Register_체크리스트.html"
    assert config.artifact_path(exp, "기록", ".md") == exp / "체크리스트/실험07_Shift_Register_기록.md"
    assert config.artifact_path(exp, "예비보고서", ".md") == exp / "output/실험07_Shift_Register_예비보고서.md"
    assert config.artifact_path(exp, "예비보고서표지") == exp / "output/실험07_Shift_Register_예비보고서표지.pdf"


def test_old_paths_do_not_require_spec(tmp_path):
    exp = tmp_path / "실험06"
    assert config.artifact_path(exp, "체크리스트") == exp / "체크리스트/체크리스트.pdf"
    assert config.artifact_path(exp, "기록", ".md") == exp / "체크리스트/기록.md"
    assert config.artifact_path(exp, "예비보고서", ".md") == exp / "output/실험06_예비보고서.md"
    assert config.artifact_path(exp, "따라그리기") == exp / "결선도/팀원전달용/실험06_따라그리기.pdf"


def test_legacy_submission_path_keeps_title(tmp_path):
    exp = tmp_path / "실험06"
    (exp / "체크리스트").mkdir(parents=True)
    (exp / "체크리스트/명세.md").write_text("---\nexperiment: 6\ntitle: Latch & Flip-Flop\n---\n", encoding="utf-8")
    assert config.artifact_path(exp, "결과보고서") == exp / "실험6_Latch_&_Flip-Flop_결과보고서.pdf"


def test_hand_and_report_consumers_use_new_names():
    assert hand_sim.output_paths(7)[0].name == "실험07_Shift_Register_손그림모사.pdf"
    assert hand_sim.output_paths(7)[1].name == "실험07_Shift_Register_부품그리기.pdf"
    assert trace_guide.output_path(7).name == "실험07_Shift_Register_따라그리기.pdf"
    assert report_compare.approved_report_path(7).name == "실험07_Shift_Register_결과보고서.md"
    assert hand_sim.output_paths(6)[0].name == "실험06_손그림모사.pdf"


@pytest.mark.parametrize("title", ["", "../Shift", "Shift/Register", "Shift:Register"])
def test_invalid_titles_cannot_escape_artifact_directory(title):
    with pytest.raises(ValueError):
        config.artifact_filename(7, title, "체크리스트")


def test_notion_history_keeps_original_stem_after_source_rename(tmp_path):
    record = {"source": "실험07_Shift_Register_예비보고서.md", "version": 1,
              "history_source": "실험07_예비보고서.md"}
    baseline = tmp_path / "실험07_예비보고서_notion_baseline_v1.md"
    baseline.write_text("원래 baseline", encoding="utf-8")
    assert notion.history_path(tmp_path, record).read_text(encoding="utf-8") == "원래 baseline"
    assert notion.history_path(tmp_path, record, baseline=False).name == "실험07_예비보고서_notion_v1.md"
    fresh = {"source": "실험07_Shift_Register_예비보고서.md", "version": 2}
    assert notion.history_path(tmp_path, fresh).name == "실험07_Shift_Register_예비보고서_notion_baseline_v2.md"
