import json
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config, validate
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
WEEK2_SPEC = ROOT / "실험01/체크리스트/명세.md"
WEEK2_NETLIST = ROOT / "실험01/결선도/netlist.md"


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

    def test_unreadable_cell_only_skips_its_own_row(self):
        """해독 불가 셀 하나가 나머지 행 검산을 통째로 막으면 안 된다 —
        예전엔 `break` 로 표 전체(그 target 의 남은 행)를 포기했다 (C1)."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A·B)\n\n"
            "| A | B | Y |\n|---|---|---|\n"
            "| ? | 0 | 0 |\n"      # 행1: A 해독 불가(don't-care 아님) — eval 실패
            "| 1 | 0 | 0 |\n"      # 행2: 정상, 일치
            "| 1 | 1 | 0 |\n"      # 행3: 정상 셀인데 값이 틀렸다 — break 였다면 못 잡는다
        ))
        errors = [f for f in validate.check_boolean(spec) if f.level == "error"]
        self.assertEqual(len(errors), 2)
        self.assertIn("행1", errors[0].where)
        self.assertIn("?", errors[0].message)   # 문제된 셀 값이 메시지에 있어야 한다
        self.assertIn("행3", errors[1].where)

    def test_repeated_identical_eval_errors_are_reported_once(self):
        """같은 열이 통째로 깨지면 모든 행에서 같은 메시지가 반복된다 —
        표 하나당 한 번만 보고한다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A·B)\n\n"
            "| A | B | Y |\n|---|---|---|\n"
            "| ? | 0 | 0 |\n| ? | 1 | 0 |\n| ? | 1 | 1 |\n"
        ))
        errors = [f for f in validate.check_boolean(spec) if f.level == "error"]
        self.assertEqual(len(errors), 1)

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
        for folder in ("실험01", "실험06", "실험10"):
            with self.subTest(folder=folder):
                spec = parse_spec(ROOT / folder / "체크리스트" / "명세.md")
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

    # --- 렌더되지 않는 영역은 검사에서 뺀다 -------------------------------
    # CSS 주석에 `position: fixed` 를 쓰는 건 자연스러운 저작인데, 이걸 잡으면
    # 그 템플릿이 낸 모든 HTML 이 영구히 error 가 되어 검사를 못 믿게 된다.

    def _doc(self, head, body):
        path = self.dir / "d.html"
        path.write_text(f"<html><head>{head}</head><body>{body}</body></html>",
                        encoding="utf-8")
        return path

    def test_backtick_in_a_css_comment_is_not_a_finding(self):
        path = self._doc("<style>/* `position: fixed` 는 위험 */ p{margin:0}</style>",
                         "<p>본문</p>")
        self.assertEqual(validate.check_rendered_html(path), [])

    def test_backtick_in_an_html_comment_is_not_a_finding(self):
        path = self._doc("", "<!-- `74HC08` 자리 --><p>본문</p>")
        self.assertEqual(validate.check_rendered_html(path), [])

    def test_bold_markers_in_a_script_are_not_a_finding(self):
        path = self._doc("<script>var s = '**x**';</script>", "<p>본문</p>")
        self.assertEqual(validate.check_rendered_html(path), [])

    def test_body_backticks_still_caught_when_a_style_block_exists(self):
        """비렌더 영역 제거가 문서를 통째로 삼키면 검사가 죽은 채로 통과한다."""
        path = self._doc("<style>/* `a` */</style>",
                         "<table><tr><td>`74HC08`</td></tr></table>")
        self.assertTrue(any("백틱" in f.message
                            for f in validate.check_rendered_html(path)))

    def test_body_backticks_still_caught_between_two_style_blocks(self):
        path = self._doc("<style>/* `a` */</style><style>/* `b` */</style>",
                         "<p>`74HC02`</p>")
        self.assertTrue(any("백틱" in f.message
                            for f in validate.check_rendered_html(path)))

    def test_body_backticks_still_caught_between_two_html_comments(self):
        """주석 제거가 greedy 면 첫 주석~마지막 주석 사이 본문이 통째로 사라져,
        검사가 죽은 채로 조용히 통과한다. 실제로 이 구성만 그 결함을 잡는다."""
        path = self._doc("", "<!-- 앞 --><table><tr><td>`74HC08`</td></tr>"
                             "</table><!-- 뒤 -->")
        self.assertTrue(any("백틱" in f.message
                            for f in validate.check_rendered_html(path)))

    def test_real_preview_template_is_clean(self):
        """① 프리뷰 템플릿(사용자가 디자인한 실물)이 통과해야 한다."""
        tmpl = ROOT / ".claude/skills/explain-lab-preview/template.html"
        rendered = self.dir / "preview.html"
        text = tmpl.read_text(encoding="utf-8")
        for ph in ("{{TITLE}}", "{{COURSE}}", "{{DATE}}", "{{CONTENT}}"):
            text = text.replace(ph, "샘플")
        rendered.write_text(text, encoding="utf-8")
        self.assertEqual(validate.check_rendered_html(rendered), [])

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
        html = ROOT / "실험01/체크리스트/체크리스트.html"
        self.assertEqual(validate.check_rendered_html(html), [])
        self.assertEqual(validate.check_embedded_images(html), [])

    # 예비보고서 HTML 을 보던 테스트가 여기 있었다. 실제로 깨진 채 제출됐던 것이
    # ②(기계 렌더)가 아니라 그 파일이었기 때문이다 — 표 셀 백틱 230개와,
    # 스크래치패드에서 렌더해 경로가 안 풀린 브레드보드 그림.
    #
    # **그 산출물이 더는 존재하지 않는다.** 보고서는 md 를 그대로 노션에 올리고
    # 사용자가 거기서 PDF 로 내보낸다 — 사람이 마크다운을 HTML 로 옮기는 단계가
    # 사라졌으므로 그 단계의 결함도 사라졌다. 같은 목적(사람이 쓴 보고서 본문을
    # 기계로 검사한다)은 `TestCheckNotionMarkdown.test_실제_실험1_예비보고서는_깨끗하다`
    # 가 md 자체를 대상으로 이어받았다.
    #
    # 위 `test_real_checklist_html_is_clean` 은 남긴다 — 체크리스트는 인쇄물이라
    # 여전히 HTML 을 거친다.


