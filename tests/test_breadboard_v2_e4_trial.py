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


class MuxFinal(_Trial):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bb = cls.board.build_trial_mux(os.path.join(cls.tmp, 'mux.png'))

    def test_v2_규약을_지킨다(self):
        self.assert_v2_layout(self.bb)

    def test_진리표_전_행(self):
        nets = self.bb.nets()
        names = ('E', 'S1', 'S0', 'D0', 'D1', 'D2', 'D3')
        for vals in itertools.product((0, 1), repeat=7):
            ins = dict(zip(names, vals))
            sel = ins['S1'] * 2 + ins['S0']
            want = 1 if ins['E'] == 0 and ins[f'D{sel}'] else 0
            self.assertEqual(value_of(nets, 'LED Y 애노드', ins), want, str(ins))

    def test_중계는_n_c_셋과_미사용_입력_하나다(self):
        relay = [w for w in self.bb.wiring()['wires'] if '중계' in w['desc']]
        self.assertEqual(len(relay), 4, [w['desc'] for w in relay])


def _walk(board):
    """사슬 순서대로 (이름, 빌더, 단계, 그릴지) 를 낸다. 막힌 보드 뒤는 기준선이 없으므로
    다음 회로의 첫 보드(`RESTART`, `fresh_board` 로 기준선을 끊는 자리)까지 건너뛴다 —
    MUX 가 막혀도 DMUX 는 잰다."""
    skipping = False
    for name, fn, stage in board.BOARDS:
        if name in board.RESTART:
            skipping = False
        yield name, fn, stage, not skipping
        if name in board.KNOWN_BLOCKERS:
            skipping = True


class Chain(_Trial):
    """단계 사슬 — 막힘은 `KNOWN_BLOCKERS` 로, 새 신호선 수는 `MEASURED_NEW_SIGNAL` 로 고정한다."""

    def test_단계_보드마다_R10_이_통과하거나_기록된_막힘이다(self):
        base = None
        for name, fn, stage, draw in _walk(self.board):
            if name in self.board.RESTART:
                base = None
            if not draw:
                continue
            path = os.path.join(self.tmp, name)
            want = self.board.KNOWN_BLOCKERS.get(name)
            if want:
                with self.assertRaisesRegex(AssertionError, want):
                    fn(path, None, stage=stage, baseline=base)
                continue
            bb = fn(path, None, stage=stage, baseline=base)
            self.assertEqual(bb._block_role_violations(), [], name)
            self.assertEqual(len(bb.new_signal), self.board.MEASURED_NEW_SIGNAL[name], name)
            base = bb.snapshot()

    def test_측정표가_그린_보드를_빠짐없이_덮는다(self):
        drawn = [n for n, _f, _s, draw in _walk(self.board)
                 if draw and n not in self.board.KNOWN_BLOCKERS]
        self.assertEqual(list(self.board.MEASURED_NEW_SIGNAL), drawn)


if __name__ == '__main__':
    unittest.main()
