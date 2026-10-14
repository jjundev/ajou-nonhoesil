import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.lab import config, validate
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.spec_parser import parse_spec
from tests._netlist_copy import netlist_copy

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
WEEK2_SPEC = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"
WEEK2_NETLIST = ROOT / config.experiment_dir(1) / "결선도/netlist.md"


def spec_from(text):
    tmp = tempfile.mkdtemp()
    path = Path(tmp) / "명세.md"
    path.write_text(text, encoding="utf-8")
    return parse_spec(path)


def scoped_spec(experiment, item_ids):
    """범위 검사용 최소 명세 — 항목마다 표 하나."""
    items = "".join(
        f"  - id: {i}\n    title: {i}\n    device: [LED]\n"
        f"    ics: [\"74HC08\"]\n    tables: [T{n}]\n"
        for n, i in enumerate(item_ids, start=1))
    tables = "".join(
        f"\n## T{n} · 표 {n}\n\n- kind: truth-table\n- encoding: 0/1\n"
        "- source: manual:p1\n\n| A | Y |\n|---|---|\n| 0 | 0 |\n| 1 | 1 |\n"
        for n in range(1, len(item_ids) + 1))
    return spec_from(
        "---\nschema: lab-spec/v2\n"
        f"experiment: {experiment}\ntitle: 범위\nsource_manual: x.pdf\n"
        'power: {VCC: "+5V", GND: "GND"}\n'
        f"items:\n{items}---\n{tables}")


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


