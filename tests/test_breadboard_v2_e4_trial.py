"""실험04 v2 시험판 — MUX/디코더 류가 R8 면제 없이 v2 규약(R7~R10)을 지키는지 잰다.

승인본(`보고서/실험04`)은 v1 그대로다. 이 파일은 `tests/fixtures/board_v2_e4/배치.py` 만 본다.
진리표는 넷을 `tests/_gate_sim.py` 로 돌려 맞댄다 — 시험판은 교안 핀 번호를 일부러 바꿔서
netlist 핀 줄 대조를 쓸 수 없다.
"""
import importlib.util
import itertools
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tests._gate_sim import value_of

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Trial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')
        cls.tmp = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def assert_v2_layout(self, bb):
        self.assertEqual({ch['block'] for ch in bb.chips}, {'left'})
        self.assertEqual(bb.cross_side_wires(), [])
        self.assertEqual(bb._block_role_violations(), [])
        worst = max(s['count'] for s in bb.side_leads())
        self.assertLessEqual(worst, self.mod.SIDE_LEAD_MAX)


class DmuxFinal(_Trial):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bb = cls.board.build_trial_dmux(os.path.join(cls.tmp, 'dmux.png'))

    def test_v2_규약을_지킨다(self):
        self.assert_v2_layout(self.bb)

    def test_진리표_전_행(self):
        nets = self.bb.nets()
        for d, s1, s0 in itertools.product((0, 1), repeat=3):
            ins = {'D': d, 'S1': s1, 'S0': s0}
            for i in range(4):
                want = 1 if d and (s1 * 2 + s0) == i else 0
                got = value_of(nets, f'LED Y{i} 애노드', ins)
                self.assertEqual(got, want, f'Y{i} @ {ins}')


if __name__ == '__main__':
    unittest.main()
