"""v2 배선기 — 엔진 `route_plan`·`wire_metrics`·밀도 재순위.

설계: `docs/plans/2026-10-04-v2-배선기-밀도-설계.md`. 기준 데이터는 실험04 v2 시험판
(`tests/fixtures/board_v2_e4/배치.py`). `plans_lambda0.json` 은 지금 `LAYOUT` 에서 λ=0 경로·번호 원
자리다 — 배선기를 바꿔도 λ=0 이면 그대로 나와야 한다. 배치(`LAYOUT`)를 바꾸면 다시 뜬다(2026-10-05
배치기 적용 때, 배선기가 신호 이름 배지를 피하게 고칠 때 다시 떴다).
"""
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.lab import route_sweep as rs
from tests import _renders

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'
SNAP = ROOT / 'tests/fixtures/board_v2_e4/plans_lambda0.json'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plain(plans):
    """튜플 → 리스트 (JSON 과 맞대려고)."""
    return json.loads(json.dumps(plans))


class LambdaZero(unittest.TestCase):
    """λ=0 이면 옮기기 전 시험판 배선기와 같은 경로·번호 원 자리."""
    render_group = 'board_v2_e4'

    @classmethod
    def setUpClass(cls):
        cls.mod = _renders.engine()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')
        cls.snap = json.loads(SNAP.read_text(encoding='utf-8'))

    def test_MUX(self):
        self.assertEqual(_plain(self.board._mux_paths(0.0)), self.snap['mux'])

    def test_DMUX(self):
        self.assertEqual(_plain(self.board._dmux_paths(0.0)), self.snap['dmux'])


class RoutePlanBoard(unittest.TestCase):
    def test_v1_이면_멈춘다(self):
        mod = _load()
        with self.assertRaisesRegex(ValueError, 'v2'):
            mod.route_plan(lambda bb, stage, superset=False: None, {}, [], board='v1')

    def test_막히면_막힌_선을_댄다(self):
        """수리가 앞 선을 바꿔 봐도 안 풀리면, 메시지는 수리하던 앞 선이 아니라 막힌 선의 끝을 댄다
        (2026-10-04 최종 검토 — 수리 루프가 frm·to 를 덮어써 앞 선 끝 + 막힌 선 설명이 섞였다)."""
        mod = _load()

        def fake_routes(bb, chips, frm, to, density_weight=0.0):
            if to == ('U', 99):
                return
            x, y = bb.cols['left']['b'], bb.r_y(frm[1])
            yield [(x, y), (x, y + 2 * bb.spec.row_pitch)], (x + 12, y + bb.spec.row_pitch)

        mod._routes = fake_routes
        wires = [(1, None, 'sig', ('U', 10), ('U', 12), '앞 선'),
                 (1, None, 'sig', ('U', 30), ('U', 99), '막힌 선')]
        with self.assertRaises(AssertionError) as cm:
            mod.route_plan(lambda bb, stage, superset=False: None, {}, wires)
        self.assertEqual(str(cm.exception), "경로 없음: ('U', 30) -> ('U', 99) (막힌 선)")


    def test_뒤_선_끝점을_덮은_번호_원은_다시_고른다(self):
        """번호 원은 그 선을 깔 때 고르니 **뒤에 깔린 선의 끝점**을 모른다 — 배치 탐색 후보 3 의 DMUX 에서
        Y1 번호 원이 나중에 꽂힌 좌 i22 를 덮었다(2026-10-05). 다 깐 superset 판에서 다시 본다."""
        mod = _load()
        L = mod.board_spec('v2').cols['left']
        y = lambda r: mod.board_spec('v2').row0 + (r - 1) * mod.board_spec('v2').row_pitch

        def fake_routes(bb, chips, frm, to, density_weight=0.0):
            if frm == ('U', 1):    # 앞 선 — 번호 원을 (아직 빈) c12 위에 둔다
                yield [(L['a'], y(10)), (L['a'] - 30, y(10)), (L['a'] - 30, y(14)), (L['a'], y(14))], (L['c'], y(12))
            else:                  # 뒤 선 — c12 에 꽂힌다
                yield [(L['c'], y(12)), (L['c'] + 12, y(12)), (L['c'] + 12, y(30)), (L['c'], y(30))], (L['c'] + 12, y(21))

        mod._routes = fake_routes
        wires = [(1, None, 'sig', ('U', 1), ('U', 2), '앞 선'),
                 (1, None, 'sig', ('U', 3), ('U', 4), '뒤 선')]
        plans = mod.route_plan(lambda bb, stage, superset=False: None, {}, wires)
        self.assertNotEqual(plans[0][1], (L['c'], y(12)))
        bb = mod.BreadboardRenderer(None, board='v2')
        bb.enable_steps()
        for (_s, _e, kind, _f, _t, desc), (p, m) in zip(wires, plans):
            bb.step_wire(p, kind, desc, marker_at=m)
        self.assertEqual([x for x in bb.marker_problems() if '홀' in x], [])

class Metrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_붙어_달리는_정도(self):
        c = self.mod._crowding
        self.assertEqual(c(('v', 0, 0, 100), ('h', 0, 0, 100), 19), 0)         # 축이 다르다
        self.assertEqual(c(('v', 0, 0, 100), ('v', 0, 0, 100), 19), 0)         # 포개짐은 R4 몫
        self.assertEqual(c(('v', 0, 0, 100), ('v', 19, 0, 100), 19), 0)        # 1칸 떨어지면 0
        self.assertAlmostEqual(c(('v', 0, 0, 100), ('v', 9.5, 50, 200), 19), 25)  # 겹침 50 × 0.5

    def test_지표(self):
        bb = SimpleNamespace(spec=SimpleNamespace(row_pitch=19.0), _segments=[
            ('sig', [(0, 0), (0, 190)], 'a'),
            ('mid', [(9.5, 0), (9.5, 95), (50, 95)], 'b'),
            ('gnd', [(4, 0), (4, 190)], '전원은 안 센다'),
        ])
        m = self.mod.wire_metrics(bb)
        self.assertAlmostEqual(m['length'], (190 + 95 + 40.5) / 19)
        self.assertEqual(m['bends'], 1)
        self.assertAlmostEqual(m['density'], 95 * 0.5 / 19)

    def test_사선은_밀도에_안_든다(self):
        bb = SimpleNamespace(spec=SimpleNamespace(row_pitch=19.0), _segments=[
            ('sig', [(0, 0), (30, 40)], '사선'),
            ('sig', [(5, 0), (35, 40)], '사선'),
        ])
        m = self.mod.wire_metrics(bb)
        self.assertAlmostEqual(m['length'], 100 / 19)
        self.assertEqual(m['density'], 0)

    def test_같은_선_안은_안_센다(self):
        bb = SimpleNamespace(spec=SimpleNamespace(row_pitch=19.0), _segments=[
            ('sig', [(0, 0), (0, 100), (6, 100), (6, 0)], 'U자'),
        ])
        self.assertEqual(self.mod.wire_metrics(bb)['density'], 0)

    def test_새_경로의_밀도_증분(self):
        placed = [('v', 100, 0, 200)]
        self.assertAlmostEqual(self.mod._density_cost(((105, 0), (105, 200)), placed, 19),
                               200 * (1 - 5 / 19))


class Rerank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    A = ((105, 0), (105, 200))      # 깔린 선(x=100) 5px 옆 — 싸지만 붙어 달린다
    B = ((150, 0), (150, 200))      # 50px 떨어짐 — 조금 비싸다

    def test_λ0_은_정적_순서다(self):
        got = self.mod._rerank([(200, self.A), (210, self.B)], [('v', 100, 0, 200)], 19, 0.0)
        self.assertEqual(got, [self.A, self.B])

    def test_λ_가_크면_떨어진_선이_앞선다(self):
        got = self.mod._rerank([(200, self.A), (210, self.B)], [('v', 100, 0, 200)], 19, 1.0)
        self.assertEqual(got, [self.B, self.A])

    def test_앞_top_개만_다시_매긴다(self):
        got = self.mod._rerank([(200, self.A), (210, self.B)], [('v', 100, 0, 200)], 19, 1.0, top=1)
        self.assertEqual(got, [self.A, self.B])

    def test_동률은_경로_순서다(self):
        C = ((160, 0), (160, 200))
        got = self.mod._rerank([(210, C), (210, self.B)], [], 19, 1.0)
        self.assertEqual(got, [self.B, C])


def _row(w, length, density):
    return {'weight': w, 'length': length, 'bends': 0, 'density': density}


class Sweep(unittest.TestCase):
    def test_한도_안에서_밀도_합_최소(self):
        rows = {'mux': [_row(0, 100, 10), _row(1, 110, 6), _row(2, 120, 2)],
                'dmux': [_row(0, 50, 5), _row(1, 52, 4), _row(2, 53, 1)]}
        self.assertEqual(rs.pick(rows), 1)        # λ=2 는 MUX 길이 +20%

    def test_줄지_않으면_0(self):
        rows = {'mux': [_row(0, 100, 10), _row(1, 101, 10)], 'dmux': [_row(0, 50, 5), _row(1, 50, 5)]}
        self.assertEqual(rs.pick(rows), 0)

    def test_막힌_λ_는_건너뛴다(self):
        rows = {'mux': [_row(0, 100, 10), {'weight': 1, 'blocked': '경로 없음'}],
                'dmux': [_row(0, 50, 5), _row(1, 50, 1)]}
        self.assertEqual(rs.pick(rows), 0)

    def test_기준_행이_없으면_멈춘다(self):
        with self.assertRaises(ValueError):
            rs.pick({'mux': [{'weight': 0, 'blocked': '경로 없음'}], 'dmux': [_row(0, 50, 5)]})
        with self.assertRaises(ValueError):
            rs.pick({'mux': [_row(1, 100, 10)], 'dmux': [_row(1, 50, 5)]})

    def test_막히면_막힘_행이다(self):
        def build(path, density_weight):
            raise AssertionError('경로 없음: U1 -> U3\n자세히')
        got = rs.measure(None, build, 'x.png', 4.0)
        self.assertEqual(got, {'weight': 4.0, 'blocked': '경로 없음: U1 -> U3'})


