import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude/skills/logic-lab-concept-check"
SCRIPTS = SKILL / "scripts"
TEMPLATE_SHA = "345324b7d1cdcbfadd2e538c4a871d92597bbceb946abbb7bf793d95b68b5a93"


def test_template_is_pinned_upstream_bytes():
    assert hashlib.sha256((SKILL / "assets/review-template.html").read_bytes()).hexdigest() == TEMPLATE_SHA


def test_skill_entry_points_share_new_pack_hook():
    skill = (ROOT / ".agents/skills/logic-lab-concept-check/SKILL.md").read_text()
    parent = (ROOT / ".claude/skills/logic-lab-review-pack/SKILL.md").read_text()
    assert "../logic-lab-concept-check/SKILL.md" in parent
    assert parent.index("workbook_pdf 실험NN") < parent.index("../logic-lab-concept-check/SKILL.md")
    assert "단독" in skill and "prepare" in skill and "publish" in skill


def test_prepare_missing_pack_leaves_no_stage(tmp_path):
    run = tmp_path / "run"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "delivery.py"), "prepare", "실험10",
         "--root", str(tmp_path), "--run", str(run)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "학습팩" in result.stderr
    assert not run.exists()


@pytest.fixture
def scripts(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import content
    import delivery
    return content, delivery


def test_compute_preserves_bit_width_and_control_polarity(scripts):
    content, _ = scripts
    assert content.compute({"op": "boolean", "expression": "A'·B", "inputs": {"A": 0, "B": 1}}) == "1"
    assert content.compute({"op": "select", "address": "01", "words": ["00", "01", "10", "11"]}) == "01"
    assert content.compute({"op": "hold_or_load", "previous": "01", "data": "10",
                            "enable": 1, "active": 0}) == "01"


def test_failed_publication_preserves_previous_quiz(tmp_path, scripts):
    _, delivery = scripts
    target = tmp_path / "복습노트/실험09"
    target.mkdir(parents=True)
    quiz = target / "실험09_확인문제.html"
    quiz.write_text("previous")
    previous = target / ".pack/자료_확인문제"
    previous.mkdir(parents=True)
    (previous / "items.json").write_text(json.dumps({"previous": True}))
    with pytest.raises(ValueError):
        delivery.publish(tmp_path, 9, tmp_path / "work")
    assert quiz.read_text() == "previous"
    assert json.loads((previous / "items.json").read_text()) == {"previous": True}


def test_blind_packet_preserves_truth_table_and_escaped_pipes(scripts):
    from blind import _card, parse_answers

    item = {
        "id": "q1",
        "format": "short",
        "title": "출력",
        "stem_html": "<p>표를 채워요.</p><table><tr><th>A</th><th>Y</th></tr>"
                     "<tr><td>0</td><td>?</td></tr></table>",
        "hint": "answer leak",
    }
    packet = _card(item)
    assert "| A | Y |" in packet and "| 0 | ? |" in packet
    assert "answer leak" not in packet
    row = parse_answers(r"| q1 | 1 | $A \| B$를 적용해요 | |")["q1"]
    assert row == {"answer": "1", "rationale": "$A | B$를 적용해요", "objection": ""}
