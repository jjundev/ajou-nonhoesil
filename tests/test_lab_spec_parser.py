import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.lab import config
from scripts.lab.spec_parser import (SpecError, derived_parts, parse_spec,
                                     split_columns)

ROOT = Path(__file__).resolve().parents[1]
WEEK2 = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"
# 파서 동작을 보는 씨앗이라 픽스처다 — 살아 있는 주차를 쓰면 그 주차를 다시
# 저작할 때마다 여기 박힌 행 수·토큰이 함께 바뀌어, 파서는 멀쩡한데 빨개진다.
EDGE = ROOT / "tests/fixtures/spec_edge.md"          # 심볼릭 토큰·축약 행
CAPTURE = ROOT / "tests/fixtures/spec_capture.md"    # capture/stepped·두 레일


class TestWeek2(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(WEEK2)

    def test_frontmatter(self):
        self.assertEqual(self.spec.experiment, 1)
        self.assertEqual(self.spec.power["VCC"], "+5V")

    def test_five_items(self):
        """신판(2026-2 배포본)은 실험 1-1/1-2/2-1/2-2/3 로 다섯 항목이다."""
        self.assertEqual([i.id for i in self.spec.items],
                         ["E1.P1-1", "E1.P1-2", "E1.P2-1", "E1.P2-2", "E1.P3"])

    def test_ic_list_matches_manual_parts_page(self):
        """교안 p10 준비물이 근거다. 74HC08 은 quad AND 라 3-input 에 1개면 된다."""
        self.assertEqual(self.spec.items[0].ics, ["74HC08"])
        self.assertEqual(self.spec.items[1].ics, ["74HC32"])

    def test_three_input_truth_tables_are_eight_rows(self):
        for tid in ("T1", "T2", "T3", "T4"):
            with self.subTest(table=tid):
                self.assertEqual(len(self.spec.table(tid).rows), 8)
                self.assertEqual(self.spec.table(tid).kind, "truth-table")

    def test_composite_table_is_two_input(self):
        """교안 p15 복합회로는 3입력이 아니라 2입력이다 (vision 판독으로 확정).

        쪽 번호가 오래 p13 이라고 적혀 있었다 — 아카이브 2020-2 판(13 쪽)
        기준이고, 배포본 2026-2(15 쪽)에서 p13 은 NAND 다.
        """
        self.assertEqual(len(self.spec.table("T5").rows), 4)

    def test_every_table_declares_source(self):
        for t in self.spec.tables:
            self.assertTrue(t.source, f"{t.id} 에 source 가 없다")

    def test_split_columns_finds_inputs_and_outputs(self):
        """T1 은 출력이 둘이다 — 교안 p11 이 중간단 L1 과 최종단 L2 를 둘 다
        연결하라고 지시하므로 표가 둘 다 받는다."""
        inputs, outputs = split_columns(self.spec.table("T1"))
        self.assertEqual(inputs, ["A", "B", "C"])
        self.assertEqual(outputs, ["L1", "L2"])

    def test_derived_parts_extracts_expression(self):
        self.assertEqual(derived_parts(self.spec.table("T1")),
                         [("L1", "A·B"), ("L2", "A·B·C")])

    def test_derived_parts_handles_multiple_outputs(self):
        """실험1 p15 복합회로는 입력 2개에 출력이 3개다."""
        pairs = derived_parts(self.spec.table("T5"))
        self.assertEqual([name for name, _ in pairs], ["X", "Y", "Z"])
        self.assertEqual([expr for _, expr in pairs],
                         ["A + (A'·B)'", "A + B", "(A'·B)'"])

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
        self.spec = parse_spec(CAPTURE)

    def test_dac_is_capture_with_prose_expectation(self):
        t = self.spec.table("T1")
        self.assertEqual(t.kind, "capture")
        self.assertEqual(t.rows, [])

    def test_multiline_expected_joins_the_whole_block(self):
        """`assertIn` 한 조각으로는 첫 줄이나 끝 줄이 빠져도 통과한다.
        양 끝을 다 짚어야 이어붙이기가 블록 전체를 덮는지 증명된다."""
        expected = self.spec.table("T1").expected
        self.assertTrue(expected.startswith("1KHz"), expected[:40])
        self.assertTrue(expected.rstrip().endswith("."), expected[-40:])
        self.assertIn("1:2:4:8", expected)          # 마지막 줄의 토큰
        self.assertNotIn("\n", expected)           # 한 줄로 합쳐졌다

    def test_power_is_an_open_rail_map(self):
        """실험10 은 +5V 와 +15V 두 레일을 쓴다 (스키마 파손 3번의 근거)."""
        self.assertEqual(set(self.spec.power), {"VCC", "V15", "GND"})

    def test_adc_is_stepped_with_a_table(self):
        t = self.spec.table("T2")
        self.assertEqual(t.kind, "stepped")
        self.assertEqual(t.encoding, "0/1")
        self.assertGreater(len(t.rows), 0)


class TestWeek6SymbolicTokens(unittest.TestCase):
    """열린 토큰 모델(R3)이 심볼릭 값을 담는지."""

    def setUp(self):
        self.spec = parse_spec(EDGE)

    def test_encoding_is_binary_not_hl(self):
        """실험6 교안은 0/1, 실험1 교안은 H/L. 섞지 않는다."""
        for t in self.spec.tables:
            self.assertEqual(t.encoding, "0/1")

    def test_composite_tokens_survive(self):
        cells = {c for t in self.spec.tables for row in t.rows for c in row}
        self.assertIn("Q(t-1)", cells)
        self.assertTrue(any(":" in c for c in cells),
                        "`0 : Reset` 같은 복합 토큰이 살아 있어야 한다")

    def test_row_counts_are_not_powers_of_two(self):
        """`x x 0` 축약 때문에 3입력 표가 5행이다. 이게 정상이라는 근거 픽스처다."""
        counts = [len(t.rows) for t in self.spec.tables]
        self.assertEqual(counts, [5, 3, 3, 5, 5])

    def test_manual_sourced_tables_have_no_derived_pairs(self):
        for t in self.spec.tables:
            with self.subTest(table=t.id):
                self.assertTrue(t.source.startswith("manual:"))
                self.assertEqual(derived_parts(t), [])


class TestDeclaredOutputs(unittest.TestCase):
    """`derived` 가 아닌 표가 출력 열을 `outputs` 로 선언한다.

    실험3 이 실물이다. 교안 p4~p7 의 `Truth Table` 은 출력이 둘(합·올림 /
    차·내림)인데, 원문 그대로 옮긴 참조표라 `source` 가 `manual:pN` 이어야
    한다. 선언할 자리가 없으면 `split_columns` 는 마지막 열 하나만 출력으로
    본다.
    """

    SPEC = ROOT / "tests/fixtures/spec_manual_outputs.md"

    def setUp(self):
        self.spec = parse_spec(self.SPEC)

    def test_리스트로_읽힌다(self):
        self.assertEqual(self.spec.table("T2").outputs, ["S", "C"])
        self.assertEqual(self.spec.table("T8").outputs, ["D", "Bo"])

    def test_없으면_None_이다(self):
        self.assertIsNone(self.spec.table("T1").outputs)

    def test_참조표는_manual_source_를_그대로_지닌다(self):
        for tid in ("T2", "T4", "T6", "T8"):
            with self.subTest(table=tid):
                t = self.spec.table(tid)
                self.assertTrue(t.source.startswith("manual:p"), t.source)
                self.assertEqual(t.role, "reference")
                self.assertEqual(derived_parts(t), [])

    def test_split_columns_가_선언을_따른다(self):
        cases = {"T2": (["A", "B"], ["S", "C"]),
                 "T4": (["A", "B", "Ci"], ["S", "Co"]),
                 "T6": (["A", "B"], ["D", "Bo"]),
                 "T8": (["A", "B", "Bi"], ["D", "Bo"])}
        for tid, want in cases.items():
            with self.subTest(table=tid):
                self.assertEqual(split_columns(self.spec.table(tid)), want)

    def test_참조표와_기록표의_분할이_같다(self):
        for record, reference in (("T1", "T2"), ("T3", "T4"),
                                  ("T5", "T6"), ("T7", "T8")):
            with self.subTest(pair=(record, reference)):
                self.assertEqual(split_columns(self.spec.table(reference)),
                                 split_columns(self.spec.table(record)))

    def test_출력_순서는_선언이_아니라_헤더를_따른다(self):
        """`derived` 분할도 헤더 순서다. 둘이 갈리면 확인 칸 순서가 갈린다."""
        t = replace(self.spec.table("T2"), outputs=["C", "S"])
        self.assertEqual(split_columns(t), (["A", "B"], ["S", "C"]))

    def test_선언이_없으면_마지막_열_규칙_그대로다(self):
        t = replace(self.spec.table("T2"), outputs=None)
        self.assertEqual(split_columns(t), (["A", "B", "S"], ["C"]))

    def test_derived_식이_선언보다_우선한다(self):
        """어긋난 선언은 `validate.check_metadata` 가 error 로 잡는다."""
        t = replace(self.spec.table("T1"), outputs=["C"])
        self.assertEqual(split_columns(t), (["A", "B"], ["S", "C"]))

    def test_헤더에_없는_열을_가리켜도_던지지_않는다(self):
        """의미 결함이다 — 파서는 싣고 validate 가 findings 로 보고한다."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = Path(tmp.name) / "명세.md"
        target.write_text(self.SPEC.read_text(encoding="utf-8").replace(
            "- outputs: [S, C]", "- outputs: [S, 없는열]"), encoding="utf-8")
        self.assertEqual(parse_spec(target).table("T2").outputs, ["S", "없는열"])


class TestErrors(unittest.TestCase):
    """실물 명세를 한 군데씩 망가뜨려 파서가 거절하는지 본다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _broken(self, old, new):
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(
            CAPTURE.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
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
            parse_spec(self._broken("lab-spec/v2", "lab-spec/v0"))

    def test_missing_cell_table_raises(self):
        """네 가지 구조적 실패 중 하나. 나머지 셋과 함께 반드시 지켜져야 한다."""
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken(
                "| 스텝 | 조작", "삭제됨 | 조작"))     # stepped 표의 헤더를 깬다
        self.assertIn("마크다운 표가 없습니다", str(ctx.exception))

    def test_capture_with_a_cell_table_raises(self):
        """capture 는 셀 표 대신 expected 를 갖는다. 표가 붙어 있으면 데이터가
        조용히 버려지므로 — 증거가 LabSpec 이전에 사라진다 — 여기서 막는다."""
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken(
                "- source: manual:p11",
                "- source: manual:p11\n\n| A | B |\n|---|---|\n| 0 | 1 |"))
        self.assertIn("capture", str(ctx.exception))

    def test_duplicate_table_id_raises(self):
        """`.table()` 이 조용히 첫 번째만 돌려주므로 두 번째 표가 통째로 숨는다."""
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken("## T2 · ", "## T1 · "))
        self.assertIn("T1", str(ctx.exception))

    def test_duplicate_item_id_raises(self):
        """표 ID 중복을 막는 것과 같은 이유다 — `specdiff.compare_specs` 의
        `{i.id: i for i in items}` 가 나중 것만 남기고 앞 항목을 조용히
        지운다. 재생성물이 항목 ID 를 실수로 중복시키면(예: `E3.P2` 를
        두 번 쓰면) 그 항목이 통째로 대조에서 빠져 차이 0건(거짓 합격)이
        될 수 있다."""
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken("id: E10.P2", "id: E10.P1"))
        self.assertIn("E10.P1", str(ctx.exception))
        self.assertIn("두 번", str(ctx.exception))

    def test_duplicate_column_name_raises(self):
        """실물이 있다 — 실험3 반감산기 헤더가 `A B D B` 다(출력 borrow 가
        입력 `B` 와 이름이 같다). `header.index()` 가 첫 번째만 주므로
        역검산이 입력 열을 출력으로 보고 **표를 틀리게 고치라는** error 를
        낸다. 중복 표 ID 를 막는 것과 같은 이유다."""
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken("| 핀6 | 핀4 |", "| 7405 핀8 | 핀4 |"))
        self.assertIn("7405 핀8", str(ctx.exception))
        self.assertIn("두 번", str(ctx.exception))


