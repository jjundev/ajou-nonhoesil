import json
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config, validate
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
WEEK2_SPEC = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"
WEEK2_NETLIST = ROOT / config.experiment_dir(1) / "결선도/netlist.md"


def spec_from(text):
    tmp = tempfile.mkdtemp()
    path = Path(tmp) / "명세.md"
    path.write_text(text, encoding="utf-8")
    return parse_spec(path)


HEAD = """---
schema: lab-spec/v2
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
        for n in (1, 6, 10):
            with self.subTest(experiment=n):
                spec = parse_spec(
                    ROOT / config.experiment_dir(n) / "체크리스트" / "명세.md")
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

    def test_info_가_error_앞으로_끼어들지_않는다(self):
        # `test_missing_file_is_an_error` 가 `findings[0].level` 을 본다.
        # 진단 문장 info 를 앞에 붙이면 그 테스트가 조용히 깨진다.
        spec = parse_spec(WEEK2_SPEC)
        findings = validate.check_netlist(
            self._netlist("값이 크게 나오면 의심한다\n"), spec)
        self.assertEqual(findings[0].level, "error")   # VCC 누락
        self.assertEqual(findings[-1].level, "info")


class TestNetlistCircuits(unittest.TestCase):
    """회로 메타의 **의미** 결함. 구조 결함은 `netlist_parser` 가 예외로 던진다."""

    HEAD = """---
schema: lab-netlist/v2
experiment: 1
spec: ../체크리스트/명세.md
---