class TestDeclaredOutputs(unittest.TestCase):
    """`manual:pN` 참조표가 출력 열을 `outputs` 로 선언한다 (실험3 이 실물).

    선언이 없으면 `split_columns` 는 마지막 열 하나만 출력으로 본다. 출력이
    둘인 교안 원문 표에서는 첫 출력(`S`·`D`)이 입력으로 세어져 행 수 warn
    과 열 역할 info 가 거짓으로 난다.
    """

    SPEC = FIXTURES / "spec_manual_outputs.md"

    def _without_outputs(self):
        text = self.SPEC.read_text(encoding="utf-8")
        return spec_from("\n".join(line for line in text.split("\n")
                                   if not line.startswith("- outputs:")))

    def test_선언하면_행_수_warn_이_없다(self):
        self.assertEqual(validate.check_row_count(parse_spec(self.SPEC)), [])

    def test_선언하면_열_역할_충돌이_없다(self):
        self.assertEqual(validate.check_column_roles(parse_spec(self.SPEC)), [])

    def test_선언하면_error_도_warn_도_없다(self):
        findings = [f for f in validate.validate_spec(parse_spec(self.SPEC))
                    if f.level in ("error", "warn")]
        self.assertEqual(findings, [], "\n".join(str(f) for f in findings))

    def test_선언을_걷으면_원래의_오탐이_돌아온다(self):
        """픽스처가 결함 자리를 실제로 지나는지 본다. 이게 없으면 위 세
        검사는 "원래 아무 문제 없던 표" 에서도 통과한다."""
        spec = self._without_outputs()
        warns = {f.where.rsplit(":", 1)[-1]: f.message
                 for f in validate.check_row_count(spec)}
        self.assertEqual(sorted(warns), ["T2", "T4", "T6", "T8"])
        self.assertIn("입력 3비트(A, B, S)면 8행이어야 하는데 4행이다", warns["T2"])
        self.assertIn("16행", warns["T4"])
        roles = {f.where.rsplit(":", 1)[-1]
                 for f in validate.check_column_roles(spec)}
        self.assertEqual(roles, {"S", "D"})

    def test_헤더에_없는_열을_가리키면_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n- source: manual:p4\n"
            "- outputs: [S, Q]\n\n"
            "| A | B | S | C |\n|---|---|---|---|\n| 0 | 0 | 0 | 0 |\n"
        ))
        errors = [f.message for f in validate.check_metadata(spec)
                  if f.level == "error"]
        self.assertTrue(any("outputs" in m and "'Q'" in m for m in errors), errors)

    def test_derived_대입_대상과_다르면_error(self):
        """출력을 두 곳에 적으면 한쪽만 고쳐진다. 어긋나면 시끄럽게 만든다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (S = A⊕B ; C = A·B)\n- outputs: [S]\n\n"
            "| A | B | S | C |\n|---|---|---|---|\n| 0 | 0 | 0 | 0 |\n"
        ))
        errors = [f.message for f in validate.check_metadata(spec)
                  if f.level == "error"]
        self.assertTrue(any("outputs" in m and "derived" in m for m in errors),
                        errors)

    def test_derived_대입_대상과_같으면_순서가_달라도_조용하다(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (S = A⊕B ; C = A·B)\n- outputs: [C, S]\n\n"
            "| A | B | S | C |\n|---|---|---|---|\n| 0 | 0 | 0 | 0 |\n"
        ))
        self.assertFalse(any("outputs" in f.message
                             for f in validate.check_metadata(spec)))


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
        # 번호를 박으면 그 실험이 재작성 대기 중일 때 통째로 빨개진다.
        # 살아 있는 명세를 훑으면 다음에 놓이는 명세가 자동으로 든다.
        paths = sorted((ROOT / config.EXPERIMENT_BASE)
                       .glob("실험*/체크리스트/명세.md"))
        self.assertTrue(paths, "명세를 하나도 못 찾았다")
        for path in paths:
            with self.subTest(path.parent.parent.name):
                self.assertEqual(
                    validate.check_orphan_tables(parse_spec(path)), [])

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


class TestOneTruthTablePerItem(unittest.TestCase):
    """항목마다 기록 진리표는 하나, 그것도 항목의 첫 기록 표여야 한다.

    `contact_sheet.load_records` 는 기록.md 의 항목 헤딩 아래 **첫 표**만 읽고,
    인쇄된 사진 파일명(`<항목> <입력비트>.jpg`)에는 표 ID 가 없다.
    """

    TT = ("\n## {tid} · 표\n\n- kind: truth-table\n- encoding: 0/1\n"
          "- source: manual:p1\n{role}\n| A | Y |\n|---|---|\n| 0 | 0 |\n| 1 | 1 |\n")
    CAP = ("\n## {tid} · 파형\n\n- kind: capture\n- source: manual:p1\n"
           "- expected: 파형이 나온다\n")

    def _spec(self, tables, bodies):
        return spec_from(
            "---\nschema: lab-spec/v2\nexperiment: 1\ntitle: t\n"
            'source_manual: x.pdf\npower: {VCC: "+5V", GND: "GND"}\n'
            "items:\n  - id: E1.P1-1\n    title: 1-1\n    device: [LED]\n"
            f"    ics: [\"74HC08\"]\n    tables: [{', '.join(tables)}]\n---\n"
            + "".join(bodies))

    def _hits(self, spec):
        return [f for f in validate.validate_spec(spec)
                if f.level == "warn" and "load_records" in f.message]

    def test_two_record_truth_tables_warn(self):
        spec = self._spec(["T1", "T2"], [self.TT.format(tid="T1", role=""),
                                         self.TT.format(tid="T2", role="")])
        hits = self._hits(spec)
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("E1.P1-1", hits[0].where)

    def test_reference_truth_table_does_not_count(self):
        spec = self._spec(["T1", "T2"], [
            self.TT.format(tid="T1", role=""),
            self.TT.format(tid="T2", role="- role: reference\n")])
        self.assertEqual(self._hits(spec), [])

    def test_truth_table_behind_another_kind_warns(self):
        spec = self._spec(["T1", "T2"], [self.CAP.format(tid="T1"),
                                         self.TT.format(tid="T2", role="")])
        hits = self._hits(spec)
        self.assertEqual(len(hits), 1, hits)

    def test_truth_table_first_then_capture_is_fine(self):
        spec = self._spec(["T1", "T2"], [self.TT.format(tid="T1", role=""),
                                         self.CAP.format(tid="T2")])
        self.assertEqual(self._hits(spec), [])

    def test_real_specs_do_not_warn(self):
        for n in (1, 2, 3):
            path = ROOT / config.experiment_dir(n) / "체크리스트/명세.md"
            with self.subTest(experiment=n):
                self.assertEqual(
                    validate.check_one_truth_table_per_item(parse_spec(path)), [])


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

    def _netlist(self, circuits, experiment=1):
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        head = self.HEAD.replace("experiment: 1", f"experiment: {experiment}")
        path.write_text(head + circuits, encoding="utf-8")
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

    STAGED_C1 = ("# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T1]\n"
                 "- diagram: 완성.png\n\n## 단계\n\n"
                 "| 단계 | 그림 | 이 단계에서 | 확인 |\n|---|---|---|---|\n"
                 "| 1 | 1단계.png | 칩 하나 | L1 = A·B 4조합 |\n"
                 "| 2 | 2단계.png | 칩 둘 | T1 8행 |\n")

    def test_단계_그림이_없으면_warn(self):
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(self.STAGED_C1)
        warns = [f.message for f in validate.check_netlist_circuits(netlist, spec)
                 if f.level == "warn"]
        self.assertTrue(any("1단계.png" in m for m in warns))
        self.assertTrue(any("2단계.png" in m for m in warns))

    def test_단계_확인_칸이_비면_error(self):
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(self.STAGED_C1.replace("| 칩 하나 | L1 = A·B 4조합 |", "| 칩 하나 |  |"))
        errors = [f.message for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertTrue(any("확인 칸" in m for m in errors))

    def test_마지막_단계_그림이_완성본과_같으면_error(self):
        """단계 그림에는 회색 기준선이 있다 — 손그림 원도로 쓰면 회색 선을 빠뜨린다."""
        spec = parse_spec(WEEK2_SPEC)
        netlist = self._netlist(self.STAGED_C1.replace("| 2 | 2단계.png |", "| 2 | 완성.png |"))
        errors = [f.message for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertTrue(any("완성본" in m for m in errors))

    NODED_C1 = ("# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T1]\n"
                "- diagram: 완성.png\n\n## 노드\n\n"
                "| 노드 | 식 | 핀 |\n|---|---|---|\n"
                "| L1 | A·B | U1 pin 3 |\n"
                "| L2 | A·B·C | U1 pin 6 |\n\n"
                "- U1 = 74HC08 (quad 2-input AND)\n  - pin 14 → VCC(+5V)\n")

    def _node_errors(self, text):
        spec = parse_spec(WEEK2_SPEC)
        return [f.message for f in validate.check_netlist_circuits(self._netlist(text), spec)
                if f.level == "error"]

    def test_노드_표가_맞으면_error_가_없다(self):
        self.assertEqual([m for m in self._node_errors(self.NODED_C1) if "노드" in m], [])

    def test_단계는_있는데_노드가_없으면_warn(self):
        spec = parse_spec(WEEK2_SPEC)
        warns = [f.message for f in validate.check_netlist_circuits(self._netlist(self.STAGED_C1), spec)
                 if f.level == "warn"]
        self.assertTrue(any("노드" in m for m in warns), warns)

    def test_실험1과_2는_단계가_있어도_노드표_부재가_warn이다(self):
        spec = parse_spec(WEEK2_SPEC)
        for experiment in (1, 2):
            with self.subTest(experiment=experiment):
                found = validate.check_netlist_circuits(
                    self._netlist(self.STAGED_C1, experiment=experiment), spec)
                self.assertTrue(any(f.level == "warn" and "노드" in f.message for f in found), found)
                self.assertFalse(any(f.level == "error" and "노드" in f.message for f in found), found)

    def test_실험3부터_단계가_있는데_노드표가_없으면_error(self):
        spec = parse_spec(WEEK2_SPEC)
        found = validate.check_netlist_circuits(
            self._netlist(self.STAGED_C1, experiment=3), spec)
        self.assertTrue(any(f.level == "error" and "노드" in f.message for f in found), found)

    def test_걷기_오타는_노드표가_없어도_error(self):
        spec = parse_spec(WEEK2_SPEC)
        for bad in ("2 걷기", "걷기2"):
            with self.subTest(value=bad):
                text = self.STAGED_C1.replace("| 2 | 2단계.png |", f"| {bad} | 2걷기.png |")
                errors = [f.message for f in validate.check_netlist_circuits(
                    self._netlist(text, experiment=1), spec) if f.level == "error"]
                self.assertTrue(any("양의 정수" in m and bad in m for m in errors), errors)

    def test_0단계와_0걷기는_error(self):
        spec = parse_spec(WEEK2_SPEC)
        for bad in ("0", "0걷기"):
            with self.subTest(value=bad):
                text = self.STAGED_C1.replace("| 2 | 2단계.png |", f"| {bad} | 0단계.png |")
                errors = [f.message for f in validate.check_netlist_circuits(
                    self._netlist(text), spec) if f.level == "error"]
                self.assertTrue(any("1 이상" in m and bad in m for m in errors), errors)

    STAGED_NODED_C1 = ("# C1\n\n- kind: circuit\n- id: C1\n- item: E1.P1-1\n- tables: [T1]\n"
                       "- diagram: 완성.png\n\n## 단계\n\n"
                       "| 단계 | 그림 | 이 단계에서 | 확인 |\n|---|---|---|---|\n"
                       "| 1 | 1단계.png | 칩 하나 | 노드 `L1` — L1 을 네 조합으로 본다 |\n"
                       "| 2 | 2단계.png | 칩 둘 | 노드 `L2` — T1 8행 |\n\n"
                       "## 노드\n\n"
                       "| 노드 | 식 | 핀 |\n|---|---|---|\n"
                       "| L1 | A·B | U1 pin 3 |\n"
                       "| L2 | A·B·C | U1 pin 6 |\n\n"
                       "- U1 = 74HC08 (quad 2-input AND)\n  - pin 14 → VCC(+5V)\n")

    def _stage_node_findings(self, text, level):
        spec = parse_spec(WEEK2_SPEC)
        return [f.message for f in validate.check_netlist_circuits(self._netlist(text), spec)
                if f.level == level and "노드" in f.message]

    def test_단계가_가리키는_노드가_노드표에_있으면_조용하다(self):
        self.assertEqual(self._stage_node_findings(self.STAGED_NODED_C1, "error"), [])
        warns = self._stage_node_findings(self.STAGED_NODED_C1, "warn")
        self.assertEqual([w for w in warns if "가리키지" in w], [])

    def test_단계가_없는_노드를_가리키면_error(self):
        """결선도 안에서 이름이 표류하는 유일한 자리다 — 그림은 맞는데 표가 옛 이름을 쥔다."""
        bad = self.STAGED_NODED_C1.replace("노드 `L2` — T1 8행", "노드 `L9` — T1 8행")
        errors = self._stage_node_findings(bad, "error")
        self.assertTrue(any("L9" in m and "단계 2" in m for m in errors), errors)

    def test_노드표가_있는데_단계가_노드를_안_가리키면_warn(self):
        bad = self.STAGED_NODED_C1.replace("노드 `L1` — L1 을 네 조합으로 본다", "L1 을 네 조합으로 본다")
        warns = self._stage_node_findings(bad, "warn")
        self.assertTrue(any("가리키지" in m and "단계 1" in m for m in warns), warns)

    def _with_walk(self, todo="걷기 ①(좌 a1→좌 b2)을 뽑는다",
                   check="좌 a1·좌 b2 홀이 비었다"):
        return self.STAGED_NODED_C1.replace(
            "| 1 | 1단계.png |",
            f"| 1걷기 | 1걷기.png | {todo} | {check} |\n"
            "| 1 | 1단계.png |")

    def test_걷기_행에_주소쌍이_없으면_error(self):
        errors = self._node_errors(self._with_walk(todo="걷기 ①을 뽑는다"))
        self.assertTrue(any("주소쌍" in m for m in errors), errors)

    def test_걷기_확인에_양끝_홀이_모두_있으면_조용하다(self):
        errors = self._node_errors(self._with_walk())
        self.assertFalse(any("홀 목록" in m or "주소쌍" in m for m in errors), errors)

    def test_걷기_확인에서_출발_홀이_빠지면_error(self):
        errors = self._node_errors(self._with_walk(check="좌 b2 홀이 비었다"))
        self.assertTrue(any("홀 목록" in m and "좌 a1" in m for m in errors), errors)

    def test_걷기_행의_빈_확인_칸은_error(self):
        errors = self._node_errors(self._with_walk(check=""))
        self.assertTrue(any("확인 칸" in m for m in errors), errors)
        self.assertFalse(any("홀 목록" in m for m in errors), errors)

    def test_걷기_행은_노드를_가리키지_않아도_된다(self):
        """걷기 보드는 걷기만 하므로 관측할 출력이 없다."""
        text = self.STAGED_NODED_C1.replace(
            "| 1 | 1단계.png |",
            "| 1걷기 | 1걷기_세가닥.png | **걷기 ①(좌 a1→좌 b2)을 뽑는다** | 좌 a1·좌 b2 홀이 비었다 |\n"
            "| 1 | 1단계.png |")
        warns = self._stage_node_findings(text, "warn")
        self.assertEqual([w for w in warns if "단계 1걷기" in w], [])
        # `_stage_node_findings` 는 "노드" 가 든 메시지만 남긴다 — 걷기 구조 error 에는
        # 그 낱말이 없으니 필터 없이 전부 모아야 거짓 양성 방향을 문다.
        spec = parse_spec(WEEK2_SPEC)
        errors = [f.message for f in validate.check_netlist_circuits(self._netlist(text), spec)
                  if f.level == "error"]
        self.assertEqual(errors, [])

    def test_걷기_행이_표의_마지막이면_error(self):
        """걷기는 다음 단계의 머리다 — 뒤에 꽂는 단계가 없으면 무엇을 위해 걷는지가 없다."""
        text = self.STAGED_NODED_C1.replace(
            "| 2 | 2단계.png | 칩 둘 | 노드 `L2` — T1 8행 |",
            "| 2 | 2단계.png | 칩 둘 | 노드 `L2` — T1 8행 |\n"
            "| 3걷기 | 3걷기.png | **걷기 ①(좌 a1→좌 b2)을 뽑는다** | 좌 a1·좌 b2 홀이 비었다 |")
        spec = parse_spec(WEEK2_SPEC)
        errors = [f.message for f in validate.check_netlist_circuits(self._netlist(text), spec)
                  if f.level == "error"]
        self.assertTrue(any("마지막이다" in m and "3걷기" in m for m in errors), errors)

    def test_걷기_번호가_다음_행과_다르면_error(self):
        """`<k>걷기` 의 k 는 바로 다음 행의 단계 번호다 — 안 묶으면 번호를 밀 때 표류한다."""
        text = self.STAGED_NODED_C1.replace(
            "| 1 | 1단계.png |",
            "| 2걷기 | 2걷기.png | **걷기 ①(좌 a1→좌 b2)을 뽑는다** | 좌 a1·좌 b2 홀이 비었다 |\n"
            "| 1 | 1단계.png |")
        spec = parse_spec(WEEK2_SPEC)
        errors = [f.message for f in validate.check_netlist_circuits(self._netlist(text), spec)
                  if f.level == "error"]
        self.assertTrue(any("2걷기" in m and "뒤의 단계" in m for m in errors), errors)

    def test_앞자리_0_걷기와_다음_단계는_숫자로_비교한다(self):
        text = self.STAGED_NODED_C1.replace(
            "| 1 | 1단계.png |",
            "| 03걷기 | 3걷기.png | **걷기 ①(좌 a1→좌 b2)을 뽑는다** | 좌 a1·좌 b2 홀이 비었다 |\n"
            "| 03 | 1단계.png |")
        errors = self._node_errors(text)
        self.assertFalse(any("뒤의 단계" in m for m in errors), errors)

    def test_걷기_행_둘이_연달아_오면_error(self):
        text = self.STAGED_NODED_C1.replace(
            "| 1 | 1단계.png |",
            "| 1걷기 | a.png | **걷기 ①(좌 a1→좌 b2)을 뽑는다** | 좌 a1·좌 b2 홀이 비었다 |\n"
            "| 1걷기 | b.png | **걷기 ①(좌 c3→좌 d4)을 뽑는다** | 좌 c3·좌 d4 홀이 비었다 |\n"
            "| 1 | 1단계.png |")
        errors = self._node_errors(text)
        self.assertTrue(any("연달아" in m for m in errors), errors)

    def test_노드표가_없는_회로의_단계는_노드를_묻지_않는다(self):
        """실험01·02 승인본이 그렇다 — '단계는 있는데 노드 표가 없다' warn 이 이미 한 번 말한다."""
        warns = self._stage_node_findings(self.STAGED_C1, "warn")
        self.assertEqual([w for w in warns if "가리키지" in w], [])

    def test_노드_식의_변수가_표에_없으면_error(self):
        errors = self._node_errors(self.NODED_C1.replace("| L1 | A·B |", "| L1 | A·Q |"))
        self.assertTrue(any("노드 L1" in m and "Q" in m for m in errors), errors)

    def test_핀_형식이_다르면_error(self):
        errors = self._node_errors(self.NODED_C1.replace("U1 pin 3", "U1 p3"))
        self.assertTrue(any("형식" in m for m in errors), errors)

    def test_선언되지_않은_칩의_핀이면_error(self):
        errors = self._node_errors(self.NODED_C1.replace("U1 pin 3", "U9 pin 3"))
        self.assertTrue(any("선언" in m and "U9" in m for m in errors), errors)

    def test_노드_이름이_겹치면_error(self):
        errors = self._node_errors(self.NODED_C1.replace("| L2 | A·B·C |", "| L1 | A·B·C |"))
        self.assertTrue(any("두 번" in m for m in errors), errors)

    def test_명세_출력이_노드에_없으면_error(self):
        errors = self._node_errors(self.NODED_C1.replace("| L2 | A·B·C | U1 pin 6 |\n", ""))
        self.assertTrue(any("출력 L2" in m for m in errors), errors)

    def test_출력_노드_값이_명세_식과_다르면_error(self):
        """결선도가 A·B 를 L2 라 부르면 명세(A·B·C)와 표류한 것이다 — 행 110 에서 갈린다."""
        errors = self._node_errors(self.NODED_C1.replace("| L2 | A·B·C |", "| L2 | A·B |"))
        self.assertTrue(any("표류" in m and "L2" in m for m in errors), errors)

    def test_명세_출력_식을_평가할_수_없으면_error(self):
        """검사는 던지지 않는다 — 명세 식의 변수가 기록표 입력에 없어도 Finding 으로 낸다."""
        text = WEEK2_SPEC.read_text(encoding="utf-8")
        # `C` 를 `Q` 로 **바꾸면** 안 된다 — `split_indices` 는 derived 식이 참조하는
        # 이름으로 입력 열을 정하므로 C 가 입력에서 빠지고, 노드 식 `A·B·C` 가 먼저
        # `nodes.compute` 에서 터져 이 가드까지 오지 못한다. 미지의 변수를 **더한다**.
        broken = text.replace("- source: derived (L1 = A·B ; L2 = A·B·C)",
                              "- source: derived (L1 = A·B ; L2 = A·B·C·Q)")
        self.assertNotEqual(broken, text)
        path = Path(tempfile.mkdtemp()) / "명세.md"
        path.write_text(broken, encoding="utf-8")
        errors = [f.message for f in
                  validate.check_netlist_circuits(self._netlist(self.NODED_C1), parse_spec(path))
                  if f.level == "error"]
        self.assertTrue(any("평가할 수 없다" in m and "L2" in m for m in errors), errors)

    def test_실험03_실물_노드_표는_error_가_없다(self):
        """Task 7 이 백필한 뒤에만 뜻이 있다 — 그 전에는 노드가 없어 자명하게 통과한다."""
        spec = parse_spec(ROOT / config.experiment_dir(3) / "체크리스트/명세.md")
        netlist = parse_netlist(ROOT / config.experiment_dir(3) / "결선도/netlist.md")
        errors = [f for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_자리표가_둘이면_error(self):
        spec = parse_spec(WEEK2_SPEC)
        layout = "# 자리표\n\n- kind: layout\n\n| 슬롯 | 자리 | 회로별 칩 |\n|---|---|---|\n| S1 | 좌 7행 | x |\n\n"
        netlist = self._netlist(layout + layout.replace("# 자리표", "# 자리표 2") + self.STAGED_C1)
        errors = [f.message for f in validate.check_netlist_circuits(netlist, spec)
                  if f.level == "error"]
        self.assertTrue(any("layout" in m for m in errors))


class TestSchematics(unittest.TestCase):
    """명세 항목 `schematic` 이 가리키는 강의노트 회로도가 명세 옆에 있는가."""

    def _spec(self, schematic_line, make_png):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = Path(tmp.name) / "명세.md"
        text = (FIXTURES / "spec_shared_letter.md").read_text(encoding="utf-8")
        self.assertIn("pages: [6]", text)
        if schematic_line:
            text = text.replace("pages: [6]", "pages: [6]\n    " + schematic_line, 1)
        target.write_text(text, encoding="utf-8")
        if make_png:
            (target.parent / "실험03_2-1_회로도.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        return parse_spec(target)

    def test_필드가_없으면_아무것도_내지_않는다(self):
        self.assertEqual(validate.check_schematics(self._spec(None, False)), [])

    def test_파일이_있으면_아무것도_내지_않는다(self):
        spec = self._spec("schematic: [실험03_2-1_회로도.png]", True)
        self.assertEqual(validate.check_schematics(spec), [])

    def test_파일이_없으면_warn_하나(self):
        spec = self._spec("schematic: [실험03_2-1_회로도.png]", False)
        findings = validate.check_schematics(spec)
        self.assertEqual([f.level for f in findings], ["warn"])
        self.assertIn("실험03_2-1_회로도.png", findings[0].message)
        self.assertIn("E3.P2-1", findings[0].where)

    def test_validate_spec_이_부른다(self):
        spec = self._spec("schematic: [실험03_2-1_회로도.png]", False)
        self.assertTrue(any("회로도" in f.message and f.level == "warn"
                            for f in validate.validate_spec(spec)))


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

    def test_실물_문서에서_실제로_잡힌다(self):
        # 목록이 비면 검사가 무의미하다. 씨앗은 픽스처지만 **손으로 심은
        # 문장이 아니라** 저작된 문서에서 온 산문이라 이 대조가 성립한다.
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        infos = [f for f in validate.validate_spec(spec) if f.level == "info"]
        self.assertTrue(infos, "명세에서 한 건도 안 잡혔다")

    def test_결선도에도_건다(self):
        # 결선도 쪽이 명세보다 많다 (이 픽스처는 9 대 1).
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        infos = [f for f in validate.check_netlist(
            ROOT / "tests/fixtures/netlist_full_wiring.md", spec)
            if f.level == "info"]
        self.assertTrue(infos, "결선도에서 한 건도 안 잡혔다")


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
        """`generate: false` 섹션(퀴즈 해설)은 없어도 누락이 아니다. `추가 공부` 는
        2026-09-12 부터 생성 대상이라 가짜 보고서에도 넣는다."""
        fmt = config.load_report_format(ROOT)
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 실험 결과\n# 예비보고서와의 비교\n# 결과 분석\n# 고찰\n"
                       "# 추가 공부\n", encoding="utf-8")
        findings = validate.check_report_sections(tmp, fmt.result)
        self.assertTrue(all("퀴즈" not in f.message for f in findings),
                        [str(f) for f in findings])


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

    def test_legacy_preview_template_is_clean(self):
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

    # 2026-09-10: `test_실험02_되감은_판본은_조용하다` 를 걷어냈다. 실험02
    # 예비보고서를 2026-2 교안 기준 재저작 대상으로 지웠고, 이 검사는 **그
    # 문서가 실제로 되감겨 있다**는 사실에 기댄다 — 픽스처로 옮기면 자기가
    # 심은 답을 채점하게 된다. 위 `CANON`(실험01 정본)이 같은 성격의 대조를
    # 계속 맡는다. 실험02 를 다시 저작할 때 되살린다.

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

    def test_참고문헌의_URL_줄은_쪼개진_문단이_아니다(self):
        # 데이터시트 인용은 서지 한 줄 + 링크 한 줄이 관행이다. 실험01·02
        # 승인본이 그 모양으로 올라갔는데도 이 검사가 둘 다 error 로 잡았다.
        self.assertEqual(validate.check_report_wrapping(
            "- Nexperia. 74HC00; 74HCT00 — Quad 2-input NAND gate. Rev. 11, 2025-04-29.\n"
            "  https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf"), [])

    def test_URL_이_아닌_이어진_줄은_그대로_잡는다(self):
        # 오탐을 없애면서 진짜 감싸기까지 놓치면 안 된다. 줄 **전체**가 URL
        # 하나일 때만 넘어간다 — 산문이 URL 뒤에 붙으면 감싸기다.
        got = validate.check_report_wrapping(
            "- Nexperia. 74HC00 데이터시트인데 서지가 길어서\n"
            "  https://example.com/x.pdf 를 보라고 이어 붙였다.")
        self.assertEqual(len(got), 1, got)

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
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
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
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
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


class RebuildValidation(unittest.TestCase):
    """`rebuild: true` 는 앞 회로를 전부 걷는 경계다 — 이어 붙이기·입구 걷기와 모순이다."""

    STAGES = ("\n## 단계\n\n| 단계 | 그림 | 이 단계에서 | 확인 |\n|---|---|---|---|\n"
              "{rows}\n")

    def _findings(self, extra, circuit="C2", tail=""):
        text = (ROOT / "tests/fixtures/netlist_capture.md").read_text(encoding="utf-8")
        table = "[T2]" if circuit == "C2" else "[T1]"
        text = text.replace(f"- tables: {table}", f"- tables: {table}\n{extra}") + tail
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        return [f for f in validate.check_netlist_circuits(parse_netlist(path), spec)
                if "rebuild" in f.message]

    def test_두번째_회로의_rebuild_는_말이_없다(self):
        self.assertEqual(self._findings("- rebuild: true"), [])

    def test_continues_와_함께면_error(self):
        hits = self._findings("- rebuild: true\n- continues: C1")
        self.assertEqual([f.level for f in hits], ["error"])

    def test_첫_회로의_rebuild_는_error(self):
        hits = self._findings("- rebuild: true", circuit="C1")
        self.assertEqual([f.level for f in hits], ["error"])
        self.assertIn("첫 회로", hits[0].message)

    def test_입구_걷기_행과_함께면_error(self):
        rows = ("| 1걷기 | `w.png` | 걷기 ①(좌 a1→좌 b2)을 뽑는다 | 좌 a1·좌 b2 홀이 비었다 |\n"
                "| 1 | `s.png` | 신호선: A→pin 1 | 노드 `X` — 본다 |")
        hits = self._findings("- rebuild: true", tail=self.STAGES.format(rows=rows))
        self.assertEqual([f.level for f in hits], ["error"])
        self.assertIn("걷기", hits[0].message)


class OrderValidation(unittest.TestCase):
    """`order` 는 기록표 하나의 행 번호를 한 번씩 담는다 — 빠지면 그 행을 언제 넣는지 사라진다."""

    def _findings(self, extra):
        text = (ROOT / "tests/fixtures/netlist_capture.md").read_text(encoding="utf-8")
        text = text.replace("- tables: [T2]", f"- tables: [T2]\n{extra}")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        return [f for f in validate.check_netlist_circuits(parse_netlist(path), spec)
                if "order" in f.message]

    def _rows(self):
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        return len(spec.table("T2").rows)

    def test_행_번호를_한_번씩_담으면_말이_없다(self):
        order = list(range(self._rows(), 0, -1))
        self.assertEqual(self._findings(f"- order: {order}"), [])

    def test_빠지거나_겹치면_error(self):
        n = self._rows()
        for order in ([1] * n, list(range(1, n))):
            with self.subTest(order=order):
                hits = self._findings(f"- order: {order}")
                self.assertEqual([f.level for f in hits], ["error"])


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


class ManualQuotes(unittest.TestCase):
    """교안을 인용한다고 주장하는 문장이 실제로 그 교안에 있는지 본다.

    실험01 이 실물 근거다. 명세가 `source_manual` 을 2026-2 배포본으로 갈면서
    산문은 아카이브 2020-2 판의 문장을 그대로 이고 갔고, 검사기 아홉 개가
    전부 통과시켰다.
    """

    def test_교안에_있는_인용은_통과한다(self):
        text = '교안 p11 의 "다이오드 연결 시, 330Ω 저항 필수" 박스를 따른다.\n'
        manual = "3. 실험 방법 ※ 다이오드 연결 시, 330Ω 저항 필수\n"
        self.assertEqual(validate.check_manual_quotes(text, manual, "명세.md"), [])

    def test_교안에_없는_인용은_info_로_올라온다(self):
        text = ('교안이 IC 를 지정하지 않고 "OR gate에 대한 IC 찾아서 수행" '
                '이라고만 쓴다.\n')
        manual = "실험 1-2) 3-input OR gate\n주어진 회로를 구성한다.\n"
        found = validate.check_manual_quotes(text, manual, "명세.md")
        self.assertEqual([f.level for f in found], ["info"])
        self.assertIn("OR gate에 대한 IC 찾아서 수행", found[0].message)
        self.assertEqual(found[0].where, "명세.md:1")

    def test_교안을_안_가리키는_줄의_인용은_건너뛴다(self):
        """자기 이전 판을 인용하는 문장까지 잡으면 오탐이 된다 — 실물이다."""
        text = '이전에는 "표준 DIP-14 배치" 가정이었고 미확정 M1 이었다.\n'
        self.assertEqual(validate.check_manual_quotes(text, "아무 내용", "결선도"), [])

    def test_강의노트라고_불러도_검사한다(self):
        text = '강의노트가 "없는 문장" 이라고 적는다.\n'
        found = validate.check_manual_quotes(text, "다른 내용", "명세.md")
        self.assertEqual([f.level for f in found], ["info"])

    def test_공백_차이는_무시한다(self):
        """`pdftotext -layout` 은 칸을 맞추려고 공백을 넣는다."""
        text = '교안은 "5V 전압원" 만 적는다.\n'
        manual = " - 5V    전압원\n"
        self.assertEqual(validate.check_manual_quotes(text, manual, "명세.md"), [])

    def test_백틱_안의_토큰은_인용이_아니다(self):
        text = '교안이 `74HC32` 를 지정한다.\n'
        self.assertEqual(validate.check_manual_quotes(text, "", "명세.md"), [])

    def test_짧은_인용이_뒤_인용과_짝이_어긋나지_않는다(self):
        """실물 오탐이었다 — `"5V"` 가 길이 미달로 밀리면서 그 닫는 따옴표가
        다음 인용의 여는 따옴표로 붙어 `"를 언급할 뿐 "` 이 인용이 됐다.
        짝을 먼저 맞추고 길이는 나중에 거른다."""
        text = ('교안은 "5V"를 언급할 뿐 "전압원"이라는 표현은 p10 에만 있다.\n')
        self.assertEqual(
            validate.check_manual_quotes(text, "5V 전압원", "결선도"), [])

    def test_교안_텍스트를_못_뽑았으면_아무것도_내지_않는다(self):
        """래스터라 0 자가 나온 경우까지 없다고 단정하면 안 된다."""
        text = '교안이 "없는 말" 이라고 쓴다.\n'
        self.assertEqual(validate.check_manual_quotes(text, "", "명세.md"), [])


MANUAL_CMOS = ROOT / "강의노트/실험2. CMOS 회로의 전기적 특성.pdf"


class ExtractManualText(unittest.TestCase):
    """`extract_manual_text` 는 **항상 str** 이고, `pdftotext` 가 한글을 못
    뽑으면 `pypdf` 로 보충한다.

    2026-09-13 Windows(cp949) 실물 두 건이다.
    - `pdftotext` 가 글머리표 `0xb7` 을 내놓자 `text=True` 읽기 스레드가
      UnicodeDecodeError 를 내고 함수가 None 을 돌려줘 호출자의 `len()` 이
      깨졌다.
    - 실험2 교안은 내장 NanumSquare 에 한글 ToUnicode 가 없어 `pdftotext`
      가 ASCII 만 내놓았고, 명세의 한글 인용 12건이 전부 info 로 오진됐다.
      `pypdf` 는 같은 파일에서 한글을 되살린다.
    """

    @staticmethod
    def _done(stdout: bytes, returncode: int = 0):
        return subprocess.CompletedProcess(["pdftotext"], returncode,
                                           stdout=stdout, stderr=b"")

    def test_비UTF8_바이트가_섞여도_str_을_돌려준다(self):
        raw = "다음 항목".encode("utf-8")
        with mock.patch.object(validate.subprocess, "run",
                               return_value=self._done(b"\xb7 " + raw)), \
             mock.patch.object(validate, "_pypdf_text") as fallback:
            text = validate.extract_manual_text("x.pdf")
        self.assertIsInstance(text, str)
        self.assertIn("�", text)
        self.assertIn("다음 항목", text)
        fallback.assert_not_called()
        # 호출자가 바로 거는 `len()` 과 `check_manual_quotes` 가 깨지지 않는다.
        self.assertGreater(len(text), 0)
        self.assertEqual(validate.check_manual_quotes(
            '교안은 "다음 항목" 이라고 쓴다.\n', text, "명세.md"), [])

    def test_pdftotext_결과에_한글이_있으면_pypdf_를_부르지_않는다(self):
        with mock.patch.object(validate.subprocess, "run",
                               return_value=self._done("한글 교안".encode())), \
             mock.patch.object(validate, "_pypdf_text") as fallback:
            self.assertEqual(validate.extract_manual_text("x.pdf"), "한글 교안")
        fallback.assert_not_called()

    def test_pdftotext_가_한글을_못_뽑으면_pypdf_결과를_덧붙인다(self):
        with mock.patch.object(validate.subprocess, "run",
                               return_value=self._done(b"CMOS VCC INPUT\n")), \
             mock.patch.object(validate, "_pypdf_text",
                               return_value="CMOS 회로의 전기적 특성"):
            text = validate.extract_manual_text("x.pdf")
        self.assertIsInstance(text, str)
        self.assertIn("CMOS VCC INPUT", text)
        self.assertIn("CMOS 회로의 전기적 특성", text)
        self.assertEqual(validate.check_manual_quotes(
            '교안은 "CMOS 회로의 전기적 특성" 을 다룬다.\n', text, "명세.md"), [])

    def test_pdftotext_가_없으면_pypdf_결과만_쓴다(self):
        with mock.patch.object(validate.subprocess, "run",
                               side_effect=FileNotFoundError("pdftotext")), \
             mock.patch.object(validate, "_pypdf_text",
                               return_value="한글만 있는 교안"):
            self.assertEqual(validate.extract_manual_text("x.pdf"),
                             "한글만 있는 교안")

    def test_둘_다_한글이_없으면_pdftotext_결과를_그대로_쓴다(self):
        """영문 교안이거나 래스터인 경우 — 덧붙일 것이 없다."""
        with mock.patch.object(validate.subprocess, "run",
                               return_value=self._done(b"English only\n")), \
             mock.patch.object(validate, "_pypdf_text",
                               return_value="English only too"):
            self.assertEqual(validate.extract_manual_text("x.pdf"),
                             "English only\n")

    def test_아무것도_못_뽑으면_빈_문자열이다(self):
        """기존 계약 — 빈 문자열이면 `check_manual_quotes` 가 조용히 넘어간다."""
        with mock.patch.object(validate.subprocess, "run",
                               side_effect=FileNotFoundError("pdftotext")), \
             mock.patch.object(validate, "_pypdf_text", return_value=""):
            self.assertEqual(validate.extract_manual_text("x.pdf"), "")
        with mock.patch.object(validate.subprocess, "run",
                               return_value=self._done(b"", returncode=1)), \
             mock.patch.object(validate, "_pypdf_text", return_value=""):
            self.assertEqual(validate.extract_manual_text("x.pdf"), "")

    def test_pypdf_가_없거나_못_열어도_빈_문자열이다(self):
        self.assertEqual(validate._pypdf_text(
            Path(tempfile.mkdtemp()) / "없는.pdf"), "")
        with mock.patch.dict("sys.modules", {"pypdf": None}):
            self.assertEqual(validate._pypdf_text("x.pdf"), "")

    @unittest.skipUnless(MANUAL_CMOS.exists() and shutil.which("pdftotext"),
                         "실험2 교안 PDF 와 pdftotext 가 둘 다 있어야 한다")
    def test_실물_실험2_교안에서_한글을_뽑는다(self):
        text = validate.extract_manual_text(MANUAL_CMOS)
        self.assertIsInstance(text, str)
        self.assertRegex(text, "[가-힣]")
        self.assertEqual(validate.check_manual_quotes(
            '교안 1절은 "CMOS 회로의 전기적 특성" 을 든다.\n', text, "명세.md"), [])


class ColumnRoles(unittest.TestCase):
    """같은 열 이름이 표마다 입력·출력으로 갈리는 자리를 센다.

    실험01 이 실물이다 — `C` 가 T1~T4 에서는 세 번째 **입력**이고 T6~T9 에서는
    **출력**이다. 교안 p5·p6·p8·p9 가 `INPUT(A, B) / OUTPUT(C)` 2단 헤더를
    쓰는데 명세가 한 줄로 누르면서 구분이 사라졌다. 파서의 중복 열 거절(한 표 안)은
    표 *안*만 보므로 이 자리를 못 본다.
    """

    FRONT = """---