class FolderConventionTest(unittest.TestCase):
    """폴더 이름과 명세의 `experiment` 가 어긋나면 잡는다.

    리네임을 한 번 하고 끝내면 다음 주차에 다시 어긋난다. 규약은 사람이
    아니라 검사가 지킨다.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _spec_at(self, folder, experiment):
        """`<folder>/체크리스트/명세.md` 를 만들고 (경로, spec) 을 돌려준다."""
        d = self.dir / folder / "체크리스트"
        d.mkdir(parents=True)
        path = d / "명세.md"
        path.write_text(
            "---\n"
            "schema: lab-spec/v1\n"
            f"week: 2\n"
            f"experiment: {experiment}\n"
            "title: Basic Gates\n"
            "source_manual: x.pdf\n"
            'power: {VCC: "+5V", GND: "GND"}\n'
            "items:\n"
            "  - id: E1.P1\n"
            "    title: 첫 항목\n"
            "    device: [LED]\n"
            "    ics: ['74HC08']\n"
            "    tables: [T1]\n"
            "---\n\n"
            "# E1.P1 · 첫 항목\n\n"
            "## T1 · 표\n\n"
            "- kind: truth-table\n"
            "- source: 교안 p1\n"
            "- encoding: 0/1\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n| 1 | 1 |\n",
            encoding="utf-8",
        )
        return path, parse_spec(path)

    def test_맞으면_finding_이_없다(self):
        path, spec = self._spec_at("실험01", 1)
        self.assertEqual(validate.check_folder_convention(path, spec), [])

    def test_주차_이름이_남아_있으면_잡는다(self):
        path, spec = self._spec_at("2주차", 1)
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(any("실험01" in f.message for f in findings))

    def test_0을_안_채운_이름을_잡는다(self):
        path, spec = self._spec_at("실험1", 1)
        self.assertTrue(validate.check_folder_convention(path, spec))

    def test_번호가_어긋나면_잡는다(self):
        # 12주차는 실험10 이다. 실험12 폴더는 존재하면 안 된다.
        path, spec = self._spec_at("실험09", 10)
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(any("실험10" in f.message for f in findings))

    def test_범위_밖_번호에도_예외를_던지지_않는다(self):
        """⑤ 는 반쯤 망가진 문서에도 돌아야 한다 — 여기서 죽으면 안 된다."""
        path, spec = self._spec_at("실험11", 11)
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(findings)
        self.assertEqual(findings[0].level, "error")


def md_file(text):
    tmp = Path(tempfile.mkdtemp()) / "보고서.md"
    tmp.write_text(text, encoding="utf-8")
    return tmp


class TestCheckNotionMarkdown(unittest.TestCase):
    def test_실제_실험1_예비보고서는_깨끗하다(self):
        path = ROOT / "실험01/output/실험01_예비보고서.md"
        errors = [f for f in validate.check_notion_markdown(path)
                  if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_h5_이상은_error_다(self):
        """NFM 은 h5·h6 를 h4 로 강등한다. 절 깊이가 무너지면 ⑤ 의 섹션 검증이
        보는 헤딩 구조도 같이 무너진다."""
        findings = validate.check_notion_markdown(
            md_file("# 제목\n\n##### 다섯째 단계\n"))
        self.assertTrue(any(f.level == "error" and "h5" in f.message
                            for f in findings), findings)

    def test_각주는_error_다(self):
        findings = validate.check_notion_markdown(
            md_file("# 제목\n\n본문[^1]\n\n[^1]: 각주\n"))
        self.assertTrue(any(f.level == "error" and "각주" in f.message
                            for f in findings), findings)

    def test_각주_참조는_정의_줄과_이중_계수되지_않는다(self):
        """`[^1]: 각주` 의 `[^1]` 은 정의 패턴이 이미 세는데, 참조 패턴이
        anchor 없이 `[^n]` 을 잡으면 같은 자리를 또 센다 — 본문 참조는
        한 번뿐인데 참조 2개로 보고되면 카운트가 틀린다."""
        findings = validate.check_notion_markdown(
            md_file("# 제목\n\n본문[^1]\n\n[^1]: 각주\n"))
        ref = [f for f in findings if f.level == "error" and "각주 참조" in f.message]
        self.assertEqual(len(ref), 1, findings)
        self.assertIn("1개", ref[0].message)

    def test_각주_정의만_있고_본문_참조가_없으면_참조_finding이_없다(self):
        findings = validate.check_notion_markdown(
            md_file("# 제목\n\n[^1]: 각주\n"))
        ref = [f for f in findings if "각주 참조" in f.message]
        self.assertEqual(ref, [], findings)

    def test_열_수가_어긋난_표는_error_다(self):
        """깨진 표는 노션에서 통째로 뭉개진다."""
        findings = validate.check_notion_markdown(md_file(
            "# 제목\n\n| A | B |\n|---|---|\n| 0 | 0 |\n| 1 |\n"))
        self.assertTrue(any(f.level == "error" and "헤더는 2개" in f.message
                            for f in findings), findings)

    def test_상대경로_이미지는_error_가_아니라_info_다(self):
        """상대경로 이미지가 노션에서 깨지는 것은 결함이 아니라 설계다 — 사진은
        사용자가 노션에서 직접 끼워 넣는다. 그래서 '고쳐라'가 아니라 '무엇을 몇 장
        넣어야 하는지'를 알린다."""
        findings = validate.check_notion_markdown(md_file(
            "# 제목\n\n![브레드보드](../../.claude/assets/Breadboard.jpg)\n"))
        self.assertEqual([f.level for f in findings], ["info"])
        self.assertIn("Breadboard.jpg", findings[0].message)
        self.assertIn("1장", findings[0].message)

    def test_NFM_자체_블록_태그는_원시_HTML_로_잡지_않는다(self):
        """목차·여백 블록은 노션이 입력으로 받는 문법이다 (실측 확인). 이걸
        원시 HTML 로 잡으면 학생이 노션에서 잡은 레이아웃을 소스 md 에
        되돌려 넣을 수 없다 — 매 업로드마다 여백을 손으로 다시 잡아야 한다."""
        findings = validate.check_notion_markdown(md_file(
            '# 제목\n\n<table_of_contents color="gray"/>\n\n'
            "<empty-block/>\n<empty-block/>\n# 절\n본문\n"))
        self.assertEqual([f for f in findings if f.level == "error"], [])

    def test_NFM_이_안_받는_원시_HTML_은_여전히_잡는다(self):
        findings = validate.check_notion_markdown(md_file(
            '# 제목\n\n<figure class="photo-block">\n<img src="x.jpg">\n</figure>\n'))
        self.assertTrue(any(f.level == "error" and "원시 HTML" in f.message
                            for f in findings), findings)

    def test_원격_이미지는_알리지_않는다(self):
        findings = validate.check_notion_markdown(md_file(
            "# 제목\n\n![x](https://example.com/a.png)\n"))
        self.assertEqual(findings, [])

    def test_파일이_없으면_error_한_건이다(self):
        findings = validate.check_notion_markdown(Path("/없는/경로.md"))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].level, "error")


