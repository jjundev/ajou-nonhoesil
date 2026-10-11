"""`## 노드` 표 × 기록 진리표 → 노드 기대값. 설계: docs/plans/2026-09-20-중간노드-기대값표-설계.md"""

import unittest
from pathlib import Path

from scripts.lab import config, nodes
from scripts.lab.netlist_parser import NetlistSection, parse_netlist
from scripts.lab.spec_parser import LabSpec, SpecTable, parse_spec

ROOT = Path(__file__).resolve().parents[1]
WEEK2_SPEC = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"
E5_SPEC = ROOT / config.experiment_dir(5) / "체크리스트/명세.md"
E5_NETLIST = ROOT / config.experiment_dir(5) / "결선도/netlist.md"


def _circuit(tables, node_rows, body="- U1 = 74HC08 (quad 2-input AND)\n  - pin 14 → VCC\n"):
    return NetlistSection(kind="circuit", title="C1", body=body, line=1, id="C1",
                          item="E1.P1-1", tables=tables,
                          nodes=[{"name": n, "expr": e, "pin": p} for n, e, p in node_rows])


def _spec(*tables):
    return LabSpec(experiment=1, title="합성", source_manual="", power={"VCC": "+5V"},
                   items=[], tables=list(tables), path=Path("명세.md"))


class TestComputeOnRealSpec(unittest.TestCase):
    """실험01 T1: A B C → L1 = A·B, L2 = A·B·C. 8행."""

    def setUp(self):
        self.spec = parse_spec(WEEK2_SPEC)
        self.circuit = _circuit(["T1"], [("AB", "A·B", "U1 pin 3"), ("L2", "A·B·C", "U1 pin 6")])
        self.nt = nodes.compute(self.circuit, self.spec)

    def test_입력_열과_노드_머리를_낸다(self):
        self.assertEqual(self.nt.inputs, ["A", "B", "C"])
        self.assertEqual(self.nt.nodes, [("AB", "U1 pin 3"), ("L2", "U1 pin 6")])
        self.assertEqual(self.nt.encoding, "0/1")

    def test_행마다_노드_값을_계산한다(self):
        self.assertEqual(len(self.nt.rows), 8)
        self.assertEqual(self.nt.rows[6], (["1", "1", "0"], [1, 0]))   # 110
        self.assertEqual(self.nt.rows[7], (["1", "1", "1"], [1, 1]))   # 111
        self.assertEqual(self.nt.rows[0], (["0", "0", "0"], [0, 0]))

    def test_기록표를_고른다(self):
        self.assertEqual(nodes.record_table(self.circuit, self.spec).id, "T1")

    def test_알_수_없는_변수는_ValueError(self):
        bad = _circuit(["T1"], [("Q", "A·Q", "U1 pin 3")])
        with self.assertRaisesRegex(ValueError, "노드 Q"):
            nodes.compute(bad, self.spec)


class TestComputeSynthetic(unittest.TestCase):
    def test_H_L_표는_H_L_인코딩을_낸다(self):
        t = SpecTable(id="T9", title="x", kind="truth-table", encoding="H/L",
                      source="derived (Y = A·B)", expected=None, role="record",
                      header=["A", "B", "Y"], rows=[["L", "L", "L"], ["H", "H", "H"]], line=1)
        nt = nodes.compute(_circuit(["T9"], [("Y", "A·B", "U1 pin 3")]), _spec(t))
        self.assertEqual(nt.encoding, "H/L")
        self.assertEqual(nt.rows, [(["L", "L"], [0]), (["H", "H"], [1])])
        self.assertEqual([nodes.format_bit(b, "H/L") for b in (0, 1, None)], ["L", "H", "—"])
        self.assertEqual([nodes.format_bit(b, "0/1") for b in (0, 1, None)], ["0", "1", "—"])

    def test_dont_care_입력_행은_None(self):
        t = SpecTable(id="T9", title="x", kind="truth-table", encoding="0/1",
                      source="derived (Y = A·B)", expected=None, role="record",
                      header=["A", "B", "Y"], rows=[["X", "0", "0"], ["1", "1", "1"]], line=1)
        nt = nodes.compute(_circuit(["T9"], [("Y", "A·B", "U1 pin 3")]), _spec(t))
        self.assertEqual(nt.rows, [(["X", "0"], None), (["1", "1"], [1])])

    def test_기록_진리표가_없으면_None_이고_compute_는_ValueError(self):
        cap = SpecTable(id="T1", title="파형", kind="capture", encoding=None,
                        source="manual:p3", expected="계단", role="record",
                        header=[], rows=[], line=1)
        ref = SpecTable(id="T2", title="이론", kind="truth-table", encoding="H/L",
                        source="manual:p5", expected=None, role="reference",
                        header=["A", "B", "Y"], rows=[["L", "L", "L"]], line=1)
        circuit = _circuit(["T1", "T2"], [("Y", "A·B", "U1 pin 3")])
        self.assertIsNone(nodes.record_table(circuit, _spec(cap, ref)))
        with self.assertRaisesRegex(ValueError, "기록표"):
            nodes.compute(circuit, _spec(cap, ref))

    def test_기록표가_둘인데_입력_열이_다르면_ValueError(self):
        t1 = SpecTable(id="T1", title="x", kind="truth-table", encoding="0/1",
                       source="derived (Y = A·B)", expected=None, role="record",
                       header=["A", "B", "Y"], rows=[["0", "0", "0"]], line=1)
        t2 = SpecTable(id="T2", title="y", kind="truth-table", encoding="0/1",
                       source="derived (Z = A·B·C)", expected=None, role="record",
                       header=["A", "B", "C", "Z"], rows=[["0", "0", "0", "0"]], line=1)
        with self.assertRaisesRegex(ValueError, "입력 열"):
            nodes.record_table(_circuit(["T1", "T2"], [("Y", "A·B", "U1 pin 3")]), _spec(t1, t2))


