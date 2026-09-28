import json
import re
import tempfile
import types
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.lab import config, render
from scripts.lab.netlist_parser import NetlistSection, parse_netlist
from scripts.lab.photo_names import FILE
from scripts.lab.render import (CLOSING, _blocks, _capture_html, _chip_boxes,
                                _chip_tables, _circuit_body, _esc,
                                _has_entry_walk, _has_walk,
                                _plain,
                                _truth_table_html, circuit_pages, closing_page,
                                common_page, crop_rows, render_checklist)
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(
    encoding="utf-8")

_MISSING_DIAGRAM_NETLIST = """---
schema: lab-netlist/v2
experiment: 1
spec: ../체크리스트/명세.md
---

# C1 · 결선도 없음 (IC 한 개)

- kind: circuit
- id: C1
- item: E1.P1-1
- tables: [T1]

- U1 = 74HC08 (quad 2-input AND)
  - pin 14 → VCC(+5V)
  - 미사용 입력핀: pin 9, 10 → GND

# C2 · 결선도 없음 (IC 두 개)

- kind: circuit
- id: C2
- item: E1.P1-2
- tables: [T2]

- U2 = 74HC00 (quad 2-input NAND)
  - pin 14 → VCC(+5V)
- U3 = 74HC32 (quad 2-input OR)
  - pin 1 ← 입력 A
  - 미사용 입력핀: pin 9, 10 → GND
"""


def _netlist_missing_diagrams():
    """`diagram:` 이 없는 회로 두 개짜리 합성 픽스처.

    d556077 이 실험01 결선도에 OR·NOR PNG 를 더해 다섯 회로 전부가 `diagram:`
    을 갖게 되면서, 결선도 부재 fallback(빈 브레드보드 대체) 경로를 실물로는
    더 이상 시험할 수 없게 됐다. 실물을 도로 비우는 것은 답이 아니므로(그림을
    지우는 것) 합성한다 — 관례는 `test_lab_validate.TestNetlistCircuits._netlist`
    를 따른다: 최소 프론트매터 + `kind: circuit` 절만 갖춘 netlist.md 를 임시
    파일로 써서 `parse_netlist` 로 읽는다. `item`·`tables` 는 실험01 실물
    명세(T1·T2, E1.P1-1·E1.P1-2)를 그대로 가리켜 `spec.table()`·`spec.items`
    조회가 실물과 같은 경로를 타게 한다. IC 개수를 회로마다 다르게 두어
    (1개 vs 2개) `crop_rows` 가 회로마다 다른 행 수를 내는 것도 같이 본다."""
    path = Path(tempfile.mkdtemp()) / "netlist.md"
    path.write_text(_MISSING_DIAGRAM_NETLIST, encoding="utf-8")
    return parse_netlist(path)


