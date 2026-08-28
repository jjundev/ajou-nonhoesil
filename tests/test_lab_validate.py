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

    def test_skips_dont_care_rows_but_still_checks_the_rest(self):
        """don't-care 입력 행은 구체적 식으로 검산할 수 없다. 건너뛰되
        그 뒤의 진짜 오류는 계속 잡아야 한다 — `break` 로 표 전체를 포기하면
        don't-care 행 하나가 나머지 검산을 통째로 가려버린다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A·B)\n\n"
            "| A | B | Y |\n|---|---|---|\n"
            "| 0 | x | 0 |\n"      # 검산 불가 — 건너뛴다
            "| 1 | 0 | 0 |\n"
            "| 1 | 1 | 0 |\n"      # 진짜 오류
        ))
        errors = [f for f in validate.check_boolean(spec) if f.level == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("행3", errors[0].where)

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

    def test_checks_manual_sourced_tables_too(self):
        """`derived` 가 아니어도 행 수는 봐야 한다. 이 검사를 derived 로만
        제한하면 6주차 전부와 2주차 이론표 4개가 사각지대가 된다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: H/L\n- source: manual:p4\n\n"
            "| A | B | C |\n|---|---|---|\n"
            "| L | L | L |\n| L | H | L |\n| H | L | L |\n"   # 4행이어야 하는데 3행
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

    def test_bad_cell_contents_are_errors(self):
        """`\\|`·`<br>`·탭은 표를 깨거나 렌더링을 망가뜨린다."""
        cases = ((r"a\|b", "escape 된 파이프"), ("a<br>b", "<br> 태그"),
                 ("a\tb", "탭 문자"))
        for bad, label in cases:
            with self.subTest(cell=label):
                spec = spec_from(HEAD + (
                    "- kind: truth-table\n- encoding: 0/1\n- source: manual:p4\n\n"
                    f"| A | Y |\n|---|---|\n| {bad} | 0 |\n"
                ))
                messages = [f.message for f in validate.check_table_integrity(spec)]
                self.assertTrue(any(label in m for m in messages), messages)

    def test_ragged_row_is_an_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n- source: manual:p4\n\n"
            "| A | B | Y |\n|---|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("헤더" in f.message
                            for f in validate.check_table_integrity(spec)))


class TestNetlist(unittest.TestCase):
    def _netlist(self, text):
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_power_and_floating_pin_handling_is_an_error(self):
        """플로팅 입력은 이 과목의 대표 실패 원인이다. 이 검사가 존재하는 이유다."""
        spec = parse_spec(WEEK2_SPEC)
        findings = validate.check_netlist(
            self._netlist("- U1 = 74HC08\n  - pin 1 ← 입력 A\n"), spec)
        messages = " ".join(f.message for f in findings if f.level == "error")
        for token in ("VCC", "GND", "미사용"):
            with self.subTest(token=token):
                self.assertIn(token, messages)

    def test_ic_missing_from_netlist_is_a_warn(self):
        spec = parse_spec(WEEK2_SPEC)
        findings = validate.check_netlist(
            self._netlist("VCC GND 미사용\n"), spec)
        warns = [f for f in findings if f.level == "warn"]
        self.assertTrue(warns)
        self.assertIn("74HC08", " ".join(f.message for f in warns))

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

    def test_a_combined_heading_does_not_satisfy_two_sections(self):
        """`# 실험 결과 분석` 한 줄이 `실험 결과` 와 `결과 분석` 을 동시에
        만족시켜 버리면, 정말로 빠진 섹션이 조용히 통과한다."""
        fmt = config.load_report_format(ROOT)
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 실험 결과 분석\n내용\n", encoding="utf-8")
        missing = [f for f in validate.check_report_sections(tmp, fmt.result)
                   if "없다" in f.message]
        names = " ".join(f.message for f in missing)
        self.assertIn("실험 결과", names)
        self.assertIn("결과 분석", names)

    def test_per_item_sections_must_repeat(self):
        """항목반복형은 결보 29편 중 14편의 실제 구조다. 고찰이 항목마다 온다."""
        fmt = config.load_report_format(ROOT, preset="항목반복형")
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 결선도\n# 구성한 회로\n# 실험 결과\n# 고찰\n"
                       "# 전체적인 고찰\n", encoding="utf-8")
        findings = validate.check_report_sections(tmp, fmt.result, item_count=3)
        self.assertTrue(any("항목마다 반복" in f.message for f in findings))

    def test_optional_sections_are_not_required(self):
        fmt = config.load_report_format(ROOT)
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 실험 결과\n# 예비 비교\n# 결과 분석\n# 고찰\n",
                       encoding="utf-8")
        findings = validate.check_report_sections(tmp, fmt.result)
        self.assertTrue(all("추가 공부" not in f.message for f in findings))


class TestRenderedHtmlChecks(unittest.TestCase):
    """제출본에서 실제로 일어난 두 결함을 고정한다 — 표 셀의 백틱 유출과,
    다른 디렉토리에서 렌더해 깨진 채 굳은 그림. 둘 다 텍스트로는 안 보인다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _html(self, body):
        path = self.dir / "r.html"
        path.write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
        return path

    def test_stray_backticks_in_a_table_cell_are_an_error(self):
        path = self._html("<table><tr><td>`74HC08`</td></tr></table>")
        self.assertTrue(any("백틱" in f.message
                            for f in validate.check_rendered_html(path)))

    def test_stray_bold_markers_are_an_error(self):
        path = self._html("<p>**중요**</p>")
        self.assertTrue(any("굵게" in f.message
                            for f in validate.check_rendered_html(path)))

    def test_properly_converted_html_is_clean(self):
        path = self._html("<table><tr><td><code>74HC08</code></td></tr></table>"
                          "<p><strong>중요</strong></p>")
        self.assertEqual(validate.check_rendered_html(path), [])

    def test_missing_image_is_an_error(self):
        path = self._html('<img src="../assets/nope.jpg">')
        findings = validate.check_embedded_images(path)
        self.assertTrue(any("찾을 수 없다" in f.message for f in findings))

    def test_present_image_is_clean(self):
        (self.dir / "there.jpg").write_bytes(b"\xff\xd8\xff")
        path = self._html('<img src="there.jpg">')
        self.assertEqual(validate.check_embedded_images(path), [])

    def test_data_and_remote_uris_are_skipped(self):
        path = self._html('<img src="data:image/png;base64,AAAA">'
                          '<img src="https://example.com/a.png">')
        self.assertEqual(validate.check_embedded_images(path), [])

    def test_real_checklist_html_is_clean(self):
        """② 가 만든 실물은 통과해야 한다 — 그쪽은 코드가 렌더하므로."""
        html = ROOT / "2주차/체크리스트/체크리스트.html"
        self.assertEqual(validate.check_rendered_html(html), [])
        self.assertEqual(validate.check_embedded_images(html), [])


if __name__ == "__main__":
    unittest.main()
