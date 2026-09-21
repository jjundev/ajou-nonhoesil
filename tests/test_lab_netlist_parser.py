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


STAGED = """---
schema: lab-netlist/v2
experiment: 1
spec: ../체크리스트/명세.md
---

# 칩 자리표

- kind: layout

| 슬롯 | 자리 | 회로별 칩 |
|---|---|---|
| S1 | 좌 7행 | C1 74HC08 |

# C3 · NAND

- kind: circuit
- id: C3
- item: E1.P2-1
- tables: [T3]
- diagram: 완성.png

교안 p13 회로도 그대로.

## 단계

| 단계 | 그림 | 이 단계에서 | 확인 |
|---|---|---|---|
| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |
| 2 | `2단계.png` | 74HC00 을 더한다 | T3 8행 |

- U3 = 74HC08 (quad 2-input AND)
  - pin 14 → VCC(+5V)
  - 미사용 입력핀: pin 4, 5 → 개방
"""


class Stages(unittest.TestCase):
    def setUp(self):
        self.netlist = parse_netlist(_write(STAGED))
        self.c3 = self.netlist.circuits[0]

    def test_layout_kind_를_읽는다(self):
        layout = self.netlist.of_kind("layout")
        self.assertEqual(len(layout), 1)
        self.assertIn("| S1 |", layout[0].body)

    def test_단계_표를_읽는다(self):
        self.assertEqual([s["n"] for s in self.c3.stages], ["1", "2"])
        self.assertEqual(self.c3.stages[0]["diagram"], "1단계.png")   # 백틱을 벗긴다
        self.assertEqual(self.c3.stages[0]["todo"], "74HC08 만 꽂는다")
        self.assertEqual(self.c3.stages[1]["check"], "T3 8행")

    def test_일반_단계_번호를_정수로_읽는다(self):
        c3 = parse_netlist(_write(STAGED)).circuits[0]
        self.assertEqual([s["stage_no"] for s in c3.stages], [1, 2])

    def test_앞자리_0은_숫자로_같은_단계다(self):
        text = STAGED.replace("| 2 | `2단계.png` |", "| 03 | `3단계.png` |")
        c3 = parse_netlist(_write(text)).circuits[0]
        self.assertEqual(c3.stages[1]["stage_no"], 3)

    def test_걷기_오타는_일반_단계로_강등하지_않는다(self):
        for bad in ("2 걷기", "걷기2"):
            with self.subTest(value=bad):
                text = STAGED.replace("| 2 | `2단계.png` |", f"| {bad} | `2걷기.png` |")
                row = parse_netlist(_write(text)).circuits[0].stages[1]
                self.assertIsNone(row["stage_no"])
                self.assertFalse(row["walk"])
                self.assertIsNone(row["walk_of"])

    def test_확인_칸이_가리키는_노드를_뽑는다(self):
        """단계 하나는 관측 노드 하나를 세운다 — 그 이름이 데이터여야 검증기가 잰다.
        백틱이 이름의 경계다: `A⊕B` 는 `(A⊕B)·Ci` 의 부분 문자열이라 공백으로는 못 가른다."""
        text = STAGED.replace("| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |",
                              "| 1 | `1단계.png` | 74HC08 만 꽂는다 | 노드 `A·B` — L1 을 네 조합으로 본다 |")
        c3 = parse_netlist(_write(text)).circuits[0]
        self.assertEqual(c3.stages[0]["node"], "A·B")
        self.assertEqual(c3.stages[1]["node"], None)

    def test_확인_칸이_닫는_백틱으로_끝나도_노드를_뽑는다(self):
        """`_split_subtable` 이 셀 양끝 백틱을 떼므로 `노드 `A·B`` 는 닫는 백틱을 잃는다.
        정규식이 그 경우에도 이름을 온전히 내야 한다."""
        text = STAGED.replace("| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |",
                              "| 1 | `1단계.png` | 74HC08 만 꽂는다 | 노드 `(A⊕B)·Ci` |")
        c3 = parse_netlist(_write(text)).circuits[0]
        self.assertEqual(c3.stages[0]["node"], "(A⊕B)·Ci")

    def test_노드로_시작하지_않는_확인_칸은_None_이다(self):
        """실험01·02 승인본의 단계 표가 그렇다 — 파서가 거절하지 않는다."""
        c3 = parse_netlist(_write(STAGED)).circuits[0]
        self.assertEqual([s["node"] for s in c3.stages], [None, None])

    def test_걷기_행을_판정한다(self):
        """걷기 행은 관측 노드가 없다 — 판정이 데이터여야 검증기·렌더러가 한 곳만 읽는다.
        `<k>걷기` 의 k 는 **바로 다음 행**의 단계 번호다."""
        text = STAGED.replace(
            "| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |",
            "| 1걷기 | `1걷기_세가닥.png` | **걷기 ① 을 뽑는다** | 뽑은 선이 손에 있다 |\n"
            "| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |")
        c3 = parse_netlist(_write(text)).circuits[0]
        self.assertEqual([s["n"] for s in c3.stages], ["1걷기", "1", "2"])
        self.assertEqual([s["walk"] for s in c3.stages], [True, False, False])
        self.assertEqual([s["walk_of"] for s in c3.stages], [1, None, None])
        self.assertEqual([s["stage_no"] for s in c3.stages], [None, 1, 2])

    def test_걷기_주소쌍과_확인_홀을_순서대로_읽는다(self):
        text = STAGED.replace(
            "| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |",
            "| 1걷기 | `1걷기.png` | 걷기 ①(좌 d7→우 a10)·②(좌 a9 → 우 c13)를 뽑는다 | "
            "좌 d7·우 a10·좌 a9·우 c13 홀이 비었다 |\n"
            "| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |")
        row = parse_netlist(_write(text)).circuits[0].stages[0]
        self.assertEqual(row["walk_addresses"],
                         ["좌 d7 → 우 a10", "좌 a9 → 우 c13"])
        self.assertEqual(row["check_holes"],
                         ["좌 d7", "우 a10", "좌 a9", "우 c13"])

    def test_꽂기_행의_걷기_주소_필드는_빈_리스트다(self):
        row = parse_netlist(_write(STAGED)).circuits[0].stages[0]
        self.assertEqual(row["walk_addresses"], [])
        self.assertEqual(row["check_holes"], [])

    def test_두_자리_걷기_번호도_읽는다(self):
        """`10걷기` 가 `1` 로 잘리면 검증기의 '다음 행과 같은가' 가 거짓 통과한다."""
        text = STAGED.replace("| 2 | `2단계.png` | 74HC00 을 더한다 | T3 8행 |",
                              "| 10걷기 | `10걷기.png` | **걷기 ① 을 뽑는다** | 손에 있다 |\n"
                              "| 10 | `10단계.png` | 74HC00 을 더한다 | T3 8행 |")
        c3 = parse_netlist(_write(text)).circuits[0]
        self.assertEqual(c3.stages[1]["walk_of"], 10)

    def test_꽂기_행은_걷기가_아니다(self):
        """실험01·02 승인본의 단계 표가 그렇다 — 파서가 거절하지 않는다."""
        c3 = parse_netlist(_write(STAGED)).circuits[0]
        self.assertEqual([s["walk"] for s in c3.stages], [False, False])
        self.assertEqual([s["walk_of"] for s in c3.stages], [None, None])

    def test_단계_표는_본문에서_빠진다(self):
        """남으면 `_circuit_body` 가 참조표로 인쇄한다 — 단계 블록과 표가 두 번 찍힌다."""
        self.assertNotIn("## 단계", self.c3.body)
        self.assertNotIn("1단계.png", self.c3.body)
        self.assertIn("교안 p13", self.c3.body)
        self.assertIn("U3 = 74HC08", self.c3.body)

    def test_단계가_없으면_빈_리스트다(self):
        netlist = parse_netlist(_write(MINIMAL))
        self.assertEqual(netlist.circuits[0].stages, [])

    def test_단계_표의_열이_다르면_거절한다(self):
        bad = STAGED.replace("| 단계 | 그림 | 이 단계에서 | 확인 |", "| 단계 | 파일 | 할 일 | 확인 |")
        with self.assertRaisesRegex(NetlistError, "이 단계에서"):
            parse_netlist(_write(bad))

    def test_단계_헤딩_아래_표가_없으면_거절한다(self):
        bad = STAGED.replace("| 단계 | 그림 | 이 단계에서 | 확인 |\n|---|---|---|---|\n", "")
        bad = bad.replace("| 1 | `1단계.png` | 74HC08 만 꽂는다 | L1 = A·B, AB = 00·01·10·11 |\n", "")
        bad = bad.replace("| 2 | `2단계.png` | 74HC00 을 더한다 | T3 8행 |\n", "")
        with self.assertRaisesRegex(NetlistError, "단계"):
            parse_netlist(_write(bad))

    def test_단계_행의_셀_수가_다르면_거절한다(self):
        """짧은 행은 `md._cells` 가 채우지 않는다 — 그대로 두면 뒤에서 KeyError 로 죽는다."""
        bad = STAGED.replace("| 2 | `2단계.png` | 74HC00 을 더한다 | T3 8행 |",
                             "| 2 | `2단계.png` | 74HC00 을 더한다 |")
        with self.assertRaisesRegex(NetlistError, "셀"):
            parse_netlist(_write(bad))


