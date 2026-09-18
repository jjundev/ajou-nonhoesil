"""기준선(baseline) 계약 — 앞 보드에 이미 있던 배선은 회색이고 번호를 받지 않으며,
앞 보드에 있었는데 이번에 없는 배선은 `removed()` 에 주소로 나온다.

실험01 실험실 기록(2026-09-11): 1-1→1-2 는 칩만 갈아끼우면 되는 회로였는데
결선도가 회로마다 처음부터 그려져 있어 전부 걷었다. 회로 사이의 **차이**가
그림에 보여야 한다.
"""
import importlib.util
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


class Baseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def first(self):
        """앞 보드: 칩 하나 + 전원 + 배선 하나 + LED 사슬."""
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 7)
        bb.connect_jacks()
        bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
        bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
        bb.connect_power(7)
        bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(25))], 'sig', '출력 -> L2')
        bb.led_chain(c['a'], 25, 'L2', '최종')
        return bb

    def test_snapshot_은_배선_사슬_칩을_기호로_낸다(self):
        snap = self.first().snapshot()
        self.assertIn(('sig', ('hole', ('left', 'a', 12)), ('hole', ('left', 'a', 25))), snap['wires'])
        self.assertEqual(snap['chips'], {('left', 7): '74HC08'})
        self.assertEqual(len(snap['chains']), 1)

    def test_snapshot_은_배선_경로도_낸다(self):
        """끝점만 남기면 걷을 선을 그림에 그릴 수 없다 — 걷기 보드가 꼭짓점을 쓴다."""
        bb = self.first()
        c = bb.cols['left']
        snap = bb.snapshot()
        key = ('sig', ('hole', ('left', 'a', 12)), ('hole', ('left', 'a', 25)))
        self.assertEqual(snap['paths'][key], [(c['a'], bb.r_y(12)), (c['a'], bb.r_y(25))])
        self.assertEqual(set(snap['paths']), set(snap['wires']))

    def test_removals_는_걷을_배선에_번호와_경로를_준다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        bb.draw_chip('74HC08', 7)
        rs = bb.removals()
        self.assertEqual([r['n'] for r in rs], list(range(1, len(rs) + 1)))
        self.assertEqual([r['key'] for r in rs], list(base['wires']))   # 기준선 순서
        wire = [r for r in rs if r['desc'] == '출력 -> L2'][0]
        self.assertEqual(wire['addr'], '좌 a12 → 좌 a25')
        self.assertEqual(wire['points'], base['paths'][wire['key']])
        # 칩·사슬은 removals 에 없고 removed 에만 있다
        self.assertTrue(all(r['key'] in base['wires'] for r in rs))
        self.assertTrue(any('LED L2 사슬' in g for g in bb.removed()))
        self.assertEqual(bb.removed()[:len(rs)],
                         [f"{r['addr']} · {r['desc']}" for r in rs])

    def test_기준선이_없으면_removals_도_빈_목록이다(self):
        self.assertEqual(self.first().removals(), [])

    def test_옛_snapshot_에_paths_가_없으면_points_는_None_이다(self):
        base = self.first().snapshot()
        del base['paths']
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        self.assertTrue(all(r['points'] is None for r in bb.removals()))

    def test_기준선에_있는_배선은_회색이고_번호가_없다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 7)
        n = bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(25))], 'sig', '출력 -> L2')
        self.assertIsNone(n)
        # 같은 자리·같은 칩도 그대로 상태로 kept 에 먼저 들어간다
        self.assertEqual(bb.kept, ['74HC08 칩 그대로', '출력 -> L2'])
        self.assertEqual(bb.steps, [])
        # 회색이어도 점유표·구간에는 남는다 — verify() 가 여전히 본다
        self.assertIn((c['a'], 12), bb._leads)
        self.assertEqual(len(bb._segments), 1)

    def test_새_배선은_번호를_받는다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        c = bb.cols['left']
        n = bb.step_wire([(c['b'], bb.r_y(12)), (c['b'], bb.r_y(20))], 'sig', '새 선')
        self.assertEqual(n, 1)
        self.assertEqual(bb.kept, [])

    def test_removed_는_안_그린_기준선_배선을_주소로_낸다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        bb.draw_chip('74HC08', 7)
        gone = bb.removed()
        self.assertTrue(any('좌 a12 → 좌 a25' in g for g in gone))
        self.assertTrue(any('LED L2 사슬' in g for g in gone))
        self.assertTrue(any('전원잭' in g for g in gone))

    def test_기준선이_없으면_removed_는_빈_목록이다(self):
        self.assertEqual(self.first().removed(), [])

    def test_같은_자리에_다른_칩이면_교체_단계가_생긴다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        bb.draw_chip('74HC32', 7)
        self.assertEqual(bb.swaps, [('74HC08', '74HC32', 'left', 7)])
        self.assertEqual(bb.steps[0]['frm'], '뽑는다: 74HC08')
        self.assertEqual(bb.steps[0]['to'], '꽂는다: 74HC32')

    def test_같은_칩이면_교체_단계가_없다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        bb.draw_chip('74HC08', 7)
        self.assertEqual(bb.swaps, [])
        self.assertEqual(bb.steps, [])

    def test_같은_칩이면_그대로_상태를_기록한다(self):
        """몸통을 회색으로 그리는 것은 픽셀이라 직접 못 본다 — `kept` 에 남는
        관측 가능한 상태로 대신 검사한다."""
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        bb.draw_chip('74HC08', 7)
        self.assertIn('74HC08 칩 그대로', bb.kept)

    def test_빈_자리에_새로_꽂으면_교체라고_하지_않는다(self):
        """S2(18행)는 기준선(첫 보드)에 칩이 없던 자리다 — "뽑는다: (빈 자리)"
        처럼 뽑을 것도 없는데 교체라 부르면 안 된다."""
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        bb.draw_chip('74HC00', 18)
        self.assertEqual(bb.swaps, [(None, '74HC00', 'left', 18)])
        self.assertEqual(bb.steps[0]['frm'], '(빈 자리)')
        self.assertEqual(bb.steps[0]['to'], '꽂는다: 74HC00')
        self.assertEqual(bb.steps[0]['desc'], '좌 18행에 새로 꽂는다')

    def test_뽑힌_칩은_removed_에_나온다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        self.assertTrue(any('칩 74HC08' in g for g in bb.removed()))

    def test_기준선에_있는_사슬은_번호_없이_kept_에_남는다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        c = bb.cols['left']
        bb.led_chain(c['a'], 25, 'L2', '최종')
        self.assertEqual(bb.steps, [])          # step_note 도 GND 점퍼도 번호가 없다
        self.assertTrue(any('L2' in k for k in bb.kept))
        self.assertFalse(bb._keep_parts)         # 사슬을 다 그리면 플래그가 내려간다

    def test_기준선이_있는_그림도_그림대로_꽂힌다(self):
        base = self.first().snapshot()
        bb = self.mod.BreadboardRenderer(baseline=base)
        bb.enable_steps()
        c = bb.cols['left']
        bb.draw_chip('74HC32', 7)
        bb.connect_jacks()
        bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
        bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
        bb.connect_power(7)
        bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(25))], 'sig', '출력 -> L2')
        bb.led_chain(c['a'], 25, 'L2', '최종')
        bb.partial = True
        with tempfile.TemporaryDirectory() as d:
            bb.export(os.path.join(d, 'x.png'), max_row=31)   # verify() 가 안에서 돈다
        self.assertEqual(bb.steps[0]['desc'], '좌 7행 칩 교체')

    def test_submit_False_면_손그림_안내줄이_바뀐다(self):
        bb = self.mod.BreadboardRenderer()
        bb.set_header('t', 's', submit=False)
        self.assertFalse(bb.submit)


if __name__ == '__main__':
    unittest.main()
