"""`## 노드` 표 × 기록 진리표 → 노드 기대값. 설계: docs/plans/2026-09-20-중간노드-기대값표-설계.md"""

import unittest
from pathlib import Path

from scripts.lab import config, nodes
from scripts.lab.netlist_parser import NetlistSection
from scripts.lab.spec_parser import LabSpec, SpecTable, parse_spec

ROOT = Path(__file__).resolve().parents[1]
WEEK2_SPEC = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"


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


if __name__ == "__main__":
    unittest.main()
