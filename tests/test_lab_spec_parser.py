import tempfile
import unittest
from pathlib import Path

from scripts.lab.spec_parser import (SpecError, derived_parts, parse_spec,
                                     split_columns)

ROOT = Path(__file__).resolve().parents[1]
WEEK2 = ROOT / "2주차/체크리스트/명세.md"
WEEK6 = ROOT / "6주차/체크리스트/명세.md"
WEEK12 = ROOT / "12주차/체크리스트/명세.md"


class TestWeek2(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(WEEK2)

    def test_frontmatter(self):
        self.assertEqual(self.spec.week, 2)
        self.assertEqual(self.spec.experiment, 1)
        self.assertEqual(self.spec.power["VCC"], "+5V")

    def test_three_items(self):
        self.assertEqual([i.id for i in self.spec.items],
                         ["E1.P1-1", "E1.P1-2", "E1.P2"])

    def test_ic_list_matches_manual_parts_page(self):
        """교안 p10 준비물이 근거다. 74HC08 은 quad AND 라 3-input 에 1개면 된다."""
        self.assertEqual(self.spec.items[0].ics, ["74HC08", "74HC32"])

    def test_three_input_truth_tables_are_eight_rows(self):
        for tid in ("T1", "T2", "T3", "T4"):
            with self.subTest(table=tid):
                self.assertEqual(len(self.spec.table(tid).rows), 8)
                self.assertEqual(self.spec.table(tid).kind, "truth-table")

    def test_composite_table_is_two_input(self):
        """교안 p13 은 3입력이 아니라 2입력이다 (Task 1 vision 판독으로 확정)."""
        self.assertEqual(len(self.spec.table("T5").rows), 4)

    def test_every_table_declares_source(self):
        for t in self.spec.tables:
            self.assertTrue(t.source, f"{t.id} 에 source 가 없다")

    def test_split_columns_finds_inputs_and_outputs(self):
        inputs, outputs = split_columns(self.spec.table("T1"))
        self.assertEqual(inputs, ["A", "B", "C"])
        self.assertEqual(outputs, ["Y"])

    def test_derived_parts_extracts_expression(self):
        self.assertEqual(derived_parts(self.spec.table("T1")), [("Y", "A·B·C")])

    def test_derived_parts_handles_multiple_outputs(self):
        """실험1 p13 복합회로는 입력 2개에 출력이 3개다."""
        pairs = derived_parts(self.spec.table("T5"))
        self.assertEqual([name for name, _ in pairs], ["X", "Y", "Z"])

    def test_theory_tables_are_reference_not_record(self):
        """T6~T9 는 교안 2입력 이론표다. 학생이 배선하지도 채우지도 않는다."""
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertEqual(self.spec.table(tid).role, "reference")
                self.assertEqual(self.spec.table(tid).encoding, "H/L")

    def test_procedure_tables_default_to_record(self):
        for tid in ("T1", "T2", "T3", "T4", "T5"):
            with self.subTest(table=tid):
                self.assertEqual(self.spec.table(tid).role, "record")

    def test_both_encodings_appear_in_the_real_fixture(self):
        """`H/L` ↔ `0/1` 변환 금지 규칙을 실물로 시험할 수 있어야 한다."""
        encodings = {t.encoding for t in self.spec.tables}
        self.assertEqual(encodings, {"0/1", "H/L"})

    def test_split_columns_on_a_multi_output_table(self):
        inputs, outputs = split_columns(self.spec.table("T5"))
        self.assertEqual(inputs, ["A", "B"])
        self.assertEqual(outputs, ["X", "Y", "Z"])


class TestWeek12CaptureAndStepped(unittest.TestCase):
    """kind 는 실험 단위가 아니라 표 단위 속성이다 (실험10 이 근거)."""

    def setUp(self):
        self.spec = parse_spec(WEEK12)

    def test_dac_is_capture_with_prose_expectation(self):
        t = self.spec.table("T1")
        self.assertEqual(t.kind, "capture")
        self.assertEqual(t.rows, [])
        self.assertIn("계단", t.expected)

    def test_adc_is_stepped_with_a_table(self):
        t = self.spec.table("T2")
        self.assertEqual(t.kind, "stepped")
        self.assertEqual(t.encoding, "0/1")
        self.assertGreater(len(t.rows), 0)


class TestWeek6SymbolicTokens(unittest.TestCase):
    """열린 토큰 모델(R3)이 심볼릭 값을 담는지."""

    def setUp(self):
        self.spec = parse_spec(WEEK6)

    def test_encoding_is_binary_not_hl(self):
        """실험6 교안은 0/1, 실험1 교안은 H/L. 섞지 않는다."""
        for t in self.spec.tables:
            self.assertEqual(t.encoding, "0/1")

    def test_composite_tokens_survive(self):
        cells = {c for t in self.spec.tables for row in t.rows for c in row}
        self.assertIn("Q(t-1)", cells)
        self.assertTrue(any(":" in c for c in cells),
                        "`0 : Reset` 같은 복합 토큰이 살아 있어야 한다")


class TestErrors(unittest.TestCase):
    """실물 명세를 한 군데씩 망가뜨려 파서가 거절하는지 본다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _broken(self, old, new):
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(
            WEEK12.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
        )
        return target

    def test_unknown_kind_raises(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken("kind: stepped", "kind: numeric"))
        self.assertIn("numeric", str(ctx.exception))

    def test_dangling_table_reference_raises(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken("tables: [T2]", "tables: [T7]"))
        self.assertIn("T7", str(ctx.exception))

    def test_wrong_schema_raises(self):
        with self.assertRaises(SpecError):
            parse_spec(self._broken("lab-spec/v1", "lab-spec/v0"))


if __name__ == "__main__":
    unittest.main()