schema: lab-spec/v2
experiment: 1
title: Basic Gates
source_manual: from_the_past/정리/강의노트/실험1.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E1.P1-1
    title: 표 둘
    device: [LED]
    ics: ["74HC08"]
    tables: [T1, T2]
---
"""

    def _spec(self, body):
        return spec_from(self.FRONT + body)

    def test_한_이름이_입력과_출력으로_갈리면_info(self):
        spec = self._spec("""
## T1 · 파생표

- kind: truth-table
- encoding: 0/1
- source: derived (Y = A·B·C)

| A | B | C | Y |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 0 | 1 | 0 |
| 0 | 1 | 0 | 0 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 0 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 0 |
| 1 | 1 | 1 | 1 |

## T2 · 교안 2입력 이론표

- kind: truth-table
- encoding: 0/1
- source: manual:p5
- role: reference

| A | B | C |
|---|---|---|
| 0 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 0 | 0 |
| 1 | 1 | 1 |
""")
        found = validate.check_column_roles(spec)
        self.assertEqual([f.level for f in found], ["info"])
        self.assertIn("`C`", found[0].message)
        self.assertIn("입력 T1", found[0].message)
        self.assertIn("출력 T2", found[0].message)

    def test_역할이_한결같으면_조용하다(self):
        spec = self._spec("""