SRC = """# 실험1 Basic Gates 예비보고서

## 1. 실험 목적

목적 문장.

> 출처: 교안 p.2

## 2. 실험 이론

| A | B | C |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 1 | 1 |

> 출처: 교안 p.4
"""


class TestMarkdownShape(unittest.TestCase):
    def test_구조만_센다(self):
        shape = validate.markdown_shape(SRC)
        self.assertEqual(shape.headings,
                         ["실험1 Basic Gates 예비보고서", "1. 실험 목적", "2. 실험 이론"])
        self.assertEqual(shape.table_count, 1)
        self.assertEqual(shape.table_rows, 2)
        self.assertEqual(shape.quote_blocks, 2)

    def test_이어진_인용_줄은_한_블록이다(self):
        """여러 줄 인용이 한 줄로 합쳐지는 것은 노이즈지 손실이 아니다. 줄로 세면
        그 노이즈가 매번 error 로 올라온다."""
        self.assertEqual(validate.markdown_shape("> 가\n> 나\n").quote_blocks, 1)
        self.assertEqual(validate.markdown_shape("> 가\n\n> 나\n").quote_blocks, 2)

    def test_노션이_돌려준_HTML_표를_표로_센다(self):
        """실측 fixture(`notion_pull_markdown.json`)의 되읽기 markdown 은 파이프
        표가 아니라 HTML `<table>` 이다. `md.parse_tables()` 만 쓰면 이걸 0개로
        세서, 정상 왕복마다 "표가 통째로 사라졌다"는 거짓 경보가 뜬다."""
        pulled = json.loads((FIXTURES / "notion_pull_markdown.json")
                             .read_text("utf-8"))["markdown"]
        shape = validate.markdown_shape(pulled)
        self.assertEqual(shape.table_count, 1)
        self.assertEqual(shape.table_rows, 2)

    def test_header_row_없는_HTML_표는_모든_tr을_행으로_센다(self):
        """`header-row="true"` 가 없으면 뺄 헤더 행이 없다 — 모든 `<tr>` 이 데이터
        행이다."""
        text = "<table>\n<tr><td>0</td></tr>\n<tr><td>1</td></tr>\n</table>\n"
        shape = validate.markdown_shape(text)
        self.assertEqual(shape.table_count, 1)
        self.assertEqual(shape.table_rows, 2)