def _record(header, rows, encoding="0/1", source="derived (Y = A·B)"):
    return SpecTable(id="T9", title="x", kind="truth-table", encoding=encoding,
                     source=source, expected=None, role="record",
                     header=header, rows=rows, line=1)


class TestStageTable(unittest.TestCase):
    """단계 진리표 — 노드 식에 나오는 입력만, 기록표 행을 줄여 합친다.
    설계: docs/plans/2026-09-28-단계별-진리표-설계.md"""

    # 실험04 T1 의 축소판 — E=1 행은 나머지가 X 다.
    MUX = _record(["E", "S0", "D0", "Y"],
                  [["1", "X", "X", "0"], ["0", "0", "1", "1"],
                   ["0", "0", "0", "0"], ["0", "1", "1", "0"]],
                  source="derived (Y = E'·S0'·D0)")

    def test_실험01_기록표를_노드_입력으로_줄인다(self):
        spec = parse_spec(WEEK2_SPEC)
        circuit = _circuit(["T1"], [("AB", "A·B", "U1 pin 3"), ("L2", "A·B·C", "U1 pin 6")])
        st = nodes.stage_table(circuit, spec, "AB")
        self.assertEqual(st.inputs, ["A", "B"])
        self.assertEqual(st.node, ("AB", "U1 pin 3"))
        self.assertEqual(st.encoding, "0/1")
        self.assertEqual(st.rows, [(["0", "0"], 0), (["0", "1"], 0),
                                   (["1", "0"], 0), (["1", "1"], 1)])

    def test_모든_입력을_쓰는_노드는_기록표_행_그대로다(self):
        spec = parse_spec(WEEK2_SPEC)
        circuit = _circuit(["T1"], [("L2", "A·B·C", "U1 pin 6")])
        st = nodes.stage_table(circuit, spec, "L2")
        self.assertEqual(st.inputs, ["A", "B", "C"])
        self.assertEqual(len(st.rows), 8)
        self.assertEqual(st.rows[7], (["1", "1", "1"], 1))

    def test_X_가_남아도_값이_정해지면_X_째_싣는다(self):
        circuit = _circuit(["T9"], [("N0", "(E'·S0'·D0)'", "U1 pin 6")])
        st = nodes.stage_table(circuit, _spec(self.MUX), "N0")
        self.assertEqual(st.inputs, ["E", "S0", "D0"])
        self.assertEqual(st.rows[0], (["1", "X", "X"], 1))
        self.assertEqual(len(st.rows), 4)

    def test_값이_안_정해지는_X_행은_뺀다(self):
        circuit = _circuit(["T9"], [("S0'", "S0'", "U4 pin 2")])
        st = nodes.stage_table(circuit, _spec(self.MUX), "S0'")
        self.assertEqual(st.inputs, ["S0"])
        self.assertEqual(st.rows, [(["0"], 1), (["1"], 0)])

    def test_한_입력만_쓰는_노드는_기록표에_나온_순서대로_두_행이다(self):
        circuit = _circuit(["T9"], [("E'", "E'", "U4 pin 12")])
        st = nodes.stage_table(circuit, _spec(self.MUX), "E'")
        self.assertEqual(st.rows, [(["1"], 0), (["0"], 1)])

    def test_H_L_표는_H_L_셀과_인코딩을_낸다(self):
        t = _record(["A", "B", "Y"],
                    [["L", "L", "L"], ["L", "H", "L"], ["H", "L", "L"], ["H", "H", "H"]],
                    encoding="H/L")
        st = nodes.stage_table(_circuit(["T9"], [("A'", "A'", "U2 pin 2")]), _spec(t), "A'")
        self.assertEqual(st.encoding, "H/L")
        self.assertEqual(st.rows, [(["L"], 1), (["H"], 0)])

    def test_입력과_출력이_같은_글자여도_입력_열을_읽는다(self):
        # 실험3 반감산기 `A B D B` — 뒤의 B 가 출력이다(`split_indices`).
        # 11 행은 입력 B=1, 출력 B=0 이라 출력 칸을 읽으면 A·B 가 0 이 된다.
        t = _record(["A", "B", "D", "B"],
                    [["0", "0", "0", "0"], ["0", "1", "1", "1"],
                     ["1", "0", "1", "0"], ["1", "1", "0", "0"]],
                    source="derived (D = A⊕B ; B = A'·B)")
        st = nodes.stage_table(_circuit(["T9"], [("AB", "A·B", "U1 pin 3")]), _spec(t), "AB")
        self.assertEqual(st.inputs, ["A", "B"])
        self.assertEqual(st.rows[3], (["1", "1"], 1))

    def test_0_1_도_X_도_아닌_셀의_행은_뺀다(self):
        t = _record(["A", "B", "Y"], [["0", "?", "0"], ["1", "1", "1"]])
        st = nodes.stage_table(_circuit(["T9"], [("AB", "A·B", "U1 pin 3")]), _spec(t), "AB")
        self.assertEqual(st.rows, [(["1", "1"], 1)])

    def test_노드_표에_없는_이름은_ValueError(self):
        with self.assertRaisesRegex(ValueError, "L9"):
            nodes.stage_table(_circuit(["T9"], [("E'", "E'", "U4 pin 12")]),
                              _spec(self.MUX), "L9")

    def test_기록표에_없는_변수는_ValueError(self):
        with self.assertRaisesRegex(ValueError, "노드 Q"):
            nodes.stage_table(_circuit(["T9"], [("Q", "E·Q", "U1 pin 3")]),
                              _spec(self.MUX), "Q")

    def test_기록표가_없으면_ValueError(self):
        cap = SpecTable(id="T1", title="파형", kind="capture", encoding=None,
                        source="manual:p3", expected="계단", role="record",
                        header=[], rows=[], line=1)
        with self.assertRaisesRegex(ValueError, "기록표"):
            nodes.stage_table(_circuit(["T1"], [("Y", "A·B", "U1 pin 3")]), _spec(cap), "Y")


