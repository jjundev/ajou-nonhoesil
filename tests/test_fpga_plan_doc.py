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
            "프로젝트 동작 블록 다이어그램", "조원 역할 분담", "조교님께 확인한 사항", "출처 및 참고문헌"]


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


def test_extra_features_exactly_five():
    rows = [r for t in tables(section(REQ)) for r in t.rows if r[0].strip().startswith("A")]
    assert [r[0].strip() for r in rows] == ["A1", "A2", "A3", "A4", "A5"]


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


def test_ta_answers_recorded():
    # 2026-11-23 조교님 답변 여섯 가지
    assert len(tables(section("조교님께 확인한 사항"))[0].rows) == 6


def test_empty_ok_counts_as_wrong():
    # 조교님 답변 4: 빈 입력 OK 도 오답
    assert "오답 1회로 센" in _eval_row(5)
    assert "세지 않" not in _eval_row(5)


def test_overflow_keeps_last_six():
    # 조교님 답변 5: 마지막으로 입력된 6개의 숫자를 받는다
    assert "마지막" in _eval_row(8) and "234567" in _eval_row(8)
    assert "7번째 숫자부터" not in DOC.read_text(encoding="utf-8")


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


def test_every_task_and_date_has_work_for_both():
    # 담당·일정 표에서 두 조원의 칸이 모두 채워져 있어야 한다
    found = [t for t in tables(section("조원 역할 분담")) if any("최승민" in h for h in t.header)]
    assert len(found) == 2
    for t in found:
        for r in t.rows:
            assert len(r) == len(t.header), r
            assert all(c.strip() not in ("", "-") for c in r), r


def test_e4_covers_both_readings():
    # 조교님께 여쭌 두 해석(변경 후 옛 값 / 변경 도중 옛 값) 모두 동작이 적혀 있어야 한다
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

# ---- 2026-11-23 검토 반영 -------------------------------------------------
def test_screen_table_is_six_cells():
    # 테스트벤치 기대값이 되는 표: 화면마다 여섯 자리가 모두 정해져 있어야 한다
    t = next(t for t in tables(section(REQ)) if t.header[0].strip() == "화면")
    assert [h.strip() for h in t.header[1:]] == list("123456")
    shown = {}
    for r in t.rows:
        cells = [c.strip() for c in r[1:]]
        assert len(cells) == 6 and all(c == "끔" or len(c) == 1 for c in cells), r
        shown[r[0]] = "".join(" " if c == "끔" else c for c in cells)
    assert set(v.rstrip() for v in shown.values()) == {
        "------", "12----", "OPEn", "Error", "nonE", "donE", "InIt", "nEW", "AGAIn", "LOCK09", "GUESt", "OPEn G", "dEL"}


def test_third_wrong_goes_to_lock_in_r4():
    # R4 와 E2 가 3회째 오답을 다르게 말하지 않는다
    r4 = next(r for t in tables(section(REQ)) for r in t.rows if r[0].strip() == "R4")
    assert "3회째" in r4[2] and "LOCK" in r4[2]


def test_e9_keeps_notice_wording():
    assert "코드에 입력한 시간까지" in _eval_row(9) and "LOCK_SEC=10" in _eval_row(9)


def test_buffer_clear_points_written():
    assert "IDLE, NEW_PW, NEW_CONFIRM, GUEST_PW에 들어갈 때마다 비운다" in section(REQ)


def test_fsm_to_display_signals_named():
    for s in ["메시지 종류", "24비트", "십진 두 자리"]:
        assert s in section(BLOCK), s
    svg = (FIG / "블록다이어그램.svg").read_text(encoding="utf-8")
    assert "메시지" in svg

def test_lock_end_and_timer_written():
    text = section(REQ)
    assert '"LOCK01"을 1초 띄운 뒤 "LOCK00" 없이' in text
    assert "0부터 50MHz 클록을 세어" in text
    # 시간은 door_fsm 카운터로 재므로 100ms 틱은 본문·그림 어디에도 없다
    assert "100ms" not in DOC.read_text(encoding="utf-8")
    assert "100ms" not in (FIG / "블록다이어그램.svg").read_text(encoding="utf-8")


def test_undefined_keys_and_simultaneous_keys_written():
    assert "표에 없는 키는 모두 무시한다" in section(REQ)
    assert "모두 뗄 때까지 받지 않는다" in section(PROB)


def test_board_pass_criteria_written():
    assert "통과로 본다" in section(PROB) and "pb에 넣어" in section(PROB)

# ---- 2026-11-23 최종본 검토 반영 ------------------------------------------
def _row(sec, key):
    return next(r for t in tables(section(sec)) for r in t.rows if r[0].strip() == key)


def test_change_states_edit_buffer_and_compare_length():
    # "표에 없는 키는 무시"와 A1(변경 중 BS·CLR)이 부딪히지 않는다
    for s in ["NEW_PW", "NEW_CONFIRM"]:
        assert "BS, CLR은 버퍼를 고친다" in _row(REQ, s)[2], s
    confirm = _row(REQ, "NEW_CONFIRM")[2]
    assert "OK를 누르면" in confirm and "길이까지 비교" in confirm
    assert "그 길이" in section(REQ)


def test_ta_answers_not_widened():
    # 답변 칸에는 조교님이 답하신 내용만 적는다
    rows = tables(section("조교님께 확인한 사항"))[0].rows
    assert rows[1][1].startswith("그대로 진행하면 된다") and "열린 상태(OPEN)로 돌아가" in rows[1][1]
    assert rows[3][0].startswith("입력 대기에서")


def test_por_counter_has_initial_value():
    assert "선언할 때 초기값 0" in section(PROB)


def test_extra_features_simulated_and_separated():
    assert "E1~E10과 추가 구현 A1~A5" in section(PROB)
    assert "A1~A5" in section("조원 역할 분담")
    assert "추가 구현 A3" in _row(REQ, "R6")[2]
    assert "LOCK40" in _row(REQ, "A2")[3] and "맞히지 않고" in _row(REQ, "A2")[3]


def test_table_captions_follow_format():
    # 표 캡션 규칙: 소절 제목이 표 제목을 겸하지 못하면 불릿 제목 + 탭 들여쓰기
    lines = DOC.read_text(encoding="utf-8").splitlines()
    for name in ["상태별 표시와 전이", "화면 여섯 자리", "조교님 답변과 반영"]:
        i = lines.index(f"- **{name}**")
        assert lines[i + 1].startswith("	|"), name


def test_block_figure_draws_ticks_and_reset():
    svg = (FIG / "블록다이어그램.svg").read_text(encoding="utf-8")
    for s in [">10ms 틱<", ">1kHz 틱<", ">rst<", "clock_50m은 모든 모듈"]:
        assert s in svg, s


def test_schedule_has_report():
    assert "12/23" in section("조원 역할 분담")


def test_dummy_digits_explained():
    # 허수(A5)로 열리는 "비밀번호+숫자" 입력을 평가에서 버그로 읽지 않게 E1과 예상 문제점에 적는다
    e1 = _row(REQ, "E1")[2]
    assert '"12345"' in e1 and '"9999"' in e1 and "A5" in e1
    text = section(PROB)
    assert "허수" in text and "마지막 여섯 숫자" in text
    assert len(tables(text)[0].rows) >= 10
    assert "허수 A5 먼저 안내" in section("조원 역할 분담")