## T1 · 파생표

- kind: truth-table
- encoding: 0/1
- source: derived (Y = A·B)

| A | B | Y |
|---|---|---|
| 0 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 0 | 0 |
| 1 | 1 | 1 |

## T2 · 다중 출력이어도 같다

- kind: truth-table
- encoding: 0/1
- source: derived (Y = A ; Z = B)

| A | B | Y | Z |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 0 | 1 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 1 | 1 |
""")
        self.assertEqual(validate.check_column_roles(spec), [])

    def test_실험01_은_C_한_건만_낸다(self):
        """실물 회귀. `C` 말고 다른 이름이 걸리면 오탐이 는 것이다."""
        found = validate.check_column_roles(parse_spec(WEEK2_SPEC))
        self.assertEqual([f.level for f in found], ["info"])
        self.assertIn("`C`", found[0].message)


class BodyStyle(unittest.TestCase):
    """2026-09-12 실험01 결보 v5 회차에서 승격한 본문 문체 검사.

    v3 평가에서 백틱·em dash·"첫째" 가, v5 되읽기에서 조사·단위 띄어쓰기가
    사용자 손으로 지워졌다. 전부 기계로 셀 수 있는 것이라 warn 으로 잡는다.
    """

    CANON = ROOT / config.experiment_dir(1) / "output/실험01_결과보고서.md"

    def _msgs(self, text):
        return [f.message for f in validate.check_body_style(text)]

    def test_승인본은_0건이다(self):
        # 이 검사의 폭은 승인본 v5 로 맞춘다 — 승인본에서 하나라도 잡히면 정규식이
        # 넓은 것이지 승인본이 틀린 것이 아니다.
        got = validate.check_body_style(self.CANON.read_text(encoding="utf-8"))
        self.assertEqual(got, [], [str(f) for f in got])

    def test_조사_띄어쓰기를_잡는다(self):
        msgs = self._msgs("# 실험 결과\n앞단 출력 L1 이 A·B 다.\n")
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn("조사", msgs[0])

    def test_붙여_쓴_조사는_잡지_않는다(self):
        self.assertEqual(self._msgs("# 실험 결과\n앞단 출력 L1이 A·B다. C 하나만 1이어도 켜진다.\n"), [])

    def test_단위_띄어쓰기를_잡는다(self):
        msgs = self._msgs("# 결과 분석\n전류는 (5.0 − 1.9) / 330 ≈ 9.4 mA 다.\n")
        self.assertEqual(len(msgs), 1, msgs)   # `9.4 mA` 하나. `330 ≈` 는 조사가 아니다
        self.assertIn("단위", msgs[0])

    def test_백틱과_em_dash와_첫째를_잡는다(self):
        msgs = self._msgs("# 고찰\n`L1` 이 켜졌다 — 첫째, 배선이 맞았다.\n")
        self.assertTrue(any("백틱" in m for m in msgs), msgs)
        self.assertTrue(any("em dash" in m for m in msgs), msgs)
        self.assertTrue(any("첫째" in m for m in msgs), msgs)

    def test_참고문헌_절과_표_줄은_보지_않는다(self):
        text = ("# 실험 결과\n\t| A | L1 |\n\t|---|---|\n\t| 1 | 1 |\n"
                "# 출처 및 참고문헌\n- Nexperia, 74HC_HCT08 — Rev. 9 — 2021-12-13, 5 V 조건\n")
        self.assertEqual(self._msgs(text), [])

    def test_HTML_표_줄도_보지_않는다(self):
        # 노션 되읽기는 표를 `<table>` 로 돌려준다 — 셀 안의 `5 V` 처럼 숫자
        # 뒤 단위를 띄어 쓴 것은 표의 정상 표기라 파이프 표와 똑같이 걸러야
        # 한다(`report_compare` 0단계가 이 함수를 baseline 에도 돌린다).
        text = ("# 실험 결과\n"
                "<table header-row=\"true\"><tr><td>전원</td></tr><tr><td>5 V</td></tr></table>\n")
        self.assertEqual(self._msgs(text), [])

    def test_각_갈래는_한_건으로_요약하고_첫_줄을_적는다(self):
        msgs = self._msgs("# 고찰\nL1 이 켜졌다.\nL2 가 꺼졌다.\n")
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn("2곳", msgs[0])
        self.assertIn("2행", msgs[0])


TABLE_SPEC_HEAD = """---
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
    tables: [T1, T6]
  - id: E1.P1-2
    title: 3-input OR
    device: [LED]
    ics: ["74HC32"]
    tables: [T2]
