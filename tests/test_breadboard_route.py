"""v2 배선기 — 엔진 `route_plan`·`wire_metrics`·밀도 재순위.

설계: `docs/plans/2026-10-04-v2-배선기-밀도-설계.md`. 기준 데이터는 실험04 v2 시험판
(`tests/fixtures/board_v2_e4/배치.py`). `plans_lambda0.json` 은 배선기를 엔진으로 옮기기 **전**
시험판이 고른 경로·번호 원 자리다 — λ=0 이면 그대로 나와야 한다.
"""
import importlib.util
import json
import unittest
from pathlib import Path

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
        self.assertEqual(_plain(self.board._mux_paths()), self.snap['mux'])

    def test_DMUX(self):
        self.assertEqual(_plain(self.board._dmux_paths()), self.snap['dmux'])


if __name__ == '__main__':
    unittest.main()
