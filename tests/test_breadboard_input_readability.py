"""입력 점퍼 읽기 규칙 R16·R17 과 배지 예약(`reserve_badges`) — 2026-11-09 실험09 C2(74670).

R16: 레일 빈 행(8·14·20…) 때문에 `free_rail_row` 가 입력 점퍼의 레일 끝을 다른 행으로 밀면 점퍼가 사선이
되고, 이웃 입력과 X자로 엇갈려도 `verify()` 가 통과했다.

R17: 가운데 레일 입력의 번호 원은 제 배지 위 18px 에 앉고 **이미 그린** 배지만 비켜, f쪽 입력을 아래 행부터
그리면 원이 위 이웃의 배지를 덮었다. 배지 검사는 가독성 시험(`_badge_hits`)에만 있었다. 이제 엔진이 다 그린
뒤에 보고, 빌더가 앞 판의 배지 자리를 예약하면 그리는 순서와 무관하게 비킨다.
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


K = 10     # 칩 pin 1 행. 14행이 레일 빈 행이라 pin 5(a쪽)·pin 10(f쪽) 입력의 레일 끝이 밀린다


class InputReadability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self, inputs, side, reserve=None, board='v2'):
        bb = self.mod.BreadboardRenderer(board=board)
        bb.enable_steps()
        bb.partial = True
        if reserve is not None:
            bb.reserve_badges(reserve)
        bb.draw_chip('74HC00', K)
        L = bb.cols['left']
        for row, name in inputs:
            self.mod._input_jumper(bb, L, row, name, f'pin {row}', side=side,
                                   col='j' if side == 'f' else 'b')
        return bb

    def problems(self, bb):
        try:
            bb.verify()
        except AssertionError as e:
            return str(e)
        return ''

    def test_R16_밀린_레일_끝이_이웃_점퍼와_엇갈리면_멈춘다(self):
        # 13·15행이 제 레일 행을 먼저 차지해 14행 입력의 레일 끝이 12행으로 밀린다 — 13행 점퍼를 가로지른다
        bb = self.board([(K + 3, 'A'), (K + 5, 'B'), (K + 4, 'C')], 'a')
        self.assertEqual(bb.r_y(K + 2), bb._segments[bb.inputs[2]['seg']][1][0][1])
        msg = self.problems(bb)
        self.assertIn('R16', msg)
        self.assertIn('A(', msg)
        self.assertIn('C(', msg)

    def test_R16_나란한_사선은_엇갈림이_아니다(self):
        bb = self.board([(K + 3, 'A'), (K + 4, 'C'), (K + 5, 'B')], 'a')
        self.assertEqual(bb.input_crossings(), [])
        self.assertEqual(self.problems(bb), '')

    def test_R16_끝점_맞닿음은_엇갈림이_아니다(self):
        seg = self.mod.BreadboardRenderer._segs_cross
        self.assertTrue(seg((0, 0), (10, 10), (0, 10), (10, 0)))
        self.assertFalse(seg((0, 0), (10, 10), (10, 10), (20, 0)))   # 끝점을 나눠 쓴다
        self.assertFalse(seg((0, 0), (10, 0), (5, 0), (15, 0)))      # 한 직선 위 — R4 몫
        self.assertFalse(seg((0, 0), (10, 0), (5, 0), (5, 10)))      # T자 — 한쪽 끝이 다른 선 위

    def test_v1_은_소급하지_않는다(self):
        bb = self.board([(K + 3, 'A'), (K + 5, 'B'), (K + 4, 'C')], 'a', board='v1')
        self.assertFalse(bb.spec.readability)
        self.assertNotIn('R16', self.problems(bb))

    def test_R17_f쪽_입력을_아래_행부터_그리면_배지가_가려져_멈춘다(self):
        bb = self.board([(K + 2, 'X'), (K + 1, 'Y')], 'f')
        msg = self.problems(bb)
        self.assertIn('R17', msg)
        self.assertIn('Y: 번호 원', msg)

    def test_R17_핀_행_순서로_그리면_통과한다(self):
        self.assertEqual(self.problems(self.board([(K + 1, 'Y'), (K + 2, 'X')], 'f')), '')

    def test_배지를_예약하면_그리는_순서와_무관하다(self):
        for order in ([(K + 2, 'X'), (K + 1, 'Y')],
                      [(K + 3, 'X'), (K + 2, 'Y'), (K + 1, 'Z')]):
            with self.subTest(order=order):
                first = self.board(order, 'f')
                self.assertIn('R17', self.problems(first))
                again = self.board(order, 'f', reserve=first)
                self.assertEqual(self.problems(again), '')
                self.assertEqual(again.badge_problems(), [])

    def test_예약이_없으면_그림이_그대로다(self):
        """예약은 자리가 겹칠 때만 원을 옮긴다 — 겹침이 없던 판은 같은 자리다(승인본 도장 불변)."""
        order = [(K + 1, 'Y'), (K + 2, 'X')]
        plain = self.board(order, 'f')
        held = self.board(order, 'f', reserve=plain)
        self.assertEqual(plain.marker_boxes, held.marker_boxes)


if __name__ == '__main__':
    unittest.main()
