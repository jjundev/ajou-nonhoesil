"""`lab-netlist/v2` 파서 계약. 정본은 `docs/schema/lab-netlist-v2.md` 다.

`spec_parser` 와 같은 분업을 지킨다 — 여기서는 **표현할 수 없는 것**만 예외로
던지고(알 수 없는 kind, 회로인데 id 가 없음), 의미 결함(없는 항목을 가리킴,
그림 파일 부재)은 `validate.check_netlist_circuits` 가 findings 로 보고한다.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.netlist_parser import NetlistError, parse_netlist

ROOT = Path(__file__).resolve().parents[1]

MINIMAL = """---
schema: lab-netlist/v2
experiment: 1
spec: ../체크리스트/명세.md
---

# 공통 규칙

- kind: common
- 모든 IC: pin 14 → VCC, pin 7 → GND
- 미사용 입력핀은 전부 GND

# C1 · 3-input AND

- kind: circuit
- id: C1
- item: E1.P1-1
- tables: [T1]
- diagram: 그림.png

- U1 = 74HC08 (quad 2-input AND, DIP-14)
  - pin 14 → VCC(+5V)
  - pin 1  ← 입력 A
  - 미사용 입력핀: pin 9, 10 → GND
"""


def _write(text):
    path = Path(tempfile.mkdtemp()) / "netlist.md"
    path.write_text(text, encoding="utf-8")
    return path


class ParseMinimal(unittest.TestCase):
    def setUp(self):
        self.netlist = parse_netlist(_write(MINIMAL))

    def test_프론트매터를_읽는다(self):
        self.assertEqual(self.netlist.experiment, 1)
        self.assertEqual(self.netlist.spec, "../체크리스트/명세.md")

    def test_절을_kind_로_가른다(self):
        self.assertEqual([s.kind for s in self.netlist.sections],
                         ["common", "circuit"])
        self.assertEqual(len(self.netlist.circuits), 1)
        self.assertEqual(len(self.netlist.of_kind("common")), 1)

    def test_회로_메타를_읽는다(self):
        c = self.netlist.circuits[0]
        self.assertEqual(c.id, "C1")
        self.assertEqual(c.item, "E1.P1-1")
        self.assertEqual(c.tables, ["T1"])
        self.assertEqual(c.diagram, "그림.png")

    def test_속성_리스트를_본문에서_걷어낸다(self):
        """속성 줄이 본문에 남으면 인쇄본에 `kind: circuit` 이 배선 단계로 찍힌다."""
        c = self.netlist.circuits[0]
        self.assertNotIn("kind:", c.body)
        self.assertNotIn("tables:", c.body)
        self.assertIn("U1 = 74HC08", c.body)

    def test_콜론이_든_한글_불릿을_속성으로_오인하지_않는다(self):
        """`- 미사용 입력핀: pin 9, 10 → GND` 는 속성이 아니라 배선이다."""
        c = self.netlist.circuits[0]
        self.assertIn("미사용 입력핀", c.body)

    def test_칩_이름을_배선_본문에서_뽑는다(self):
        """`- ics:` 필드를 따로 두지 않는다 — 필드를 늘리면 본문과 표류한다."""
        self.assertEqual(self.netlist.circuits[0].ics, ["74HC08"])

    def test_공통_절은_회로_필드가_비어_있다(self):
        common = self.netlist.of_kind("common")[0]
        self.assertIsNone(common.id)
        self.assertEqual(common.tables, [])


class ParseRejects(unittest.TestCase):
    def test_kind_가_없으면_거절하고_백필_방법을_알린다(self):
        text = MINIMAL.replace("- kind: common\n", "")
        with self.assertRaises(NetlistError) as cm:
            parse_netlist(_write(text))
        self.assertIn("kind", str(cm.exception))
        self.assertIn("docs/schema/lab-netlist-v2.md", str(cm.exception))

    def test_모르는_kind_를_거절한다(self):
        text = MINIMAL.replace("- kind: common", "- kind: 잡담")
        with self.assertRaises(NetlistError):
            parse_netlist(_write(text))

    def test_회로에_tables_가_없으면_거절한다(self):
        text = MINIMAL.replace("- tables: [T1]\n", "")
        with self.assertRaises(NetlistError) as cm:
            parse_netlist(_write(text))
        self.assertIn("tables", str(cm.exception))

    def test_회로_id_중복을_거절한다(self):
        text = MINIMAL + MINIMAL[MINIMAL.index("# C1"):]
        with self.assertRaises(NetlistError) as cm:
            parse_netlist(_write(text))
        self.assertIn("C1", str(cm.exception))

    def test_회로가_하나도_없으면_거절한다(self):
        text = MINIMAL[:MINIMAL.index("# C1")]
        with self.assertRaises(NetlistError) as cm:
            parse_netlist(_write(text))
        self.assertIn("회로", str(cm.exception))

    def test_스키마가_다르면_거절한다(self):
        text = MINIMAL.replace("lab-netlist/v2", "lab-netlist/v0")
        with self.assertRaises(NetlistError):
            parse_netlist(_write(text))

    def test_줄_번호가_파일_기준이다(self):
        """프론트매터를 뺀 본문 기준으로 세면 오류가 프론트매터 한복판을 가리킨다."""
        text = MINIMAL.replace("- kind: common\n", "")
        with self.assertRaises(NetlistError) as cm:
            parse_netlist(_write(text))
        self.assertIn(":7 ", str(cm.exception))


class ChipNames(unittest.TestCase):
    """칩 이름은 배선 본문에서 뽑는다. 칩 교체 배너가 이것을 그대로 말한다."""

    def _section(self, body):
        text = MINIMAL.replace(
            "- U1 = 74HC08 (quad 2-input AND, DIP-14)\n"
            "  - pin 14 → VCC(+5V)\n"
            "  - pin 1  ← 입력 A\n"
            "  - 미사용 입력핀: pin 9, 10 → GND\n", body)
        return parse_netlist(_write(text)).circuits[0]

    def test_괄호_설명이_붙은_칩(self):
        self.assertEqual(
            self._section("- U1 = 74HC08 (quad 2-input AND, DIP-14)\n").ics,
            ["74HC08"])

    def test_백틱으로_감싼_칩(self):
        self.assertEqual(self._section("## U1 = `7490` (decade counter)\n").ics,
                         ["7490"])

    def test_낱말이_여럿인_칩을_자르지_않는다(self):
        """실험10 의 `741 OP amp`. 첫 공백에서 끊으면 `741` 이 된다."""
        self.assertEqual(
            self._section("## U4 = `741 OP amp` (반전 가산 증폭기)\n").ics,
            ["741 OP amp"])

    def test_같은_칩을_두_번_세지_않는다(self):
        self.assertEqual(
            self._section("- U1 = 74HC08 (quad)\n- U3 = 74HC08 (quad)\n").ics,
            ["74HC08"])


class RealExperiment1(unittest.TestCase):
    """실물이 적합성 픽스처다 (`docs/schema/lab-spec-v2.md` 와 같은 규율)."""

    def test_실험01_결선도가_회로_다섯을_준다(self):
        netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        self.assertEqual([c.id for c in netlist.circuits],
                         ["C1", "C2", "C3", "C4", "C5"])
        self.assertEqual([c.tables for c in netlist.circuits],
                         [["T1"], ["T2"], ["T3"], ["T4"], ["T5"]])

    def test_실험01_이_비회로_kind_네_종류를_모두_쓴다(self):
        netlist = parse_netlist(
            ROOT / config.experiment_dir(1) / "결선도/netlist.md")
        for kind in ("common", "lookup", "sources", "open-issues"):
            with self.subTest(kind=kind):
                self.assertTrue(netlist.of_kind(kind), f"{kind} 절이 없다")


class ContinuesField(unittest.TestCase):
    def _netlist(self, extra):
        text = ("---\nschema: lab-netlist/v2\nexperiment: 10\n"
                "spec: ../체크리스트/명세.md\n---\n\n"
                "# C1 · DAC\n\n- kind: circuit\n- id: C1\n- item: E10.P1\n"
                "- tables: [T1]\n\n- U1 = 7490\n  - pin 5 → VCC\n\n"
                "# C2 · ADC\n\n- kind: circuit\n- id: C2\n- item: E10.P2\n"
                f"- tables: [T2]\n{extra}\n\n- U5 = 741\n  - pin 7 → +15V\n")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        return parse_netlist(path)

    def test_continues_를_읽는다(self):
        netlist = self._netlist("- continues: C1")
        self.assertEqual(netlist.circuits[1].continues, "C1")

    def test_없으면_None_이다(self):
        netlist = self._netlist("")
        self.assertIsNone(netlist.circuits[1].continues)
        self.assertIsNone(netlist.circuits[0].continues)


class RefsField(unittest.TestCase):
    def _netlist(self, extra):
        text = ("---\nschema: lab-netlist/v2\nexperiment: 2\n"
                "spec: ../체크리스트/명세.md\n---\n\n"
                "# C1 · tpd\n\n- kind: circuit\n- id: C1\n- item: E2.P4\n"
                f"- tables: [T7]\n{extra}\n\n- U1 = 74HC04\n  - pin 14 → VCC\n")
        path = Path(tempfile.mkdtemp()) / "netlist.md"
        path.write_text(text, encoding="utf-8")
        return parse_netlist(path)

    def test_refs_를_리스트로_읽는다(self):
        self.assertEqual(self._netlist("- refs: [T8]").circuits[0].refs, ["T8"])

    def test_없으면_빈_리스트다(self):
        self.assertEqual(self._netlist("").circuits[0].refs, [])

    def test_스칼라도_리스트로_감싼다(self):
        self.assertEqual(self._netlist("- refs: T8").circuits[0].refs, ["T8"])


class SchemaV2(unittest.TestCase):
    """`week:` 를 걷어낸 v2. v1 은 이제 구조적으로 거절된다."""

    def test_v2는_week_없이_읽힌다(self):
        netlist = parse_netlist(_write(MINIMAL))
        self.assertEqual(netlist.experiment, 1)
        self.assertFalse(hasattr(netlist, "week"))

    def test_v1은_거절한다(self):
        text = (
            "---\nschema: lab-netlist/v1\nexperiment: 1\n"
            "spec: ../체크리스트/명세.md\n---\n\n"
            "# C1 · 시험\n\n- kind: circuit\n- id: C1\n"
            "- item: E1.P1-1\n- tables: [T1]\n\n"
            "- U1 = 74HC08\n  - pin 14 → VCC\n"
        )
        with self.assertRaises(NetlistError) as cm:
            parse_netlist(_write(text))
        self.assertIn("lab-netlist/v2", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