---

"""
_AND_ROWS = [(a, b, c, a & b, a & b & c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
_OR_ROWS = [(a, b, c, a | b, a | b | c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
_H5 = ["A", "B", "C", "L1", "L2"]


def _spec_truth(tid, title, source, rows):
    return (f"## {tid} · {title}\n\n- kind: truth-table\n- encoding: 0/1\n"
            f"- source: derived ({source})\n\n"
            "| A | B | C | L1 | L2 |\n|---|---|---|---|---|\n"
            + "".join("| " + " | ".join(map(str, r)) + " |\n" for r in rows) + "\n")


TABLE_SPEC = (TABLE_SPEC_HEAD
              + _spec_truth("T1", "3-input AND 진리표", "L1 = A·B ; L2 = A·B·C", _AND_ROWS)
              + _spec_truth("T2", "3-input OR 진리표", "L1 = A+B ; L2 = A+B+C", _OR_ROWS)
              + "## T6 · AND Gate Truth Table\n\n- kind: truth-table\n- encoding: H/L\n"
                "- source: manual:p5\n- role: reference\n\n"
                "| A | B | C |\n|---|---|---|\n"
                "| L | L | L |\n| L | H | L |\n| H | L | L |\n| H | H | H |\n")


def _report_table(header, rows, cols):
    """불릿 아래 탭 들여쓴 표 — ③ §절대 규칙 13 의 모양 그대로."""
    lines = ["\t| " + " | ".join(header) + " |", "\t|" + "---|" * len(header)]
    lines += ["\t| " + " | ".join(str(r[k]) for k in cols) + " |" for r in rows]
    return "\n".join(lines) + "\n"


_AND_T = _report_table(_H5, _AND_ROWS, [0, 1, 2, 3, 4])
_OR_T = _report_table(_H5, _OR_ROWS, [0, 1, 2, 3, 4])
_THEORY_T = ("- **AND**\n\t| A | B | C |\n\t|---|---|---|\n"
             "\t| L | L | L |\n\t| L | H | L |\n\t| H | L | L |\n\t| H | H | H |\n")
_STEP_H = ["구간", "CH1 에지 (U1 pin 4)", "CH2 에지 (U1 pin 8)", "측정값 (ns)"]
_STEP_ROWS = [("상승", "↑", "↓", ""), ("하강", "↓", "↑", "")]
_STEP_T = "- **전달 지연**\n" + _report_table(_STEP_H, _STEP_ROWS, [0, 1, 2, 3])
STEP_SPEC = (TABLE_SPEC
             + "\n## T3 · 전달 지연 측정\n\n- kind: stepped\n- encoding: 0/1\n"
               "- source: manual:p12\n\n"
               "| 구간 | CH1 에지 (U1 pin 4) | CH2 에지 (U1 pin 8) | 측정값 (ns) |\n"
               "|---|---|---|---|\n| 상승 | ↑ | ↓ |  |\n| 하강 | ↓ | ↑ |  |\n")

# 12열 기록 진리표 — §절대 규칙 19 로 A B C D Y0..Y3 / A B C D Y4..Y7 두 표로 나뉜다.
_WIDE_HEADER = ["A", "B", "C", "D", "Y0", "Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7"]
_WIDE_ROWS = [(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)]
_WIDE_SPEC = ("""---
schema: lab-spec/v2
experiment: 1
title: Wide Table
source_manual: from_the_past/정리/강의노트/실험1.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E1.P1-1
    title: 8-output demo
    device: [LED]
    ics: ["74HC138"]
    tables: [T1]
---

## T1 · 8-output 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (Y0..Y7)

