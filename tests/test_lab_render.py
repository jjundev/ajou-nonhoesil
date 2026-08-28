import unittest
from pathlib import Path

from scripts.lab.render import crop_rows, render_checklist
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(
    encoding="utf-8")


class TestChecklistHtml(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        self.netlist = (ROOT / "2주차/결선도/netlist.md").read_text(encoding="utf-8")
        self.html = render_checklist(self.spec, self.netlist, TEMPLATE)

    def test_no_placeholder_survives(self):
        self.assertNotIn("{{", self.html)

    def test_power_and_floating_pins_come_first(self):
        """플로팅 입력이 이 과목의 대표 실패 원인이다. 절차 맨 위에 온다."""
        power = self.html.index("VCC")
        first_table = self.html.index("<table")
        self.assertLess(power, first_table)
        self.assertIn("미사용", self.html)

    def test_check_cells_exist_for_every_truth_table_row(self):
        """개수를 박지 말고 명세에서 센다. 참조표(role=reference)는 빠진다."""
        expected = sum(len(self.spec.table(t).rows)
                       for item in self.spec.items for t in item.tables
                       if self.spec.table(t).kind != "capture"
                       and self.spec.table(t).role != "reference")
        self.assertEqual(self.html.count('class="check"'), expected)
        self.assertGreaterEqual(expected, 32)   # T1~T4 가 8행씩

    def test_expected_value_sits_next_to_the_check_cell(self):
        self.assertIn("Y예상", self.html)

    def test_source_is_surfaced_for_every_printed_table(self):
        """참조표는 인쇄본에 없으므로 출처도 없다 — 기록 대상만 본다."""
        for table in self.spec.tables:
            if table.role == "reference":
                continue
            with self.subTest(table=table.id):
                self.assertIn(table.source, self.html)

    def test_reference_tables_do_not_get_check_cells(self):
        """참조표는 인쇄본에 없다 — ③ 예비보고서 이론 절의 재료다."""
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertNotIn(f"{tid} ·", self.html)

    def test_wiring_photo_pair_is_present(self):
        """결선도 | 회로 2열 대조는 코퍼스에서 가장 강한 관행이다."""
        self.assertIn("결선도", self.html)
        self.assertIn("회로", self.html)


class TestCapturePage(unittest.TestCase):
    def test_capture_renders_a_sketch_box_not_a_grid(self):
        spec = parse_spec(ROOT / "12주차/체크리스트/명세.md")
        html = render_checklist(spec, "VCC GND 미사용", TEMPLATE)
        self.assertIn('class="sketch"', html)


class TestCrop(unittest.TestCase):
    def test_row_count_comes_from_the_netlist(self):
        """쓰는 행만 남겨 작도 면적을 줄이는 것이 실제 관행이다 (2020 예보2)."""
        netlist = "- U1 = 74HC08\n  - pin 1 ← 입력 A\n  - pin 14 → VCC(+5V)\n"
        self.assertGreater(crop_rows(netlist), 0)
        self.assertLessEqual(crop_rows(netlist), 30)


class TestPrintConstraints(unittest.TestCase):
    """실험실 물리 조건은 CSS 에만 있어서 문자열 검증이 없으면 조용히 사라진다.
    실제로 이 공백 때문에 브레드보드 그림이 제목과 갈라진 채 두 라운드를 통과했다."""

    def test_check_cell_is_big_enough_for_a_pen(self):
        self.assertIn("width: 10mm", TEMPLATE)
        self.assertIn("height: 8mm", TEMPLATE)

    def test_pin_numbers_are_readable_under_lab_lighting(self):
        self.assertIn("font-size: 12pt", TEMPLATE)

    def test_page_break_rules_survive(self):
        for rule in ("break-inside: avoid",
                     "display: table-header-group",
                     "break-after: avoid"):
            with self.subTest(rule=rule):
                self.assertIn(rule, TEMPLATE)

    def test_table_and_breadboard_blocks_are_kept_whole(self):
        """제목만 앞 쪽에 남고 내용이 넘어가면 실험실에서 못 읽는다."""
        self.assertIn(".tblock", TEMPLATE)
        spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        netlist = (ROOT / "2주차/결선도/netlist.md").read_text(encoding="utf-8")
        html = render_checklist(spec, netlist, TEMPLATE)
        self.assertEqual(html.count('<div class="tblock">'),
                         5 + 1)   # 기록 대상 표 5개 + 브레드보드 1


class TestProcedureCarriesEveryWarning(unittest.TestCase):
    """영문 `pin` 이 든 줄만 고르면 한글로 쓴 경고가 통째로 사라진다.
    이 과목의 대표 실패 원인(플로팅 입력) 경고가 실제로 그렇게 빠져 있었다."""

    def setUp(self):
        spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        netlist = (ROOT / "2주차/결선도/netlist.md").read_text(encoding="utf-8")
        self.html = render_checklist(spec, netlist, TEMPLATE)

    def test_korean_only_warnings_reach_the_printout(self):
        for warning in ("띄워두지 않는다", "가장 흔한 배선 실수",
                        "330Ω 직렬", "칩 재사용"):
            with self.subTest(warning=warning):
                self.assertIn(warning, self.html)

    def test_multiline_bullets_are_not_truncated(self):
        """`74HC02` 경고는 세 줄짜리 불릿이다. 이어지는 줄을 버리면 잘린다."""
        self.assertIn("핀 1·4·10·13", self.html)

    def test_markdown_syntax_does_not_reach_print(self):
        body = self.html[self.html.index('<div class="power">'):]
        self.assertNotIn("**", body)
        self.assertNotIn("`", body)


if __name__ == "__main__":
    unittest.main()
