"""FPGA 도어락 설계 계획서 본문 검사.

계획서에 쓴 내용은 12/11 구두 평가와 12/23 보고서에서 그대로 채점되므로,
평가 항목 대응·수치·표시 문구가 빠지거나 갈리지 않았는지와 노션 호환을 본다.
"""
import hashlib
import re
from pathlib import Path

from scripts.lab import md, validate
from scripts.lab.svg_png import png_text, svg_size

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


FIG = ROOT / "보고서/프로젝트/그림"
BLOCK = "프로젝트 동작 블록 다이어그램"


def test_images_resolve():
    text = section(BLOCK)
    srcs = re.findall(r"!\[[^\]]+\]\(([^)]+)\)", text)
    assert [Path(s).name for s in srcs] == ["블록다이어그램.png", "상태도.png", "키배치.png"]
    for s in srcs:
        assert (DOC.parent / s).is_file(), s


def test_block_figure_names_every_module():
    svg = (FIG / "블록다이어그램.svg").read_text(encoding="utf-8")
    for m in ["tick_gen", "key_input", "key_decode", "door_fsm", "display_ctrl", "seg_driver", "por"]:
        assert m in svg, m


def test_state_figure_mentions_confirm():
    svg = (FIG / "상태도.svg").read_text(encoding="utf-8")
    for s in ["IDLE", "CHECK", "OPEN", "NEW_PW", "NEW_CONFIRM", "MSG", "LOCK"]:
        assert s in svg, s


def test_key_figure_matches_table():
    svg = (FIG / "키배치.svg").read_text(encoding="utf-8")
    for label in ["CHG", "RST", "OK", "BS", "CLR"] + [str(d) for d in range(10)]:
        assert f">{label}<" in svg, label


def test_goal_written():
    assert "7 Segment" in section("설계 목표") and "Keypad" in section("설계 목표")


def test_roles_cover_both_members_and_modules():
    text = section("조원 역할 분담")
    for s in ["최승민", "신현준", "door_fsm", "key_input", "seg_driver", "테스트벤치"]:
        assert s in text, s


def test_ta_questions_three():
    assert len(re.findall(r"^- ", section("조교님께 확인할 사항"), re.M)) == 3


def test_no_placeholders():
    assert "(작성 예정)" not in DOC.read_text(encoding="utf-8")


def test_ta_always_honorific():
    assert not re.search(r"조교(?!님)", DOC.read_text(encoding="utf-8"))


# ---- 최종 리뷰 반영 -------------------------------------------------------
MODULES = ["tick_gen", "key_input", "key_decode", "door_fsm", "display_ctrl", "seg_driver", "por"]


def _eval_row(n):
    rows = [r for t in tables(section(REQ)) for r in t.rows if r[0].strip() == f"E{n}"]
    return " ".join(rows[0])


def test_roles_cover_every_module():
    # 블록 다이어그램의 모든 상자와 최상위 모듈·핀 배치에 담당자가 있어야 한다
    text = section("조원 역할 분담")
    for s in MODULES + ["최상위", "핀"]:
        assert s in text, s


def test_e4_covers_both_readings():
    # 조교님께 묻는 두 해석(변경 후 옛 값 / 변경 도중 옛 값) 모두 동작이 적혀 있어야 한다
    assert "도중" in _eval_row(4)


def test_e3_second_lock_is_conditional():
    # A2: 한 번 맞히면 10초로 돌아가므로 "두 번째는 20초"에는 조건이 붙어야 한다
    assert "맞히지 않" in _eval_row(3)


def test_e10_does_not_say_locked_for_idle():
    # "잠긴"은 LOCK 상태를 뜻하므로 닫힌 입력 대기를 그렇게 부르지 않는다
    assert "잠긴" not in _eval_row(10)


def test_h2_headings_unique():
    h2 = [l for l in DOC.read_text(encoding="utf-8").splitlines() if l.startswith("## ")]
    assert len(h2) == len(set(h2)), h2


def test_figure_text_legible():
    # 노션 PDF 는 그림을 본문 폭(약 165mm)에 맞춘다. 글자/폭 ≥ 0.014 → 약 6.5pt 이상
    for name in ["블록다이어그램", "상태도", "키배치"]:
        svg = (FIG / f"{name}.svg").read_text(encoding="utf-8")
        width, _ = svg_size(svg)
        smallest = min(float(s) for s in re.findall(r'font-size="([\d.]+)"', svg))
        assert smallest / width >= 0.014, (name, smallest, width)


def test_png_matches_svg():
    # 문서에 들어가는 것은 PNG 다. SVG 를 고치고 다시 변환하지 않으면 잡는다
    for name in ["블록다이어그램", "상태도", "키배치"]:
        digest = hashlib.sha256((FIG / f"{name}.svg").read_bytes()).hexdigest()
        assert png_text(FIG / f"{name}.png").get("svg-sha256") == digest, name
