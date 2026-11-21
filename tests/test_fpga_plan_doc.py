"""FPGA 도어락 설계 계획서 본문 검사.

계획서에 쓴 내용은 12/11 구두 평가와 12/23 보고서에서 그대로 채점되므로,
평가 항목 대응·수치·표시 문구가 빠지거나 갈리지 않았는지와 노션 호환을 본다.
"""
import re
from pathlib import Path

from scripts.lab import md, validate

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "보고서/프로젝트/output/FPGA_설계_계획서.md"
TITLE = "FPGA 설계 Digital Door Lock 설계 계획서"
SECTIONS = ["설계 목표", "과제 요구사항 분석 및 구현 방안", "예상 문제점 및 해결 방안",
            "프로젝트 동작 블록 다이어그램", "조원 역할 분담", "조교님께 확인할 사항", "출처 및 참고문헌"]


def section(name: str) -> str:
    """h1 절 `name` 의 본문(다음 h1 전까지)."""
    lines = DOC.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"# {name}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("# ")), len(lines))
    return "\n".join(lines[start:end])


def tables(text: str) -> list:
    return md.parse_tables(text)


def test_title_and_sections_in_order():
    lines = DOC.read_text(encoding="utf-8").splitlines()
    assert lines[0] == f"# {TITLE}"
    h1 = [l[2:] for l in lines[1:] if l.startswith("# ")]
    assert h1 == SECTIONS


def test_notion_markdown_has_no_errors():
    errors = [f for f in validate.check_notion_markdown(DOC) if f.level == "error"]
    assert errors == []


def test_body_style_clean():
    # 백틱·em dash·조사 띄어쓰기·조교 호칭 (.claude/보고서서식.md §AI 티·§붙여쓰기·§호칭)
    assert validate.check_body_style(DOC.read_text(encoding="utf-8")) == []


REQ = "과제 요구사항 분석 및 구현 방안"


def test_eval_items_each_once():
    rows = [r for t in tables(section(REQ)) for r in t.rows]
    for n in range(1, 11):
        assert sum(r[0].strip() == f"E{n}" for r in rows) == 1, f"E{n}"


def test_key_map_covers_all_pb():
    text = section(REQ)
    for n in range(16):
        assert f"pb{n})" in text, f"pb{n}"


def test_display_words_present():
    # 서식 규칙상 백틱 대신 큰따옴표로 감싼다 (원 계획은 백틱)
    text = section(REQ)
    for w in ["------", "OPEn", "Error", "LOCK", "nonE", "donE", "InIt", "nEW", "AGAIn"]:
        assert f'"{w}' in text, w


def test_extra_features_exactly_three():
    rows = [r for t in tables(section(REQ)) for r in t.rows if r[0].strip().startswith("A")]
    assert [r[0].strip() for r in rows] == ["A1", "A2", "A3"]


def test_numbers_match_spec():
    text = section(REQ)
    for s in ["1~6자리", "4~6자리", '"1234"', "10→20→40초", "1.5초", "10ms", "1kHz"]:
        assert s in text, s


PROB = "예상 문제점 및 해결 방안"


def test_problem_table_has_eight_rows():
    t = tables(section(PROB))[0]
    assert t.header[:2] == ["문제", "해결 방안"]
    assert len(t.rows) >= 8


def test_verification_plan_named():
    text = section(PROB)
    assert "Questa" in text and "테스트벤치" in text and "E1~E10" in text
