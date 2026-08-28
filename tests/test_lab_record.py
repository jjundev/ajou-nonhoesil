import unittest
from pathlib import Path

from scripts.lab.record import PROMPTS, derive_record
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]


class TestWeek2Record(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        self.text = derive_record(self.spec)

    def test_frontmatter_marks_it_unfilled(self):
        self.assertIn("schema: lab-record/v1", self.text)
        self.assertIn("filled_by: ~", self.text)

    def test_expected_column_is_labelled_and_check_column_is_blank(self):
        self.assertIn("Y예상", self.text)
        self.assertIn("확인", self.text)

    def test_every_table_gets_a_memo_line(self):
        """개수를 박지 말고 명세에서 센다. 참조표(role=reference)는 기록에
        들어가지 않으므로 셈에서도 빼야 한다."""
        used = sum(1 for item in self.spec.items for tid in item.tables
                   if self.spec.table(tid).role != "reference")
        self.assertEqual(self.text.count("- 메모:"), used)

    def test_closing_prompts_are_present(self):
        for prompt in PROMPTS:
            self.assertIn(f"- {prompt}:", self.text)

    def test_row_count_survives_derivation(self):
        """8행 진리표는 기록에서도 8행이어야 한다."""
        block = self.text[self.text.index("### T1"):self.text.index("### T2")]
        data_rows = [ln for ln in block.split("\n")
                     if ln.startswith("|") and not set(ln) <= set("|- ")]
        self.assertEqual(len(data_rows), 9)   # 헤더 1 + 데이터 8


class TestKindSpecificShapes(unittest.TestCase):
    def test_capture_gets_a_sketch_grid_not_a_table(self):
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        block = text[text.index("### T1"):text.index("### T2")]
        self.assertIn("스케치", block)
        self.assertIn("- 캡션:", block)
        self.assertNotIn("예상 |", block)

    def test_reference_tables_are_excluded(self):
        """T6~T9 는 교안 2입력 이론표다. 기록 칸을 만들면 안 된다."""
        spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        text = derive_record(spec)
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertNotIn(f"### {tid} ·", text)
        for tid in ("T1", "T5"):
            with self.subTest(table=tid):
                self.assertIn(f"### {tid} ·", text)

    def test_capture_carries_the_prose_expectation(self):
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        self.assertIn("> 예상:", text)

    def test_stepped_keeps_its_columns_without_an_expected_suffix(self):
        """스텝 표는 비어 있는 열 자체가 채울 칸이다. `예상` 을 붙이면 안 된다."""
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        block = text[text.index("### T2"):]
        self.assertIn("| 스텝", block)
        self.assertNotIn("예상", block.split("- 메모:")[0])


class TestAlignment(unittest.TestCase):
    def test_korean_headers_align(self):
        """손으로 채울 표라 정렬이 실제로 중요하다 (한글은 2칸)."""
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        block = [ln for ln in text.split("\n") if ln.startswith("| 스텝")][0]
        rule = text.split("\n")[text.split("\n").index(block) + 1]
        self.assertEqual(len(rule), len(rule.rstrip()))
        self.assertEqual(block.count("|"), rule.count("|"))


if __name__ == "__main__":
    unittest.main()
