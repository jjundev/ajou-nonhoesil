"""DIP-16 칩과 Negative Logic LED — 그리기·배선기 단위 시험.

설계: docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md
배치기 시험은 `test_breadboard_place.py` 의 `Dip16Place`, 시험판은 `test_breadboard_v2_e5_trial.py`.
"""
import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _board(mod, **kw):
    bb = mod.BreadboardRenderer(None, board='v2', **kw)
    bb.enable_steps()
    return bb


class PinGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_DIP14_는_그대로(self):
        rows = [self.mod._dip_pin_row(10, p) for p in range(1, 15)]
        self.assertEqual(rows, [10, 11, 12, 13, 14, 15, 16, 16, 15, 14, 13, 12, 11, 10])
        self.assertEqual([self.mod._dip_side(p) for p in (7, 8)], ['a', 'f'])

    def test_DIP16_핀_행과_쪽(self):
        rows = [self.mod._dip_pin_row(10, p, 16) for p in range(1, 17)]
        self.assertEqual(rows, [10, 11, 12, 13, 14, 15, 16, 17, 17, 16, 15, 14, 13, 12, 11, 10])
        self.assertEqual([self.mod._dip_side(p, 16) for p in (8, 9)], ['a', 'f'])

    def test_칩_모델_표(self):
        self.assertEqual(self.mod.dip_pins('74HC42'), 16)
        self.assertEqual(self.mod.dip_pins('74HC08'), 14)
        self.assertEqual(self.mod.dip_pins('74HC9999'), 14)       # 그리기는 v1 호환으로 14
        with self.assertRaisesRegex(ValueError, 'DIP_PINS'):
            self.mod.dip_pins('74HC9999', strict=True)


class DrawDip16(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.bb = _board(cls.mod)
        cls.bb.draw_chip('74HC42', 10)
        cls.bb.connect_power(10, gnd_col='a')
        cls.L = cls.bb.cols['left']

    def half(self, r):
        """행 r 과 r+1 사이 반 행의 y."""
        return (self.bb.r_y(r) + self.bb.r_y(r + 1)) / 2

    def test_핀_16개가_e_f_열_8행에(self):
        ch = self.bb.chips[-1]
        self.assertEqual(sorted(ch['pins']), list(range(1, 17)))
        self.assertEqual(ch['pins'][8], self.bb.sym(self.L['e'], 17))
        self.assertEqual(ch['pins'][9], self.bb.sym(self.L['f'], 17))
        self.assertEqual(ch['pins'][16], self.bb.sym(self.L['f'], 10))
        self.assertEqual(set(ch), {'label', 'block', 'pin1_row', 'pins'})   # wiring() → 도장

    def test_몸통은_pin_1_행부터_pin_8_행까지(self):
        (box, _x, _ch), = self.bb._chip_bodies()
        self.assertEqual(box[1], self.bb.r_y(10) - 10)
        self.assertEqual(box[3], self.bb.r_y(17) + 10)

    def test_이름_상자는_가운데_반_행_하나만_막는다(self):
        """74HC42 는 a쪽 출력 일곱이 다 LED 로 건넌다 — 건널 반 행 9개 중 이름이 하나만 막아야
        핀마다 하나씩 남는다(설계 #5)."""
        (box, _ch), = self.bb.chip_label_boxes
        self.assertLessEqual(box[3] - box[1], 2 * self.bb.spec.row_pitch - 4)
        xa, xb = self.L['d'], self.L['g']
        free = [r for r in range(9, 17)
                if not self.bb._seg_in_box((xa, self.half(r)), (xb, self.half(r)), box)]
        self.assertEqual(free, [9, 10, 11, 12, 14, 15, 16])

    def test_DIP14_이름_글꼴은_그대로(self):
        bb = _board(self.mod)
        bb.draw_chip('74HC20', 10)
        (box, _ch), = bb.chip_label_boxes
        lb = bb.font_chip.getbbox('74HC20')
        self.assertAlmostEqual(box[3] - box[1], lb[2] - lb[0] + 4)

    def test_모르는_이름은_14핀으로_그린다(self):
        bb = _board(self.mod)
        bb.draw_chip('74HCXX', 10)
        self.assertEqual(len(bb.chips[-1]['pins']), 14)

    def test_전원은_pin_16_과_pin_8(self):
        segs = {d: pts for _k, pts, d in self.bb._segments}
        vcc, gnd = segs['pin 16 -> +5V 레일'], segs['pin 8 -> GND 레일']
        self.assertEqual(vcc[0], (self.L['g'], self.bb.r_y(10)))
        self.assertEqual(vcc[-1][0], self.L['mid_vcc'])
        self.assertEqual(gnd[0], (self.L['a'], self.bb.r_y(17)))
        self.assertEqual(gnd[-1][0], self.L['gnd'])

    def test_칩보다_전원을_먼저_부르면_경고(self):
        bb = _board(self.mod)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            bb.connect_power(10)
        self.assertIn('[WARN]', err.getvalue())
        self.assertIn('pin 14 -> +5V 레일', [d for _k, _p, d in bb._segments])

    def test_미사용_입력_행은_16핀_기준(self):
        bb = _board(self.mod)
        bb.draw_chip('74HC42', 10)
        bb.connect_unused_inputs([13], 10, chip='74HC42', bridge_row=30)    # pin 13 = 행 13, f쪽
        (pts,) = [pts for _k, pts, d in bb._segments if 'pin 13' in d]
        self.assertEqual(pts[0], (bb.cols['left']['g'], bb.r_y(13)))

    def test_칩_쪽_판정과_리드_수는_8행까지(self):
        end = ('hole', self.bb.sym(self.L['b'], 17))
        self.assertEqual(self.bb.chip_side_of(end)['side'], 'a')
        a_side = next(s for s in self.bb.side_leads() if s['side'] == 'a')
        self.assertIn(self.bb.addr(self.L['a'], self.bb.r_y(17)), a_side['addrs'])   # pin 8 GND 점퍼


if __name__ == '__main__':
    unittest.main()
