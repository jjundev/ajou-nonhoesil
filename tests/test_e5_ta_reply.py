"""실험05 조교 회신(2026-10-05) 반영 검사 — T1 은 BCD 0~9 열 행, 10~15 는 선택 확인."""

import unittest
from pathlib import Path

from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
E5 = ROOT / "보고서" / "실험05"


def _t1():
    spec = parse_spec(E5 / "체크리스트" / "명세.md")
    return next(t for t in spec.tables if t.id == "T1")


class TestT1Scope(unittest.TestCase):
    def test_T1_은_열_행이다(self):
        self.assertEqual(len(_t1().rows), 10)

    def test_입력은_BCD_0_9_순서다(self):
        got = ["".join(r[:4]) for r in _t1().rows]
        self.assertEqual(got, [f"{n:04b}" for n in range(10)])

    def test_행마다_그_수의_출력_하나만_0이다(self):
        for n, row in enumerate(_t1().rows):
            ys = row[4:]
            self.assertEqual(len(ys), 10)
            self.assertEqual([i for i, v in enumerate(ys) if v == "0"], [n], row)


class TestNetlistWording(unittest.TestCase):
    def setUp(self):
        self.text = (E5 / "결선도" / "netlist.md").read_text(encoding="utf-8")

    def test_C1_단계_확인에_열여섯_행이_남지_않는다(self):
        c1 = self.text.split("# C1 ·")[1].split("# C2 ·")[0]
        self.assertNotIn("열여섯", c1)

    def test_4단계는_10_15_를_선택_확인으로_안내한다(self):
        c1 = self.text.split("# C1 ·")[1].split("# C2 ·")[0]
        self.assertIn("선택", c1)
        self.assertIn("1010~1111", c1)

    def test_M4_M5_가_닫힘_표시다(self):
        self.assertIn("| ~~M4~~ |", self.text)
        self.assertIn("| ~~M5~~ |", self.text)


if __name__ == "__main__":
    unittest.main()