class ChosenWeight(unittest.TestCase):
    """엔진 DENSITY_WEIGHT 가 설계 #11 을 지킨다 — 두 회로 모두 길이 ≤ λ=0 × 1.15, 밀도 합은 줄었다.
    2026-10-04 스윕에서 λ=0.5 가 골라졌다(밀도 합 40.7 → 26.9칸) — 0 으로 돌아가면 걸린다."""
    render_group = 'board_v2_e4'

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.mod = _renders.engine()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')
        cls.tmp = tempfile.mkdtemp()

    def _m(self, build, name, w):
        import os
        return self.mod.wire_metrics(build(os.path.join(self.tmp, name), density_weight=w))

    def test_설계_11(self):
        w = self.mod.DENSITY_WEIGHT
        self.assertGreater(w, 0)
        got = {}
        for key, build in (('mux', self.board.build_trial_mux), ('dmux', self.board.build_trial_dmux)):
            got[key] = (self._m(build, f'{key}0.png', 0.0), self._m(build, f'{key}w.png', w))
            self.assertLessEqual(got[key][1]['length'], got[key][0]['length'] * 1.15, key)
        self.assertLess(sum(v[1]['density'] for v in got.values()),
                        sum(v[0]['density'] for v in got.values()))


class BadgeObstacle(unittest.TestCase):
    """2026-10-05 실험05 — v2 배선기가 신호 이름 배지를 장애물로 본다. C1 `Y0` 급전선이 가운데 레일 입력
    배지 `Bit0`~`Bit2` 위로 내려갔고, 번호 원이 `Bit1`~`Bit3`·`D1` 을 덮었다
    (설계 `docs/plans/2026-10-05-v2-배선기-배지회피-설계.md`)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _bb(self):
        bb = self.mod.BreadboardRenderer(None, board='v2')
        bb.enable_steps()
        return bb

    def test_배지를_지나는_경로는_거절한다(self):
        bb = self._bb()
        bb.signal_tag('Bit0', 212, bb.r_y(15))
        path = [(212, bb.r_y(10)), (212, bb.r_y(20))]
        self.assertFalse(self.mod._valid(bb, path, [], []))

    def test_배지를_비켜_가는_경로는_그대로다(self):
        bb = self._bb()
        bb.signal_tag('Bit0', 212, bb.r_y(30))
        path = [(212, bb.r_y(10)), (212, bb.r_y(20))]
        self.assertTrue(self.mod._valid(bb, path, [], []))

    def test_배지_위에는_번호_원을_안_둔다(self):
        bb = self._bb()
        x, y = 640, bb.r_y(15)
        self.assertTrue(bb._marker_clear(x, y))
        bb.signal_tag('Bit0', x, y)
        self.assertFalse(bb._marker_clear(x, y))

    def test_빈_행_핀의_가운데_레일_입력은_번호_원이_제_배지를_안_덮는다(self):
        bb = self._bb()
        bb.draw_chip('74HC04', 17)
        bb.partial = True
        L = bb.cols['left']
        self.mod._input_jumper(bb, L, 20, 'D1', 'U1 pin 11', side='f', col='j')
        (_n, box, _s), = [t for t in bb.tag_boxes if t[0] == 'D1']
        self.assertEqual([m for m in bb.marker_boxes if self.mod._boxes_touch(box, m)], [])

    def test_가운데_레일에_배지가_쌓여도_번호_원이_어느_배지도_안_덮는다(self):
        # 실험05 C1 — 74HC42 pin 15~12 입력 넷이 가운데 레일에 한 행씩 배지를 쌓는다. 원 자리를 고를 때
        # 제 배지가 아직 없어 `Bit1` 원이 곧 그려질 `Bit1` 배지 위에 앉았다
        bb = self._bb()
        bb.draw_chip('74HC42', 3)
        bb.partial = True
        L = bb.cols['left']
        for name, row in (('Bit0', 4), ('Bit1', 5), ('Bit2', 6), ('Bit3', 7)):
            self.mod._input_jumper(bb, L, row, name, name, side='f', col='j')
        hits = [(n, m) for n, box, _s in bb.tag_boxes for m in bb.marker_boxes
                if self.mod._boxes_touch(box, m)]
        self.assertEqual(hits, [])


if __name__ == '__main__':
    unittest.main()