"""

    def _netlist(self, circuits):
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(self.HEAD + circuits, encoding="utf-8")
        return parse_netlist(path)

    def test_없는_항목을_가리키면_error(self):
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(
            "# C1\n\n- kind: circuit\n- id: C1\n- item: E9.P9\n- tables: [T1]\n")
        errors = [f for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertIn("E9.P9", " ".join(f.message for f in errors))

    def test_없는_표를_가리키면_error(self):
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(
            "# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T99]\n")
        errors = [f for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertIn("T99", " ".join(f.message for f in errors))

    def test_diagram_이_없으면_warn(self):
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(
            "# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T1]\n")
        warns = [f for f in validate.check_netlist_circuits(netlist, spec)
                 if f.level == "warn" and f.where.endswith("C1")]
        self.assertTrue(warns)
        self.assertIn("breadboard-diagram", " ".join(f.message for f in warns))

    def test_diagram_파일이_없으면_warn(self):
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(
            "# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n"
            "- tables: [T1]\n- diagram: 없는그림.png\n")
        warns = [f for f in validate.check_netlist_circuits(netlist, spec)
                 if f.level == "warn"]
        self.assertIn("없는그림.png", " ".join(f.message for f in warns))

    def test_어느_회로도_안_가리키는_기록표는_warn(self):
        """인쇄본은 회로를 통해서만 표를 싣는다 — 고아 표는 조용히 사라진다."""
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(
            "# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T1]\n")
        warns = " ".join(f.message for f in
                         validate.check_netlist_circuits(netlist, spec)
                         if f.level == "warn")
        for orphan in ("T2", "T3", "T4", "T5"):
            with self.subTest(table=orphan):
                self.assertIn(orphan, warns)

    def test_참조표는_고아로_치지_않는다(self):
        """T6~T9 는 role: reference 라 인쇄본에 애초에 안 들어간다."""
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(
            "# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T1]\n")
        warns = " ".join(f.message for f in
                         validate.check_netlist_circuits(netlist, spec)
                         if f.level == "warn")
        for ref in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=ref):
                self.assertNotIn(ref, warns)

    def test_참조표를_가리키면_error(self):
        """명세 항목의 tables 를 회로에 그대로 복사하면 교안 이론표가 확인 칸을
        달고 인쇄된다. 실험1 의 E1.P1-1 은 [T1, T2, T6, T7] 이라 자연스러운 실수다."""
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(
            "# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T1, T6]\n")
        errors = [f for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertIn("T6", " ".join(f.message for f in errors))
        self.assertNotIn("T1 는", " ".join(f.message for f in errors))

    def test_실험01_실물은_error_가_없다(self):
        spec = parse_spec(WEEK2_SPEC)
        netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        errors = [f for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_실험01_실물은_다섯_회로_모두_diagram_을_갖는다(self):
        """C2(OR)·C4(NOR) 결선도가 이제 존재한다 — 더는 부재를 warn 할 대상이
        아니다. `check_netlist_circuits` 는 diagram 줄이 없거나 그 파일이
        없을 때만 warn 하므로(위 `test_diagram_이_없으면_warn`·
        `test_diagram_파일이_없으면_warn` 참고), C1~C5 다섯 회로 전부에
        diagram 이 있고 파일도 존재하면 그 종류의 warn 은 하나도 없어야
        한다."""
        spec = parse_spec(WEEK2_SPEC)
        netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        self.assertEqual([c.id for c in netlist.circuits],
                         ["C1", "C2", "C3", "C4", "C5"])
        for circuit in netlist.circuits:
            with self.subTest(circuit=circuit.id):
                self.assertTrue(circuit.diagram,
                    f"{circuit.id} 에 diagram 줄이 없다")
                self.assertTrue(
                    (netlist.path.parent / circuit.diagram).exists(),
                    f"{circuit.id} 의 diagram 파일 {circuit.diagram} 이 없다")
        warns = [f for f in validate.check_netlist_circuits(netlist, spec)
                 if f.level == "warn" and "diagram" in f.message]
        self.assertEqual(warns, [], "\n".join(str(f) for f in warns))

    # 표 줄 warn 을 검증하던 두 테스트(`test_회로_본문의_표는_인쇄되지_않으므로_warn`·
    # `test_lookup_절의_표는_warn_하지_않는다`)가 여기 있었다. 렌더러가 표를
    # 인쇄하게 되면서 그 경고 자체가 거짓이 되어 지웠다 — 같은 자리(칩 선언
    # 부재·배선 부재)는 아래 `NetlistCircuitWiring` 이 이어받는다.


class TestDiagnosticClaims(unittest.TestCase):
    """방향을 붙인 문장을 센다. **판정하지 않는다** — 방향이 맞는지는
    절차의 산술을 굴려 봐야 알고 그건 코드가 못 한다."""

    def test_방향을_붙인_줄을_info_로_센다(self):
        findings = validate.check_diagnostic_claims(
            "값이 크게 나오면 배선을 의심한다.\n평범한 서술이다.\n", "x.md")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].level, "info")
        self.assertEqual(findings[0].where, "x.md:1")

    def test_error_나_warn_으로_올리지_않는다(self):
        # 코드가 판정하면 방향이 맞는 문장까지 고치게 된다.
        findings = validate.check_diagnostic_claims("의심한다\n", "x.md")
        self.assertEqual([f.level for f in findings], ["info"])

    def test_실험02_명세에서_실제로_잡힌다(self):
        # 이 부류로 두 번 거꾸로였던 문서다. 목록이 비면 검사가 무의미하다.
        spec = parse_spec(ROOT / config.experiment_dir(2) / "체크리스트/명세.md")
        infos = [f for f in validate.validate_spec(spec) if f.level == "info"]
        self.assertTrue(infos, "실험02 명세에서 한 건도 안 잡혔다")

    def test_결선도에도_건다(self):
        # 결선도 쪽이 명세보다 많다 (실험10: 9 대 1).
        spec = parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md")
        infos = [f for f in validate.check_netlist(
            ROOT / config.experiment_dir(10) / "결선도/netlist.md", spec) if f.level == "info"]
        self.assertTrue(infos, "실험10 결선도에서 한 건도 안 잡혔다")


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
        html = ROOT / config.experiment_dir(1) / "체크리스트/체크리스트.html"
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

    def _spec_at(self, folder, experiment, base=config.EXPERIMENT_BASE):
        """`<base>/<folder>/체크리스트/명세.md` 를 만들고 (경로, spec) 을 준다.

        `base` 를 기본값으로 둔 것은 실제 배치가 `보고서/실험NN/...` 이기
        때문이다. 위치를 일부러 어긋내는 테스트만 이 인자를 넘긴다.
        """
        d = self.dir / base / folder / "체크리스트" if base \
            else self.dir / folder / "체크리스트"
        d.mkdir(parents=True)
        path = d / "명세.md"
        path.write_text(
            "---\n"
            "schema: lab-spec/v2\n"
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

    def test_요구하는_이름에_기반_경로가_섞이지_않는다(self):
        """검사는 조부모 폴더의 **이름** 과 견준다. 기대값에 `보고서/` 가
        섞이면 옳게 놓인 명세까지 전부 error 가 되고, 메시지도
        "폴더 이름이 `실험1` 인데 `보고서/실험01` 를 요구한다"로 읽힌다."""
        path, spec = self._spec_at("실험1", 1)
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(findings)
        self.assertTrue(any("`실험01`" in f.message for f in findings))
        self.assertFalse(any(config.EXPERIMENT_BASE in f.message
                             for f in findings), findings)

    def test_기반_폴더_밖에_있으면_잡는다(self):
        """이름은 맞는데 위치가 옛 루트인 경우. 이름만 보던 시절엔 통과했다 —
        2026-09 이동에서 실제로 아홉 스킬이 이 상태를 못 보고 지나갔다."""
        path, spec = self._spec_at("실험01", 1, base="")
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(findings)
        self.assertTrue(any(config.EXPERIMENT_BASE in f.message
                            for f in findings), findings)

    def test_엉뚱한_기반_폴더도_잡는다(self):
        path, spec = self._spec_at("실험01", 1, base="문서")
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(any("문서" in f.message for f in findings), findings)

    def test_이름과_위치가_둘_다_틀리면_둘_다_보고한다(self):
        """한쪽만 알려주면 고친 뒤 다시 돌려야 나머지가 드러난다."""
        path, spec = self._spec_at("실험1", 1, base="")
        findings = validate.check_folder_convention(path, spec)
        self.assertEqual(len(findings), 2, findings)

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
        path = ROOT / config.experiment_dir(1) / "output/실험01_예비보고서.md"
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
    BEFORE = ROOT / config.experiment_dir(1) / "output/실험01_예비보고서_notion_baseline_v7.md"
    AFTER = ROOT / config.experiment_dir(1) / "output/실험01_예비보고서_notion_v7.md"

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
    CANON = ROOT / config.experiment_dir(1) / "output/실험01_예비보고서.md"
    WEEK3 = ROOT / config.experiment_dir(2) / "output/실험02_예비보고서.md"

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

    def test_번호_목록은_쪼개진_문단이_아니다(self):
        # 재생성 대조(⑦ 14단계)가 잡은 오탐이다. `1.` `2.` 를 산문으로 봐서
        # 연달아 오는 번호 단계를 통째로 error 로 냈다. 규칙은 번호 목록을
        # 금지하지 않는데 검사가 금지한 셈이라, 에이전트가 불릿으로 우회했다.
        self.assertEqual(validate.check_report_wrapping(
            "1. 첫째 단계다.\n2. 둘째 단계다.\n3. 셋째 단계다."), [])

    def test_번호_목록의_이어진_줄은_잡는다(self):
        # 오탐을 없애면서 진짜 감싸기까지 놓치면 안 된다.
        got = validate.check_report_wrapping(
            "1. 첫째 단계인데 문장이 길어서\n   다음 줄로 이어진다.")
        self.assertEqual(len(got), 1, got)

    def test_그림_줄은_쪼개진_문단이_아니다(self):
        # 그림은 블록이다. 앞 산문과 붙어 있어도 "문장이 토막 났다" 가 아니다.
        self.assertEqual(validate.check_report_wrapping(
            "아래 캔버스에 미리 그려 둔다.\n![브레드보드 작도 캔버스](x.jpg)"), [])

    def test_되읽은_baseline_은_이_검사의_범위가_아니다(self):
        # 범위를 못 박는 테스트다. 노션 되읽기는 문단 사이 빈 줄을 지워서
        # **각자 완결된** 문단이 나란히 붙는다 — 쪼개진 것이 아닌데도 잡힌다.
        # 실험01 승인본은 0곳인데 그 v7 되읽기는 잡힌다는 사실 자체를 고정해
        # 둔다. 이 함수는 `check_notion_markdown` 이 부르는 자리, 곧 올리기 전
        # 원본에만 쓴다. 검사를 "앞줄이 문장 중간에서 끝났을 때만" 으로 좁히면
        # 이 오탐은 사라지지만 실물 감싸기 160곳 중 2곳(문장이 줄바꿈 자리에서
        # 딱 끝난 경우)을 놓친다 — 실제 호출 경로에 없는 오탐을 막자고
        # 진짜 대상에서 약해지는 거래라 하지 않았다.
        readback = self.ROOT / config.experiment_dir(1) / "output/실험01_예비보고서_notion_v7.md"
        self.assertEqual(validate.check_report_wrapping(
            self.CANON.read_text(encoding="utf-8")), [])
        self.assertTrue(validate.check_report_wrapping(
            readback.read_text(encoding="utf-8")))

    def test_check_notion_markdown_이_이_검사를_함께_낸다(self):
        # 배선이 이 검사의 유일한 발화 경로다. `check_notion_markdown` 에서
        # 호출을 지우면 함수가 죽은 코드가 되는데 단위 테스트는 그대로 통과한다.
        found = validate.check_notion_markdown(md_file(
            "# 제목\n\n문단이 여기서 끊기고\n다음 줄로 이어진다."))
        self.assertTrue(any("줄바꿈" in f.where for f in found), found)


class TestCheckHeadingBackticks(unittest.TestCase):
    """헤딩 텍스트 안의 코드 스팬을 잡는다.

    노션 목차 블록이 헤딩 텍스트를 그대로 가져가므로 목차에까지 코드 배경이
    번진다. 라운드 1 에서 학생이 실험02 의 `## `Rn` 측정 회로` 두 개를 직접
    지웠고, 확인 결과 체계적 분류였다(실험01 승인본에는 백틱 헤딩이 0개다).
    """

    CANON = ROOT / config.experiment_dir(1) / "output/실험01_예비보고서.md"

    def test_헤딩_안의_백틱을_잡는다(self):
        got = validate.check_heading_backticks("## `Rn` 측정 회로")
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0].level, "error")

    def test_맨몸_헤딩은_잡지_않는다(self):
        self.assertEqual(validate.check_heading_backticks("## Rn 측정 회로"), [])

    def test_본문의_백틱은_보지_않는다(self):
        # 기호를 본문에서 백틱으로 감싸는 것은 규칙이 시키는 일이다.
        self.assertEqual(validate.check_heading_backticks(
            "## Rn 측정 회로\n\n`Rn(on) = V_OLmax / I_OLmax` 로 구한다."), [])

    def test_여러_개여도_한_줄로_요약한다(self):
        got = validate.check_heading_backticks(
            "# `A` 절\n## `B` 절\n## C 절\n## `D` 절")
        self.assertEqual(len(got), 1, got)
        self.assertIn("3개", got[0].message)

    def test_헤딩이_아닌_줄의_샵은_헤딩이_아니다(self):
        self.assertEqual(validate.check_heading_backticks(
            "값이 `#1` 이면 무시한다."), [])

    def test_실험01_승인본은_조용하다(self):
        # 실측 통제군. 승인본 헤딩에는 백틱이 하나도 없다.
        got = validate.check_heading_backticks(self.CANON.read_text(encoding="utf-8"))
        self.assertEqual(got, [], got)

    def test_check_notion_markdown_이_이_검사를_함께_낸다(self):
        found = validate.check_notion_markdown(md_file("# 제목\n\n## `Rn` 측정 회로"))
        self.assertTrue(any("헤딩" in f.where for f in found), found)


class TestCheckTableWidth(unittest.TestCase):
    """A4 한 장에 안 들어가는 표를 잡는다.

    노션 PDF 내보내기는 넓은 표를 **경고 없이 오른쪽부터 자른다.** 화면에서는
    가로 스크롤로 다 보이므로 눈으로는 안 드러나고, 제출본에서만 사라진다.

    실측(실험05 v1, A4): 14열 표는 `Y7`·`Y8`·`Y9` 가, 13열 표는 `GS`·`EO` 가
    잘렸고, 11열 표 셋은 온전했다. 그래서 한계는 **11열**이다.
    """

    CANON = ROOT / config.experiment_dir(1) / "output/실험01_예비보고서.md"

    def _table(self, n, rows=2):
        head = "| " + " | ".join(f"C{i}" for i in range(n)) + " |"
        sep = "|" + "---|" * n
        body = "\n".join("| " + " | ".join("0" for _ in range(n)) + " |"
                         for _ in range(rows))
        return f"{head}\n{sep}\n{body}"

    def test_열_열한_개는_통과한다(self):
        # 실험05 의 이론표 셋이 정확히 11열이고 PDF 에서 온전했다.
        self.assertEqual(validate.check_table_width(self._table(11)), [])

    def test_열_열두_개부터_잡는다(self):
        got = validate.check_table_width(self._table(12))
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0].level, "error")

    def test_몇_열인지와_몇_열이_잘리는지_알린다(self):
        got = validate.check_table_width(self._table(14))
        self.assertIn("14열", got[0].message)
        self.assertIn("3", got[0].message)      # 넘친 열 수

    def test_잘리는_열_이름을_댄다(self):
        # 어느 열이 사라지는지 모르면 사용자가 심각성을 판단할 수 없다.
        head = "| D | C | B | A | Y0 | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 |"
        md = head + "\n" + "|" + "---|" * 14 + "\n" + "| " + " | ".join("0" * 1 for _ in range(14)) + " |"
        got = validate.check_table_width(md)
        self.assertIn("Y7", got[0].message)
        self.assertIn("Y9", got[0].message)

    def test_탭으로_들여쓴_표도_센다(self):
        # §절대 규칙 13 이 불릿 아래 표를 탭으로 들여쓰라고 시킨다.
        md = "- **캡션**\n\t" + self._table(13).replace("\n", "\n\t")
        self.assertEqual(len(validate.check_table_width(md)), 1)

    def test_표가_여러_개면_각각_낸다(self):
        md = self._table(13) + "\n\n산문\n\n" + self._table(14)
        self.assertEqual(len(validate.check_table_width(md)), 2)

    def test_좁은_표만_있으면_조용하다(self):
        md = self._table(3) + "\n\n산문\n\n" + self._table(4)
        self.assertEqual(validate.check_table_width(md), [])

    def test_파이프가_든_산문은_표가_아니다(self):
        self.assertEqual(validate.check_table_width(
            "출력이 `A|B` 꼴이면 OR 이다."), [])

    def test_실험01_승인본은_조용하다(self):
        # 실측 통제군. 승인본의 가장 넓은 표가 11열 이하다.
        got = validate.check_table_width(self.CANON.read_text(encoding="utf-8"))
        self.assertEqual(got, [], got)

    def test_check_notion_markdown_이_이_검사를_함께_낸다(self):
        found = validate.check_notion_markdown(md_file(
            "# 제목\n\n" + self._table(14)))
        self.assertTrue(any("표 너비" in f.where for f in found), found)


class NetlistCircuitWiring(unittest.TestCase):
    """표 줄 warn 은 렌더러 한계의 증상 완화였다. 한계가 사라지면 거짓이 된다.
    진짜 조용한 손실은 '칩 선언이 아예 없다'와 '칩에 배선이 하나도 없다'다."""

    def _netlist(self, circuit_body):
        text = ("---\nschema: lab-netlist/v2\nexperiment: 1\n"
                "spec: ../체크리스트/명세.md\n---\n\n"
                "# C1 · 시험\n\n- kind: circuit\n- id: C1\n"
                "- item: E1.P1-1\n- tables: [T1]\n\n" + circuit_body)
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        return parse_netlist(path)

    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")

    def _messages(self, body):
        return [f.message for f
                in validate.check_netlist_circuits(self._netlist(body), self.spec)]

    def test_표_줄만으로는_더_이상_경고하지_않는다(self):
        """표는 이제 인쇄된다 — 경고가 거짓이 되면 사람이 경고를 안 믿는다."""
        body = ("## U1 = 74HC08\n\n| 핀 | 연결 |\n|---|---|\n| 14 | VCC |\n")
        self.assertEqual(
            [m for m in self._messages(body) if "마크다운 표 줄" in m], [])

    def test_칩_선언이_없으면_경고한다(self):
        body = "회로 설명만 있고 배선이 없다.\n"
        self.assertTrue([m for m in self._messages(body) if "칩 선언" in m])

    def test_칩에_배선이_없으면_그_칩을_지목해_경고한다(self):
        body = "## U1 = 74HC08\n\n설명만 있다.\n"
        hits = [m for m in self._messages(body) if "배선" in m]
        self.assertTrue(hits)
        self.assertIn("U1 = 74HC08", hits[0])

    def test_배선이_있으면_조용하다(self):
        body = ("## U1 = 74HC08\n\n| 핀 | 연결 |\n|---|---|\n| 14 | VCC |\n")
        self.assertEqual([m for m in self._messages(body)
                          if "칩 선언" in m or "배선" in m], [])

    def test_불릿형_배선도_배선으로_센다(self):
        body = "- U1 = 74HC08 (quad)\n  - pin 14 → VCC(+5V)\n"
        self.assertEqual([m for m in self._messages(body)
                          if "칩 선언" in m or "배선" in m], [])

    def test_상자_밖의_배선처럼_보이는_줄을_경고한다(self):
        body = "- U1 = 74HC08\n  - pin 1 ← A\n- 미사용 입력핀: pin 9 → GND\n"
        hits = [m for m in self._messages(body) if "칩 상자" in m]
        self.assertTrue(hits)
        self.assertIn("미사용", hits[0])


class ContinuesValidation(unittest.TestCase):
    def test_없는_회로를_가리키면_error(self):
        text = (ROOT / "tests/fixtures/netlist_capture.md").read_text(
            encoding="utf-8").replace("- tables: [T2]",
                                      "- tables: [T2]\n- continues: C9")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md")
        found = validate.check_netlist_circuits(parse_netlist(path), spec)
        hits = [f for f in found if "continues" in f.message]
        self.assertEqual([f.level for f in hits], ["error"])
        self.assertIn("C9", hits[0].message)

    def test_자기_자신을_가리키면_error(self):
        text = (ROOT / "tests/fixtures/netlist_capture.md").read_text(
            encoding="utf-8").replace("- tables: [T2]",
                                      "- tables: [T2]\n- continues: C2")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md")
        found = validate.check_netlist_circuits(parse_netlist(path), spec)
        self.assertTrue([f for f in found
                         if "continues" in f.message and f.level == "error"])
        hits = [f for f in found if "continues" in f.message]
        self.assertIn("자기 자신", hits[0].message)

    def test_직전이_아닌_회로를_가리키면_error(self):
        """C5 에 `continues: C1` 을 적으면 그 사이 회로들의 점퍼를 어떻게
        하라는 지시가 사라진다."""
        text = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(
            encoding="utf-8").replace("- tables: [T5]",
                                      "- tables: [T5]\n- continues: C1")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        found = validate.check_netlist_circuits(parse_netlist(path), spec)
        hits = [f for f in found if "continues" in f.message]
        self.assertEqual([f.level for f in hits], ["error"])
        self.assertIn("직전 회로", hits[0].message)


class RefsValidation(unittest.TestCase):
    def _findings(self, extra):
        text = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(
            encoding="utf-8").replace("- tables: [T1]", f"- tables: [T1]\n{extra}")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        return validate.check_netlist_circuits(parse_netlist(path), spec)

    def test_기록_대상_표를_refs_로_가리키면_error(self):
        """방향이 반대다 — 기록할 표는 `tables` 로 간다."""
        hits = [f for f in self._findings("- refs: [T2]") if "refs" in f.message]
        self.assertEqual([f.level for f in hits], ["error"])
        self.assertIn("tables", hits[0].message)

    def test_없는_표를_refs_로_가리키면_error(self):
        hits = [f for f in self._findings("- refs: [T99]") if "refs" in f.message]
        self.assertEqual([f.level for f in hits], ["error"])

    def test_참조표를_refs_로_가리키면_조용하다(self):
        self.assertEqual(
            [f for f in self._findings("- refs: [T6]") if "refs" in f.message], [])


if __name__ == "__main__":
    unittest.main()
