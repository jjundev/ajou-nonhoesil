import tempfile
import unittest
from pathlib import Path

from scripts.lab import config, validate
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
WEEK2_SPEC = ROOT / "2주차/체크리스트/명세.md"
WEEK2_NETLIST = ROOT / "2주차/결선도/netlist.md"


def spec_from(text):
    tmp = tempfile.mkdtemp()
    path = Path(tmp) / "명세.md"
    path.write_text(text, encoding="utf-8")
    return parse_spec(path)


HEAD = """---
schema: lab-spec/v1
week: 2
experiment: 1
title: Basic Gates
source_manual: from_the_past/정리/강의노트/실험1.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E1.P1-1
    title: 3-input AND
    device: [LED]
    ics: ["74HC08"]
    tables: [T1]
---

## T1 · 3-input AND 진리표

"""


class TestRealWeek2SpecIsClean(unittest.TestCase):
    def test_no_errors(self):
        findings = validate.validate_spec(parse_spec(WEEK2_SPEC))
        errors = [f for f in findings if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))


class TestBooleanCrosscheck(unittest.TestCase):
    def test_catches_a_wrong_output_bit(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A·B·C)\n\n"
            "| A | B | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 0 | 0 | 1 | 0 |\n"
            "| 0 | 1 | 0 | 0 |\n| 0 | 1 | 1 | 0 |\n"
            "| 1 | 0 | 0 | 0 |\n| 1 | 0 | 1 | 0 |\n"
            "| 1 | 1 | 0 | 1 |\n| 1 | 1 | 1 | 1 |\n"   # 7행이 틀렸다
        ))
        errors = [f for f in validate.check_boolean(spec) if f.level == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("행7", errors[0].where)

    def test_accepts_a_correct_table(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A+B+C)\n\n"
            "| A | B | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 0 | 0 | 1 | 1 |\n"
            "| 0 | 1 | 0 | 1 |\n| 0 | 1 | 1 | 1 |\n"
            "| 1 | 0 | 0 | 1 |\n| 1 | 0 | 1 | 1 |\n"
            "| 1 | 1 | 0 | 1 |\n| 1 | 1 | 1 | 1 |\n"
        ))
        self.assertEqual(validate.check_boolean(spec), [])

    def test_crosschecks_every_output_of_a_multi_output_table(self):
        """실험1 p13 은 출력이 3개다. 하나만 검산하고 넘어가면 안 된다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (X = A+B ; Y = A·B)\n\n"
            "| A | B | X | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 0 | 1 | 1 | 0 |\n"
            "| 1 | 0 | 1 | 0 |\n| 1 | 1 | 1 | 0 |\n"   # Y 마지막 행이 틀렸다
        ))
        errors = [f for f in validate.check_boolean(spec) if f.level == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("Y", errors[0].message)

    def test_works_on_hl_encoded_tables(self):
        """평가용으로만 비트로 읽는다. 데이터는 H/L 그대로 남는다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: H/L\n"
            "- source: derived (Y = A·B)\n\n"
            "| A | B | Y |\n|---|---|---|\n"
            "| L | L | L |\n| L | H | L |\n"
            "| H | L | L |\n| H | H | H |\n"
        ))
        self.assertEqual(validate.check_boolean(spec), [])
        self.assertEqual(spec.table("T1").rows[0], ["L", "L", "L"])


class TestRowCount(unittest.TestCase):
    def test_warns_when_rows_are_not_two_to_the_n(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A·B·C)\n\n"
            "| A | B | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 1 | 1 | 1 | 1 |\n"
        ))
        warns = validate.check_row_count(spec)
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].level, "warn")

    def test_skips_tables_that_use_dont_care(self):
        """실험6 R-S Latch 는 3입력인데 `x x 0` 축약으로 5행이다. 정상이다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = S·R·C)\n\n"
            "| S | R | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 1 | 0 |\n| x | x | 0 | 0 |\n"
        ))
        self.assertEqual(validate.check_row_count(spec), [])


class TestMetadata(unittest.TestCase):
    def test_missing_source_is_an_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("source" in f.message
                            for f in validate.check_metadata(spec)))

    def test_missing_encoding_is_an_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- source: manual:p4\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("encoding" in f.message
                            for f in validate.check_metadata(spec)))

    def test_malformed_derived_expression_is_an_error(self):
        """`derived_parts` 가 빈 리스트를 주면 `split_columns` 가 조용히 잘못된
        입출력 분할을 내놓는다. 여기서 잡지 않으면 아무도 못 잡는다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (X = A+B ; 이건 대입이 아니다 ; Z = A)\n\n"
            "| A | B | X | Z |\n|---|---|---|---|\n| 0 | 0 | 0 | 0 |\n"
        ))
        self.assertTrue(any("식을 읽지 못했다" in f.message
                            for f in validate.check_metadata(spec)))

    def test_capture_needs_expected_prose_not_encoding(self):
        spec = spec_from(HEAD + "- kind: capture\n- source: manual:p11\n")
        messages = [f.message for f in validate.check_metadata(spec)]
        self.assertTrue(any("expected" in m for m in messages))
        self.assertFalse(any("encoding" in m for m in messages))


class TestTableIntegrity(unittest.TestCase):
    def test_orphan_table_is_an_error(self):
        """파서는 반대 방향만 막는다. 고아 표는 여기서 잡아야 한다."""
        spec = spec_from(HEAD.replace("tables: [T1]", "tables: []") + (
            "- kind: truth-table\n- encoding: 0/1\n- source: manual:p4\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("가리키지 않는다" in f.message
                            for f in validate.check_orphan_tables(spec)))

    def test_real_specs_have_no_orphans(self):
        for week in ("2주차", "6주차", "12주차"):
            with self.subTest(week=week):
                spec = parse_spec(ROOT / week / "체크리스트" / "명세.md")
                self.assertEqual(validate.check_orphan_tables(spec), [])

    def test_ragged_row_is_an_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n- source: manual:p4\n\n"
            "| A | B | Y |\n|---|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("헤더" in f.message
                            for f in validate.check_table_integrity(spec)))


class TestNetlist(unittest.TestCase):
    def test_real_week2_netlist_has_power_and_floating_pins(self):
        spec = parse_spec(WEEK2_SPEC)
        errors = [f for f in validate.check_netlist(WEEK2_NETLIST, spec)
                  if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_missing_file_is_an_error(self):
        spec = parse_spec(WEEK2_SPEC)
        findings = validate.check_netlist(ROOT / "없는파일.md", spec)
        self.assertEqual(findings[0].level, "error")


class TestReportSections(unittest.TestCase):
    def test_missing_section_from_the_format_file(self):
        fmt = config.load_report_format(ROOT)
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 실험 목적\n내용\n# 실험 이론\n내용\n", encoding="utf-8")
        missing = [f.message for f in validate.check_report_sections(tmp, fmt.pre)]
        self.assertTrue(any("실험 부품" in m for m in missing))

    def test_optional_sections_are_not_required(self):
        fmt = config.load_report_format(ROOT)
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 실험 결과\n# 예비 비교\n# 결과 분석\n# 고찰\n",
                       encoding="utf-8")
        findings = validate.check_report_sections(tmp, fmt.result)
        self.assertTrue(all("추가 공부" not in f.message for f in findings))


if __name__ == "__main__":
    unittest.main()