class TestCheckNotionRoundtrip(unittest.TestCase):
    def test_노이즈만_있으면_아무것도_보고하지_않는다(self):
        noisy = SRC.replace("|---|---|---|", "| --- | --- | --- |")
        self.assertEqual(validate.check_notion_roundtrip(SRC, noisy), [])

    def test_첫_헤딩이_없어도_보고하지_않는다(self):
        """노션이 첫 `#` 헤딩을 페이지 제목으로 흡수하므로 되읽기에 없을 수 있다."""
        without_h1 = SRC.split("\n", 1)[1]
        self.assertEqual(validate.check_notion_roundtrip(SRC, without_h1), [])

    def test_사라진_절을_error_로_보고한다(self):
        pulled = SRC.replace("## 2. 실험 이론", "")
        findings = validate.check_notion_roundtrip(SRC, pulled)
        self.assertTrue(any(f.level == "error" and "2. 실험 이론" in f.message
                            for f in findings), findings)

    def test_사라진_표를_error_로_보고한다(self):
        pulled = "\n".join(ln for ln in SRC.split("\n") if not ln.startswith("|"))
        findings = validate.check_notion_roundtrip(SRC, pulled)
        self.assertTrue(any(f.level == "error" and "표" in f.message
                            for f in findings), findings)

    def test_사라진_출처_인용을_error_로_보고한다(self):
        pulled = SRC.replace("> 출처: 교안 p.4", "")
        findings = validate.check_notion_roundtrip(SRC, pulled)
        self.assertTrue(any(f.level == "error" and "인용" in f.message
                            for f in findings), findings)

    def test_늘어난_것은_error_가_아니다(self):
        """사용자가 노션에서 절이나 표를 더한 것은 손실이 아니다."""
        pulled = SRC + "\n## 3. 추가한 절\n\n내용\n"
        self.assertEqual(validate.check_notion_roundtrip(SRC, pulled), [])

    def test_중복된_헤딩_중_하나만_사라져도_보고한다(self):
        """항목반복형 프리셋(`.claude/보고서양식.md`)처럼 같은 헤딩이 여러 번
        나오면, 집합 포함 검사(`h not in got.headings`)는 이름이 하나라도
        남아 있으면 손실을 못 본다. 다중집합 차만이 이걸 잡는다."""
        src = ("# 실험 보고서\n\n## 항목 1\n\n내용\n\n## 고찰\n\n내용1\n\n"
               "## 항목 2\n\n내용\n\n## 고찰\n\n내용2\n")
        pulled = "## 항목 1\n\n내용\n\n## 고찰\n\n내용1\n\n## 항목 2\n\n내용\n"
        findings = validate.check_notion_roundtrip(src, pulled)
        self.assertTrue(any(f.level == "error" and "고찰" in f.message
                            for f in findings), findings)

    def test_반복된_헤딩이_전부_남으면_보고하지_않는다(self):
        """같은 이름이 여러 번 나오되 아무것도 안 사라졌으면 findings 가 없어야
        한다 — 다중집합 차가 과다 보고하지 않는지 본다."""
        src = "# 실험 보고서\n\n## 고찰\n\n내용1\n\n## 고찰\n\n내용2\n"
        pulled = "## 고찰\n\n내용1\n\n## 고찰\n\n내용2\n"
        self.assertEqual(validate.check_notion_roundtrip(src, pulled), [])

    def test_HTML_표로_바뀐_것은_손실로_보지_않는다(self):
        """이게 진짜 회귀 테스트다 — fixture 그대로의 되읽기(HTML 표)를 파이프
        표 소스와 비교했을 때 findings 가 있으면, 모든 업로드가 "표가 0개로
        줄었다"는 거짓 경보를 낸다는 뜻이다."""
        pulled = json.loads((FIXTURES / "notion_pull_markdown.json")
                             .read_text("utf-8"))["markdown"]
        src = ("# 표 왕복 테스트\n\n첫 문단이다.\n## 표 검사\n\n"
               "| A | B | C |\n|---|---|---|\n| 0 | 0 | 0 |\n| 1 | 1 | 1 |\n\n"
               "> 출처: 프로브\n")
        self.assertEqual(validate.check_notion_roundtrip(src, pulled), [])


