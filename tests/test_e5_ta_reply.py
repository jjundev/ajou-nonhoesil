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


if __name__ == "__main__":
    unittest.main()
