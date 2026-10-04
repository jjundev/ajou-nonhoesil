"""v2 배치기 — 칩 슬롯 행·LED 윗행·브리지 행 고르기.

설계: `docs/plans/2026-10-05-v2-배치기-설계.md`. 단위 시험은 작은 장난감 회로로, 시험판 시험은
`tests/fixtures/board_v2_e4/배치.py` 로 잰다.
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _toy(mod, wires, leds=('L1',), inputs=(), models=None):
    """U1(K1)·U2(K2) 두 칩 장난감 회로. `fixed` 는 단위 시험에서 안 부른다."""
    return mod.PlaceCircuit('toy', {'U1': 'K1', 'U2': 'K2'},
                            models or {'U1': '74HC04', 'U2': '74HC08'},
                            tuple(leds), tuple(wires), lambda bb, stage, superset, layout: None,
                            tuple(inputs))


_LAY = {'slots': {'K1': 5, 'K2': 17}, 'leds': {'toy': {'L1': 7}}, 'bridge': [27, 28]}


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_칩_행은_슬롯에서(self):
        c = _toy(self.mod, [])
        self.assertEqual(self.mod.place_chips(c, _LAY), {'U1': 5, 'U2': 17})

    def test_LED_태그를_윗행으로_바꾼다(self):
        w = (1, None, 'sig', ('U1', 12), ('LED', 'L1'), 'x')
        c = _toy(self.mod, [w])
        self.assertEqual(self.mod.place_wires(c, _LAY), [(1, None, 'sig', ('U1', 12), ('LED', 7), 'x')])

    def test_14핀이_아니면_멈춘다(self):
        c = _toy(self.mod, [], models={'U1': '74HC04', 'U2': '74HC138'})
        with self.assertRaisesRegex(ValueError, '14핀'):
            self.mod.place_check(c)

    def test_leds_에_없는_태그면_멈춘다(self):
        c = _toy(self.mod, [(1, None, 'sig', ('U1', 12), ('LED', 'L9'), 'x')])
        with self.assertRaisesRegex(ValueError, 'L9'):
            self.mod.place_check(c)

    def test_지문은_배선표가_바뀌면_바뀐다(self):
        a = _toy(self.mod, [(1, None, 'sig', ('U1', 12), ('LED', 'L1'), 'x')])
        b = _toy(self.mod, [(1, None, 'sig', ('U1', 10), ('LED', 'L1'), 'x')])
        self.assertEqual(self.mod.place_hash([a], ('K1', 'K2')), self.mod.place_hash([a], ('K1', 'K2')))
        self.assertNotEqual(self.mod.place_hash([a], ('K1', 'K2')), self.mod.place_hash([b], ('K1', 'K2')))
        self.assertNotEqual(self.mod.place_hash([a], ('K1', 'K2')),
                            self.mod.place_hash([a], ('K1', 'K2'), gmin=4))

    def test_layout_열쇠는_키_순서와_무관(self):
        a = {'slots': {'K1': 5, 'K2': 17}, 'bridge': [1, 2]}
        b = {'bridge': [1, 2], 'slots': {'K2': 17, 'K1': 5}}
        self.assertEqual(self.mod.layout_key(a), self.mod.layout_key(b))


if __name__ == '__main__':
    unittest.main()