class TestCheckPulledImages(unittest.TestCase):
    """되읽은 본문에서 **아직 안 끼운 그림**을 잡는다.

    실험01 v7 에서 브레드보드 그림이 빈 링크로 올라갔는데 아무 검사도 잡지
    못했다 — `check_notion_markdown` 은 올리기 전 md 만 보고,
    `check_notion_roundtrip` 은 헤딩·표·인용 개수만 세어 그림을 안 본다.
    """

    ROOT = Path(__file__).resolve().parents[1]
    BEFORE = ROOT / "실험01/output/실험01_예비보고서_notion_baseline_v7.md"
    AFTER = ROOT / "실험01/output/실험01_예비보고서_notion_v7.md"

    def test_빈_링크를_error_로_잡는다(self):
        got = validate.check_pulled_images("![브레드보드 작도 캔버스]()")
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0].level, "error")
        self.assertIn("브레드보드 작도 캔버스", got[0].message)

    def test_채워진_링크는_잡지_않는다(self):
        text = "![그림](https://prod-files-secure.s3.amazonaws.com/a/b.jpg)"
        self.assertEqual(validate.check_pulled_images(text), [])

    def test_공백만_있는_링크도_빈_것으로_센다(self):
        # 노션이 자리는 남기고 대상만 비우는 변형을 실제로 만든 적이 있다.
        got = validate.check_pulled_images("![x](   )")
        self.assertEqual(len(got), 1, got)

    def test_그림이_여러_장이면_빈_것만_센다(self):
        text = "![a]() 와 ![b](https://x/y.jpg) 와 ![c]()"
        got = validate.check_pulled_images(text)
        self.assertEqual(len(got), 2, got)
        self.assertIn("a", got[0].message)
        self.assertIn("c", got[1].message)

    def test_그림이_없으면_아무것도_보고하지_않는다(self):
        self.assertEqual(validate.check_pulled_images("# 제목\n\n본문뿐이다."), [])

    def test_실험01_v7_의_넣기_전_판본에서_실제로_잡는다(self):
        # 실측 회귀. 이 파일이 바로 사용자가 눈으로 찾아낸 그 상태다.
        got = validate.check_pulled_images(self.BEFORE.read_text(encoding="utf-8"))
        self.assertEqual(len(got), 1, got)
        self.assertIn("브레드보드 작도 캔버스", got[0].message)

    def test_실험01_v7_의_넣은_뒤_판본에서는_조용하다(self):
        # 거짓 경보를 내지 않는다는 쪽의 실측 회귀. 둘이 한 쌍이다.
        got = validate.check_pulled_images(self.AFTER.read_text(encoding="utf-8"))
        self.assertEqual(got, [], got)


