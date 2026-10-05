"""DIP-16 칩과 Negative Logic LED — 그리기·배선기 단위 시험.

설계: docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md
배치기 시험은 `test_breadboard_place.py` 의 `Dip16Place`, 시험판은 `test_breadboard_v2_e5_trial.py`.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _board(mod, **kw):
    bb = mod.BreadboardRenderer(None, board='v2', **kw)
    bb.enable_steps()
    return bb


class PinGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_DIP14_는_그대로(self):
        rows = [self.mod._dip_pin_row(10, p) for p in range(1, 15)]
        self.assertEqual(rows, [10, 11, 12, 13, 14, 15, 16, 16, 15, 14, 13, 12, 11, 10])
        self.assertEqual([self.mod._dip_side(p) for p in (7, 8)], ['a', 'f'])

    def test_DIP16_핀_행과_쪽(self):
        rows = [self.mod._dip_pin_row(10, p, 16) for p in range(1, 17)]
        self.assertEqual(rows, [10, 11, 12, 13, 14, 15, 16, 17, 17, 16, 15, 14, 13, 12, 11, 10])
        self.assertEqual([self.mod._dip_side(p, 16) for p in (8, 9)], ['a', 'f'])

    def test_칩_모델_표(self):
        self.assertEqual(self.mod.dip_pins('74HC42'), 16)
        self.assertEqual(self.mod.dip_pins('74HC08'), 14)
        self.assertEqual(self.mod.dip_pins('74HC9999'), 14)       # 그리기는 v1 호환으로 14
        with self.assertRaisesRegex(ValueError, 'DIP_PINS'):
            self.mod.dip_pins('74HC9999', strict=True)


if __name__ == '__main__':
    unittest.main()