class TestSemanticDefectsStaySilent(unittest.TestCase):
    """이 Task 의 핵심 설계다 — 파서가 의미 결함에 예외를 던지면 반쯤 망가진
    명세를 ⑤ 검증 스킬이 읽고 지적할 수 없게 된다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _spec_without(self, old, new=""):
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(
            CAPTURE.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
        )
        return parse_spec(target)

    def test_missing_source_parses_with_none(self):
        self.assertIsNone(self._spec_without("- source: manual:p16\n").table("T2").source)

    def test_missing_encoding_parses_with_none(self):
        self.assertIsNone(self._spec_without("- encoding: 0/1\n").table("T2").encoding)

    def test_unknown_role_is_carried_through_not_rejected(self):
        spec = self._spec_without("- kind: stepped", "- kind: stepped\n- role: bogus")
        self.assertEqual(spec.table("T2").role, "bogus")


class TestSchemaV2(unittest.TestCase):
    """`week:` 를 걷어낸 v2. v1 은 이제 구조적으로 거절된다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _write(self, text):
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(text, encoding="utf-8")
        return target

    def test_v2는_week_없이_읽힌다(self):
        md = (
            "---\n"
            "schema: lab-spec/v2\n"
            "experiment: 1\n"
            "title: Basic Gates\n"
            "source_manual: 강의노트/실험1. Basic Gates.pdf\n"
            'power: {VCC: "+5V", GND: "GND"}\n'
            "items:\n"
            "  - id: E1.P1\n"
            "    title: 3-input AND\n"
            "    device: [LED]\n"
            '    ics: ["74HC08"]\n'
            "    tables: [T1]\n"
            "---\n\n"
            "## T1 · 3-input AND\n\n"
            "- kind: truth-table\n"
            "- source: derived\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n"
        )
        path = self._write(md)
        spec = parse_spec(path)
        self.assertEqual(spec.experiment, 1)
        self.assertFalse(hasattr(spec, "week"))

    def test_v1은_거절한다(self):
        md = "---\nschema: lab-spec/v1\nexperiment: 1\n---\n"
        with self.assertRaises(SpecError) as cm:
            parse_spec(self._write(md))
        self.assertIn("lab-spec/v2", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