class TestCheckReportWrapping(unittest.TestCase):
    """문단이 여러 줄로 쪼개져 있는지 본다.

    노션은 원본의 줄바꿈을 하나하나 그대로 렌더한다. 실험02 초판이 76열에
    맞춰 감싸인 채 올라갔고, 노션에서 문장 중간이 토막 났다. 사용자가 v2 를
    고치려다 눈으로 찾았다 — 그때까지 아무 검사도 이것을 안 봤다.
    """

    ROOT = ROOT
    CANON = ROOT / "실험01/output/실험01_예비보고서.md"
    WEEK3 = ROOT / "실험02/output/실험02_예비보고서.md"

    def test_문단이_두_줄로_쪼개져_있으면_잡는다(self):
        got = validate.check_report_wrapping(
            "출력 규격이 입력 규격보다 안쪽으로 여유를 두고 있어서, 배선에서\n"
            "잡음이 실려도 다음 단이 여전히 옳게 판정한다.")
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0].level, "error")

    def test_한_줄_문단은_잡지_않는다(self):
        self.assertEqual(validate.check_report_wrapping(
            "출력 규격이 입력 규격보다 안쪽으로 여유를 두고 있어서 잡음이 실려도 된다."), [])

    def test_빈_줄로_나뉜_두_문단은_잡지_않는다(self):
        self.assertEqual(validate.check_report_wrapping(
            "첫 문단이다.\n\n둘째 문단이다."), [])

    def test_콜론_뒤에_수식을_따로_놓은_것은_의도된_줄바꿈이다(self):
        # 규칙이 아니라 저자의 배치다. 이것까지 잡으면 거짓 경보가 된다.
        self.assertEqual(validate.check_report_wrapping(
            "- 입력 HIGH → 출력 LOW → 부하에서 전류를 빨아들인다(sinking):\n"
            "  `Rn(on) = V_OLmax / I_OLmax`"), [])

    def test_표와_헤딩과_태그는_흐름_밖이다(self):
        self.assertEqual(validate.check_report_wrapping(
            "# 실험 이론\n## 잡음 여유\n| 핀 | 처리 |\n|---|---|\n| 3 | GND |\n"
            "<empty-block/>\n\t| 중첩 | 표 |"), [])

    def test_불릿의_이어진_줄도_잡는다(self):
        got = validate.check_report_wrapping(
            "- 전파지연 — 입력이 출력으로 전달되는 시간. 입력과 출력이 각각\n"
            "  VCC 의 50% 를 지나는 시점 사이를 잰다.")
        self.assertEqual(len(got), 1, got)

    def test_여러_군데여도_한_줄로_요약한다(self):
        # 160곳이 나오면 160줄을 뱉는 검사는 아무도 안 읽는다.
        got = validate.check_report_wrapping("가\n나\n다\n라")
        self.assertEqual(len(got), 1, got)
        self.assertIn("3곳", got[0].message)

    def test_실험01_승인본은_조용하다(self):
        # 실측 통제군. 일곱 번 올려 문제없던 판본이다.
        got = validate.check_report_wrapping(self.CANON.read_text(encoding="utf-8"))
        self.assertEqual(got, [], got)

    def test_실험02_되감은_판본은_조용하다(self):
        got = validate.check_report_wrapping(self.WEEK3.read_text(encoding="utf-8"))
        self.assertEqual(got, [], got)

    def test_check_notion_markdown_이_이_검사를_함께_낸다(self):
        # 배선이 이 검사의 유일한 발화 경로다. `check_notion_markdown` 에서
        # 호출을 지우면 함수가 죽은 코드가 되는데 단위 테스트는 그대로 통과한다.
        found = validate.check_notion_markdown(md_file(
            "# 제목\n\n문단이 여기서 끊기고\n다음 줄로 이어진다."))
        self.assertTrue(any("줄바꿈" in f.where for f in found), found)


if __name__ == "__main__":
    unittest.main()
