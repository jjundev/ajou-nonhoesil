"""손그림 모사 — 완성본 배선을 마커로 그은 것처럼 흔들어 그린다(2026-10-12 시험판).

흔들림은 그리기에만 걸리고 점유표·순서표·`verify()` 는 평소와 같아야 한다.
"""
import importlib.util
import random
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HandPolyline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _pts(self, seed=7):
        pts = [(100.0, 50.0), (100.0, 300.0), (400.0, 300.0)]
        return pts, self.mod._hand_polyline(pts, random.Random(seed))

    def test_끝점은_그대로다(self):
        pts, out = self._pts()
        self.assertEqual(out[0], pts[0])
        self.assertEqual(out[-1], pts[-1])

    def test_진폭은_2px_를_안_넘는다(self):
        # 원 경로(두 축 정렬 구간) 위 가장 가까운 점까지 축별 거리
        _, out = self._pts()
        for x, y in out:
            d = min(max(abs(x - 100), max(0, 50 - y, y - 300)),
                    max(abs(y - 300), max(0, 100 - x, x - 400)))
            self.assertLessEqual(d, 2.0 + 1e-9)

    def test_실제로_흔들린다(self):
        _, out = self._pts()
        self.assertTrue(any(abs(x - 100) > 0.5 for x, y in out if 80 < y < 280))

    def test_같은_시드는_같은_점(self):
        self.assertEqual(self._pts(3)[1], self._pts(3)[1])
        self.assertNotEqual(self._pts(3)[1], self._pts(4)[1])

    def test_짧은_선도_된다(self):
        out = self.mod._hand_polyline([(10.0, 10.0), (13.0, 10.0)], random.Random(1))
        self.assertEqual((out[0], out[-1]), ((10.0, 10.0), (13.0, 10.0)))

    def test_굵기는_0_7_에서_1_3_배(self):
        ws = {self.mod._hand_width(3, random.Random(s)) for s in range(200)}
        self.assertTrue(ws <= {2, 3, 4} and len(ws) > 1)
        self.assertGreaterEqual(self.mod._hand_width(1, random.Random(0)), 1)

    def test_도트는_반지름_1px_안에서_찌그러진다(self):
        boxes = [self.mod._hand_dot((50.0, 60.0), 3, random.Random(s)) for s in range(50)]
        for x0, y0, x1, y1 in boxes:
            self.assertAlmostEqual((x0 + x1) / 2, 50.0)
            self.assertAlmostEqual((y0 + y1) / 2, 60.0)
            self.assertTrue(2 <= (x1 - x0) / 2 <= 4 and 2 <= (y1 - y0) / 2 <= 4)
        self.assertGreater(len({tuple(b) for b in boxes}), 1)


if __name__ == "__main__":
    unittest.main()