class TestChecklistHtml(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
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
        """개수를 박지 말고 명세에서 센다. `.check` 는 `truth-table` 전용이다 —
        `stepped` 는 명세의 빈 셀(`.fill`)이 기록 칸이고, `capture` 는 셀 표가
        아니다."""
        expected = sum(len(self.spec.table(t).rows)
                       for item in self.spec.items for t in item.tables
                       if self.spec.table(t).kind == "truth-table"
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

    def test_사진_부착_2열_상자를_인쇄하지_않는다(self):
        """실험실에서 종이에 사진을 붙일 수 없고, 보고서 배치는 ④ 가 한다.
        결과보고서 레이아웃이 실험실 인쇄본에 샌 것이었다."""
        self.assertNotIn('class="pair"', self.html)
        self.assertNotIn("(사진 부착)", self.html)

    def test_사진_파일명_규칙이_인쇄본에_있다(self):
        """규칙은 SKILL.md 에만 있었다 — 실험실에서 기억에 의존해야 했다.
        2026-09-19 부터는 행마다 찍을 이름 자체를 인쇄한다(시트 엔진 규칙)."""
        self.assertIn("사진 파일명", self.html)
        self.assertIn("1-1 000.jpg", self.html)
        self.assertNotIn("row3.jpg", self.html)

    def test_종료_전_확인_목록이_마지막에_온다(self):
        self.assertIn("부품", self.html)
        self.assertLess(self.html.index("오늘의 흐름"), self.html.index("반납"))

    def test_종료_전_확인_항목이_하나도_빠지지_않는다(self):
        """항목을 하나만 남겨도 위치 테스트는 통과한다. 실험실에서 놓치면
        결과보고서에서 복구할 수 없는 것들이라 전수로 센다."""
        self.assertGreaterEqual(len(CLOSING), 7)
        for item in CLOSING:
            with self.subTest(item=item):
                self.assertIn(_esc(item), self.html)


class TestSharedLetterTruthTable(unittest.TestCase):
    """실험3 반감산기 `A B D B` — 입력 `B` 칸에 출력 값이 찍히면 안 된다."""

    def test_입력_B_와_출력_B예상_이_따로_찍힌다(self):
        spec = parse_spec(ROOT / "tests/fixtures/spec_shared_letter.md")
        html = _truth_table_html(spec.table("T5"))
        self.assertEqual(re.findall(r"<th>([^<]*)</th>", html),
                         ["A", "B", "D예상", "B예상", "확인"])
        rows = [re.findall(r"<td>([^<]*)</td>", tr)
                for tr in re.findall(r"<tr>(.*?)</tr>", html)]
        self.assertEqual([r for r in rows if r],
                         [["0", "0", "0", "0"], ["0", "1", "1", "1"],
                          ["1", "0", "1", "0"], ["1", "1", "0", "0"]])


class TestPhotoNameColumn(unittest.TestCase):
    """진리표 행마다 찍을 사진 파일명 — `contact_sheet` 가 그대로 읽는 이름이다."""

    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.t1 = self.spec.table("T1")

    def _names(self, html):
        return re.findall(r'<td class="photo-name">([^<]*)</td>', html)

    def test_행마다_시트_규칙의_이름이_찍힌다(self):
        html = _truth_table_html(self.t1, "1-1")
        names = self._names(html)
        self.assertEqual(len(names), len(self.t1.rows))
        self.assertEqual(names[0], "1-1 000.jpg")
        for name in names:
            with self.subTest(name=name):
                self.assertIsNotNone(FILE.match(name))
        self.assertIn("<th>사진 파일명</th>", html)

    def test_비트는_입력_자리_순서다(self):
        """`A B D B` — 뒤의 `B` 는 출력이다. 이름으로 찾으면 출력 값이 비트에 섞인다."""
        spec = parse_spec(ROOT / "tests/fixtures/spec_shared_letter.md")
        names = self._names(_truth_table_html(spec.table("T5"), "2-1"))
        self.assertEqual(names, ["2-1 00.jpg", "2-1 01.jpg", "2-1 10.jpg", "2-1 11.jpg"])

    def test_토큰이_없으면_열을_내지_않는다(self):
        html = _truth_table_html(self.t1)
        self.assertNotIn("photo-name", html)
        self.assertNotIn("사진 파일명", html)

    def test_입력에_0_1_이_아닌_값이_있으면_대시다(self):
        rows = [["X"] + list(self.t1.rows[0][1:])] + list(self.t1.rows[1:])
        names = self._names(_truth_table_html(replace(self.t1, rows=rows), "1-1"))
        self.assertEqual(names[0], "—")

    def test_확인_칸_개수는_그대로다(self):
        """`.check` 개수는 명세의 truth-table 행 수와 대조되는 불변식이다."""
        html = _truth_table_html(self.t1, "1-1")
        self.assertEqual(html.count('class="check"'), len(self.t1.rows))

    def test_회로_페이지가_항목_토큰을_넘긴다(self):
        netlist = parse_netlist(ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        html = circuit_pages(self.spec, netlist)
        self.assertIn("1-2 000.jpg", html)
        self.assertIn("3 00.jpg", html)

    def test_토큰은_표를_가진_항목에서_온다(self):
        """회로의 `item` 이 표의 소유 항목과 달라도 파일명은 소유 항목의 번호다 —
        `contact_sheet` 는 기록.md 의 항목 헤딩(표를 가진 항목)으로 사진을 묶는다."""
        text = _MISSING_DIAGRAM_NETLIST.replace(
            "- item: E1.P1-1\n- tables: [T1]", "- item: E1.P1-1\n- tables: [T2]")
        self.assertNotEqual(text, _MISSING_DIAGRAM_NETLIST)
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        netlist = parse_netlist(path)
        c1 = next(s for s in netlist.sections if s.id == "C1")
        self.assertEqual(c1.item, "E1.P1-1")
        html = circuit_pages(self.spec, replace(netlist, sections=[c1]))
        self.assertIn("1-2 000.jpg", html)
        self.assertNotIn("1-1 000.jpg", html)

    def test_파형_사진_지시는_표ID_규칙이다(self):
        spec = parse_spec(ROOT / config.experiment_dir(2) / "체크리스트/명세.md")
        netlist = parse_netlist(ROOT / config.experiment_dir(2) / "결선도/netlist.md")
        html = circuit_pages(spec, netlist)
        self.assertIn("1-1 T1 &lt;설명&gt;.jpg", html)


class TestClosingChecklist(unittest.TestCase):
    def test_옛_파일명_관례가_없다(self):
        self.assertNotIn("row", " ".join(CLOSING))

    def test_파일명과_종료_메모를_묻는다(self):
        joined = " ".join(CLOSING)
        self.assertIn("표에 인쇄된 이름 그대로", joined)
        self.assertIn("종료 메모", joined)


class TestPlainStrikethrough(unittest.TestCase):
    """실험05 미확정 표가 닫힌 항목을 취소선(`~~`)으로 표시한다. `_plain` 이
    `*`·백틱처럼 벗기지 않으면 물결표째 인쇄본에 찍힌다."""

    def test_물결표_두_개짜리_취소선을_벗긴다(self):
        self.assertEqual(_plain("~~닫힌 항목~~ — 사유"), "닫힌 항목 — 사유")

    def test_낱개_물결표는_지우지_않는다(self):
        """실험10 이 `p15~p16` 처럼 쪽 범위 구분자로 낱개 `~` 를 쓴다 — 짝
        없는 `~` 까지 지우면 그 범위 표기가 붙어 버린다."""
        self.assertEqual(_plain("교안 p15~p16."), "교안 p15~p16.")

    # 2026-09-10: 실물 회귀 검사를 여기서 걷어냈다. 실험02~10 을 2026-2 교안
    # 기준으로 재저작하려고 지웠고, 이 검사들은 **그 문서가 실제로 그 결함을
    # 담고 있다**는 사실에 기대므로 픽스처로 옮기면 자기가 심은 답을 채점하게
    # 된다. 해당 주차 명세·결선도를 다시 저작할 때 함께 되살린다 —
    # `docs/plans/2026-09-10-코퍼스-재작성-되살릴-검사.md` 에 목록이 있다.


class TestCapturePage(unittest.TestCase):
    """파형은 셀 표가 아니다. `expected` 산문이 판정 기준 전부이고, 판독 조건이
    없으면 결과보고서에서 화면의 칸을 볼트로 환산할 수 없다."""

    def setUp(self):
        self.spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        self.netlist = parse_netlist(ROOT / "tests/fixtures/netlist_capture.md")
        self.html = render_checklist(self.spec, self.netlist, TEMPLATE)

    def _block(self):
        # 회로 절 끝까지 자른다. `</div>` 로 자르면 `_capture_html` 이 내는
        # 첫 상자(`.expected`)에서 끊겨 판독 조건·캡션·`예상과 다른 점` 이
        # 전부 창 밖으로 밀린다. T1 은 C1 의 유일한 표다.
        start = self.html.index("<h3>T1 ·")
        return self.html[start:self.html.index("</section>", start)]

    def test_capture_는_격자가_아니라_스케치_상자를_낸다(self):
        self.assertIn('class="sketch"', self.html)

    def test_예상_산문을_통째로_싣는다(self):
        """실험10 T1 의 expected 는 여섯 줄이다. 잘리면 판정 기준이 사라진다."""
        block = self._block()
        for phrase in ("계단 상승한 뒤 리셋되는 톱니 형태",
                       "7490 의 모듈러스(10)", "가중 저항망 오차를 먼저 의심한다"):
            with self.subTest(phrase=phrase):
                self.assertIn(_esc(phrase), block)

    def test_마크다운_표기를_벗긴다(self):
        """`_plain` 을 안 씌우면 실험02 의 `**두 갈래로**` 가 그대로 인쇄된다."""
        block = self._block()
        self.assertNotIn("**", block)
        self.assertNotIn("`", block)

    def test_expected_의_마크다운_표기를_벗긴다(self):
        """씨앗 픽스처의 T1 expected 에는 마크다운이 하나도 없어 위 테스트가
        `_plain` 제거 변이를 못 문다. 그래서 여기서 `**` 를 직접 심는다.

        실물 회귀였다 — 실험02 T2 가 `**두 갈래로 갈라져 … 닫힌 루프**` 를
        담았고, 옛 `_capture_html` 이 `_plain` 을 안 씌워 별 두 개가 인쇄본에
        그대로 찍혔다. 그 명세는 2026-09-10 에 재저작 대상으로 지웠으므로,
        무는 자리만 남기고 씨앗은 픽스처에서 만든다."""
        text = (ROOT / "tests/fixtures/spec_capture.md").read_text(
            encoding="utf-8").replace(
                "계단 상승한 뒤 리셋되는 톱니 형태",
                "**두 갈래로 갈라져 계단 상승한 뒤 리셋되는 톱니 형태**", 1)
        target = Path(tempfile.mkdtemp()) / "명세.md"
        target.write_text(text, encoding="utf-8")
        table = parse_spec(target).table("T1")
        self.assertIn("**", table.expected)          # 원문에는 있다
        html = _capture_html(table)
        self.assertNotIn("**", html)                 # 인쇄본에는 없다
        self.assertIn("두 갈래로 갈라져", html)

    def _spec_with_figure(self, make_png: bool):
        text = (ROOT / "tests/fixtures/spec_capture.md").read_text(
            encoding="utf-8").replace(
                "- kind: capture", "- kind: capture\n- figure: 예상.png", 1)
        target = Path(tempfile.mkdtemp()) / "명세.md"
        target.write_text(text, encoding="utf-8")
        if make_png:
            (target.parent / "예상.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        return target

    def test_figure_그림을_예상_산문과_스케치_사이에_싣는다(self):
        """실험02 T1·T2 는 예비보고서의 예상 결과 그림을 실험실에서도 보며
        화면과 대조한다. 산문(판정 기준) 바로 아래, 그려 넣을 스케치 위다."""
        target = self._spec_with_figure(make_png=True)
        table = parse_spec(target).table("T1")
        self.assertEqual(table.figure, "예상.png")
        html = _capture_html(table, target.parent)
        img = html.index('src="예상.png"')
        self.assertLess(html.index('class="expected"'), img)
        self.assertLess(img, html.index('class="sketch"'))

    def test_figure_파일이_없으면_그림_대신_안내를_낸다(self):
        """없는 파일에 `<img>` 를 내면 깨진 그림이 PDF 로 굳는다."""
        target = self._spec_with_figure(make_png=False)
        html = _capture_html(parse_spec(target).table("T1"), target.parent)
        self.assertNotIn("<img", html)
        self.assertIn("예상 그림이 아직 없어요", html)

    def test_figure_가_없으면_그림_자리를_내지_않는다(self):
        self.assertNotIn("예상 그림", self._block())

    def test_판독_조건_줄이_붙는다(self):
        block = self._block()
        for token in ("V/div", "time/div", "프로브", "X-Y"):
            with self.subTest(token=token):
                self.assertIn(token, block)

    def test_캡션과_사진_파일_칸이_붙는다(self):
        block = self._block()
        self.assertIn("캡션", block)
        self.assertIn("사진 파일", block)

    def test_예상과_다른_점_상자가_붙는다(self):
        """`capture` 에는 미니표가 없다 — 그 자리를 이 상자가 맡는다."""
        self.assertIn("예상과 다른 점", self._block())

    def test_불일치_행_미니표를_붙이지_않는다(self):
        """파형에 '불일치 행'도 '이상 스텝'도 없다."""
        block = self._block()
        self.assertNotIn('class="mismatch"', block)
        self.assertNotIn("불일치 행", block)

    def test_확인_칸을_만들지_않는다(self):
        self.assertNotIn('class="check"', self._block())


class TestCommonPage(unittest.TestCase):
    """공통면은 한 번만 보면 되는 것만 싣는다 — 전원·꼭 읽을 것·범례·흐름·핀아웃·자리표.
    공통 규칙과 미확정 표는 읽히지 않아 인쇄하지 않는다(2026-09-28)."""

    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        self.html = common_page(self.spec, self.netlist)

    def test_전원_박스가_맨_위에_온다(self):
        self.assertLess(self.html.index('class="power"'), self.html.index("<table"))
        self.assertIn("미사용", self.html)

    def test_오늘의_흐름_표가_회로를_전부_센다(self):
        """`C3` 는 칩 이름 `74HC32` 의 부분문자열이다 — 페이지 전체에서 찾으면
        흐름표에서 그 행을 지워도 통과한다. 흐름표 안에서만 본다."""
        flow = self.html[self.html.index("<table class='flow'>"):]
        flow = flow[: flow.index("</table>")]
        self.assertEqual(flow.count("<tr>"), len(self.netlist.circuits) + 1)
        for n, circuit in enumerate(self.netlist.circuits, start=1):
            with self.subTest(circuit=circuit.id):
                self.assertIn(f"<td>{n}/{len(self.netlist.circuits)}</td>", flow)
                self.assertIn(f"<td>{circuit.id} · ", flow)

    def test_참조_핀아웃_표가_인쇄본에_실린다(self):
        """74HC02 만 출력이 pin 1·4·10·13 이다. netlist 가 스스로 '가장 흔한
        배선 실수'라고 표시한 정보인데 옛 렌더러는 표 줄이라는 이유로 버렸다."""
        self.assertIn("74HC02 (quad NOR)", self.html)
        self.assertIn("2,3 → 1", self.html)

    def test_공통_규칙은_인쇄하지_않는다(self):
        self.assertNotIn("<h2>공통 규칙</h2>", self.html)
        self.assertNotIn("74HC08 결함(2026-09-11)", self.html)   # 실험01 공통 규칙에만 있는 구절

    def test_미확정_표는_인쇄하지_않는다(self):
        self.assertNotIn("실험실에서 확인할 것", self.html)
        self.assertNotIn('<tr><td class="box"></td>', self.html)

    def test_꼭_읽을_것이_전원_박스_바로_뒤에_온다(self):
        power = self.html.index('class="power"')
        must = self.html.index('class="must-read"')
        self.assertLess(power, must)
        self.assertLess(must, self.html.index('class="caution"'))
        box = self.html[must:self.html.index("</div>", must)]
        self.assertEqual(box.count("<li>"), 5)

    def test_선_색_범례가_있다(self):
        self.assertIn('class="wire-legend"', self.html)
        self.assertIn("빨간 점선 = 뽑는다", self.html)

    def test_전원_박스는_공통_규칙을_가리키지_않는다(self):
        box = self.html[self.html.index('class="power"'):]
        box = box[:box.index("</div>")]
        self.assertNotIn("공통 규칙", box)
        self.assertIn("핀 점검", box)

    def test_핀아웃_출처는_인쇄하지_않는다(self):
        """참고문헌이 배선 단계 7~11번으로 찍히던 결함이다."""
        self.assertNotIn("Philips", self.html)
        self.assertNotIn("SCLS081J", self.html)

    def test_기록_규약_범례가_kind_마다_있다(self):
        """규약은 기록.md 에만 있었다 — 태블릿에 PDF 만 띄운 사람은 알 수 없다.
        그리고 진리표 규약 하나로는 실험02·10 을 설명하지 못한다. 두 주차에는
        진리표가 한 장도 없다."""
        self.assertIn("다르면 실제로 본 값", self.html)
        self.assertIn("안 본 행은 비워", self.html)
        self.assertIn("단위", self.html)          # 스텝표
        self.assertIn("판독 조건", self.html)      # 파형
        self.assertEqual(self.html.count("class=\"legend\""), 3)

    def test_여러_줄_경고가_잘리지_않는다(self):
        """74HC02 경고는 세 줄짜리 불릿 하나다. 이어지는 줄을 앞 항목에 붙이지
        않으면 목록이 중간에서 끊기고 나머지가 별도 문단으로 떨어진다. 구절
        하나만 찾으면 그 깨진 출력에서도 발견되므로, 첫 줄과 끝 줄이 **같은
        `<li>` 안**에 있는지를 본다."""
        import re as _re
        items = _re.findall(r"<li>(.*?)</li>", self.html, _re.S)
        joined = [i for i in items
                  if "나머지 셋과 핀 배치가 다르다" in i and "가장 흔한 배선 실수" in i]
        self.assertEqual(len(joined), 1, f"이어붙은 <li> 를 못 찾았다: {items}")
        self.assertIn("핀 1·4·10·13", joined[0])

    def test_기록_대상_표의_확인_칸을_공통면이_만들지_않는다(self):
        """`.check` 개수는 회로 페이지에서만 나온다 — 개수 검사가 명세에서 센다."""
        self.assertNotIn('class="check"', self.html)

    def test_참조_핀아웃_표를_두_번_찍지_않는다(self):
        """`_blocks` 가 표를 제자리에 싣게 되면서 `lookup` 이 중복 렌더가 됐다."""
        self.assertEqual(self.html.count("74HC02 (quad NOR)"), 1)

    def test_배너가_주차마다_다른_것을_말하지_않는다(self):
        """옛 배너는 `미사용 입력핀은 전부 GND` 를 하드코딩했다 — 실험02 는
        교안 p8 도면대로 pin 9·11·13 을 **VCC** 로 올리고 결선도가 "이 주차는
        '전부 GND' 가 아니다"라고 못 박는다. 실험06 은 active-low 비동기
        입력을 VCC 로 올린다. 학생이 가장 먼저 읽는 줄이라 틀리면 그대로
        잘못 배선한다."""
        banner = self.html[self.html.index('class="power"'):]
        banner = banner[:banner.index("</div>")]
        self.assertNotIn("전부 GND", banner)
        self.assertIn("플로팅 금지", banner)
        self.assertIn("핀 점검", banner)   # 공통 규칙은 2026-09-28 부터 인쇄하지 않는다

    def test_물리_주의_상자가_전원_박스_바로_아래_온다(self):
        caution = self.html.index('class="caution"')
        self.assertLess(self.html.index('class="power"'), caution)
        self.assertLess(caution, self.html.index('class="legend"'))

    def test_물리_주의_세_줄(self):
        box = self.html[self.html.index('class="caution"'):]
        box = box[:box.index("</div>")]
        self.assertEqual(box.count("<li>"), 3)
        self.assertIn("클립", box)
        self.assertIn("전원부터 꺼요", box)

    def test_걷기_보드가_없는_주차는_걷기_그림을_가리키지_않는다(self):
        """공통면은 모든 주차에서 참인 것만 말한다 — 실험01 에는 걷기 그림이 없다."""
        self.assertIn("걷을 선부터 먼저 뽑고", self.html)
        self.assertNotIn("걷기 그림", self.html)

    # 2026-09-10: 실물 회귀 검사를 여기서 걷어냈다. 실험02~10 을 2026-2 교안
    # 기준으로 재저작하려고 지웠고, 이 검사들은 **그 문서가 실제로 그 결함을
    # 담고 있다**는 사실에 기대므로 픽스처로 옮기면 자기가 심은 답을 채점하게
    # 된다. 해당 주차 명세·결선도를 다시 저작할 때 함께 되살린다 —
    # `docs/plans/2026-09-10-코퍼스-재작성-되살릴-검사.md` 에 목록이 있다.


class TestCautionWithWalkBoard(unittest.TestCase):
    """실험03 C2·C4 는 `## 단계` 표에 걷기 행(`<k>걷기`)이 있다. C4 는 **첫 행**이
    걷기라 회로 경계이고, C2 는 회로 **안**에서만 걷는다 — 배너와 주의 상자가
    보는 것이 다르다."""

    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(3) / "체크리스트/명세.md")
        self.netlist = parse_netlist(ROOT / config.experiment_dir(3) / "결선도/netlist.md")

    def test_걷기_행이_있으면_걷기_그림의_선부터(self):
        html = common_page(self.spec, self.netlist)
        box = html[html.index('class="caution"'):]
        box = box[:box.index("</div>")]
        self.assertIn("걷기 그림(빨간 점선)의 선부터 먼저 뽑고", box)

    def test_has_walk_는_아무_행이나_본다(self):
        """C2 는 회로 안에서만 걷는다 — 주의 상자는 그것도 걷기로 센다."""
        c2 = next(c for c in self.netlist.circuits if c.id == "C2")
        self.assertTrue(_has_walk(c2))
        one = parse_netlist(ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        self.assertFalse(any(_has_walk(c) for c in one.circuits))

    def test_has_entry_walk_는_첫_행만_본다(self):
        """칩 교체 배너는 회로 경계 판정이다 — C2 는 회로 안 걷기뿐이라 거짓이다."""
        c2 = next(c for c in self.netlist.circuits if c.id == "C2")
        c4 = next(c for c in self.netlist.circuits if c.id == "C4")
        self.assertFalse(_has_entry_walk(c2))
        self.assertTrue(_has_entry_walk(c4))


class TestCircuitPages(unittest.TestCase):
    """회로 하나 = 결선도 + 배선 + 유의사항 + 측정표. 실험실의 작업 단위는
    명세 항목이 아니라 회로다 — 칩이 종류당 하나라 순차로 배선해야 한다
    (netlist M10)."""

    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        self.html = circuit_pages(self.spec, self.netlist)

    def test_완성본마다_자필_안내가_한_번씩_있다(self):
        """옛 PNG 머리의 제출 안내가 사이드카로 가며 단계 있는 회로에만 남았다(2026-09-28
        최종 리뷰) — 실험01 1-1 AND 처럼 단계 없는 완성본에서 학번·이름·날짜가 빠진다."""
        for n, page in enumerate(self._pages(), start=1):
            with self.subTest(회로=n):
                self.assertEqual(page.count("학번·이름·날짜"), 1)

    def _pages(self):
        """회로 페이지를 하나씩 자른다. 문서 전체에서 찾으면 어느 회로 것인지
        모르는 채로 통과한다."""
        return [p.split("</section>")[0]
                for p in self.html.split('<section class="circuit">')[1:]]

    def test_회로마다_개쪽_상자가_하나씩_나온다(self):
        self.assertEqual(self.html.count('<section class="circuit">'),
                         len(self.netlist.circuits))

    def test_진행_표시가_붙는다(self):
        self.assertIn("1/5", self.html)
        self.assertIn("5/5", self.html)

    def test_칩_교체_배너가_뺄_칩과_꽂을_칩을_말한다(self):
        """C1(74HC08) → C2(74HC32) 는 칩을 갈아끼워야 한다."""
        self.assertIn("뺄 칩", self.html)
        self.assertIn("꽂을 칩", self.html)

    def test_결선도가_있으면_그림을_싣는다(self):
        self.assertIn("실험01_1-1_결선도_3입력_AND.png", self.html)
        self.assertIn("../결선도/", self.html)

    def test_결선도가_없으면_빈_브레드보드로_대신한다(self):
        """실물 실험01 은 d556077 이후 다섯 회로 전부에 diagram 이 있어(OR·NOR
        PNG 추가) fallback 경로를 더는 실물로 못 본다 — 합성 픽스처로 옮긴다.
        `_netlist_missing_diagrams` 의 두 회로 다 결선도가 없다."""
        netlist = _netlist_missing_diagrams()
        html = circuit_pages(self.spec, netlist)
        self.assertEqual(html.count("Breadboard.jpg"), len(netlist.circuits))
        self.assertIn("브레드보드 작도", html)

    def test_배선_번호가_칩마다_1부터_다시_센다(self):
        """`<ol start="1">` 을 내는 곳이 한 군데뿐이라, 배선 전부를 한 목록에
        몰아 칩 경계를 없애도 옛 단언은 통과했다. 목록 수 = 칩 수여야 한다."""
        chips = sum(len(_chip_boxes(_circuit_body(c)[0]))
                    for c in self.netlist.circuits)
        self.assertGreaterEqual(chips, 9)
        self.assertEqual(self.html.count('<ol start="1">'), chips)

    def test_칩이_자기_상자를_갖는다(self):
        """`U3 = 74HC08` 은 상자의 제목이지 배선 단계가 아니다."""
        self.assertIn('class="chip"', self.html)
        self.assertIn("U1 = 74HC08", self.html)

    def test_칩_상자가_원문_순서대로_인쇄된다(self):
        """노드를 뒤집는 변이가 이 클래스의 스무 개 테스트를 전부 통과했다.
        칩 선언 순서를 **원문에서 직접** 읽어 인쇄 위치와 대조한다 — 렌더러가
        센 순서로 렌더러를 재면 뒤집힌 순서끼리 맞아떨어져 아무것도 못 잡는다.
        C3·C4 는 칩이 둘, C5 는 셋이라 순서가 실제로 구별된다."""
        for page, circuit in zip(self._pages(), self.netlist.circuits):
            heads = re.findall(r"^-[ \t]+(U\d+[ \t]*=[ \t]*.+)$",
                               circuit.body, re.M)
            with self.subTest(circuit=circuit.id):
                self.assertGreaterEqual(len(heads), 1)
                at = [page.index(f"<h4>{_esc(_plain(h.rstrip()))}</h4>")
                      for h in heads]
                self.assertEqual(at, sorted(at))

    def test_미사용핀_지시가_어느_칩_것인지_밝힌다(self):
        """라벨이 없으면 다칩 회로에서 같은 핀이 정반대 지시를 동시에 받는다 —
        C4 의 pin 4 는 U5 기준 GND, U6 기준 개방이다. 칩이 죽는 사고다."""
        page = self._pages()[3]                     # C4 · NOR (74HC32 + 74HC02)
        box = page[page.index('class="unused"'):]
        self.assertIn("U5 = 74HC32", box)
        self.assertIn("U6 = 74HC02", box)
        self.assertIn("개방", box)

    def test_미사용핀_줄이_회로마다_하나도_빠지지_않는다(self):
        """첫 칩의 미사용 줄만 버리는 변이가 조용히 통과하던 자리다.
        플로팅 입력이 이 과목의 대표 실패 원인이라 개수를 센다."""
        for page, circuit in zip(self._pages(), self.netlist.circuits):
            expected = sum(1 for raw in circuit.body.split("\n")
                           if raw.strip().startswith("- 미사용"))
            with self.subTest(circuit=circuit.id):
                self.assertGreater(expected, 0)
                box = page[page.index('class="unused"'):]
                # 2026-09-28 부터 단계 블록이 핀 점검 뒤에 온다 — 단계의 ☐ 를 세지 않는다
                if '<div class="stage">' in box:
                    box = box[:box.index('<div class="stage">')]
                self.assertEqual(box.count('<span class="box">'), expected)

    def test_회로별_경고가_그_회로_페이지에만_온다(self):
        """이름과 달리 문서 전체를 보던 자리다. 모든 산문을 회로 1 로 몰아넣는
        변이가 통과했다 — C4 의 74HC02 경고가 C1 쪽에 찍혀도 잡히지 않는다."""
        pages = self._pages()
        for index, warning in ((2, "교안 p13 회로도 그대로"),
                               (3, "핀 순서에 주의"),
                               (4, "다르면 배선 오류")):
            with self.subTest(warning=warning):
                self.assertIn(warning, pages[index])
                elsewhere = [n for n, p in enumerate(pages)
                             if n != index and warning in p]
                self.assertEqual(elsewhere, [])

    def test_사진_지시가_표마다_붙는다(self):
        self.assertIn("실험 번호(예: 실험03)는 붙이지 않아요", self.html)
        self.assertIn("불일치 행", self.html)
        self.assertNotIn("T1 row", self.html)

    def test_불일치_행_미니표가_표마다_붙는다(self):
        self.assertEqual(self.html.count('class="mismatch"'), 5)

    def test_미니표가_자기_제목을_가진다(self):
        """미니표가 표 제목에서 떨어져 쪽을 넘어가면(실험10 PDF 17쪽처럼)
        `이상 스텝 | 관찰한 것 | 짐작된 원인` 만 홀로 남는, 문맥 없는 3열
        표가 된다. 표 앞에 `<h4>표ID · 종류</h4>` 를 붙여 자기 제목을 준다."""
        for tid in re.findall(r'<h3>(T\d+)', self.html):
            with self.subTest(table=tid):
                self.assertIn(f"<h4>{tid} · 불일치 기록</h4>", self.html)

    def test_사진_부착_2열_상자가_사라졌다(self):
        """실험실에서 사진을 붙일 수 없다. 보고서 배치는 ④ 가 한다."""
        self.assertNotIn('class="pair"', self.html)

    def test_참조표는_회로_페이지에도_없다(self):
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertNotIn(f"{tid} ·", self.html)

    def test_회로가_참조표를_가리켜도_인쇄하지_않는다(self):
        """`_circuit_tables` 의 `role == "reference"` 필터를 지워도 실물
        데이터로는 통과한다 — netlist 가 T6~T9 를 말하지 않기 때문이다.
        가리키는 결선도를 만들어 필터를 실제로 태운다."""
        text = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(
            encoding="utf-8").replace("- tables: [T1]", "- tables: [T1, T6]")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        html = circuit_pages(self.spec, parse_netlist(path))
        # `기록: T1, T6 · 판독: ...` 처럼 회로 h2 는 tables 원문을 그대로
        # 나열한다 — 그 목록엔 필터가 없다(그래도 되는 곳이다: 저기는 요약
        # 줄이지 표 자체가 아니다). 그래서 순수 "T6 ·" 로 찾으면 필터가
        # 살아있어도 h2 에서 우연히 걸린다. 표 블록의 <h3> 로 좁혀야
        # `_circuit_tables` 자체를 시험하는 것이 된다.
        self.assertIn("<h3>T1 ·", html)
        self.assertNotIn("<h3>T6 ·", html)
        self.assertEqual(html.count('class="check"'),
                         sum(len(self.spec.table(t).rows)
                             for c in self.netlist.circuits for t in c.tables))

    def test_모든_배선_줄이_인쇄본에_온다(self):
        """첫 칩만 싣는 변이가 58줄 중 26줄을 지워도 옛 테스트는 전부 통과했다.
        가장 파괴적인 소실 모드라 원문 줄을 하나씩 대조한다."""
        lines = [_esc(_plain(raw.strip()[2:]))
                 for circuit in self.netlist.circuits
                 for raw in circuit.body.split("\n")
                 if raw.startswith((" ", "\t")) and raw.strip().startswith("- ")]
        self.assertGreaterEqual(len(lines), 58)
        for text in lines:
            with self.subTest(line=text[:40]):
                self.assertIn(text, self.html)

    def test_빈_브레드보드_경로가_루트_접두사를_거친다(self):
        """`../` 를 손으로 적으면 그림 자리만 비고 HTML 은 정상 렌더된다 —
        눈으로는 놓친다. config.root_relative_prefix 의 docstring 이 2026-09
        이동에서 정확히 이 방식으로 끊겼다고 기록한다.

        실물 실험01 은 d556077 이후 결선도 없는 회로가 없어 이 경로 자체가
        인쇄본에 나타나지 않는다 — 합성 픽스처로 옮긴다."""
        netlist = _netlist_missing_diagrams()
        html = circuit_pages(self.spec, netlist)
        self.assertIn(f"{config.root_relative_prefix()}.claude/assets/Breadboard.jpg",
                      html)

    def test_칩_교체_배너가_뺄_칩과_꽂을_칩을_바꿔_말하지_않는다(self):
        """뺄 칩과 꽂을 칩을 서로 뒤바꾼 변이가 통과하던 자리다.
        C2 는 74HC08 을 뽑고 74HC32 를 꽂는다."""
        page = self._pages()[1]
        start = page.index('class="banner"')
        banner = page[start:page.index("</div>", start)]
        self.assertIn("뺄 칩: 74HC08", banner)
        self.assertIn("꽂을 칩: 74HC32", banner)


    def test_배선_뒤_검산_산문이_미사용_상자_뒤에_온다(self):
        """C5 의 `LED_X 와 LED_Z 가 같이 켜져야 한다` 는 배선을 마친 뒤 하는
        검산이다. 앞으로 올리면 preamble 로 읽힌다."""
        page = self._pages()[4]
        # "다르면 배선 오류" 는 완성본 결선 순서(LED 사슬 설명)에도 나온다(2026-09-28) — 산문 구절로 잰다
        self.assertLess(page.index('class="unused"'), page.index("언제나 같이 켜져야 한다"))

    def test_배선_전_경고는_배선_앞에_온다(self):
        """C4 의 `74HC02 의 핀 순서에 주의` 를 배선을 다 마친 뒤 읽으면 늦다."""
        page = self._pages()[3]
        self.assertLess(page.index("핀 순서에 주의"), page.index('class="wirebox"'))

    def _spec_with_schematic(self, make_png: bool):
        """실험01 명세 사본의 E1.P1-1 에 schematic 을 단다. 사본은 임시 폴더라
        PNG 유무를 마음대로 정한다."""
        src = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"
        text = src.read_text(encoding="utf-8")
        self.assertEqual(text.count("pages: [11]"), 1)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = Path(tmp.name) / "명세.md"
        target.write_text(text.replace(
            "pages: [11]", "pages: [11]\n    schematic: [실험01_1-1_회로도.png]"),
            encoding="utf-8")
        if make_png:
            (target.parent / "실험01_1-1_회로도.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        return parse_spec(target)

    def test_schematic_이_없으면_싣지_않는다(self):
        self.assertNotIn('class="schematic"', self.html)
        self.assertNotIn("회로도가 아직 없어요", self.html)

    def test_schematic_을_배너_뒤_작도면_앞에_싣는다(self):
        """핸드오프 B: 강의노트 회로도는 그 항목 첫머리, 브레드보드 작도면 앞이다."""
        spec = self._spec_with_schematic(make_png=True)
        page = circuit_pages(spec, _netlist_missing_diagrams()).split(
            '<section class="circuit">')[1]
        img = page.index('<img class="schematic" src="실험01_1-1_회로도.png">')
        self.assertLess(page.index('class="banner"'), img)
        self.assertLess(img, page.index('class="wirebox"'))
        self.assertIn("강의노트 p11 · 회로 구성", page)

    def test_schematic_은_항목의_첫_회로에만_싣는다(self):
        spec = self._spec_with_schematic(make_png=True)
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(_MISSING_DIAGRAM_NETLIST.replace(
            "- item: E1.P1-2", "- item: E1.P1-1"), encoding="utf-8")
        html = circuit_pages(spec, parse_netlist(path))
        self.assertEqual(html.count('class="schematic"'), 1)
        pages = html.split('<section class="circuit">')[1:]
        self.assertIn('class="schematic"', pages[0])

    def test_schematic_파일이_없으면_그림_대신_안내를_낸다(self):
        """없는 파일에 `<img>` 를 내면 `check_embedded_images` 가 error 로 막는다."""
        spec = self._spec_with_schematic(make_png=False)
        html = circuit_pages(spec, _netlist_missing_diagrams())
        self.assertNotIn('class="schematic"', html)
        self.assertIn("회로도가 아직 없어요: 실험01_1-1_회로도.png", html)
        # 그림이 없는데 캡션만 남으면 없는 그림을 가리킨다 — 안내 한 줄만 낸다
        self.assertNotIn("회로 구성", html)

    def test_schematic_캡션은_크롭한_첫_쪽만_적는다(self):
        """크롭은 `pages[0]` 에서 나온다 — `p11·p12` 라고 적으면 p12 그림인 줄 안다."""
        from scripts.lab.render import _schematic_html
        from scripts.lab.spec_parser import SpecItem
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            item = SpecItem(id="E1.P1-1", title="t", device=[], ics=[], tables=[],
                            pages=[11, 12], schematic=["a.png"])
            out = _schematic_html(item, d)
        self.assertIn("<p class='src'>강의노트 p11 · 회로 구성</p>", out)
        self.assertNotIn("p12", out)


class TestCircuitBodySplit(unittest.TestCase):
    """`_circuit_body` 의 줄 귀속. 실험01 에는 이어지는 줄이 없어 실물
    렌더로는 발화하지 않지만, 이 저장소의 결선도는 관행적으로 줄을 접는다 —
    발화하는 순간 플로팅 핀 지시가 엉뚱한 항목에 붙는다."""

    def _section(self, body):
        return NetlistSection(kind="circuit", title="C9 · 시험", body=body, line=1,
                              id="C9", item="E1.P1-1", tables=["T1"])

    def test_이어지는_줄이_미사용_줄을_이으면_미사용에_붙는다(self):
        nodes, _, _ = _circuit_body(self._section(
            "- U1 = 74HC08 (quad)\n"
            "  - pin 1 ← 입력 A\n"
            "  - 미사용 출력핀: pin 8, 11 → 개방\n"
            "    (절대 GND 로 내리지 않는다)\n"))
        chips = _chip_boxes(nodes)
        self.assertEqual(chips[0]["wires"], ["pin 1 ← 입력 A"])
        self.assertEqual(chips[0]["unused"],
                         ["미사용 출력핀: pin 8, 11 → 개방 (절대 GND 로 내리지 않는다)"])

    def test_이어지는_줄이_배선_줄을_이으면_배선에_붙는다(self):
        nodes, _, _ = _circuit_body(self._section(
            "- U1 = 74HC08 (quad)\n"
            "  - pin 3 → L1 애노드\n"
            "    (330Ω 직렬)\n"))
        self.assertEqual(_chip_boxes(nodes)[0]["wires"],
                         ["pin 3 → L1 애노드 (330Ω 직렬)"])
        self.assertEqual(_chip_boxes(nodes)[0]["unused"], [])

    def test_산문이_첫_칩_앞뒤로_갈린다(self):
        _, before, after = _circuit_body(self._section(
            "회로 소개다.\n"
            "- U1 = 74HC08 (quad)\n"
            "  - pin 1 ← 입력 A\n"
            "배선을 마친 뒤 검산한다.\n"))
        self.assertIn("회로 소개다", before)
        self.assertNotIn("검산", before)
        self.assertIn("검산", after)

    def test_칩_사이의_표가_노드_순서를_지킨다(self):
        """실험10 P1 은 U3 과 U4 **사이**에 가중 저항망 표를 둔다. 3버킷으로
        가르면 그 표가 마지막 칩 뒤로 밀려 배선 순서가 뒤집힌다."""
        nodes, _, _ = _circuit_body(self._section(
            "- U1 = 74HC08 (quad)\n"
            "  - pin 1 ← A\n"
            "| 저항 | 값 |\n|---|---|\n| R1 | 1.5k |\n"
            "- U2 = 74HC32 (quad)\n"
            "  - pin 1 ← B\n"))
        self.assertEqual([n["type"] for n in nodes], ["chip", "prose", "chip"])
        self.assertIn("| R1 | 1.5k |", nodes[1]["text"])

    def test_노드가_원문_순서를_지킨다(self):
        """노드 목록을 통째로 뒤집는 변이가 기존 테스트를 전부 통과했다 —
        `["chip","prose","chip"]` 은 뒤집어도 같은 수열이라 구별되지 않는다.
        칩 셋을 비대칭으로 두어 위치를 못 박는다."""
        nodes, _, _ = _circuit_body(self._section(
            "- U1 = 74HC08 (quad)\n"
            "  - pin 1 ← 입력 A\n"
            "중간 산문이다.\n"
            "- U2 = 74HC32 (quad)\n"
            "  - pin 2 ← 입력 B\n"
            "- U3 = 74HC04 (hex)\n"
            "  - pin 3 ← 입력 C\n"))
        self.assertEqual([n["type"] for n in nodes],
                         ["chip", "prose", "chip", "chip"])
        self.assertEqual([n["head"] for n in _chip_boxes(nodes)],
                         ["U1 = 74HC08 (quad)", "U2 = 74HC32 (quad)",
                          "U3 = 74HC04 (hex)"])

    def test_칩이_하나도_없으면_전부_앞_산문이다(self):
        """조용히 버리는 것보다 낫다."""
        nodes, before, after = _circuit_body(self._section("산문뿐이다.\n"))
        self.assertEqual(nodes, [])
        self.assertIn("산문뿐이다", before)
        self.assertEqual(after, "")

    def test_들여쓴_표가_불릿형_상자를_닫지_않는다(self):
        """상자를 닫으면 뒤따르는 배선과 미사용핀 지시가 통째로 상자 밖
        산문으로 샌다 — 체크박스도 칩 라벨도 없이 `- ` 마커째 찍히고
        미사용핀 상자가 사라진다. 플로팅 핀 지시를 잃는 사고다."""
        nodes, _, after = _circuit_body(self._section(
            "- U1 = 74HC08 (quad)\n"
            "  - pin 1 ← A\n"
            "  | 핀 | 연결 |\n  |---|---|\n  | 14 | VCC |\n"
            "  - pin 2 ← B\n"
            "  - 미사용 입력핀: pin 9 → GND\n"))
        chip = _chip_boxes(nodes)[0]
        self.assertEqual(chip["wires"], ["pin 1 ← A", "pin 2 ← B"])
        self.assertEqual(chip["unused"], ["미사용 입력핀: pin 9 → GND"])
        self.assertEqual([k for k, _ in chip["blocks"]], ["table"])
        self.assertNotIn("pin 2", after)

    def test_표가_아닌_들여쓴_파이프_줄도_상자를_닫지_않는다(self):
        nodes, _, after = _circuit_body(self._section(
            "- U1 = 74HC08 (quad)\n"
            "  - pin 1 ← A\n"
            "  | 구분선이 없다 |\n"
            "  - 미사용 입력핀: pin 9 → GND\n"))
        chip = _chip_boxes(nodes)[0]
        self.assertEqual(chip["unused"], ["미사용 입력핀: pin 9 → GND"])
        self.assertEqual(after.strip(), "")


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
        """결선도 없는 회로마다 fallback 격자가 하나씩 들어간다. 캡션이 약속한
        행 수가 실제로 보이려면 예산에 머리띠를 더해야 한다 (B1).

        실물 실험01 은 d556077 이후 다섯 회로 전부에 diagram 이 있어 결선도
        없는 회로가 하나도 없다 — `_netlist_missing_diagrams` 합성 픽스처로
        옮긴다. 아래 `assertTrue(missing, ...)` 는 그 회귀(픽스처가 다시
        조용히 diagram 을 다 갖게 되는 경우)를 그대로 잡아낸다."""
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = _netlist_missing_diagrams()
        html = render_checklist(spec, netlist, TEMPLATE)
        missing = [c for c in netlist.circuits
                   if not c.diagram
                   or not (netlist.path.parent / c.diagram).exists()]
        self.assertTrue(missing, "결선도 없는 회로가 없어 이 검사가 무의미하다")
        captions = re.findall(r"브레드보드 작도 \((\d+)행\)", html)
        heights = re.findall(r"max-height:([\d.]+)mm", html)
        self.assertEqual(len(captions), len(missing))
        self.assertEqual(len(heights), len(missing))
        for circuit, caption, height in zip(missing, captions, heights):
            with self.subTest(circuit=circuit.id):
                rows = crop_rows(circuit.body)
                self.assertEqual(int(caption), rows)
                self.assertGreater(float(height), rows * 6)


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

    def test_칩별_미사용핀_구획도_갈리지_않는다(self):
        """구획이 쪽 경계를 타면 머리글 없는 `미사용 출력핀 … 개방` 줄만 다음
        쪽 꼭대기에 남아, 칩 라벨을 되살린 이유가 그대로 무너진다."""
        rule = re.search(r"\.unused \.chipunused\s*\{[^}]*\}", TEMPLATE, re.S)
        self.assertIsNotNone(rule, "`.unused .chipunused` 규칙이 없다")
        self.assertIn("break-inside: avoid", rule.group(0))

    def test_칩_배선이_쪽_경계에서_갈리지_않는다(self):
        """원자 단위는 칩 상자다. 결선도+배선 전체를 통짜로 묶으면 새 장을
        열자마자 덩어리가 다음 장으로 밀려 제목과 배너만 남은 백지가 생긴다
        (실측 16쪽 중 3장). 칩 하나의 배선만 갈리지 않으면 충분하다."""
        rule = re.search(r"\.wirebox \.chip\s*\{[^}]*\}", TEMPLATE, re.S)
        self.assertIsNotNone(rule, "`.wirebox .chip` 규칙이 없다")
        self.assertIn("break-inside: avoid", rule.group(0))

    def test_단계_블록은_통째로_묶지_않는다(self):
        """2026-09-28: 결선도 그림이 한 쪽보다 길어 `.stage` 를 통짜로 묶으면 제목만 남은
        빈 쪽이 단계마다 생겼다(실험04 main 56쪽 중 14쪽). 제목은 그림에 붙어만 있으면 된다."""
        rule = re.search(r"\.stage\s*\{[^}]*\}", TEMPLATE, re.S)
        self.assertIsNotNone(rule, "`.stage` 규칙이 없다")
        self.assertNotIn("break-inside: avoid", rule.group(0))
        self.assertRegex(TEMPLATE, r"\.stage h3\s*\{[^}]*break-after: avoid")

    def test_가장_긴_결선도도_한_쪽에_폭_그대로_들어간다(self):
        """태블릿으로 보는 PDF 라 쪽 높이는 자유다(2026-09-28 사용자). 그림이 쪽보다 길면
        제목과 갈라지고 아래가 잘린다 — 커밋된 결선도 중 가장 긴 것으로 잰다."""
        from PIL import Image
        m = re.search(r"@page\s*\{\s*size:\s*(\d+)mm\s+(\d+)mm;\s*margin:\s*(\d+)mm\s+(\d+)mm",
                      TEMPLATE)
        self.assertIsNotNone(m, "`@page { size: <폭>mm <높이>mm; margin: …` 꼴이 아니다")
        w, h, mv, mh = map(int, m.groups())
        ratios = []
        for png in (ROOT / "보고서").glob("실험*/결선도/*.png"):
            with Image.open(png) as im:
                ratios.append(im.size[1] / im.size[0])
        self.assertTrue(ratios)
        width = w - 2 * mh - 8        # 단계 블록 테두리·안쪽 여백
        self.assertGreaterEqual(h - 2 * mv - 15, width * max(ratios))   # 15mm = 제목 줄

    def test_핀_점검_상자는_쪽에서_갈리지_않는다(self):
        """2026-09-28 실험04: 핀 점검 제목만 쪽 끝에 남고 칩 구획이 다음 쪽으로 넘어갔다.
        상자가 칩 두세 개 분량이라 통짜로 넘겨도 빈 쪽이 없다."""
        rule = re.search(r"\.unused\s*\{[^}]*\}", TEMPLATE, re.S)
        self.assertIsNotNone(rule)
        self.assertIn("break-inside: avoid", rule.group(0))

    def test_완성본_캡션이_그림과_갈라지지_않는다(self):
        """2026-09-28 실험04 5쪽: `완성본 — 손그림 원도` 캡션만 쪽 끝에 남고 그림이 넘어갔다."""
        self.assertRegex(TEMPLATE, r"\.wirebox > p\.src:first-child\s*\{[^}]*break-after: avoid")

    def test_그림은_쪽보다_길어지지_않는다(self):
        """새 주차의 그림이 더 길어도 잘리지 않고 줄어든다 — 비율은 유지한다."""
        for sel in (r"\.stage img", r"\.wirebox img"):
            with self.subTest(sel=sel):
                rule = re.search(sel + r"\s*\{[^}]*\}", TEMPLATE, re.S)
                self.assertIsNotNone(rule)
                self.assertIn("max-height", rule.group(0))
                self.assertIn("object-fit: contain", rule.group(0))

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
        netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        html = render_checklist(spec, netlist, TEMPLATE)
        record_tables = sum(
            1 for c in netlist.circuits for t in c.tables
            if spec.table(t) and spec.table(t).role != "reference")
        lookup_sections = len(netlist.of_kind("lookup"))
        layout_sections = len(netlist.of_kind("layout"))
        self.assertEqual(html.count('<div class="tblock">'),
                         record_tables + lookup_sections + layout_sections)


class TestProcedureCarriesEveryWarning(unittest.TestCase):
    """영문 `pin` 이 든 줄만 고르면 한글로 쓴 경고가 통째로 사라진다.
    이 과목의 대표 실패 원인(플로팅 입력) 경고가 실제로 그렇게 빠져 있었다."""

    def setUp(self):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = parse_netlist(ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        self.html = render_checklist(spec, netlist, TEMPLATE)

    def test_korean_only_warnings_reach_the_printout(self):
        for warning in ("띄워두지 않는다", "가장 흔한 배선 실수",
                        "330Ω 직렬",
                        # "칩 재사용" 은 공통 규칙에만 있어 2026-09-28 부터 인쇄하지 않는다
                        # — 칩 교체 배너가 회로마다 뺄 칩·꽂을 칩을 지시한다
                        # 아래 셋은 불릿이 아니라 열 0 산문이라 별도 결함(A2)으로
                        # 빠져 있었다 — X≡Z 자체 검증, 74HC02 핀 순서 재경고,
                        # E1.P1-2 NAND 절 도입문.
                        "다르면 배선 오류", "핀 순서에 주의", "교안 p13 회로도 그대로"):
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
        netlist = parse_netlist(ROOT / config.experiment_dir(1) / "결선도/netlist.md")
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
        netlist = parse_netlist(ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        tmpl = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(
            encoding="utf-8")
        self.assertIn(config.document_title(spec.experiment, spec.title, "체크리스트"),
                      render_checklist(spec, netlist, tmpl))
        self.assertIn(config.document_title(spec.experiment, spec.title, "기록"),
                      derive_record(spec))


class TestBlocksTables(unittest.TestCase):
    """회로·공통 절의 마크다운 표가 인쇄본에서 통째로 사라지던 자리다.
    실험10 공통 규칙의 전원 레일 표가 그 주차 최대 사고 지점인데 빠졌다."""

    def test_표를_원문_위치에_인쇄한다(self):
        html = _blocks("앞 산문이다.\n\n"
                       "| 레일 | 값 |\n|---|---|\n| VCC | +5V |\n\n"
                       "뒤 산문이다.\n")
        self.assertLess(html.index("앞 산문"), html.index("<table"))
        self.assertLess(html.index("<table"), html.index("뒤 산문"))
        self.assertIn("<th>레일</th>", html)
        self.assertIn("<td>+5V</td>", html)

    def test_표_행이_하나도_빠지지_않는다(self):
        """행 하나만 싣는 변이가 `<table` 존재 검사로는 통과한다."""
        body = ("| 핀 | 연결 |\n|---|---|\n"
                + "".join(f"| {n} | GND |\n" for n in range(1, 8)))
        html = _blocks(body)
        for n in range(1, 8):
            with self.subTest(pin=n):
                self.assertIn(f"<td>{n}</td>", html)

    def test_표에_체크박스를_붙이지_않는다(self):
        """산문 속 표는 참조용이다. 배선표만 체크박스를 받는다 (Task 4)."""
        html = _blocks("| 핀 | 연결 |\n|---|---|\n| 14 | VCC |\n")
        self.assertNotIn('class="box"', html)

    def test_구분선_없는_파이프_줄은_버린다(self):
        """표가 아닌 `|` 줄이 문단으로 새어 나오면 인쇄본에 파이프가 찍힌다."""
        html = _blocks("산문\n| 구분선이 없다 |\n")
        self.assertNotIn("|", html)
        self.assertIn("산문", html)

    def test_표기가_벗겨진다(self):
        html = _blocks("| 소자 |\n|---|\n| `7490` **주의** |\n")
        self.assertIn("<td>7490 주의</td>", html)


class TestHeadingChips(unittest.TestCase):
    """실험02·10 은 배선을 `## U1 = ...` 헤딩 + 핀 표로 적는다. 이 형식을
    렌더러가 못 읽어서 실험10 P1 의 배선 80줄이 통째로 사라졌다.
    `netlist_parser.IC_DECL` 은 이미 이 형식을 파싱한다 — 렌더러만 못 읽었다."""

    def setUp(self):
        self.spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        self.netlist = parse_netlist(ROOT / "tests/fixtures/netlist_heading_chips.md")
        self.html = circuit_pages(self.spec, self.netlist)

    def _pages(self):
        return [p.split("</section>")[0]
                for p in self.html.split('<section class="circuit">')[1:]]

    def test_헤딩형_칩이_자기_상자를_갖는다(self):
        self.assertIn("U1 = 7490 (decade counter)", self.html)
        self.assertIn("U2 = 7404 (hex inverter)", self.html)
        self.assertEqual(self.html.count('class="chip"'), 3)   # U1, U2, U5

    def test_배선표_행마다_체크박스가_붙는다(self):
        """C1 의 배선 행: U1 4행(NC 포함) + U2 3행 = 7행. 미사용 2행은 빠진다."""
        page = self._pages()[0]
        wirebox = page[page.index('class="wirebox"'):page.index('class="unused"')]
        self.assertEqual(wirebox.count('<td class="box"></td>'), 7)

    def test_배선표의_모든_행이_인쇄본에_온다(self):
        """회로 안 **둘째 칩의 표를 버리는** 변이가 배선 절반을 지워도 상자
        존재 검사로는 통과한다. 셀 하나씩 대조한다."""
        for cell in ("14 (INPUT A)", "함수발생기 1 kHz 구형파 출력",
                     "U1 pin 12 (QA)", "4, 13", "NC 핀"):
            with self.subTest(cell=cell):
                self.assertIn(_esc(cell), self.html)

    def test_미사용_행이_배선표에서_빠져_미사용_상자로_간다(self):
        page = self._pages()[0]
        box = page[page.index('class="unused"'):]
        self.assertIn("미사용 입력핀 11, 13 · GND · 플로팅 금지", box)
        self.assertIn("미사용 출력핀 10, 12 · 개방", box)
        wirebox = page[page.index('class="wirebox"'):page.index('class="unused"')]
        self.assertNotIn("플로팅 금지", wirebox)

    def test_미사용_상자가_어느_칩_것인지_밝힌다(self):
        page = self._pages()[0]
        box = page[page.index('class="unused"'):]
        self.assertIn("U2 = 7404 (hex inverter)", box)
        self.assertNotIn("U1 = 7490", box)      # U1 에는 미사용 행이 없다

    def test_칩이_아닌_헤딩의_표는_참조표라_체크박스가_없다(self):
        """`## 소자 배치`·`## 가중 저항망` 은 배선이 아니다."""
        page = self._pages()[0]
        block = page[page.index("소자 배치"):page.index("U1 = 7490")]
        self.assertIn("<td>10진 카운터, 4비트 디지털 워드 생성</td>", block)
        self.assertNotIn('class="box"', block)

    def test_칩_사이_참조표가_원문_순서를_지킨다(self):
        """`가중 저항망` 은 U1 뒤 U2 앞이다. 뒤로 밀리면 배선 순서가 뒤집힌다."""
        page = self._pages()[0]
        self.assertLess(page.index("U1 = 7490"), page.index("가중 저항망"))
        self.assertLess(page.index("가중 저항망"), page.index("U2 = 7404"))

    def test_칩_상자_안의_불릿은_체크박스를_받지_않는다(self):
        """헤딩형 상자의 열 0 불릿은 주석이지 배선 단계가 아니다 —
        실험02 P4 U1 의 `- 짧은 점퍼 4개…` 가 그렇다. 옛 단언은 텍스트 뒤
        200자 창에 체크박스가 없는지만 봐서, 창이 칩 상자를 벗어나 **다음
        참조표**를 재고 있었다 — 그 참조표 길이에 통과가 달려 있었다.
        불릿 엘리먼트 자체를 본다."""
        page = self._pages()[0]
        self.assertIn("<li>이 칩만 전원핀이 다르다", page)
        self.assertNotIn('<li><span class="box"></span>이 칩만', page)

    def test_칩_교체_배너가_헤딩형에서도_칩_이름을_안다(self):
        """`ics` 는 IC_DECL 이 본문에서 뽑는다 — 헤딩도 본문이다."""
        page = self._pages()[1]
        banner = page[page.index('class="banner"'):]
        self.assertIn("741 OP amp", banner[:400])

    def _netlist_of(self, section):
        """단면 결선도를 만든다. `circuit_pages` 는 `LabNetlist` 를 받는다."""
        netlist = parse_netlist(ROOT / "tests/fixtures/netlist_heading_chips.md")
        netlist.sections = [section]
        return netlist

    def test_상자_안_주석의_문단_경계가_살아_있다(self):
        """빈 줄을 버리면 서로 다른 문단이 한 덩어리가 된다. 실험02 U2 상자는
        `교안은 U2 의 역할을 설명하지 않는다…` 와 `U2 pin 2 가 개방인 것에
        주의…` 가 빈 줄로 갈려 있고, 뒤쪽은 별도의 주의 문구다."""
        section = NetlistSection(
            kind="circuit", title="C9 · 시험", line=1,
            id="C9", item="E10.P1", tables=["T1"],
            body=("## U1 = 7400\n\n"
                  "| 핀 | 연결 |\n|---|---|\n| 14 | VCC |\n\n"
                  "첫째 문단이다.\n\n"
                  "둘째 문단이다. 완전히 다른 이야기.\n"))
        nodes, _, _ = _circuit_body(section)
        html = "\n".join(
            _blocks(p) for k, p in _chip_boxes(nodes)[0]["blocks"] if k == "note")
        self.assertIn("<p>첫째 문단이다.</p>", html)
        self.assertIn("<p>둘째 문단이다. 완전히 다른 이야기.</p>", html)
        self.assertNotIn("첫째 문단이다. 둘째 문단이다", html)

    def test_표_앞_산문이_표_앞에_남는다(self):
        """실험02 U1 의 `핀 번호 순서로 흐르지 않는다` 는 표를 **읽기 전에**
        읽어야 하는 경고다. 고정 순서로 찍으면 배선표 아래로 밀린다. 실험10 은
        반대로 표가 먼저라, 어느 고정 순서도 답이 아니다."""
        section = NetlistSection(
            kind="circuit", title="C9 · 시험", line=1,
            id="C9", item="E10.P1", tables=["T1"],
            body=("## U1 = 74HC04\n\n"
                  "핀 번호 순서로 흐르지 않는다.\n\n"
                  "| 핀 | 연결 |\n|---|---|\n| 1 | 함수발생기 |\n\n"
                  "짧은 점퍼 4개는 인접 핀끼리다.\n"))
        kinds = [k for k, _ in _chip_boxes(_circuit_body(section)[0])[0]["blocks"]]
        self.assertEqual(kinds, ["note", "table", "note"])
        html = circuit_pages(self.spec, self._netlist_of(section))
        self.assertLess(html.index("핀 번호 순서로 흐르지 않는다"),
                        html.index("함수발생기"))
        self.assertLess(html.index("함수발생기"),
                        html.index("짧은 점퍼 4개"))


class TestSteppedCells(unittest.TestCase):
    """`stepped` 는 예상값이 없다. `확인`(✓ 일치)은 비교 대상 없는 빈 칸이고,
    `불일치 행 / 예상 / 실제` 미니표는 뜻이 없다. 명세가 저작해 둔 **빈 셀**이
    실험실에서 채울 칸이다 — 실험10 T2 는 빈 열이 다섯이다."""

    def setUp(self):
        self.spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        self.netlist = parse_netlist(ROOT / "tests/fixtures/netlist_capture.md")
        self.html = circuit_pages(self.spec, self.netlist)
        self.t2 = self.spec.table("T2")

    def _block(self):
        # 회로 절 끝까지 자른다 — 기록 칸이 상자를 여럿 낼 수 있다. T2 는
        # C2 의 유일한 표다.
        start = self.html.index("<h3>T2 ·")
        return self.html[start:self.html.index("</section>", start)]

    def test_확인_열을_붙이지_않는다(self):
        block = self._block()
        self.assertNotIn("<th>확인</th>", block)
        self.assertNotIn('class="check"', block)

    def test_빈_셀이_기입_칸이_된다(self):
        """T2 는 10행 × 빈 열 5개 = 50칸이다."""
        blanks = sum(1 for row in self.t2.rows for c in row if not c.strip())
        self.assertEqual(blanks, 50)
        self.assertEqual(self._block().count('<td class="fill"></td>'), blanks)

    def test_채워진_셀은_그대로_인쇄한다(self):
        self.assertIn("single pulse 1회 → counter=9", self._block())

    def test_모든_스텝_행이_인쇄본에_온다(self):
        """행 절반만 싣는 변이가 표 존재 검사로는 통과한다."""
        block = self._block()
        for n in range(1, 11):
            with self.subTest(step=n):
                self.assertIn(f"<td>S{n}</td>", block)

    def test_불일치_행_미니표_대신_이상_스텝_미니표가_온다(self):
        block = self._block()
        self.assertIn("이상 스텝", block)
        self.assertIn("짐작된 원인", block)
        self.assertNotIn("불일치 행", block)
        self.assertNotIn("<th>예상</th>", block)

    def test_계측기_설정_줄이_붙는다(self):
        """단위와 레인지를 안 적으면 결과보고서에서 숫자를 못 읽는다."""
        self.assertIn("계측기 설정", self._block())

    def test_진리표는_그대로다(self):
        """실험01 의 진리표 5장은 예상값과 확인 칸을 그대로 유지한다."""
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        html = circuit_pages(spec, netlist)
        self.assertIn("<th>확인</th>", html)
        self.assertIn("불일치 행", html)
        self.assertNotIn('class="fill"', html)


class TestContinuesBanner(unittest.TestCase):
    """`앞 회로의 점퍼선을 모두 뽑아요` 는 실험10 C2 에서 틀린 지시다 —
    E10.P2 는 다 만든 DAC 에 741 비교기를 하나 더 붙인다. 그대로 따르면
    직전 회로를 뜯는다."""

    def _html(self, extra):
        text = (ROOT / "tests/fixtures/netlist_capture.md").read_text(
            encoding="utf-8").replace("- tables: [T2]", f"- tables: [T2]\n{extra}")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        return circuit_pages(spec, parse_netlist(path))

    def _banner(self, html, index):
        page = html.split('<section class="circuit">')[1 + index]
        start = page.index('class="banner"')
        return page[start:page.index("</div>", start)]

    def test_continues_가_있으면_뜯지_말라고_한다(self):
        banner = self._banner(self._html("- continues: C1"), 1)
        self.assertIn("앞 회로(", banner)
        self.assertIn("그대로 두고", banner)
        self.assertNotIn("점퍼선을 모두 뽑아요", banner)

    def test_continues_가_추가할_칩을_말한다(self):
        banner = self._banner(self._html("- continues: C1"), 1)
        self.assertIn("741", banner)

    def test_continues_는_이름이_겹치는_칩도_추가로_꽂으라고_한다(self):
        """실험10 C1 은 `U4 = 741 OP amp`, C2 는 `U5 = 741 OP amp` 다 — 이름이
        같지만 **패키지가 둘**이다. 741 한 패키지에 op-amp 는 하나뿐이고
        결선도가 `비교기를 하나 더 붙인다` 라고 적는다. `not in previous.ics`
        로 거르면 그 지시가 배너에서 통째로 사라진다."""
        text = (ROOT / "tests/fixtures/netlist_capture.md").read_text(
            encoding="utf-8")
        text = text.replace("- U5 = 741 (비교기)", "- U5 = 7490 (두 번째 패키지)")
        text = text.replace("- tables: [T2]", "- tables: [T2]\n- continues: C1")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        netlist = parse_netlist(path)
        self.assertEqual(netlist.circuits[0].ics, netlist.circuits[1].ics)
        banner = self._banner(circuit_pages(spec, netlist), 1)
        self.assertIn("더 꽂을 칩: 7490", banner)

    def test_continues_가_없으면_옛_배너_그대로다(self):
        """이 줄을 지우면 배너가 되돌아와야 한다 — 뮤테이션으로 무는 자리."""
        banner = self._banner(self._html(""), 1)
        self.assertIn("점퍼선을 모두 뽑아요", banner)

    def test_첫_회로에는_continues_가_무의미하다(self):
        banner = self._banner(self._html("- continues: C1"), 0)
        self.assertIn("준비 — 꽂을 칩", banner)


class TestRebuildBanner(unittest.TestCase):
    """`rebuild: true` — 앞 회로의 신호선을 전부 뽑고 새로 짓는다(2026-09-27, 실험04 C2).
    단계 표가 있는 회로의 기본 배너는 `앞 회로 배선은 그대로 둬요` 라 그 반대를 말한다."""

    STAGES = ("\n## 단계\n\n| 단계 | 그림 | 이 단계에서 | 확인 |\n|---|---|---|---|\n"
              "| 1 | `s.png` | 신호선: 입력→pin 3 | 노드 `X` — 본다 |\n")

    def _banner(self, extra, tail=""):
        text = (ROOT / "tests/fixtures/netlist_capture.md").read_text(
            encoding="utf-8").replace("- tables: [T2]", f"- tables: [T2]\n{extra}") + tail
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        return TestContinuesBanner._banner(self, circuit_pages(spec, parse_netlist(path)), 1)

    def test_단계가_있어도_전부_뽑으라고_한다(self):
        banner = self._banner("- rebuild: true", self.STAGES)
        self.assertIn("신호선을 전부 뽑아요", banner)
        self.assertNotIn("배선은 그대로 둬요", banner)

    def test_남기는_것을_말한다(self):
        """전원선·LED 사슬까지 뽑으면 다음 회로 1단계의 기반을 다시 꽂게 된다."""
        banner = self._banner("- rebuild: true", self.STAGES)
        self.assertIn("전원", banner)
        self.assertIn("LED", banner)

    def test_칩_교체를_말한다(self):
        banner = self._banner("- rebuild: true")
        self.assertIn("뺄 칩: 7490", banner)
        self.assertIn("꽂을 칩: 741", banner)

    def test_rebuild_가_없으면_단계_배너_그대로다(self):
        """이 줄을 지우면 배너가 되돌아와야 한다 — 뮤테이션으로 무는 자리."""
        banner = self._banner("", self.STAGES)
        self.assertIn("그대로 둬요", banner)
        self.assertNotIn("전부 뽑는다", banner)


class TestRefsTables(unittest.TestCase):
    """실험02 T7 은 T8(데이터시트 기준값, role: reference)과 대조하는 표다.
    `tables` 에 넣으면 validate 가 error 를 내므로 갈 곳을 만든다."""

    def _html(self, extra):
        text = (ROOT / config.experiment_dir(1) / "결선도/netlist.md").read_text(
            encoding="utf-8").replace("- tables: [T1]", f"- tables: [T1]\n{extra}")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        return circuit_pages(spec, parse_netlist(path))

    def test_refs_표가_회로_페이지에_실린다(self):
        html = self._html("- refs: [T6]")
        self.assertIn("<h3>T6 ·", html)

    def test_refs_표에_기록_칸이_없다(self):
        """교안 이론표다 — 실험실에서 채우지 않는다."""
        html = self._html("- refs: [T6]")
        block = html[html.index("<h3>T6 ·"):]
        block = block[:block.index("</div>")]
        self.assertNotIn('class="check"', block)
        self.assertNotIn('class="mismatch"', block)
        self.assertNotIn("사진", block)
        self.assertIn("참조", block)

    def test_refs_표의_모든_행이_온다(self):
        html = self._html("- refs: [T6]")
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        block = html[html.index("<h3>T6 ·"):]
        block = block[:block.index("</div>")]
        self.assertEqual(block.count("<tr>"), len(spec.table("T6").rows) + 1)

    def test_refs_가_없으면_참조표는_어디에도_없다(self):
        """뮤테이션으로 무는 자리 — 필터를 지워도 실물로는 발화하지 않는다."""
        self.assertNotIn("<h3>T6 ·", self._html(""))


class Test배선전수(unittest.TestCase):
    """배선 51행이 전부 표 안인 픽스처다. 첫 칩·첫 표만 싣는 변이가
    가장 파괴적인 소실 모드라 원문 셀을 하나씩 대조한다.

    개수는 리터럴로 박는다. `_circuit_body` 가 센 값으로 대조하면 파서와
    렌더러가 같은 결함을 공유할 때 조용히 통과한다."""

    #: 백필 전 원문을 재서 얻은 값. U1 13 · U2 10 · U3 10 · U4 10 · U5 8.
    WIRE_ROWS = 51
    UNUSED_ROWS = 4
    CHIPS = 5

    def setUp(self):
        self.spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
        self.netlist = parse_netlist(
            ROOT / "tests/fixtures/netlist_full_wiring.md")
        self.html = circuit_pages(self.spec, self.netlist)

    def test_칩_상자_수가_원문의_칩_선언_수와_같다(self):
        self.assertEqual(self.html.count('class="chip"'), self.CHIPS)

    def test_원문_배선표의_모든_행이_인쇄본에_온다(self):
        rows = [row for circuit in self.netlist.circuits
                for chip in _chip_boxes(_circuit_body(circuit)[0])
                for table in _chip_tables(chip) for row in table.rows]
        self.assertEqual(len(rows), self.WIRE_ROWS)
        for row in rows:
            for cell in row:
                text = _esc(_plain(cell)).strip()
                if len(text) < 3:
                    continue          # `7`·`14` 같은 핀 번호는 우연히 겹친다
                with self.subTest(cell=text[:40]):
                    self.assertIn(text, self.html)

    def test_배선_체크박스_수가_원문_배선행_수와_같다(self):
        self.assertEqual(self.html.count('<td class="box"></td>'),
                         self.WIRE_ROWS)

    def test_미사용_행이_배선표에서_빠져_미사용_상자로_간다(self):
        """미사용 판정을 지우면 체크박스가 4개 늘고 미사용 상자가 빈다."""
        boxes = 0
        for page in self.html.split('<section class="circuit">')[1:]:
            if 'class="unused"' not in page:
                continue
            boxes += page[page.index('class="unused"'):].count('<span class="box">')
        self.assertEqual(boxes, self.UNUSED_ROWS)

    def test_미사용핀_지시가_어느_칩_것인지_밝힌다(self):
        """U2·U3 둘 다 `pin 11, 13 → GND` 다. 라벨이 없으면 구별되지 않는다."""
        page = self.html.split('<section class="circuit">')[1]
        box = page[page.index('class="unused"'):]
        self.assertIn("U2 = 7404", box)
        self.assertIn("U3 = 7405", box)

    def test_C2_배너가_C1_을_뜯지_말라고_한다(self):
        page = self.html.split('<section class="circuit">')[2]
        start = page.index('class="banner"')
        banner = page[start:page.index("</div>", start)]
        self.assertIn("앞 회로(", banner)
        self.assertIn("그대로 두고", banner)
        self.assertNotIn("점퍼선을 모두 뽑아요", banner)

    def test_전원_레일_표가_공통면에_인쇄된다(self):
        """이 주차 최대 사고 지점이다 — 두 전원의 GND 를 같은 노드로 묶는 것."""
        html = common_page(self.spec, self.netlist)
        self.assertIn("V15", html)
        self.assertIn(_esc("+15V"), html)


_STAGED_NETLIST = """---
schema: lab-netlist/v2
experiment: 1
spec: ../체크리스트/명세.md
---

# 칩 자리표

- kind: layout

| 슬롯 | 자리 | 회로별 칩 |
|---|---|---|
| S1 | 좌 7행 | C1 74HC08 · C2 74HC00 |

# C1 · 첫 회로

- kind: circuit
- id: C1
- item: E1.P1-1
- tables: [T1]

- U1 = 74HC08 (quad 2-input AND)
  - pin 14 → VCC(+5V)
  - 미사용 입력핀: pin 9, 10 → 개방

# C2 · 단계 있는 회로

- kind: circuit
- id: C2
- item: E1.P2-1
- tables: [T3]
- diagram: 완성.png

## 단계

| 단계 | 그림 | 이 단계에서 | 확인 |
|---|---|---|---|
| 1 | 1단계.png | **앞단만** 꽂는다 | L1 = A·B, AB = 00·01·10·11 |
| 2 | 2단계.png | 뒷단을 더한다 | T3 8행 |

- U2 = 74HC08 (quad 2-input AND)
  - pin 14 → VCC(+5V)
  - 미사용 입력핀: pin 4, 5 → 개방
- U3 = 74HC00 (quad 2-input NAND)
  - pin 1 ← U2.pin3
  - 미사용 입력핀: pin 9, 10 → 개방

# C3 · 단계 없는 뒤 회로

- kind: circuit
- id: C3
- item: E1.P1-2
- tables: [T2]

- U4 = 74HC32 (quad 2-input OR)
  - pin 14 → VCC(+5V)
  - 미사용 입력핀: pin 9, 10 → 개방
"""

_STAGE_NODED_NETLIST = """---
schema: lab-netlist/v2
experiment: 1
spec: ../체크리스트/명세.md
---

# C1 · 단계와 노드가 있는 회로

- kind: circuit
- id: C1
- item: E1.P1-1
- tables: [T1]

## 단계

| 단계 | 그림 | 이 단계에서 | 확인 |
|---|---|---|---|
| 1 | 1단계.png | 앞단 AND 를 꽂는다 | 노드 `A·B` — 네 조합 |
| 2걷기 | 2걷기.png | 걷기 ① 을 뽑는다 | 뽑은 선이 손에 있다 |
| 2 | 2단계.png | 뒷단을 더한다 | 노드 `L2` — T1 8행 전부 |

## 노드

| 노드 | 식 | 핀 |
|---|---|---|
| A·B | A·B | U1 pin 3 |
| L2 | A·B·C | U1 pin 6 |

- U1 = 74HC08 (quad 2-input AND)
  - pin 14 → VCC(+5V)
  - 미사용 입력핀: pin 9, 10 → 개방
"""


class TestStages(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(_STAGED_NETLIST, encoding="utf-8")
        self.netlist = parse_netlist(path)
        self.html = render_checklist(self.spec, self.netlist, TEMPLATE)
        self.pages = self.html.split('<section class="circuit">')[1:]

    def test_자리표가_공통면에_실린다(self):
        common = self.html[:self.html.index('<section class="circuits">')]
        self.assertIn("칩 자리표", common)
        self.assertIn("좌 7행", common)

    def test_단계_블록이_순서대로_실린다(self):
        page = self.pages[1]
        self.assertEqual(page.count('class="stage"'), 2)
        self.assertLess(page.index("단계 1"), page.index("단계 2"))
        self.assertIn("1단계.png", page)
        self.assertIn("확인:", page)
        self.assertIn("AB = 00·01·10·11", page)

    def test_단계_블록은_체크박스를_가진다(self):
        page = self.pages[1]
        stage = page[page.index('class="stage"'):page.index('class="tblock"')]
        self.assertEqual(stage.count('<span class="box">'), 2)
        self.assertNotIn('class="stage-table"', stage)   # 옛 단계 표는 노드를 안 가리킨다

    def test_결선도_상자와_핀_점검이_단계_앞에_온다(self):
        """2026-09-28: 완성본을 먼저 보고 단계를 밟는다. 기록표는 마지막 단계 바로 뒤다."""
        page = self.pages[1]
        self.assertLess(page.index('class="wirebox"'), page.index('class="unused"'))
        self.assertLess(page.index('class="unused"'), page.index('class="stage"'))
        self.assertLess(page.rindex('class="stage"'), page.index('class="tblock"'))

    def test_단계가_있으면_완성본에_캡션이_붙는다(self):
        self.assertIn("완성본 — 손그림 원도", self.pages[1])
        self.assertNotIn("완성본 — 손그림 원도", self.pages[0])

    def test_단계_표가_참조표로_두_번_찍히지_않는다(self):
        self.assertNotIn("<th>이 단계에서</th>", self.html)

    def test_단계_문구의_마크다운을_벗긴다(self):
        self.assertNotIn("**앞단만**", self.html)
        self.assertIn("앞단만", self.pages[1])

    def test_단계가_없는_회로는_블록이_없다(self):
        self.assertNotIn('class="stage"', self.pages[0])

    def test_배너가_선_단위_변경의_위치를_말한다(self):
        """C2 는 단계가 있는 회로다 — 배너가 `모두 뽑아요` 대신 단계 그림을
        가리켜야 한다. C1 은 첫 회로라 배너에 해당 문구가 없다."""
        self.assertNotIn("그대로 둬요", self.pages[0])
        self.assertIn("그대로 둬요", self.pages[1])
        self.assertNotIn("모두 뽑아요", self.pages[1])

    def test_단계_있는_회로_배너는_그대로_둔다_뿐이고_모두_걷는다는_없다(self):
        banner = self.pages[1][self.pages[1].index('class="banner"'):]
        banner = banner[:banner.index("</div>")]
        self.assertIn("그대로 둬요", banner)
        self.assertNotIn("모두 뽑아요", banner)

    def test_단계_없는_뒤_회로는_옛_배너_그대로다(self):
        """C3 은 단계가 없고 첫 회로도 아니다 — 기본 문구가 그대로 남는다."""
        banner = self.pages[2][self.pages[2].index('class="banner"'):]
        banner = banner[:banner.index("</div>")]
        self.assertIn("모두 뽑아요", banner)

    def test_걷기_단계가_없는_회로는_걷기_그림을_가리키지_않는다(self):
        """C2 는 `## 단계` 표가 있지만 첫 행이 걷기가 아니다 — 걷기 보드로 들어가는
        회로가 아니다(실험01 전부). 없는 그림을 가리키면 학생이 그것을 찾는다."""
        banner = self.pages[1][self.pages[1].index('class="banner"'):]
        banner = banner[:banner.index("</div>")]
        self.assertIn("'걷는다' 표", banner)
        self.assertNotIn("걷기 그림", banner)

    def test_첫_행이_걷기면_배너가_걷기_그림을_가리킨다(self):
        """실험03 C4 처럼 `## 단계` 표의 첫 행이 걷기인 회로만 빨간 점선 그림을 가리킨다."""
        text = _STAGED_NETLIST.replace(
            "| 1 | 1단계.png |",
            "| 1걷기 | 1걷기_세가닥.png | **걷기 ①·② 를 뽑는다** | 뽑은 선이 손에 있다 |\n"
            "| 1 | 1단계.png |")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        pages = render_checklist(
            self.spec, parse_netlist(path), TEMPLATE
        ).split('<section class="circuit">')[1:]
        banner = pages[1][pages[1].index('class="banner"'):]
        banner = banner[:banner.index("</div>")]
        self.assertIn("걷기 그림(빨간 점선)", banner)
        self.assertNotIn("'걷는다' 표", banner)

    def test_회로_안_걷기만_있으면_배너는_걷기_그림을_가리키지_않는다(self):
        """배너는 회로 **경계** 판정이라 좁은 쪽(`_has_entry_walk`)만 본다. 넓은 쪽
        (`_has_walk`)을 쓰면 실험03 C2 처럼 회로 안에서만 걷는 회로의 배너가 없는
        걷기 그림을 가리킨다 — 학생이 그 그림을 찾는다."""
        text = _STAGED_NETLIST.replace(
            "| 2 | 2단계.png |",
            "| 2걷기 | 2걷기_프로브.png | **걷기 ① 을 뽑는다** | 뽑은 선이 손에 있다 |\n"
            "| 2 | 2단계.png |")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        netlist = parse_netlist(path)
        c2 = next(c for c in netlist.circuits if c.id == "C2")
        # 지금껏 어느 테스트도 덮지 않은 조합이다 — 이 픽스처가 그 조합인지 못 박는다.
        self.assertIs(_has_walk(c2), True)
        self.assertIs(_has_entry_walk(c2), False)
        pages = render_checklist(
            self.spec, netlist, TEMPLATE
        ).split('<section class="circuit">')[1:]
        banner = pages[1][pages[1].index('class="banner"'):]
        banner = banner[:banner.index("</div>")]
        self.assertIn("'걷는다' 표", banner)
        self.assertNotIn("걷기 그림", banner)

    def test_미사용_상자_제목이_핀_점검이다(self):
        self.assertIn("핀 점검", self.pages[0])
        self.assertIn("개방", self.pages[0])

    def test_전원_박스가_사용_게이트_입력을_말한다(self):
        power = self.html[self.html.index('class="power"'):]
        power = power[:power.index("</div>")]
        self.assertIn("쓰는 게이트의 입력", power)
        self.assertIn("플로팅 금지", power)
        self.assertIn("핀 점검", power)   # 공통 규칙은 2026-09-28 부터 인쇄하지 않는다
        self.assertNotIn("전부 GND", power)


class TestStageTable(unittest.TestCase):
    """단계 진리표 — 단계 블록 안, 노드 입력만, 행마다 ☐(`td.box`), `.check` 없음.
    마지막 관측 단계는 표 대신 기록표가 바로 뒤에 온다.
    설계: docs/plans/2026-09-28-단계별-진리표-설계.md"""

    def _render(self, text):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        html = render_checklist(spec, parse_netlist(path), TEMPLATE)
        return html, html.split('<section class="circuit">')[1:]

    def setUp(self):
        self.html, pages = self._render(_STAGE_NODED_NETLIST)
        self.page = pages[0]

    def _block(self, head):
        """`<h3>{head}</h3>` 로 시작하는 단계 블록 하나 — 블록 안에 div 가 없다."""
        start = self.page.index(f"<h3>{head}</h3>")
        return self.page[start:self.page.index("</div>", start)]

    def test_관측_단계에_단계_진리표가_붙는다(self):
        self.assertIn('class="stage-table"', self._block("단계 1"))

    def test_입력_열은_노드가_쓰는_입력만이다(self):
        block = self._block("단계 1")
        self.assertIn("<tr><th>A</th><th>B</th></tr>", block)
        self.assertNotIn("<th>C</th>", block)
        # LED 급전 표기가 없는 단계는 노드 이름만 찍는다
        self.assertIn('<th rowspan="2">A·B예상<br><small>U1 pin 3</small></th>', block)

    def test_입력_열_묶음_머리가_점퍼_규약을_말한다(self):
        """입력 열을 LED 로 읽지 않게 — 입력은 학생이 거는 점퍼다(2026-09-28 사용자 질문)."""
        self.assertIn('<th colspan="2">입력 — 점퍼 1=+5V · 0=GND</th>', self._block("단계 1"))

    def test_급전_표기가_하나면_노드_열_머리에_LED_번호가_먼저_온다(self):
        page = self._render(_STAGE_NODED_NETLIST.replace(
            "| 앞단 AND 를 꽂는다 |", "| 앞단 AND 를 꽂는다. 임시로 U1 pin 3→LED2 급전 |"))[1][0]
        start = page.index("<h3>단계 1</h3>")
        block = page[start:page.index("</div>", start)]
        self.assertIn('<th rowspan="2">LED2 = A·B<br><small>예상 · U1 pin 3</small></th>', block)

    def test_급전_표기가_둘이면_LED_번호를_짐작하지_않는다(self):
        page = self._render(_STAGE_NODED_NETLIST.replace(
            "| 앞단 AND 를 꽂는다 |", "| U1 pin 3→LED2 급전, U1 pin 6→LED1 급전 |"))[1][0]
        start = page.index("<h3>단계 1</h3>")
        block = page[start:page.index("</div>", start)]
        self.assertNotIn("LED2 =", block)
        self.assertIn('<th rowspan="2">A·B예상<br>', block)

    def test_행은_겹치지_않게_줄이고_행마다_확인_칸이_있다(self):
        block = self._block("단계 1")
        self.assertEqual(block.count("<tr>"), 6)          # 머리 2 + AB 네 조합
        self.assertIn('<tr><td>1</td><td>1</td><td>1</td><td class="box"></td></tr>', block)
        self.assertIn('<tr><td>0</td><td>1</td><td>0</td><td class="box"></td></tr>', block)

    def test_걷기_단계와_마지막_단계에는_표가_없다(self):
        self.assertEqual(self.page.count('class="stage-table"'), 1)
        self.assertNotIn('class="stage-table"', self._block("단계 2 · 걷기"))
        self.assertNotIn('class="stage-table"', self._block("단계 2"))

    def test_기록표가_마지막_단계_바로_뒤에_온다(self):
        self.assertLess(self.page.index('class="wirebox"'), self.page.index('class="stage"'))
        self.assertLess(self.page.rindex('class="stage"'), self.page.index("<h3>T1 ·"))

    def test_check_셀_개수는_변하지_않는다(self):
        self.assertEqual(self.html.count('class="check"'), 8)   # T1 8행

    def test_중간_노드_기대값_표는_없다(self):
        self.assertNotIn("중간 노드 기대값", self.html)
        self.assertNotIn("<th>식</th>", self.html)

    def test_계산할_수_없으면_안내_한_줄이고_죽지_않는다(self):
        _, pages = self._render(_STAGE_NODED_NETLIST.replace("| A·B | A·B |", "| A·B | A·Q |"))
        self.assertIn("단계 진리표를 계산할 수 없어요", pages[0])
        self.assertNotIn('class="stage-table"', pages[0])


class TestUnstagedNodes(unittest.TestCase):
    """최종 리뷰(2026-09-28) Important 1·2 — 단계가 가리키지 않는 노드의 핀·기대값이
    인쇄본에서 사라지면 안 되고, 마지막 단계가 기록표 출력이 아닌 노드를 보면 그 단계에도
    단계 진리표가 있어야 한다."""

    def _page(self, text):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        return render_checklist(spec, parse_netlist(path), TEMPLATE).split(
            '<section class="circuit">')[1]

    def test_단계가_안_보는_노드는_기록표_뒤_표에_남는다(self):
        page = self._page(_STAGE_NODED_NETLIST.replace(
            "| L2 | A·B·C | U1 pin 6 |", "| L2 | A·B·C | U1 pin 6 |\n| C' | C' | U1 pin 8 |"))
        self.assertIn("단계에서 안 본 노드", page)
        block = page[page.index("단계에서 안 본 노드"):]
        self.assertIn("<th>C'<br><small>U1 pin 8</small></th>", block)
        self.assertNotIn("<th>A·B<br>", block)           # 단계가 본 노드는 겹쳐 찍지 않는다
        self.assertLess(page.index("<h3>T1 ·"), page.index("단계에서 안 본 노드"))
        self.assertIn("입력 쪽 노드부터", block)

    def test_모든_노드를_단계가_보면_그_표가_없다(self):
        self.assertNotIn("단계에서 안 본 노드", self._page(_STAGE_NODED_NETLIST))

    def test_단계_없는_회로의_노드는_전부_표에_남는다(self):
        text = _STAGE_NODED_NETLIST
        a = text.index("## 단계"); b = text.index("## 노드")
        page = self._page(text[:a] + text[b:])
        block = page[page.index("단계에서 안 본 노드"):]
        self.assertIn("<th>A·B<br><small>U1 pin 3</small></th>", block)
        self.assertIn("<th>L2<br><small>U1 pin 6</small></th>", block)

    def test_마지막_단계가_출력이_아닌_노드면_단계_진리표를_싣는다(self):
        page = self._page(_STAGE_NODED_NETLIST
                          .replace("| L2 | A·B·C | U1 pin 6 |",
                                   "| L2 | A·B·C | U1 pin 6 |\n| C' | C' | U1 pin 8 |")
                          .replace("노드 `L2` — T1 8행 전부", "노드 `C'` — 두 값"))
        start = page.index("<h3>단계 2</h3>")
        self.assertIn('class="stage-table"', page[start:page.index("</div>", start)])


class StageNodeLine(unittest.TestCase):
    """단계 블록은 그 단계에서 볼 노드의 이름과 핀을 찍는다 — 핀은 `## 노드` 표에서
    조회한다. 저작자가 핀을 단계 표에도 적으면 두 자리가 표류한다."""

    def _stage(self, node):
        return {"n": "1", "diagram": "", "todo": "칩 하나", "check": "노드 `A⊕B` — 네 조합", "node": node}

    def _section(self):
        return types.SimpleNamespace(nodes=[{"name": "A⊕B", "expr": "A⊕B", "pin": "U1 pin 3"}])

    def _netlist(self):
        return types.SimpleNamespace(path=Path(tempfile.mkdtemp()) / "결선도" / "netlist.md")

    def test_노드_이름과_핀을_찍는다(self):
        html = render._stage_html(self._stage("A⊕B"), self._netlist(), self._section())
        self.assertIn("확인 노드", html)
        self.assertIn("A⊕B", html)
        self.assertIn("U1 pin 3", html)

    def test_노드를_안_가리키면_그_줄이_없다(self):
        html = render._stage_html(self._stage(None), self._netlist(), self._section())
        self.assertNotIn("확인 노드", html)

    def test_노드_표에_없는_이름이면_핀_없이_이름만_찍는다(self):
        """검증기가 이미 error 로 막았다 — 렌더는 죽지 않고 이름만 낸다."""
        html = render._stage_html(self._stage("L9"), self._netlist(), self._section())
        self.assertIn("확인 노드", html)
        self.assertIn("L9", html)
        self.assertNotIn("U1 pin 3", html)

    def test_확인_줄은_백틱_없이_인쇄된다(self):
        html = render._stage_html(self._stage("A⊕B"), self._netlist(), self._section())
        self.assertNotIn("`", html)

    def test_걷기_행의_제목은_단계_k_걷기다(self):
        """`단계 2걷기` 로 찍으면 인쇄본에서 읽히지 않는다."""
        stage = {"n": "2걷기", "diagram": "", "todo": "걷기 ① 을 뽑는다",
                 "check": "뽑은 선이 손에 있다", "node": None, "walk": True, "walk_of": 2}
        html = render._stage_html(stage, self._netlist(), self._section())
        self.assertIn("단계 2 · 걷기", html)
        self.assertNotIn("단계 2걷기", html)
        self.assertNotIn("확인 노드", html)


def _board_png(folder, name, data):
    """1×1 PNG 와 사이드카를 나란히 쓴다 — 렌더러를 돌리지 않는다."""
    from PIL import Image
    Image.new("RGB", (1, 1)).save(folder / name)
    (folder / name).with_suffix(".json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8")


_SIDE = {
    "schema": "breadboard-sidecar/v1", "title": "t", "subtitle": "s", "kept": 7,
    "steps": [{"n": 1, "kind": "sig", "from": "우 a12", "to": "좌 a18",
               "desc": "S0' (U4 pin 6) -> U1 pin 1", "count": 1},
              {"n": 2, "kind": "gnd", "from": "좌 b3", "to": "좌 GND레일3행",
               "desc": "U1 GND", "count": 2}],
    "removals": [], "probes": [],
}


class TestBoardText(unittest.TestCase):
    """결선도 PNG 는 보드만 싣는다(2026-09-28) — 결선 순서·걷기·계측은 옆 JSON 에서 온다."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.board_dir = self.dir / "결선도"
        self.board_dir.mkdir()
        (self.board_dir / "netlist.md").write_text("x", encoding="utf-8")
        self.netlist = types.SimpleNamespace(path=self.board_dir / "netlist.md")

    def _stage(self, data, walk=False):
        _board_png(self.board_dir, "s.png", data)
        stage = {"n": "1", "diagram": "s.png", "todo": "할 일", "check": "확인",
                 "node": None, "walk": walk, "walk_of": 1}
        section = types.SimpleNamespace(nodes=[])
        return render._stage_html(stage, self.netlist, section)

    def test_결선_순서가_체크박스_목록으로_실린다(self):
        html = self._stage(_SIDE)
        steps = html[html.index('<ol class="steps">'):]
        steps = steps[:steps.index("</ol>")]
        self.assertEqual(steps.count('<li class="step"'), 2)
        self.assertEqual(steps.count('<span class="box"></span>'), 2)
        self.assertIn('data-kind="sig"', steps)
        self.assertIn("우 a12 → 좌 a18", steps)
        self.assertIn("×2", steps)

    def test_설명의_특수문자를_이스케이프한다(self):
        html = self._stage(_SIDE)
        self.assertIn("S0' (U4 pin 6) -&gt; U1 pin 1", html)   # `_esc` 는 quote=False 다

    def test_회색_개수를_한_줄로_싣는다(self):
        self.assertIn('<p class="kept">회색 = 앞 단계에서 그대로 둔 것 7개</p>',
                      self._stage(_SIDE))

    def test_걷기_번호가_실린다(self):
        data = dict(_SIDE, steps=[], removals=[
            {"n": 1, "text": "좌 d23 → 우 c42 · 임시 급전"},
            {"n": None, "text": "칩 74HC20 (좌 17행) 뽑는다"}])
        html = self._stage(data, walk=True)
        self.assertIn('<p class="list-head">먼저 뽑아요</p>', html)
        self.assertIn('<span class="n">1</span><span class="text">좌 d23 → 우 c42', html)
        self.assertIn('<li class="removal"><span class="box"></span><span class="text">칩 74HC20',
                      html)
        self.assertNotIn('<ol class="steps">', html)

    def test_계측_목록이_실린다(self):
        data = dict(_SIDE, probes=[{"n": 1, "label": "함수발생기 + CH1 (가로축)",
                                    "at": "좌 a10", "desc": "사인파"}])
        html = self._stage(data)
        self.assertIn('<ol class="probes">', html)
        self.assertIn("함수발생기 + CH1 (가로축) → 좌 a10", html)

    def test_사이드카가_없으면_멈춘다(self):
        from PIL import Image
        Image.new("RGB", (1, 1)).save(self.board_dir / "old.png")
        stage = {"n": "1", "diagram": "old.png", "todo": "t", "check": "c",
                 "node": None, "walk": False, "walk_of": 1}
        with self.assertRaises(FileNotFoundError) as e:
            render._stage_html(stage, self.netlist, types.SimpleNamespace(nodes=[]))
        self.assertIn("render_breadboard.py", str(e.exception))

    def test_스키마가_다르면_멈춘다(self):
        with self.assertRaises(ValueError):
            self._stage(dict(_SIDE, schema="breadboard-sidecar/v0"))

    def test_완성본에도_결선_순서가_실린다(self):
        """손그림을 따라 그리는 순서표다 — PNG 아래에 있던 것이 여기로 온다."""
        _board_png(self.board_dir, "f.png", dict(_SIDE, kept=None))
        section = types.SimpleNamespace(diagram="f.png", body="")
        html = render._diagram_html(section, self.netlist)
        self.assertIn('<figure class="board">', html)
        self.assertIn('<ol class="steps">', html)
        self.assertNotIn('class="kept"', html)


class TestIssueRefsDropped(unittest.TestCase):
    """미확정 표는 인쇄하지 않는다(2026-09-28) — 산문의 `(M9)` 같은 참조가 가리킬 곳이 없어
    학생에게는 뜻 없는 글자다. netlist 원문은 저작용이라 그대로 두고 인쇄할 때만 벗긴다."""

    def test_괄호째_참조를_벗긴다(self):
        cases = {
            "교안 근거가 없다(M4).": "교안 근거가 없다.",
            "배선 편의다(M11, M12).": "배선 편의다.",
            "(U4F — 교안은 U4A pin 1, M9)": "(U4F — 교안은 U4A pin 1)",
            "넷~다섯이다(예산 5, M8).": "넷~다섯이다(예산 5).",
            "새로 짓는다(M6, 2026-09-27 결정).": "새로 짓는다(2026-09-27 결정).",
            "(교안 p10 머리글 — 기종은 M8). CH1": "(교안 p10 머리글). CH1",
            "교안 원문이 아니다(M8 에서 함께 확인)": "교안 원문이 아니다",
        }
        for src, want in cases.items():
            with self.subTest(src=src):
                self.assertEqual(render._drop_issue_refs(src), want)

    def test_M_이_아닌_괄호는_두다(self):
        for keep in ("74HC20 (dual 4-input NAND)", "(n.c.)", "MUX(4x1)", "M 자 모양"):
            self.assertEqual(render._drop_issue_refs(keep), keep)

    def test_실험01_04_인쇄본에_M번호가_없다(self):
        for n in (1, 2, 3, 4):
            spec = parse_spec(ROOT / config.experiment_dir(n) / "체크리스트/명세.md")
            netlist = parse_netlist(ROOT / config.experiment_dir(n) / "결선도/netlist.md")
            body = common_page(spec, netlist) + circuit_pages(spec, netlist)
            with self.subTest(실험=n):
                self.assertEqual(re.findall(r".{0,20}\bM\d{1,2}\b.{0,10}", body), [])


class TestPinCheckHeading(unittest.TestCase):
    def test_핀_점검_제목이_미사용_핀을_비우라고_단정하지_않는다(self):
        """실험02 는 미사용 입력을 GND·VCC 에 묶는다 — 전원 박스가 이 상자를 가리키므로
        제목이 '비어 있는가' 면 그 주차에 틀린 지시가 된다(2026-09-28 최종 리뷰)."""
        spec = parse_spec(ROOT / config.experiment_dir(2) / "체크리스트/명세.md")
        netlist = parse_netlist(ROOT / config.experiment_dir(2) / "결선도/netlist.md")
        html = circuit_pages(spec, netlist)
        self.assertIn('class="unused"', html)
        self.assertNotIn("미사용 핀은 비어 있는가", html)
        self.assertIn("미사용 핀은 지시대로인가", html)


class TestWalkNumberMatchesPicture(unittest.TestCase):
    def test_걷기_번호_원은_그림처럼_빨갛게_채운다(self):
        """결선도의 걷기 번호는 빨간 채움·흰 숫자다(`_marker_removed`, filled=True). 목록의
        번호가 흰 바탕·점선이면 학생이 그림의 ①과 목록의 ①을 바로 짝짓지 못한다."""
        # 공용 규칙(`.step .n, .probe .n, .removal .n`)이 아니라 걷기 전용 규칙을 본다
        rule = re.search(r"^\s*\.removal \.n\s*\{[^}]*\}", TEMPLATE, re.M)
        self.assertIsNotNone(rule)
        self.assertIn("background: var(--pull)", rule.group(0))
        self.assertIn("color: var(--paper)", rule.group(0))