NODED = MINIMAL.replace(
    "- diagram: 그림.png\n",
    "- diagram: 그림.png\n\n## 노드\n\n"
    "| 노드 | 식 | 핀 |\n|---|---|---|\n"
    "| A·B | A·B | `U1 pin 3` |\n"
    "| L2 | A·B·C | U1 pin 6 |\n")


class ParseNodes(unittest.TestCase):
    """`## 노드` 표 — 프로브로 찍을 핀과 그 기대값 식. 단계 표와 같은 메커니즘이다."""

    def setUp(self):
        self.c1 = parse_netlist(_write(NODED)).circuits[0]

    def test_노드_표를_읽는다(self):
        self.assertEqual([n["name"] for n in self.c1.nodes], ["A·B", "L2"])
        self.assertEqual(self.c1.nodes[0]["expr"], "A·B")
        self.assertEqual(self.c1.nodes[0]["pin"], "U1 pin 3")   # 백틱을 벗긴다
        self.assertEqual(self.c1.nodes[1]["expr"], "A·B·C")

    def test_노드_표는_본문에서_빠진다(self):
        """남으면 `_circuit_body` 가 참조표로 인쇄한다 — 기대값 표가 두 번 찍힌다."""
        self.assertNotIn("## 노드", self.c1.body)
        self.assertNotIn("U1 pin 6", self.c1.body)
        self.assertIn("U1 = 74HC08", self.c1.body)

    def test_노드가_없으면_빈_리스트다(self):
        self.assertEqual(parse_netlist(_write(MINIMAL)).circuits[0].nodes, [])

    def test_노드_표의_열이_다르면_거절한다(self):
        bad = NODED.replace("| 노드 | 식 | 핀 |", "| 이름 | 식 | 핀 |")
        with self.assertRaisesRegex(NetlistError, "노드"):
            parse_netlist(_write(bad))

    def test_노드_헤딩_아래_표가_없으면_거절한다(self):
        bad = NODED.replace("| 노드 | 식 | 핀 |\n|---|---|---|\n", "")
        bad = bad.replace("| A·B | A·B | `U1 pin 3` |\n", "")
        bad = bad.replace("| L2 | A·B·C | U1 pin 6 |\n", "")
        with self.assertRaisesRegex(NetlistError, "노드"):
            parse_netlist(_write(bad))

    def test_노드_행의_셀_수가_다르면_거절한다(self):
        """핀 칸이 빠진 행은 `pin` 키가 없는 dict 이 된다 — `_check_nodes` 가 KeyError 로
        죽어 검증기 밖으로 예외가 샌다. 구조 결함이라 파서가 먼저 거절한다."""
        bad = NODED.replace("| A·B | A·B | `U1 pin 3` |", "| A·B | A·B |")
        with self.assertRaisesRegex(NetlistError, "셀"):
            parse_netlist(_write(bad))

    def test_단계와_노드가_함께_있으면_둘_다_뗀다(self):
        both = NODED.replace(
            "## 노드\n",
            "## 단계\n\n| 단계 | 그림 | 이 단계에서 | 확인 |\n|---|---|---|---|\n"
            "| 1 | 1단계.png | 칩 하나 | L1 4조합 |\n\n## 노드\n")
        c1 = parse_netlist(_write(both)).circuits[0]
        self.assertEqual([s["n"] for s in c1.stages], ["1"])
        self.assertEqual([n["name"] for n in c1.nodes], ["A·B", "L2"])
        self.assertNotIn("## 단계", c1.body)
        self.assertNotIn("## 노드", c1.body)

    def test_스키마_문서가_노드_표_계약을_적는다(self):
        """정본은 코드지만 저작자는 문서를 읽는다 — 열 이름과 핀 형식이 문서에 있어야 한다."""
        doc = (ROOT / "docs/schema/lab-netlist-v2.md").read_text(encoding="utf-8")
        self.assertIn("### 회로 안의 `## 노드` 표", doc)
        self.assertIn("| 노드 | 식 | 핀 |", doc)
        self.assertIn("U<n> pin <m>", doc)
        for skill in ("prep-lab-checklist", "draft-lab-spec"):
            text = (ROOT / f".claude/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertIn("## 노드", text)


if __name__ == "__main__":
    unittest.main()
