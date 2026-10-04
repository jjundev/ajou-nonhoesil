"""v2 배선기 — 엔진 `route_plan`·`wire_metrics`·밀도 재순위.

설계: `docs/plans/2026-10-04-v2-배선기-밀도-설계.md`. 기준 데이터는 실험04 v2 시험판
(`tests/fixtures/board_v2_e4/배치.py`). `plans_lambda0.json` 은 배선기를 엔진으로 옮기기 **전**
시험판이 고른 경로·번호 원 자리다 — λ=0 이면 그대로 나와야 한다.
"""
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

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

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
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


if __name__ == '__main__':
    unittest.main()
