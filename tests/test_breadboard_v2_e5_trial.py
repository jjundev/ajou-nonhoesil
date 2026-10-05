"""실험05 v2 시험판 — 1-2 BCD → 10진 디코더(74HC42). DIP-16 칩과 Negative Logic LED 를 엔진이 v2 규약
(R7~R14) 안에서 그리는지 잰다. 설계: docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md
"""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e5/배치.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Trial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e5')
        cls.tmp = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class BcdFinal(_Trial):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bb = cls.board.build_trial_bcd(os.path.join(cls.tmp, 'bcd.png'))

    def test_v2_규약을_지킨다(self):
        self.assertEqual({ch['block'] for ch in self.bb.chips}, {'left'})
        self.assertEqual(self.bb.cross_side_wires(), [])
        self.assertEqual(self.bb._block_role_violations(), [])
        self.assertLessEqual(max(s['count'] for s in self.bb.side_leads()), self.mod.SIDE_LEAD_MAX)

    def test_칩은_16핀이다(self):
        (ch,) = self.bb.chips
        self.assertEqual(len(ch['pins']), 16)

    def test_LED_는_핀_행_순서로_위에서_아래(self):
        tops = self.board.LAYOUT['leds']['bcd']
        self.assertEqual(sorted(tops, key=tops.get), list(self.board._LEDS))
        self.assertEqual(self.board._LEDS, ('Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y9', 'Y6', 'Y8', 'Y7'))


class Readability(_Trial):
    """단계 그림 넷과 완성본이 읽기 규칙 R11~R14 를 지킨다(`verify()` 가 이미 집행하지만 판형 스위치가
    꺼지면 조용히 안 돌기 때문에 직접 본다 — e4 시험판과 같다)."""

    def test_완성본과_단계_그림이_R11_R14_를_지킨다(self):
        bad, base = {}, None
        boards = list(self.board.BOARDS) + [(n, f, 'final') for n, f in self.board.FINALS]
        for name, fn, stage in boards:
            if stage == 'final':
                bb = fn(os.path.join(self.tmp, name))
            else:
                bb = fn(os.path.join(self.tmp, name), None, stage=stage, baseline=base)
                base = bb.snapshot()
            got = (bb.marker_problems() + bb.wires_over_holes() + bb.needless_body_crossings()
                   + bb.wires_over_chip_labels())
            if got:
                bad[name] = got
        self.assertEqual(bad, {}, '\n'.join(f'{k}: {len(v)}건 — {v[:3]}' for k, v in bad.items()))


if __name__ == '__main__':
    unittest.main()
