"""눕혀 꽂는 풀업 저항(`pull_up`) — 실험09 `74HC03` 열린 드레인 출력(2026-11-09).

세로 저항(`draw_resistor`)은 한 열 두 행만 이어 핀 스트립과 레일을 못 잇는다. `pull_up` 은 핀 스트립
홀에서 가까운 +5V 레일 홀로 가로로 눕힌다. 넷 모형이 저항을 단락으로 보지 않는지, 기준선에서
회색이 되는지, 그 위를 지나는 선을 R15 가 막는지 본다.
"""
import importlib.util
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


K = 10


class PullUp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self, baseline=None):
        bb = self.mod.BreadboardRenderer(board='v2', baseline=baseline)
        bb.enable_steps()
        bb.partial = True
        bb.draw_chip('74HC03', K)
        bb.connect_jacks()
        bb.connect_rail_bridges({'bridge': [40, 41], 'bridge_policy': 'lower-clearance-v1'})
        bb.connect_power(K)
        L = bb.cols['left']
        bb.pull_up(L['a'], K + 2, 'U3 pin 3')
        bb.pull_up(L['j'], K + 3, 'U3 pin 11')
        return bb

    def test_레일_홀까지_눕혀_꽂고_기록한다(self):
        bb = self.board()
        bb.verify()
        self.assertEqual(bb.pullups, [
            {'label': '10kΩ', 'top': ('left', 'a', K + 2), 'bottom': ('left', 'vcc', K + 2)},
            {'label': '10kΩ', 'top': ('left', 'j', K + 3), 'bottom': ('left', 'mid_vcc', K + 3)}])
        self.assertEqual(bb.resistors, bb.pullups)
        self.assertEqual(sum('풀업' in s['desc'] for s in bb.steps), 2)

    def test_가운데_GND_홀은_몸통_아래라_찬_홀이다(self):
        bb = self.board()
        x_gnd = bb.cols['left']['mid_gnd']
        self.assertIn((x_gnd, K + 3), bb._passed)

    def test_저항은_넷을_잇지_않는다(self):
        bb = self.board()
        pin3 = next(n for n in bb.nets() if '74HC03#10 pin 3' in n['labels'])
        self.assertNotIn('vcc', pin3['rails'])

    def test_기준선에_같은_풀업이면_번호가_없다(self):
        first = self.board()
        again = self.board(baseline=first.snapshot())
        self.assertFalse(any('풀업' in s['desc'] for s in again.steps))
        self.assertEqual(sum('풀업' in k for k in again.kept), 2)

    def test_빠진_풀업은_걷기_줄에_나온다(self):
        first = self.board()
        bb = self.mod.BreadboardRenderer(board='v2', baseline=first.snapshot())
        bb.enable_steps()
        self.assertTrue(any('풀업' in line and '뽑는다' in line for line in bb.removed()))

    def test_몸통_위를_지나는_선은_R15_가_막는다(self):
        bb = self.board()
        L = bb.cols['left']
        y0, y1 = bb.r_y(K - 1), bb.r_y(K + 4)
        bb.step_wire([(L['b'], y0), (236, y0), (236, y1), (L['b'], y1)], 'sig', '풀업 위를 지나는 선')
        with self.assertRaises(AssertionError) as cm:
            bb.verify()
        self.assertIn('R15', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
