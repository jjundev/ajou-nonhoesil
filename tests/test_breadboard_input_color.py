"""입력 점퍼선은 입력 배지와 같은 보라(`INPUT`)로 그린다. kind 는 'sig' 그대로다(2026-10-06)."""
import importlib.util
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')

INPUT = (110, 40, 160, 255)
BLACK = (25, 25, 25, 255)


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pixel_on(bb, seg_index, t=0.75):
    """구간 `seg_index` 의 첫 두 점 사이 t 지점의 overlay 픽셀. 좌표는 템플릿 기준이라 배율을 곱한다."""
    _kind, pts, _d = bb._segments[seg_index]
    (x0, y0), (x1, y1) = pts[0], pts[1]
    k = bb.overlay.size[0] / bb.base_im.size[0]
    x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    return bb.overlay.getpixel((round(x * k), round(y * k)))


class InputWireColor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self, **kw):
        bb = self.mod.BreadboardRenderer(board='v1', **kw)
        bb.enable_steps()
        return bb

    def test_입력_점퍼는_보라다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        self.mod._input_jumper(bb, bb.cols['left'], 10, 'A', '74HC08 pin 1')
        i = next(i for i, s in enumerate(bb._segments) if '입력 A' in s[2])
        self.assertEqual(_pixel_on(bb, i), INPUT)

    def test_다른_신호선은_검정_그대로다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(20)), (c['a'], bb.r_y(25))], 'sig', '출력 시험')
        self.assertEqual(_pixel_on(bb, len(bb._segments) - 1), BLACK)

    def test_입력_점퍼의_kind_는_sig_다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        self.mod._input_jumper(bb, bb.cols['left'], 10, 'A', '74HC08 pin 1')
        seg = next(s for s in bb._segments if '입력 A' in s[2])
        self.assertEqual(seg[0], 'sig')
        step = next(s for s in bb.steps if '입력 A' in s['desc'])
        self.assertEqual(step['kind'], 'sig')

    def test_기준선의_입력_점퍼는_회색이다(self):
        first = self.board()
        first.draw_chip('74HC08', 10)
        self.mod._input_jumper(first, first.cols['left'], 10, 'A', '74HC08 pin 1')
        base = first.snapshot()
        bb = self.board(baseline=base)
        bb.draw_chip('74HC08', 10)
        self.mod._input_jumper(bb, bb.cols['left'], 10, 'A', '74HC08 pin 1')
        i = next(i for i, s in enumerate(bb._segments) if '입력 A' in s[2])
        self.assertEqual(_pixel_on(bb, i), self.mod.KEEP)


if __name__ == '__main__':
    unittest.main()
