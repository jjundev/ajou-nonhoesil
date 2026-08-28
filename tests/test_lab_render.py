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

    def test_source_is_surfaced_for_every_table(self):
        for table in self.spec.tables:
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


if __name__ == "__main__":
    unittest.main()
