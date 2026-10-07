"""따라 그리기 층 쪽 — 이번 층 신호선은 선마다 다른 색(`LAYER_PALETTE`, 2026-10-07 팀원 피드백).

선·끝점·번호 원이 같은 색이라 같은 색 점끼리 이으면 된다. 완성본(layer 없음)은 그대로다.
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


def _pixel(bb, x, y):
    """템플릿 좌표 (x, y) 의 overlay 픽셀."""
    k = bb.overlay.size[0] / bb.base_im.size[0]
    return bb.overlay.getpixel((round(x * k), round(y * k)))


def _mid(bb, seg_index):
    """첫 구간의 1/4 지점 — 가운데는 번호 원(흰 바탕)이 덮는다."""
    _kind, pts, _d = bb._segments[seg_index]
    (x0, y0), (x1, y1) = pts[0], pts[1]
    return (3 * x0 + x1) / 4, (3 * y0 + y1) / 4


class LayerColor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self, layer=None, n_sig=3):
        """잭 두 가닥(1·2번) + 네 행짜리 세로 신호선 n_sig 가닥(3번부터) — 짧으면 번호 원이 선을 다 덮는다."""
        bb = self.mod.BreadboardRenderer(board='v1', layer=layer)
        bb.enable_steps()
        bb.set_header('층 색', '테스트')
        bb.connect_jacks()
        c = bb.cols['left']
        for i in range(n_sig):
            bb.step_wire([(c['a'], bb.r_y(10 + 5 * i)), (c['a'], bb.r_y(14 + 5 * i))], 'sig', f'신호 {i}')
        return bb

    def test_팔레트는_열_색이고_넷_색과_겹치지_않는다(self):
        p = self.mod.LAYER_PALETTE
        self.assertEqual(len(p), 10)
        self.assertEqual(len(set(p)), 10)
        taken = set(self.mod.WIRE.values()) | {self.mod.INPUT, self.mod.KEEP, self.mod.PROBE, self.mod.REMOVE}
        self.assertFalse(set(p) & taken)

    def test_층_신호선은_선마다_다른_팔레트_색이다(self):
        bb = self.board((3, 5))
        self.assertEqual(bb.wire_colors, {3: self.mod.LAYER_PALETTE[0], 4: self.mod.LAYER_PALETTE[1],
                                           5: self.mod.LAYER_PALETTE[2]})
        for i, n in enumerate((3, 4, 5)):
            self.assertEqual(_pixel(bb, *_mid(bb, n - 1)), self.mod.LAYER_PALETTE[i])

    def test_전원선은_층에서도_빨강_파랑이다(self):
        bb = self.board((1, 5))
        self.assertEqual(_pixel(bb, *_mid(bb, 0)), self.mod.WIRE['vcc'])
        self.assertEqual(_pixel(bb, *_mid(bb, 1)), self.mod.WIRE['gnd'])
        self.assertEqual(sorted(bb.wire_colors), [3, 4, 5])

    def test_끝점_점이_커진다(self):
        bb = self.board((3, 3), n_sig=1)
        _kind, pts, _d = bb._segments[2]
        x, y = pts[0]
        self.assertEqual(_pixel(bb, x + 4, y), self.mod.LAYER_PALETTE[0])   # 반지름 5 안, 선 폭(3) 밖

    def test_층_없으면_팔레트를_안_쓴다(self):
        bb = self.board(None)
        self.assertEqual(bb.wire_colors, {})
        self.assertEqual(_pixel(bb, *_mid(bb, 2)), self.mod.WIRE['sig'])
        _kind, pts, _d = bb._segments[2]
        x, y = pts[0]
        self.assertEqual(_pixel(bb, x + 4, y)[3], 0)   # 완성본 끝점 반지름 3 그대로

    def test_앞뒤_층_신호선은_팔레트를_안_받는다(self):
        bb = self.board((4, 4))
        self.assertEqual(bb.wire_colors, {4: self.mod.LAYER_PALETTE[0]})
        self.assertEqual(_pixel(bb, *_mid(bb, 2)), self.mod.KEEP)
        self.assertEqual(_pixel(bb, *_mid(bb, 4))[3], 0)

    def test_입력_점퍼는_층에서도_보라다(self):
        bb = self.mod.BreadboardRenderer(board='v1', layer=(3, 20))   # 입력 점퍼가 번호를 몇 개 쓰든 출력선까지 덮는다
        bb.enable_steps()
        bb.connect_jacks()
        bb.draw_chip('74HC08', 10)
        self.mod._input_jumper(bb, bb.cols['left'], 10, 'A', '74HC08 pin 1')
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(30)), (c['a'], bb.r_y(31))], 'sig', '출력')
        i = next(i for i, s in enumerate(bb._segments) if '입력 A' in s[2])
        self.assertEqual(_pixel(bb, *_mid(bb, i)), self.mod.INPUT)
        self.assertEqual(list(bb.wire_colors.values()), [self.mod.LAYER_PALETTE[0]])

    def test_층_색은_도장에_없다(self):
        a, b = self.board((3, 5)), self.board((3, 5))
        b.wire_colors.clear()
        self.assertEqual(a.content(), b.content())
        self.assertEqual(self.board(None).sidecar()['steps'], a.sidecar()['steps'])


class StageColor(unittest.TestCase):
    """체크리스트 단계 그림 — 빌더가 `palette=True` 로 켜면 층 없이도 새 신호선이 팔레트 색이다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self, palette, baseline=None, n_sig=2, layer=None):
        bb = self.mod.BreadboardRenderer(board='v1', baseline=baseline, palette=palette, layer=layer)
        bb.enable_steps()
        bb.set_header('단계 색', '테스트')
        bb.connect_jacks()
        c = bb.cols['left']
        for i in range(n_sig):
            bb.step_wire([(c['a'], bb.r_y(10 + 5 * i)), (c['a'], bb.r_y(14 + 5 * i))], 'sig', f'신호 {i}')
        return bb

    def test_palette_를_켜면_층_없이도_선마다_색이다(self):
        P = self.mod.LAYER_PALETTE
        bb = self.board(True)
        self.assertEqual(bb.wire_colors, {3: P[0], 4: P[1]})
        self.assertEqual(_pixel(bb, *_mid(bb, 2)), P[0])
        self.assertEqual(_pixel(bb, *_mid(bb, 0)), self.mod.WIRE['vcc'])

    def test_도장과_사이드카에_색이_실린다(self):
        bb = self.board(True)
        self.assertEqual(bb.content()['palette'], [[3, '#e67800'], [4, '#009696']])
        steps = bb.sidecar()['steps']
        self.assertEqual([s.get('color') for s in steps], [None, None, '#e67800', '#009696'])

    def test_끄면_예전_그대로다(self):
        bb = self.board(False)
        self.assertEqual(bb.wire_colors, {})
        self.assertNotIn('palette', bb.content())
        self.assertFalse(any('color' in s for s in bb.sidecar()['steps']))
        self.assertEqual(_pixel(bb, *_mid(bb, 2)), self.mod.WIRE['sig'])

    def test_색_받은_선이_없으면_도장에_palette_가_없다(self):
        bb = self.board(True, n_sig=0)
        self.assertEqual(bb.content(), self.board(False, n_sig=0).content())

    def test_기준선_회색은_팔레트를_안_받는다(self):
        first = self.board(True, n_sig=2)
        second = self.board(True, baseline=first.snapshot(), n_sig=3)
        self.assertEqual(second.wire_colors, {1: self.mod.LAYER_PALETTE[0]})
        self.assertEqual(_pixel(second, *_mid(second, 2)), self.mod.KEEP)

    def test_층_렌더는_사이드카와_도장에_색을_안_싣는다(self):
        bb = self.board(False, layer=(3, 4))
        self.assertTrue(bb.palette)
        self.assertEqual(len(bb.wire_colors), 2)
        self.assertNotIn('palette', bb.content())
        self.assertFalse(any('color' in s for s in bb.sidecar()['steps']))


if __name__ == '__main__':
    unittest.main()
