"""7-Segment 표시기와 실험08 결선 — 그림의 넷이 netlist 표와 같은가.

R1~R15 는 꽂을 수 있는지를 본다. 7447 핀이 맞는 세그먼트로 가는지는 여기서 본다. 기대값은 netlist
`꼭 읽을 것` 표(교안 p16 핀표)와 U1·U2 표를 옮겼다.
"""
import tempfile
import unittest
from pathlib import Path

from tests._boards import ENGINE
from tests.test_breadboard_boards import _load


def _net_of(bb, label):
    return next((n['labels'] for n in bb.nets() if label in n['labels']), set())


def _resistor_bridges(bb, a, b):
    """라벨 a·b 가 330Ω 하나를 사이에 둔 두 넷에 있는가."""
    na, nb = _net_of(bb, a), _net_of(bb, b)
    for i, _r in enumerate(bb.resistors, 1):
        top, bottom = f'저항{i}(330Ω) 윗다리', f'저항{i}(330Ω) 아랫다리'
        if (top in na and bottom in nb) or (bottom in na and top in nb):
            return True
    return False


class Fixture:
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board(8)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.addClassCleanup(cls.tmp.cleanup)

    def render(self, fn):
        return fn(str(Path(self.tmp.name) / f'{fn.__name__}.png'))


class Chips(unittest.TestCase):
    def test_칩_표와_전원핀(self):
        mod = _load()
        self.assertEqual(mod.dip_pins('7490', strict=True), 14)
        self.assertEqual(mod.dip_pins('7447', strict=True), 16)
        self.assertEqual(mod.dip_power('7490'), (5, 10))
        self.assertEqual(mod.dip_power('7447'), (16, 8))


class Display(Fixture, unittest.TestCase):
    def setUp(self):
        self.bb = self.mod.BreadboardRenderer(board='v2')
        self.bb.enable_steps()
        self.bb.display_chain('FND 507', 28)

    def test_표시기는_칩이_아니다(self):
        self.assertEqual(self.bb.chips, [])
        self.assertEqual(self.bb.displays[0]['label'], 'FND 507')

    def test_핀은_왼쪽_위에서_돈다(self):
        pins = self.bb.displays[0]['pins']
        self.assertEqual(pins[1][2], 28)
        self.assertEqual(pins[5][2], 32)
        self.assertEqual(pins[6][2], 32)
        self.assertEqual(pins[10][2], 28)

    def test_배선은_몸통이_덮는_열에_꽂히지_않는다(self):
        covered = {'c', 'd', 'e', 'f', 'g', 'h'}
        for x, r in self.bb._leads:
            block, col, row = self.bb.sym(x, r)
            what = self.bb._leads[(x, r)]
            if block == 'right' and 28 <= row <= 32 and 'FND' not in what.split(' pin')[0]:
                self.assertNotIn(col, covered, what)

    def test_세그먼트_끝_후보는_몸통_밖_행이다(self):
        for seg, holes in self.bb.seg_ends.items():
            self.assertTrue(holes, seg)
            self.assertFalse([r for _x, r in holes if 28 <= r <= 32], seg)

    def test_몸통_위_선은_R15(self):
        y = self.bb.r_y(30)
        self.bb.step_wire([(self.bb.cols['right']['a'], y), (self.bb.cols['right']['j'], y)], 'gnd', '가로지르는 선')
        self.assertIn('가로지르는 선', self.bb.wires_over_display())

    def test_세그먼트_저항은_색띠가_보인다(self):
        for seg, (pin, col, far) in self.mod.DISPLAYS['FND 507']['segments'].items():
            x = self.bb.cols['right'][col]
            row = self.mod._dip_pin_row(28, pin, 10)
            ymid = (self.bb.r_y(row) + self.bb.r_y(28 + far)) // 2
            band = self.bb.overlay.getpixel((x * self.mod.SCALE, (ymid - 7) * self.mod.SCALE))
            self.assertEqual(band[:3], (204, 85, 0), seg)

    def test_세그먼트_글자는_표준_배지다(self):
        names = [n for n, _box, _seg in self.bb.tag_boxes]
        self.assertEqual(sorted(names), list('abcdefg'))

    def test_표시기가_없으면_도장_키가_없다(self):
        bb = self.mod.BreadboardRenderer(board='v2')
        self.assertNotIn('displays', bb.wiring())
        self.assertNotIn('displays', bb.snapshot())
        self.assertIn('displays', self.bb.wiring())


