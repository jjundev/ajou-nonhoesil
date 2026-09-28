"""따라 그리기 층 — `BreadboardRenderer(layer=(lo, hi))` (2026-09-28 팀원 전달용).

완성본 빌더를 그대로 돌리되 번호 lo 앞은 회색·번호 없음, lo~hi 는 색·원래 번호,
hi 뒤는 안 보인다. 점유표·결선 순서표는 층과 상관없이 완성본과 같아야 한다.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Layer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _jacks(self, layer=None):
        """전원 잭 두 가닥 — 1번 +5V, 2번 0V."""
        bb = self.mod.BreadboardRenderer(None, layer=layer)
        bb.enable_steps()
        bb.set_header('층', '테스트')
        bb.connect_jacks()
        return bb

    def _px(self, bb, n):
        """n 번 배선 첫 구간 가운데의 overlay 픽셀."""
        _kind, pts, _desc = bb._segments[n - 1]
        (x0, y0), (x1, y1) = pts[0], pts[1]
        s = self.mod.SCALE
        return bb.overlay.getpixel(((x0 + x1) // 2 * s, (y0 + y1) // 2 * s))

    def test_층_없으면_완성본과_같다(self):
        bb = self._jacks()
        self.assertIsNone(bb.layer)
        self.assertEqual(self._px(bb, 1), self.mod.WIRE['vcc'])
        self.assertEqual(self._px(bb, 2), self.mod.WIRE['gnd'])
        self.assertEqual(len(bb.marker_boxes), 2)

    def test_앞_층은_회색이고_번호가_없다(self):
        bb = self._jacks((2, 2))
        self.assertEqual(self._px(bb, 1), self.mod.KEEP)
        self.assertEqual(self._px(bb, 2), self.mod.WIRE['gnd'])
        self.assertEqual(len(bb.marker_boxes), 1)

    def test_뒤_층은_안_보인다(self):
        bb = self._jacks((1, 1))
        self.assertEqual(self._px(bb, 1), self.mod.WIRE['vcc'])
        self.assertEqual(self._px(bb, 2)[3], 0)
        self.assertEqual(len(bb.marker_boxes), 1)

    def test_번호는_완성본_그대로(self):
        full, part = self._jacks(), self._jacks((2, 2))
        self.assertEqual([s['n'] for s in part.steps], [1, 2])
        self.assertEqual(part.sidecar()['steps'], full.sidecar()['steps'])

    def test_뒤_배선도_점유표에_남는다(self):
        full, part = self._jacks(), self._jacks((1, 1))
        self.assertEqual(set(part._leads), set(full._leads))
        self.assertEqual(part._passed, full._passed)

    def _unused(self, layer=None):
        """잭 두 가닥(1·2번) + 74HC04 미사용 입력 pin 1·3 접지(3번, 두 가닥이 번호 하나)."""
        bb = self._jacks(layer)
        bb.draw_chip('74HC04', 10)
        bb.connect_unused_inputs([1, 3], 10, chip='74HC04')
        return bb

    def _unused_px(self, bb):
        _kind, pts, _desc = next(seg for seg in bb._segments if '미사용 입력' in seg[2])
        (x0, y0), (x1, y1) = pts[0], pts[1]
        s = self.mod.SCALE
        return bb.overlay.getpixel(((x0 + x1) // 2 * s, (y0 + y1) // 2 * s))

    def test_미사용_입력선도_층을_따른다(self):
        self.assertEqual(self._unused_px(self._unused()), self.mod.WIRE['gnd'])
        self.assertEqual(self._unused_px(self._unused((3, 3))), self.mod.WIRE['gnd'])
        self.assertEqual(self._unused_px(self._unused((4, 4))), self.mod.KEEP)
        self.assertEqual(self._unused_px(self._unused((1, 2)))[3], 0)

    def test_미사용_입력선도_점유표에_남는다(self):
        full, part = self._unused(), self._unused((1, 2))
        self.assertEqual(set(part._leads), set(full._leads))
        self.assertEqual(part.sidecar()['steps'], full.sidecar()['steps'])

    def test_잘못된_층은_거절한다(self):
        for bad in [(0, 1), (3, 2), (1.0, 2), (1,)]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.mod.BreadboardRenderer(None, layer=bad)

    def test_기준선과_층은_함께_못_준다(self):
        base = self._jacks().snapshot()
        with self.assertRaises(ValueError):
            self.mod.BreadboardRenderer(None, baseline=base, layer=(1, 1))

    def test_도장은_층을_담는다(self):
        self.assertNotIn('layer', self._jacks().content())
        self.assertEqual(self._jacks((1, 2)).content()['layer'], [1, 2])


if __name__ == "__main__":
    unittest.main()
