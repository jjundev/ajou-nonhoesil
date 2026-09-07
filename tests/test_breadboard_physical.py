"""결선도가 **그림대로 꽂히는가**를 렌더러가 내보내기 전에 증명하는지 검사한다.

2026-09-07 에 발견: 입력 A·B·C 가 보드 밖 x=95 허공에서 출발하고 있었다.
`addr()` 이 그 자리에 '보드밖(입력)' 이라는 이름을 붙여 주었고, `verify()` 는
docstring 과 달리 레일 끝점의 빈 행만 봤다. 그림도 순서표도 멀쩡해 보였다 —
따라 그리던 사람이 왼쪽 끝을 어디에 꽂아야 할지 몰라서 걸렸다.

합성 보드에 배선 한두 줄을 그리고 `verify()` 만 부른다. 파일을 쓰지 않아
빠르고, 어느 규칙이 잡았는지 메시지로 확인한다.
"""
import importlib.util
import inspect
import os
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PhysicalRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    # ---- R1. 모든 끝점은 홀이다 ----

    def test_허공에서_출발한_배선은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(95, bb.r_y(10)), (c['b'], bb.r_y(10))], 'sig', '입력 A')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다.*보드밖'):
            bb.verify()

    def test_레일_빈_행에_꽂은_끝점은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['gnd'], bb.r_y(14)), (c['b'], bb.r_y(14))], 'sig', '입력 C')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다.*GND레일14행'):
            bb.verify()

    def test_전원잭은_보드_밖이어도_된다(self):
        bb = self.board()
        bb.connect_jacks()
        bb.verify()

    # ---- R2. 한 홀에 리드 하나 ----

    def test_한_홀에_배선_둘은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], 'mid', '1단 -> 2단')
        bb.step_wire([(c['c'], bb.r_y(12)), (c['a'], bb.r_y(12))], 'mid', '갈래')
        with self.assertRaisesRegex(AssertionError, '한 홀에 리드 둘.*좌 c12'):
            bb.verify()

    def test_레일_홀이_차면_가까운_빈_홀로_옮긴다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.lead(c['gnd'], bb.r_y(7), '먼저 꽂힌 것')
        # 8행은 빈 행이고 7행은 찼다 -> 9행
        self.assertEqual(bb.free_rail_row(8, c['gnd']), 9)
        self.assertEqual(bb.free_rail_row(10, c['gnd']), 10)
        # 두 열을 같이 주면 둘 다 비어야 한다
        bb.lead(c['mid_gnd'], bb.r_y(31), '브리지 끝')
        self.assertEqual(bb.free_rail_row(31, c['mid_gnd'], c['mid_vcc']), 30)

    # ---- R2. 부품 다리와 칩 핀도 홀을 차지한다 ----

    def test_칩_핀_홀에_배선을_꽂으면_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        bb.step_wire([(c['f'], bb.r_y(10)), (c['mid_vcc'], bb.r_y(10))], 'vcc', 'pin 14')
        with self.assertRaisesRegex(AssertionError, '한 홀에 리드 둘.*74HC08 pin 14'):
            bb.verify()

    def test_LED_사슬은_다리마다_다른_홀을_쓴다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], 'sig', '출력 -> L2')
        bb.led_chain(c['c'], 24, 'L2', '최종 출력')
        bb.verify()
        self.assertEqual(bb._leads[(c['c'], 24)], '신호 배선 · 출력 -> L2')
        self.assertEqual(bb._leads[(c['d'], 24)], 'L2 LED 애노드')
        self.assertEqual(bb._leads[(c['d'], 25)], 'L2 LED 캐소드')
        self.assertEqual(bb._leads[(c['e'], 25)], '330Ω 윗다리')
        self.assertEqual(bb._leads[(c['e'], 27)], '330Ω 아랫다리')
        # GND 점퍼는 레일 쪽 끝 홀(c27)에서. LED 열(d27)에서 뽑으면 레일로 가는 길에
        # 다른 다리 위를 지나진 않지만, 레일 쪽 끝이 항상 아무것도 안 넘는 자리다
        self.assertIn((c['c'], 27), bb._leads)
        self.assertNotIn((c['d'], 27), bb._leads)

    def test_오른쪽_끝_열의_LED_사슬은_왼쪽으로_자란다(self):
        bb = self.board()
        c = bb.cols['right']
        bb.step_wire([(c['d'], bb.r_y(12)), (c['d'], bb.r_y(22))], 'sig', 'pin 3 -> X')
        bb.led_chain(c['d'], 22, 'X', 'X 출력', block='right')
        bb.verify()
        self.assertEqual(bb._leads[(c['c'], 22)], 'X LED 애노드')
        self.assertEqual(bb._leads[(c['b'], 23)], '330Ω 윗다리')
        # 왼쪽으로 자란 사슬의 GND 점퍼는 저항 너머(a25)에서 — c25 나 d25 에서 뽑으면
        # 레일(542, 왼쪽)로 가는 가로선이 저항 아랫다리 b25 위를 지난다
        self.assertIn((c['a'], 25), bb._leads)
        self.assertNotIn((c['c'], 25), bb._leads)


if __name__ == '__main__':
    unittest.main()