class E8Nets(Fixture, unittest.TestCase):
    def test_C4_세그먼트_사슬은_핀표대로다(self):
        bb = self.render(self.board.build_e8_driver)
        s2 = self.board.LAYOUT['slots']['S2']
        for out, fnd in ((13, 7), (12, 6), (11, 4), (10, 2), (9, 1), (15, 9), (14, 10)):
            self.assertTrue(_resistor_bridges(bb, f'7447#{s2} pin {out}', f'FND 507 pin {fnd}'), (out, fnd))
            self.assertFalse(_net_of(bb, f'7447#{s2} pin {out}') & {f'FND 507 pin {fnd}'}, '330Ω 없이 이어졌다')

    def test_FND_공통_애노드는_VCC고_소수점은_비운다(self):
        # 2026-11-06 조교 공지 `_356971_1`: VCC → 3·8번(Common Anode), 5번(DP)은 사용하지 않는다
        bb = self.render(self.board.build_e8_fnd)
        for pin in (3, 8):
            net = next(n for n in bb.nets() if f'FND 507 pin {pin}' in n['labels'])
            self.assertEqual(net['rails'], {'vcc'}, pin)
        dp = [n for n in bb.nets() if 'FND 507 pin 5' in n['labels']]
        self.assertFalse(any(n['rails'] for n in dp), 'DP(pin 5)가 레일에 묶였다')

    def test_C5_는_7490_출력이_7447_입력에_닿는다(self):
        bb = self.render(self.board.build_e8_final)
        s1, s2 = self.board.LAYOUT['slots']['S1'], self.board.LAYOUT['slots']['S2']
        for qa, inp, tag in ((12, 7, 'A'), (9, 1, 'B'), (8, 2, 'C'), (11, 6, 'D')):
            net = _net_of(bb, f'7490#{s1} pin {qa}')
            self.assertIn(f'7447#{s2} pin {inp}', net)
            self.assertIn(f'LED {tag} 애노드', net)
        self.assertEqual({i['name'] for i in bb.inputs}, {'R0', 'CLK'})
        self.assertIn(f'7490#{s1} pin 1', _net_of(bb, f'7490#{s1} pin 12'))
        self.assertEqual(bb.cross_side_wires(), [])

    def test_C1_게이트_입력은_교안_논리다(self):
        bb = self.render(self.board.build_e8_counter)
        s1, s2 = self.board.LAYOUT['slots']['S1'], self.board.LAYOUT['slots']['S2']
        ff, gate = f'74HC76#{s1}', f'74HC08#{s2}'
        a, an, b, bn = 15, 14, 11, 10
        for out, (x, y), tag in ((11, (an, bn), 'Y0'), (3, (a, bn), 'Y1'), (6, (an, b), 'Y2'), (8, (a, b), 'Y3')):
            ins = {11: (13, 12), 3: (1, 2), 6: (4, 5), 8: (9, 10)}[out]
            nets = {frozenset(_net_of(bb, f'{gate} pin {p}')) for p in ins}
            self.assertEqual(nets, {frozenset(_net_of(bb, f'{ff} pin {x}')), frozenset(_net_of(bb, f'{ff} pin {y}'))}, tag)
            self.assertIn(f'LED {tag} 애노드', _net_of(bb, f'{gate} pin {out}'))
        self.assertIn(f'{ff} pin 6', _net_of(bb, f'{ff} pin 15'))
        self.assertEqual(bb.cross_side_wires(), [])


if __name__ == '__main__':
    unittest.main()
