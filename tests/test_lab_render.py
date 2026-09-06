import re
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.render import crop_rows, render_checklist
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(
    encoding="utf-8")


class TestChecklistHtml(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.netlist = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(encoding="utf-8")
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
        spec = parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md")
        html = render_checklist(spec, "VCC GND 미사용", TEMPLATE)
        self.assertIn('class="sketch"', html)


class TestCrop(unittest.TestCase):
    def test_row_count_comes_from_the_netlist(self):
        """쓰는 행만 남겨 작도 면적을 줄이는 것이 실제 관행이다 (2020 예보2).

        `0 < crop_rows(x) <= 30` 는 공식이 `min(max(6, n*8), 30)` 이라 **모든**
        입력에서 참이라 상수를 반환해도 통과했다(C2) — 계산된 실제 값을 단언한다.
        """
        netlist = "- U1 = 74HC08\n  - pin 1 ← 입력 A\n  - pin 14 → VCC(+5V)\n"
        self.assertEqual(crop_rows(netlist), 8)   # IC 1개 → max(6, 1*8) = 8

    def test_row_count_is_capped_at_the_maximum(self):
        netlist = "\n".join(f"- U{i} = 74HC08 (quad 2-input AND)" for i in range(1, 10))
        self.assertEqual(crop_rows(netlist), 30)   # max(6, 9*8=72) 를 30 에서 자른다

    def test_ic_count_is_not_limited_to_the_74xx_family(self):
        """" = 74" 휴리스틱은 40xx·555 계열을 0개로 세 격자가 아예 없는
        크롭(바닥값 6행 = 36mm, 머리띠 51.4mm 보다 작다)으로 이어졌다 (B1)."""
        with_ic = "- U1 = 4011 (quad 2-input NAND)\n  - pin 14 → VCC(+5V)\n"
        without_ic = "IC 선언이 전혀 없는 netlist 다\n"
        self.assertEqual(crop_rows(with_ic), 8)
        self.assertEqual(crop_rows(without_ic), 6)
        self.assertGreater(crop_rows(with_ic), crop_rows(without_ic))


class TestBreadboardHeaderBand(unittest.TestCase):
    """Breadboard.jpg 상단 로고·범례 띠가 크롭 계산에 없으면, `object-position:
    top` 크롭이 머리띠부터 자르기 시작해 캡션이 약속하는 행 수만큼의 실제
    격자가 안 보인다 (B1)."""

    def test_visible_height_budget_includes_the_header_band(self):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(encoding="utf-8")
        html = render_checklist(spec, netlist, TEMPLATE)
        rows = crop_rows(netlist)
        caption = re.search(r"브레드보드 작도 \((\d+)행\)", html)
        self.assertIsNotNone(caption)
        self.assertEqual(int(caption.group(1)), rows)
        height = re.search(r"max-height:([\d.]+)mm", html)
        self.assertIsNotNone(height)
        # rows*6mm 만 예산으로 두면 그만큼이 전부 머리띠에 먹혀 격자가 0행
        # 보인다 — 머리띠만큼 더 커야 캡션의 행 수가 실제로 보인다.
        self.assertGreater(float(height.group(1)), rows * 6)


class TestPrintConstraints(unittest.TestCase):
    """실험실 물리 조건은 CSS 에만 있어서 문자열 검증이 없으면 조용히 사라진다.
    실제로 이 공백 때문에 브레드보드 그림이 제목과 갈라진 채 두 라운드를 통과했다."""

    def test_회로마다_새_쪽에서_시작한다(self):
        """회로 둘이 한 쪽을 나눠 쓰면 칩 교체 경계가 지면에서 사라진다."""
        rule = re.search(r"\.circuit\s*\{[^}]*\}", TEMPLATE, re.S)
        self.assertIsNotNone(rule, "`.circuit` 규칙이 없다")
        self.assertIn("break-before: page", rule.group(0))

    def test_배선_체크박스가_펜으로_칠할_만큼_크다(self):
        rule = re.search(r"\.box\s*\{[^}]*\}", TEMPLATE, re.S)
        self.assertIsNotNone(rule, "`.box` 규칙이 없다")
        self.assertIn("4mm", rule.group(0))

    def test_결선도와_배선이_한_덩어리로_유지된다(self):
        """넘치면 표만 다음 쪽으로 가야 한다 — 그림과 배선이 갈리면 못 쓴다."""
        rule = re.search(r"\.wirebox\s*\{[^}]*\}", TEMPLATE, re.S)
        self.assertIsNotNone(rule, "`.wirebox` 규칙이 없다")
        self.assertIn("break-inside: avoid", rule.group(0))

    def test_플레이스홀더_네_개가_있다(self):
        for token in ("{{TITLE}}", "{{COMMON}}", "{{CIRCUITS}}", "{{CLOSING}}"):
            with self.subTest(token=token):
                self.assertIn(token, TEMPLATE)

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
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(encoding="utf-8")
        html = render_checklist(spec, netlist, TEMPLATE)
        self.assertEqual(html.count('<div class="tblock">'),
                         5 + 1)   # 기록 대상 표 5개 + 브레드보드 1


class TestProcedureCarriesEveryWarning(unittest.TestCase):
    """영문 `pin` 이 든 줄만 고르면 한글로 쓴 경고가 통째로 사라진다.
    이 과목의 대표 실패 원인(플로팅 입력) 경고가 실제로 그렇게 빠져 있었다."""

    def setUp(self):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(encoding="utf-8")
        self.html = render_checklist(spec, netlist, TEMPLATE)

    def test_korean_only_warnings_reach_the_printout(self):
        for warning in ("띄워두지 않는다", "가장 흔한 배선 실수",
                        "330Ω 직렬", "칩 재사용",
                        # 아래 셋은 불릿이 아니라 열 0 산문이라 별도 결함(A2)으로
                        # 빠져 있었다 — X≡Z 자체 검증, 74HC02 핀 순서 재경고,
                        # E1.P1-2 NAND 절 도입문.
                        "다르면 배선 오류", "핀 순서에 주의", "교안 p12 회로도 그대로"):
            with self.subTest(warning=warning):
                self.assertIn(warning, self.html)

    def test_multiline_bullets_are_not_truncated(self):
        """`74HC02` 경고는 세 줄짜리 불릿이다. 이어지는 줄을 버리면 잘린다."""
        self.assertIn("핀 1·4·10·13", self.html)

    def test_markdown_syntax_does_not_reach_print(self):
        body = self.html[self.html.index('<div class="power">'):]
        self.assertNotIn("**", body)
        self.assertNotIn("`", body)


class TestOverbarCssAcrossTemplates(unittest.TestCase):
    """`border-top` 만으로는 중첩 오버바 두 겹이 같은 높이에 겹쳐 그려져
    `(A'·B)'` 가 바 하나로 뭉개진다. 실제 렌더로 확인한 결함이고, 그 식은
    2주차 T5 의 실제 source 다 — 제출 보고서에 틀린 표기가 인쇄된다."""

    def test_every_template_that_uses_overbars_supports_nesting(self):
        skills = (ROOT / ".claude" / "skills").glob("*/template.html")
        checked = 0
        for template in skills:
            css = template.read_text(encoding="utf-8")
            if ".ov" not in css:
                continue          # 표지처럼 부울식을 쓰지 않는 템플릿
            checked += 1
            with self.subTest(template=template.parent.name):
                # `.ov` 규칙 자체를 본다. 파일 아무 데나 inline-block 이 있으면
                # 통과하는 검사로는 옛 CSS 로의 회귀를 잡지 못한다.
                rule = re.search(r"\.ov\s*\{[^}]*\}", css, re.S)
                self.assertIsNotNone(rule, f"{template} 에 .ov 규칙이 없다")
                self.assertIn("inline-block", rule.group(0))
        self.assertGreaterEqual(checked, 3)


if __name__ == "__main__":
    unittest.main()


class ChecklistTitleTest(unittest.TestCase):
    """인쇄 체크리스트 제목. record 쪽과 같은 이유로 고정한다."""

    def test_제목이_실험_기준이고_주차가_없다(self):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(encoding="utf-8")
        tmpl = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(
            encoding="utf-8")
        html = render_checklist(spec, netlist, tmpl)
        self.assertIn("실험1 Basic Gates 체크리스트", html)
        self.assertNotIn("2주차 · 실험1", html)

    def test_두_산출물의_제목이_같은_함수에서_나온다(self):
        """기록과 체크리스트가 갈라지면 한쪽만 고쳐진다."""
        from scripts.lab import config
        from scripts.lab.record import derive_record
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(encoding="utf-8")
        tmpl = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(
            encoding="utf-8")
        self.assertIn(config.document_title(spec.experiment, spec.title, "체크리스트"),
                      render_checklist(spec, netlist, tmpl))
        self.assertIn(config.document_title(spec.experiment, spec.title, "기록"),
                      derive_record(spec))
