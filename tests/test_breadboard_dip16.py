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
        self.assertEqual(self.mod.dip_pins('74HC76'), 16)
        self.assertEqual(self.mod.dip_power('74HC76'), (5, 13))
        self.assertEqual(self.mod.dip_power('74HC42'), (16, 8))
        self.assertEqual(self.mod.dip_power('74HC00'), (14, 7))
        self.assertEqual(self.mod.dip_pins('74HC08'), 14)
        self.assertEqual(self.mod.dip_pins('74HC9999'), 14)       # 그리기는 v1 호환으로 14
        with self.assertRaisesRegex(ValueError, 'DIP_PINS'):
            self.mod.dip_pins('74HC9999', strict=True)


class InnerPower(unittest.TestCase):
    """전원핀이 모서리가 아닌 칩 — 74HC76 VCC 5(a쪽)·GND 13(f쪽). 교안 p11 "GND와 Vcc 위치 유의"
    (실험06, 2026-10-11)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.bb = _board(cls.mod)
        cls.bb.draw_chip('74HC76', 10)
        cls.bb.connect_power(10)
        cls.L = cls.bb.cols['left']

    def test_pin_5_는_좌_바깥_VCC_pin_13_은_가운데_GND(self):
        segs = {d: pts for _k, pts, d in self.bb._segments}
        vcc, gnd = segs['pin 5 -> +5V 레일'], segs['pin 13 -> GND 레일']
        self.assertEqual(vcc[0], (self.L['d'], self.bb.r_y(14)))
        self.assertEqual(vcc[-1][0], self.L['vcc'])
        self.assertEqual(gnd[0], (self.L['g'], self.bb.r_y(13)))
        self.assertEqual(gnd[-1][0], self.L['mid_gnd'])

    def test_모서리_핀은_비워_둔다(self):
        self.assertNotIn((self.L['g'], 10), self.bb._leads)     # pin 16 = K, 전원 아님
        self.assertNotIn((self.L['d'], 17), self.bb._leads)     # pin 8 = 2CLR


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

    def test_16핀_VCC_번호_원은_pin_1_의_반_행을_비운다(self):
        """a쪽 pin 1 이 LED 로 건널 반 행은 k−0.5 하나뿐이다(설계 #5). pin 16 전원선 번호 원이 그 반 행
        위(기본 자리 = 선 11px 위)에 앉으면 가운데 여백으로 못 간다 — 2026-10-05 e5 시험판 Y0 경로 없음."""
        y = self.half(9)
        hit = [m for m in self.bb.marker_boxes + self.bb._marker_slots
               if m[0] - 1 < 656 and m[2] + 1 > self.L['d'] and m[1] - 1 < y < m[3] + 1]
        self.assertEqual(hit, [])

    def test_v1_은_빈_소켓_전원에_경고하지_않는다(self):
        """v1 승인 빌더(실험01~03)는 뒤 단계에 꽂을 칩의 전원을 먼저 깐다 — 고칠 수 없는 빌더에 경고를
        내지 않는다(2026-10-05 최종 검토)."""
        bb = self.mod.BreadboardRenderer(None, board='v1')
        bb.enable_steps()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            bb.connect_power(10)
        self.assertNotIn('[WARN]', err.getvalue())

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


class RouterDip16(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_끝_홀은_16핀_기하(self):
        bb = _board(self.mod)
        bb.draw_chip('74HC42', 10)
        L = bb.cols['left']
        self.assertEqual(self.mod._end_holes(bb, {'U1': 10}, ('U1', 9)),
                         [(L[c], bb.r_y(17)) for c in 'ghij'])
        self.assertEqual(self.mod._end_holes(bb, {'U1': 10}, ('U1', 8)),
                         [(L[c], bb.r_y(17)) for c in 'abcd'])

    def test_a쪽_가운데_아래_핀은_아래_반_행으로_건넌다(self):
        """pin 5(행 14)의 위 반 행 13.5 는 이름 상자가 막는다 — 아래 14.5 로 건너야 한다."""
        def fixed(bb, stage, superset=False):
            bb.draw_chip('74HC42', 10)
            bb.led_chain(bb.cols['right']['a'], 21, 'Y4', '시험', block='right')

        (path, _m), = self.mod.route_plan(fixed, {'U1': 10},
                                          [(1, None, 'sig', ('U1', 5), ('LED', 21), 'Y4')])
        bb = _board(self.mod)
        self.assertEqual(path[1][1], (bb.r_y(14) + bb.r_y(15)) / 2)


class NegativeLed(unittest.TestCase):
    """출력 0 에서 켜지는 LED(교안 실험5 p9) — 신호 → 330Ω → LED(캐소드 → 애노드) → +5V."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.bb = _board(cls.mod)
        cls.R = cls.bb.cols['right']
        cls.bb.led_chain(cls.R['a'], 10, 'Y0', '시험', block='right', active_low=True)
        cls.ch = cls.bb.led_chains[-1]

    def test_저항이_신호_옆_LED_가_그다음(self):
        s, R = self.bb.sym, self.R
        self.assertEqual(self.ch['signal'], s(R['a'], 10))
        self.assertEqual(self.ch['res_top'], s(R['b'], 10))
        self.assertEqual(self.ch['res_bottom'], s(R['b'], 12))
        self.assertEqual(self.ch['cathode'], s(R['c'], 12))
        self.assertEqual(self.ch['anode'], s(R['c'], 13))
        self.assertIs(self.ch['active_low'], True)

    def test_애노드_줄에서_가운데_VCC_로(self):
        (kind, pts), = [(k, p) for k, p, d in self.bb._segments if d == 'Y0 LED 애노드 -> +5V']
        self.assertEqual(kind, 'vcc')
        self.assertEqual(pts[0], (self.R['a'], self.bb.r_y(13)))
        self.assertEqual(pts[-1], (self.R['mid_vcc'], self.bb.r_y(13)))

    def test_넷은_신호_저항_캐소드_애노드_VCC(self):
        nets = self.bb.nets()

        def net_of(label):
            return next(n for n in nets if label in n['labels'])
        self.assertIn('vcc', net_of('LED Y0 애노드')['rails'])
        self.assertIs(net_of('LED Y0 캐소드'), net_of('저항1(330Ω) 아랫다리'))

    def test_순서표_사슬_줄에_0_이면_켜짐(self):
        self.assertTrue(any('0 이면 켜짐' in st['desc'] for st in self.bb.steps))

    def test_보통_사슬은_키가_그대로(self):
        bb = _board(self.mod)
        bb.led_chain(self.R['a'], 10, 'Y0', '시험', block='right')
        self.assertEqual(set(bb.led_chains[-1]),
                         {'tag', 'signal', 'anode', 'cathode', 'res_top', 'res_bottom'})

    def test_뽑는_Negative_사슬은_윗행부터_아랫행까지_적는다(self):
        """사슬 걷기 줄은 사슬이 차지하는 위·아래 끝 홀이다. Negative 는 맨 위가 330Ω 윗다리(b 윗행),
        맨 아래가 LED 애노드(c 윗행+3)다 — 보통 사슬 열쇠 순서(애노드~저항 아랫다리)로 읽으면 c13~b12 가
        된다(2026-10-05 최종 검토)."""
        bb = _board(self.mod, baseline=self.bb.snapshot())
        (line,) = [s for s in bb.removed() if 'LED Y0 사슬' in s]
        self.assertIn('b10~', line)
        self.assertIn('c13)', line)

    def test_기준선의_Negative_사슬은_그대로(self):
        """다음 단계 그림에서 같은 사슬은 회색·번호 없음이다 — 열쇠가 극성 따라 어긋나면 매 단계
        새로 꽂으라고 나온다."""
        snap = self.bb.snapshot()
        bb = _board(self.mod, baseline=snap)
        bb.led_chain(self.R['a'], 10, 'Y0', '시험', block='right', active_low=True)
        self.assertFalse(any('0 이면 켜짐' in st['desc'] for st in bb.steps))
        self.assertTrue(any('0 이면 켜짐' in k for k in bb.kept))


if __name__ == '__main__':
    unittest.main()