""" + _report_table(_WIDE_HEADER, _WIDE_ROWS, list(range(12))) + "\n")
_WIDE_T1 = _report_table(_WIDE_HEADER[:8], _WIDE_ROWS, [0, 1, 2, 3, 4, 5, 6, 7])
_WIDE_T2 = _report_table(["A", "B", "C", "D", "Y4", "Y5", "Y6", "Y7"], _WIDE_ROWS,
                         [0, 1, 2, 3, 8, 9, 10, 11])


class ReportTables(unittest.TestCase):
    """③ §절대 규칙 22 · `check_report_tables`.

    2026-09 실험01 예보가 명세 T1~T4 의 `A B C L1 L2` 를 `A B C Y` 로 내고도
    ⑤ 를 통과했다 — 행 수 대조는 명세 안에서만 돈다. 조교 감점(-1).
    """

    def setUp(self):
        self.spec = spec_from(TABLE_SPEC)

    def _check(self, body):
        return validate.check_report_tables(md_file("# 제목\n\n" + body), self.spec)

    def test_명세_머리의_굵게와_백틱도_벗기고_본다(self):
        self.spec.table('T1').header = ['A', 'B', 'C', '`L1`', '**L2**']
        self.assertEqual(self._check(_AND_T + "\n" + _OR_T), [])

    def test_명세와_같은_표는_조용하다(self):
        self.assertEqual(self._check(_AND_T + "\n" + _OR_T + "\n" + _THEORY_T), [])

    def test_머리가_같은_명세_표_둘을_섞어_대조하지_않는다(self):
        """AND·OR 표는 머리도 행 수도 같다. 셀까지 같은 표끼리 짝지어야 한다 —
        머리만 보고 짝지으면 OR 표를 AND 명세로 대조해 셀 오류가 헛난다
        (2026-09-14 초안이 복원된 실험01 예보에서 12건을 헛냈다)."""
        self.assertEqual(self._check(_OR_T + "\n" + _AND_T), [])

    def test_열을_줄이고_이름을_바꾼_표를_짚는다(self):
        found = self._check(_report_table(["A", "B", "C", "Y"], _AND_ROWS, [0, 1, 2, 4])
                            + "\n" + _OR_T)
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0].level, "error")
        self.assertIn("명세 T1", found[0].message)
        self.assertIn("빠진 열: L1, L2", found[0].message)
        self.assertIn("명세에 없는 열: Y", found[0].message)

    def test_중간_출력_열이_빠진_표를_잡는다(self):
        found = self._check(_report_table(["A", "B", "C", "L2"], _AND_ROWS, [0, 1, 2, 4])
                            + "\n" + _OR_T)
        self.assertEqual([f.message for f in found],
                         ["명세 T1 의 열 L1 이 보고서 표에 없다 (명세: `A B C L1 L2`)"])

    def test_나눠_실은_표는_합집합으로_본다(self):
        """§절대 규칙 19 가 11열을 넘는 표를 입력 열을 되풀이해 나누게 한다."""
        body = (_report_table(["A", "B", "C", "L1"], _AND_ROWS, [0, 1, 2, 3]) + "\n"
                + _report_table(["A", "B", "C", "L2"], _AND_ROWS, [0, 1, 2, 4]) + "\n" + _OR_T)
        self.assertEqual(self._check(body), [])

    def test_열_순서가_바뀌면_잡는다(self):
        found = self._check(_report_table(["A", "B", "C", "L2", "L1"], _AND_ROWS, [0, 1, 2, 4, 3])
                            + "\n" + _OR_T)
        self.assertEqual(len(found), 1, found)
        self.assertIn("열 순서", found[0].message)

    def test_셀이_다르면_첫_행만_잡는다(self):
        wrong = _AND_T.replace("| 1 | 1 | 1 | 1 | 1 |", "| 1 | 1 | 1 | 1 | 0 |")
        found = self._check(wrong + "\n" + _OR_T)
        self.assertEqual(len(found), 1, found)
        self.assertIn("8번째 행", found[0].message)
        self.assertIn("명세 T1", found[0].message)

    def test_참조표가_없어도_조용하다(self):
        """참조표는 §절대 규칙 16 으로 빠질 수 있다."""
        self.assertEqual(self._check(_AND_T + "\n" + _OR_T), [])

    def test_명세에_없는_이론표는_잡지_않는다(self):
        """§섹션별 재료 실험 이론 ⑵ 가 데이터시트 function table 을 싣게 한다."""
        extra = ("- **x**\n\t| A | B | Y |\n\t|---|---|---|\n"
                 "\t| 0 | 0 | 0 |\n\t| 0 | 1 | 1 |\n\t| 1 | 0 | 1 |\n\t| 1 | 1 | 0 |\n")
        self.assertEqual(self._check(_AND_T + "\n" + _OR_T + "\n" + extra), [])

    def test_대응하는_표가_없으면_잡는다(self):
        self.assertEqual([f.message for f in self._check(_AND_T)],
                         ["명세 T2 (`A B C L1 L2`) 에 대응하는 표가 보고서에 없다"])

    def test_셀의_굵게와_백틱은_벗기고_본다(self):
        body = _AND_T.replace("| A | B | C | L1 | L2 |", "| **A** | B | C | `L1` | L2 |")
        self.assertEqual(self._check(body + "\n" + _OR_T), [])

    def test_보고서가_없으면_error(self):
        found = validate.check_report_tables(Path(tempfile.mkdtemp()) / "없다.md", self.spec)
        self.assertEqual([(f.level, f.message) for f in found],
                         [("error", "보고서 파일이 없다")])


class StepAndResultTables(unittest.TestCase):
    """스텝표 머리와 결과보고서 표 머리 (`check_report_tables(..., cells=False)`).

    2026-09-14 전에는 진리표만, 예비보고서에만 불렀다 — 결과보고서 표 머리는 아무도
    안 봤고 실험02 예보가 스텝표 머리를 줄여도 조용했다.
    """

    def setUp(self):
        self.spec = spec_from(STEP_SPEC)

    def _check(self, body, cells=True):
        return validate.check_report_tables(md_file("# 제목\n\n" + body), self.spec,
                                            cells=cells)

    def test_스텝표는_칸이_채워져도_머리만_맞으면_조용하다(self):
        filled = _report_table(_STEP_H, [("상승", "↑", "↓", "38"), ("하강", "↓", "↑", "41")],
                               [0, 1, 2, 3])
        self.assertEqual(self._check(_AND_T + "\n" + _OR_T + "\n" + filled), [])

    def test_스텝표_머리를_줄이면_잡는다(self):
        short = _report_table(["구간", "CH1 에지", "CH2 에지", "측정값 (ns)"], _STEP_ROWS,
                              [0, 1, 2, 3])
        found = self._check(_AND_T + "\n" + _OR_T + "\n" + short)
        self.assertEqual(len(found), 1, found)
        self.assertIn("명세 T3", found[0].message)
        self.assertIn("빠진 열: CH1 에지 (U1 pin 4), CH2 에지 (U1 pin 8)", found[0].message)

    def test_결과보고서는_셀이_달라도_머리만_본다(self):
        observed = _AND_T.replace("| 0 | 0 | 1 | 0 | 0 |", "| 0 | 0 | 1 | (미확인) | (미확인) |")
        self.assertEqual(self._check(observed + "\n" + _OR_T + "\n" + _STEP_T, cells=False), [])

    def test_결과보고서에서_표_하나가_빠지면_잡는다(self):
        """머리가 같은 AND·OR 표가 보고서 표 하나를 나눠 갖지 않는다 — 1:1 로 짝짓는다."""
        found = self._check(_AND_T + "\n" + _STEP_T, cells=False)
        self.assertEqual([f.message for f in found],
                         ["명세 T2 (`A B C L1 L2`) 에 대응하는 표가 보고서에 없다"])

    def test_결과보고서에서도_열_이름을_바꾸면_잡는다(self):
        renamed = _report_table(["A", "B", "C", "L1", "Y"], _AND_ROWS, [0, 1, 2, 3, 4])
        found = self._check(renamed + "\n" + _OR_T + "\n" + _STEP_T, cells=False)
        self.assertEqual(len(found), 1, found)
        self.assertIn("명세에 없는 열: Y", found[0].message)

    def test_나눈_결과표_두_조각을_합치면_cells_False_가_조용하다(self):
        """§절대 규칙 19 로 나뉜 12열 표 — 두 조각이 함께 명세 T1 을 덮는다."""
        spec = spec_from(_WIDE_SPEC)
        found = validate.check_report_tables(
            md_file("# 제목\n\n" + _WIDE_T1 + "\n" + _WIDE_T2), spec, cells=False)
        self.assertEqual(found, [])

    def test_나눈_결과표_한_조각이_빠지면_남은_열이_잡힌다(self):
        spec = spec_from(_WIDE_SPEC)
        found = validate.check_report_tables(
            md_file("# 제목\n\n" + _WIDE_T1), spec, cells=False)
        self.assertEqual(len(found), 1, found)
        self.assertIn("명세 T1 의 열 Y4, Y5, Y6, Y7 이 보고서 표에 없다", found[0].message)

    def test_나눈_결과표_두_조각은_cells_True_에서도_조용하다(self):
        spec = spec_from(_WIDE_SPEC)
        found = validate.check_report_tables(
            md_file("# 제목\n\n" + _WIDE_T1 + "\n" + _WIDE_T2), spec, cells=True)
        self.assertEqual(found, [])


# 강의노트 실험3 p6(반감산기) 텍스트 층의 모양 — pypdf 가 실제로 내는 줄을 줄였다
_P6 = ("2. 실험 이론\n• 반감산기 (Half Subtractor)\n"
       "- 2개 비트 A와 B를 입력 받아, 차 D와 내림 수 B를 출력\n"
       "입력 출력\nA B D B\n0 0 0 0\n0 1 1 1\n1 0 1 0\n1 1 0 0\n"
       "A\nB\nD\nB\nTruth Table74HC86\n74HC08\n회로 구성\n74HC04")
_PAGES = [""] * 5 + [_P6] + [""] * 3


class ManualNames(unittest.TestCase):
    """`check_manual_names` — 명세 열 이름을 강의노트 쪽 텍스트와 맞댄다.

    2026-09-14 실험03 명세가 반감산기 내림 수 `B` 를 `Bo` 로 바꿨는데, 이름 검사가
    전부 명세 기준이라 하류 검사가 다 통과했다.
    """

    def _spec(self, *pairs):
        text = SHARED_LETTER.read_text(encoding="utf-8")
        for old, new in pairs:
            self.assertIn(old, text)
            text = text.replace(old, new)
        return spec_from(text)

    def test_교안_그대로면_조용하다(self):
        self.assertEqual(validate.check_manual_names(self._spec(), _PAGES), [])

    def test_Bo_로_바꾸면_두_표_모두_잡는다(self):
        spec = self._spec(("| A | B | D | B |", "| A | B | D | Bo |"),
                          ("B = A'·B", "Bo = A'·B"),
                          ("- outputs: [D, B]", "- outputs: [D, Bo]"))
        found = validate.check_manual_names(spec, _PAGES)
        self.assertEqual(sorted((f.level, f.where.rsplit(":", 1)[-1]) for f in found),
                         [("error", "T5"), ("error", "T6")])
        messages = " ".join(f.message for f in found)
        self.assertIn("열 `Bo` 가 교안 p6 에 없다", messages)
        self.assertIn("머리 `A B D Bo` 가 교안 p6 에 이 순서로 없다", messages)

    def test_라틴_토큰이_아닌_머리는_info_한_줄만_내고_건너뛴다(self):
        """T5 머리만 `B'` 로 바꿔 라틴 토큰이 아닌 열을 만든다 — T6 은 그대로다."""
        spec = self._spec(("- source: derived (D = A⊕B ; B = A'·B)\n\n| A | B | D | B |",
                           "- source: derived (D = A⊕B ; B = A'·B)\n\n| A | B | D | B' |"))
        found = validate.check_manual_names(spec, _PAGES)
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0].level, "info")
        self.assertEqual(found[0].where.rsplit(":", 1)[-1], "T5")
        self.assertIn("라틴 토큰이 아닌 열", found[0].message)
        self.assertIn("B'", found[0].message)

    def test_참조표_머리_순서가_바뀌면_잡는다(self):
        spec = self._spec(("- outputs: [D, B]\n\n| A | B | D | B |",
                           "- outputs: [D, B]\n\n| B | A | D | B |"))
        found = validate.check_manual_names(spec, _PAGES)
        self.assertEqual([(f.level, f.where.rsplit(":", 1)[-1]) for f in found],
                         [("error", "T6")])

    def test_pages_가_없으면_error(self):
        found = validate.check_manual_names(self._spec(("    pages: [6]\n", "")), _PAGES)
        self.assertEqual([(f.level, f.where.rsplit(":", 1)[-1]) for f in found],
                         [("error", "E3.P2-1")])
        self.assertIn("pages", found[0].message)

    def test_없는_쪽을_가리키면_error(self):
        found = validate.check_manual_names(self._spec(("pages: [6]", "pages: [12]")), _PAGES)
        self.assertEqual([f.level for f in found], ["error"])
        self.assertIn("교안 p12 은 없다", found[0].message)

    def test_텍스트_층이_없는_쪽은_info(self):
        found = validate.check_manual_names(self._spec(), [""] * 9)
        self.assertTrue(found)
        self.assertEqual({f.level for f in found}, {"info"})

    def test_강의노트를_못_열면_info_한_줄(self):
        found = validate.check_manual_names(self._spec(), [])
        self.assertEqual([f.level for f in found], ["info"])


_RANGE_SPEC = """---
schema: lab-spec/v2
experiment: 5
title: t
source_manual: x.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E5.P1-2
    title: t
    device: [LED]
    ics: ["74HC42"]
    tables: [T1]
    pages: [1]