class TestStageNodesTable(unittest.TestCase):
    """여러 노드 × 그 노드들이 쓰는 입력의 합집합 — 단계 LED 점등 표의 계산(2026-10-11)."""

    def setUp(self):
        self.spec = parse_spec(E5_SPEC)
        net = parse_netlist(E5_NETLIST)
        self.c1, self.c2 = net.circuits[0], net.circuits[1]

    def test_입력은_합집합이고_행마다_노드별_비트다(self):
        t = nodes.stage_nodes_table(self.c1, self.spec, ["Y0", "Y1"])
        self.assertEqual(t.inputs, ["Bit3", "Bit2", "Bit1", "Bit0"])
        self.assertEqual(len(t.rows), 10)
        self.assertEqual(t.rows[0], (["0", "0", "0", "0"], [0, 1]))
        self.assertEqual(t.rows[1], (["0", "0", "0", "1"], [1, 0]))

    def test_다른_입력을_쓰는_노드를_섞으면_행을_합친다(self):
        t = nodes.stage_nodes_table(self.c2, self.spec, ["A3", "D0'"])
        self.assertEqual(t.inputs, ["D5", "D0"])
        self.assertEqual(sorted((tuple(c), tuple(b)) for c, b in t.rows),
                         [(("0", "0"), (0, 1)), (("0", "1"), (0, 0)), (("1", "0"), (1, 1))])

    def test_한_노드만_안_정해지면_그_칸만_None(self):
        # 합성 표: A=X 행에서 A·B 는 B=0 이면 0 으로 정해지고, A 자체는 안 정해진다
        t = SpecTable(id="T9", title="x", kind="truth-table", encoding="0/1", source=None,
                      expected=None, role="record", header=["A", "B", "Y"],
                      rows=[["X", "0", "0"]], line=1)
        c = _circuit(["T9"], [("A", "A", "p1"), ("AB", "A·B", "p2")])
        r = nodes.stage_nodes_table(c, _spec(t), ["A", "AB"])
        self.assertEqual(r.rows, [(["X", "0"], [None, 0])])


if __name__ == "__main__":
    unittest.main()