---

## T1 · t

- kind: truth-table
- encoding: 0/1
- source: derived (OUT = IN)

| IN | OUT |
|---|---|
| 0 | 0 |
| 1 | 1 |
"""


class ManualNameRanges(unittest.TestCase):
    """강의노트가 열 이름을 범위로만 적은 쪽 — 실험05 p9 `Bit0-3: Input, Y0-Y9: Output`.

    텍스트 층에 `Bit1`·`Y5` 토큰이 없어 교안 이름 그대로인 명세가 error 11건을 냈다
    (2026-10-05).
    """

    def _found(self, inp, out, page):
        text = _RANGE_SPEC.replace("OUT = IN", f"{out} = {inp}").replace(
            "| IN | OUT |", f"| {inp} | {out} |")
        return validate.check_manual_names(spec_from(text), [page])

    def test_범위_안의_이름은_조용하다(self):
        page = "※ Bit0-3:  Input, Y0-Y9: Output"
        self.assertEqual(self._found("Bit2", "Y5", page), [])

    def test_접두어를_되풀이한_범위도_펼친다(self):
        self.assertEqual(self._found("D2", "A1", "D0-D5 입력, A0-A3 출력"), [])

    def test_물결표와_공백도_펼친다(self):
        self.assertEqual(self._found("Bit1", "A2", "Bit0 - 3 입력, A0 ~ A3 출력"), [])

    def test_범위_밖_번호는_여전히_error(self):
        found = self._found("Bit2", "Y10", "Bit0-3: Input, Y0-Y9: Output")
        self.assertEqual([f.level for f in found], ["error"])
        self.assertIn("열 `Y10` 가 교안 p1 에 없다", found[0].message)

    def test_폭이_16_을_넘으면_펼치지_않는다(self):
        found = self._found("Rev5", "Y1", "Rev1-2024 개정, Y0-Y9")
        self.assertEqual([f.level for f in found], ["error"])
        self.assertIn("열 `Rev5`", found[0].message)

    def test_내림차순은_펼치지_않는다(self):
        found = self._found("Bit0", "Y5", "Bit0 입력, Y9-Y0 출력")
        self.assertEqual([f.level for f in found], ["error"])
        self.assertIn("열 `Y5`", found[0].message)

    def test_교안_표_머리는_펼친_토큰으로_통과하지_않는다(self):
        """`manual:pN` 표는 머리 토큰열이 그 쪽에 순서대로 있어야 한다 — 범위로 대신할 수 없다."""
        text = (_RANGE_SPEC.replace("tables: [T1]", "tables: [T1, T2]")
                .replace("OUT = IN", "Y0 = Bit0").replace("| IN | OUT |", "| Bit0 | Y0 |")
                + "\n## T2 · r\n\n- kind: truth-table\n- encoding: 0/1\n"
                  "- source: manual:p1\n- role: reference\n\n"
                  "| Bit1 | Y5 |\n|---|---|\n| 0 | 1 |\n| 1 | 0 |\n")
        found = validate.check_manual_names(spec_from(text), ["Bit0-3: Input, Y0-Y9: Output"])
        self.assertEqual([(f.level, f.where.rsplit(":", 1)[-1]) for f in found],
                         [("error", "T2")])
        self.assertIn("머리 `Bit1 Y5`", found[0].message)


class RealReportTables(unittest.TestCase):
    def test_실제_실험1_예비보고서의_표가_명세와_맞다(self):
        """2026-09 조교 감점(-1) 뒤 T1~T4 를 명세의 `A B C L1 L2` 로 되돌렸다."""
        exp = Path(config.experiment_dir(1))
        found = validate.check_report_tables(exp / "output/실험01_예비보고서.md",
                                             parse_spec(exp / "체크리스트/명세.md"))
        self.assertEqual([str(f) for f in found], [])

    def test_실제_실험1_결과보고서의_표_머리가_명세와_맞다(self):
        """결과 칸은 `(미확인)`·관측값이라 머리만 본다(`cells=False`)."""
        exp = Path(config.experiment_dir(1))
        found = validate.check_report_tables(exp / "output/실험01_결과보고서.md",
                                             parse_spec(exp / "체크리스트/명세.md"),
                                             cells=False)
        self.assertEqual([str(f) for f in found], [])

    def test_실제_실험3_예비보고서의_표가_명세와_맞다(self):
        """2026-09-14 반감산기 내림 수를 교안 표기 `B` 로 되돌린 판(`A B D B`)."""
        exp = Path(config.experiment_dir(3))
        found = validate.check_report_tables(exp / "output/실험03_예비보고서.md",
                                             parse_spec(exp / "체크리스트/명세.md"))
        self.assertEqual([str(f) for f in found], [])


SHARED_LETTER = FIXTURES / "spec_shared_letter.md"
_HS_ROWS = [(a, b, a ^ b, (1 - a) & b) for a in (0, 1) for b in (0, 1)]


class SharedLetter(unittest.TestCase):
    """교안이 입력과 출력에 같은 글자를 쓴다 — 실험3 반감산기 `A B D B`.

    이름을 키로 삼는 곳은 전부 두 `B` 를 하나로 뭉갠다. 역검산은 출력 값을 입력
    자리에 넣고, 보고서 표 대조는 둘째 `B` 를 입력 열과 맞대 "셀이 틀렸다" 는
    거짓 error 를 냈다(2026-09-14 실험03 pre_review_round2 스크래치 실측).
    """

    def setUp(self):
        self.spec = parse_spec(SHARED_LETTER)

    def _report(self, header, cols, rows=_HS_ROWS):
        body = "# 제목\n\n- **반감산기**\n" + _report_table(header, rows, cols)
        return validate.check_report_tables(md_file(body), self.spec)

    def test_교안_표기_그대로면_error_도_warn_도_없다(self):
        findings = [f for f in validate.validate_spec(self.spec)
                    if f.level in ("error", "warn")]
        self.assertEqual(findings, [], "\n".join(str(f) for f in findings))

    def test_역검산은_출력_B_를_입력_B_와_따로_본다(self):
        text = SHARED_LETTER.read_text(encoding="utf-8").replace(
            "| 0 | 1 | 1 | 1 |", "| 0 | 1 | 1 | 0 |", 1)
        found = [f for f in validate.check_boolean(spec_from(text)) if f.level == "error"]
        self.assertEqual(len(found), 1, "\n".join(str(f) for f in found))
        self.assertTrue(found[0].where.endswith("T5 행2"), found[0].where)
        self.assertIn("A=0, B(2열)=1 일 때 B(4열) = A'·B = 1 인데 표에는 '0' 이다",
                      found[0].message)

    def test_보고서_표가_교안_머리_그대로면_조용하다(self):
        self.assertEqual(self._report(["A", "B", "D", "B"], [0, 1, 2, 3]), [])

    def test_둘째_B_를_빼면_출력_열이_빠졌다고_짚는다(self):
        """이름 집합으로 보면 `B` 가 이미 있어 빠진 열이 없는 것처럼 보인다."""
        self.assertEqual([f.message for f in self._report(["A", "B", "D"], [0, 1, 2])],
                         ["명세 T5 의 열 B(4열) 이 보고서 표에 없다 (명세: `A B D B`)"])

    def test_Bo_로_바꾸면_머리가_다르다고_짚는다(self):
        found = self._report(["A", "B", "D", "Bo"], [0, 1, 2, 3])
        self.assertEqual(len(found), 1, found)
        self.assertIn("빠진 열: B · 명세에 없는 열: Bo", found[0].message)

    def test_둘째_B_의_셀은_명세_넷째_열과_맞댄다(self):
        wrong = [(a, b, d, 1 - bo) if (a, b) == (0, 1) else (a, b, d, bo)
                 for a, b, d, bo in _HS_ROWS]
        found = self._report(["A", "B", "D", "B"], [0, 1, 2, 3], wrong)
        self.assertEqual(len(found), 1, found)
        self.assertIn("2번째 행", found[0].message)
        self.assertIn("보고서 ['0', '1', '1', '0'] · 명세 ['0', '1', '1', '1']",
                      found[0].message)

    def test_한_표_안의_같은_글자는_따로_알린다(self):
        """"표마다 뜻이 다르다" 가 아니다 — 같은 표 안에서 입력이자 출력이다."""
        found = validate.check_column_roles(self.spec)
        self.assertEqual([f.level for f in found], ["info"])
        self.assertIn("열 `B` 이 한 표 안에서 입력이자 출력이다 (T5·T6)", found[0].message)
        self.assertNotIn("표마다", found[0].message)


class TestItemScope(unittest.TestCase):
    """조교 공지 `_350547_1` — 명세는 실험실에서 하는 소실험만 싣는다."""

    def test_범위와_맞으면_조용하다(self):
        spec = scoped_spec(3, ["E3.P1-2", "E3.P2-2"])
        self.assertEqual(validate.check_item_scope(spec), [])

    def test_범위가_없는_실험은_보지_않는다(self):
        spec = scoped_spec(1, ["E1.P1-1", "E1.P3"])
        self.assertEqual(validate.check_item_scope(spec), [])

    def test_범위_밖_항목은_error(self):
        found = validate.check_item_scope(scoped_spec(3, ["E3.P1-1", "E3.P1-2", "E3.P2-2"]))
        self.assertEqual([(f.level, f.where) for f in found], [("error", "명세.md:E3.P1-1")])
        self.assertIn("_350547_1", found[0].message)

    def test_범위_번호에_맞는_항목이_없으면_error(self):
        found = validate.check_item_scope(scoped_spec(3, ["E3.P1-2"]))
        self.assertEqual([(f.level, f.where) for f in found], [("error", "명세.md")])
        self.assertIn("`2-2`", found[0].message)

    def test_가지_없는_토큰은_가지_항목으로_채워진다(self):
        spec = scoped_spec(7, ["E7.P1-1", "E7.P1-2"])
        self.assertEqual(validate.check_item_scope(spec), [])

    def test_validate_spec_은_범위를_보지_않는다(self):
        """픽스처가 명세 문법의 표본으로 범위 밖 항목을 쓴다(`spec_manual_outputs.md`)."""
        spec = scoped_spec(3, ["E3.P1-1", "E3.P1-2", "E3.P2-2"])
        self.assertFalse(any("_350547_1" in f.message for f in validate.validate_spec(spec)))


class TestCheckResultPhotoDiagrams(unittest.TestCase):
    """결과보고서 실험 사진 절의 항목 소절마다 예보 결선도가 있는지 본다.

    2026-09-18 실험01 결보 조교 피드백("실험 사진과 함께 예비보고서에서
    그리셨던 회로 결선도를 첨부")에서 왔다. 산문 규칙만 두면 격리 재생성에서
    빠져도 아무도 못 잡는다.
    """

    GOOD = (
        "# 실험 사진\n\n머리말.\n\n"
        "## 실험 1-2) 전가산기\n\n"
        "![예비보고서에서 그린 전가산기 결선도](../결선도/손그림/실험03_1-2_손그림_전가산기.png)\n\n"
        "![전가산기 회로의 입력 조합 000부터 011까지](../실험사진/시트/a_1.jpg)\n\n"
        "## 실험 2-2) 전감산기\n\n"
        "![예비보고서에서 그린 전감산기 결선도](../결선도/손그림/실험03_2-2_손그림_전감산기.png)\n\n"
        "![전감산기 회로의 입력 조합 000부터 011까지](../실험사진/시트/b_1.jpg)\n\n"
        "# 예비보고서와의 비교\n\n본문.\n"
    )

    def test_소절마다_결선도가_시트_앞에_있으면_깨끗하다(self):
        self.assertEqual(validate.check_result_photo_diagrams(self.GOOD), [])

    def test_결선도가_빠진_소절을_지목한다(self):
        text = self.GOOD.replace(
            "![예비보고서에서 그린 전감산기 결선도](../결선도/손그림/실험03_2-2_손그림_전감산기.png)\n\n", "")
        found = validate.check_result_photo_diagrams(text)
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0].level, "warn")
        self.assertEqual(found[0].where, "실험 사진 / 실험 2-2) 전감산기")

    def test_결선도가_시트_뒤에_있으면_잡는다(self):
        text = (
            "# 실험 사진\n\n"
            "## 실험 1-1) 3-input AND gate\n\n"
            "![3입력 AND 회로의 네 입력 조합](../실험사진/시트/a.jpg)\n\n"
            "![예비보고서에서 그린 3입력 AND 결선도](../결선도/손그림/b.png)\n"
        )
        found = validate.check_result_photo_diagrams(text)
        self.assertEqual(len(found), 1, found)
        self.assertIn("앞", found[0].message)

    def test_다른_대절의_결선도는_세지_않는다(self):
        text = (
            "# 실험 사진\n\n"
            "## 실험 1-1) 3-input AND gate\n\n"
            "![3입력 AND 회로의 네 입력 조합](../실험사진/시트/a.jpg)\n\n"
            "# 결과 분석\n\n"
            "![예비보고서에서 그린 3입력 AND 결선도](../결선도/손그림/b.png)\n"
        )
        self.assertEqual(len(validate.check_result_photo_diagrams(text)), 1)

    def test_작도_PNG_폴백도_결선도로_센다(self):
        text = (
            "# 실험 사진\n\n"
            "## 실험 1-1) 3-input AND gate\n\n"
            "![예비보고서의 3입력 AND 결선도](../결선도/실험01_1-1_결선도_3입력_AND.png)\n\n"
            "![3입력 AND 회로의 네 입력 조합](../실험사진/시트/a.jpg)\n"
        )
        self.assertEqual(validate.check_result_photo_diagrams(text), [])

    def test_실험_사진_절이_없으면_검사하지_않는다(self):
        # 예비보고서에도 같이 부르므로 대상이 아니면 조용해야 한다.
        text = "# 회로 결선도\n\n## 실험 1-1) 결선\n\n![결선도](../결선도/a.png)\n"
        self.assertEqual(validate.check_result_photo_diagrams(text), [])

    def test_프런트매터가_있어도_동작한다(self):
        text = "---\nexperiment: 3\n---\n\n" + self.GOOD
        self.assertEqual(validate.check_result_photo_diagrams(text), [])

    def test_실험02_03_결과보고서는_결선도를_싣는다(self):
        for n in (2, 3):
            with self.subTest(n):
                name = config.experiment_folder_name(n)
                path = ROOT / config.experiment_dir(n) / f"output/{name}_결과보고서.md"
                found = validate.check_result_photo_diagrams(
                    path.read_text(encoding="utf-8"))
                self.assertEqual(found, [])
                # 가리킨 결선도 파일이 실재해야 한다 — 노션에 손으로 끼울 원본이다.
                for src in validate._IMAGE.findall(path.read_text(encoding="utf-8")):
                    if "결선도/" in src:
                        self.assertTrue((path.parent / src).exists(), src)


class TestStageLeds(unittest.TestCase):
    """LED 급전 표기 검증 — 못 풀면 체크리스트가 옛 단계 표로 물러선다(2026-10-11)."""

    E5 = ROOT / config.experiment_dir(5)

    def _check(self, text=None):
        spec = parse_spec(self.E5 / "체크리스트/명세.md")
        if text is None:
            return validate.check_netlist_circuits(
                parse_netlist(self.E5 / "결선도/netlist.md"), spec)
        # 원본 결선도 폴더를 비춘 임시 폴더에 사본을 둔다 — PNG 상대경로가 그대로 풀려야 한다
        with netlist_copy(self.E5 / "결선도", text) as path:
            return validate.check_netlist_circuits(parse_netlist(path), spec)

    def test_실험05_는_LED_급전_경고가_없다(self):
        f = self._check()
        self.assertEqual([x for x in f if x.message.startswith("LED 급전")], [])

    def test_보드에_없는_LED_태그는_경고(self):
        src = (self.E5 / "결선도/netlist.md").read_text(encoding="utf-8")
        f = self._check(src.replace("→LED Y3 급전", "→LED Y33 급전"))
        self.assertTrue(any("Y33" in x.message for x in f
                            if x.level == "warn" and x.message.startswith("LED 급전")))

    def test_관측_노드가_LED_에_없는_단계는_경고(self):
        src = (self.E5 / "결선도/netlist.md").read_text(encoding="utf-8")
        f = self._check(src.replace("**임시로** U1 pin 12→LED A2 급전", ""))
        self.assertTrue(any("단계 2" in x.message and "옛 단계 표" in x.message for x in f
                            if x.message.startswith("LED 급전")))

    def test_급전_표기_없는_관측_단계는_경고(self):
        src = (self.E5 / "결선도/netlist.md").read_text(encoding="utf-8")
        f = self._check(src.replace(", U4 pin 1→LED Y0 급전", ""))
        self.assertTrue(any("옛 단계 표" in x.message for x in f
                            if x.message.startswith("LED 급전")))


if __name__ == "__main__":
    unittest.main()
