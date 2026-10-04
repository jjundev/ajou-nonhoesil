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


def _w(frm, to, s=1, e=None):
    return (s, e, 'sig', frm, to, f'{frm}->{to}')


class Proxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_가까운_칩이_싸다(self):
        w = _w(('U1', 12), ('U2', 13))
        near = self.mod.place_wire_cost({'U1': 5, 'U2': 15}, w)
        far = self.mod.place_wire_cost({'U1': 5, 'U2': 35}, w)
        self.assertLess(near, far)

    def test_a쪽에서_LED_로_가면_몸통_벌점(self):
        f = self.mod.place_wire_cost({'U1': 5}, _w(('U1', 12), ('LED', 7)))   # pin 12 = 7행, f쪽
        a = self.mod.place_wire_cost({'U1': 5}, _w(('U1', 3), ('LED', 7)))    # pin 3 = 7행, a쪽
        self.assertGreaterEqual(a - f, 400)

    def test_브리지는_맨_아래_칩_아래_첫_비간극_두_행(self):
        # 맨 아래 칩 41 → 마지막 행 47 → 50 부터: 50 은 레일 빈 행 → 51·52
        self.assertEqual(self.mod.bridge_rows({'K1': 5, 'K2': 17, 'K3': 29, 'K4': 41}), [51, 52])
        self.assertIsNone(self.mod.bridge_rows({'K1': 55}))

    def test_가운데_레일_사용_행(self):
        c = _toy(self.mod, [], inputs=[('U1', 12), ('U2', 3)])   # f쪽 pin 12 → 7행, a쪽은 안 셈
        self.assertEqual(self.mod.mid_rail_rows(c, {'K1': 5, 'K2': 17, 'K3': 40}, [27, 28]),
                         {5, 17, 27, 28, 7})


class LedRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.slots = {'K1': 5, 'K2': 17}
        cls.bridge = [27, 28]

    def test_드라이버_행에_붙는다(self):
        c = _toy(self.mod, [_w(('U1', 12), ('LED', 'L1'))])     # 7행, 7+3=10 은 비어 있다
        self.assertEqual(self.mod.led_rows(c, self.slots, self.bridge), {'L1': 7})

    def test_GND_행이_간극이면_비켜_위쪽(self):
        c = _toy(self.mod, [_w(('U1', 1), ('LED', 'L1'))])      # 5행: 5+3=8 은 레일 빈 행 → 4·6 동률 → 4
        self.assertEqual(self.mod.led_rows(c, self.slots, self.bridge), {'L1': 4})

    def test_GND_행이_입력_행이면_비킨다(self):
        c = _toy(self.mod, [_w(('U1', 1), ('LED', 'L1'))], inputs=[('U1', 12)])   # 7행 사용 → 4 막힘 → 6
        self.assertEqual(self.mod.led_rows(c, self.slots, self.bridge), {'L1': 6})

    def test_태그_순서와_간격(self):
        c = _toy(self.mod, [_w(('U2', 12), ('LED', 'L1')), _w(('U1', 12), ('LED', 'L2'))],
                 leds=('L1', 'L2'))
        got = self.mod.led_rows(c, self.slots, self.bridge)
        self.assertLessEqual(got['L1'] + self.mod.LED_SPAN, got['L2'])

    def test_LED_가_없으면_빈_dict(self):
        self.assertEqual(self.mod.led_rows(_toy(self.mod, [], leds=()), self.slots, self.bridge), {})

    def test_다_못_놓으면_None(self):
        tags = tuple(f'L{i}' for i in range(16))                 # 16 × 4행 > 3~61행
        self.assertIsNone(self.mod.led_rows(_toy(self.mod, [], leds=tags), self.slots, self.bridge))


class R10AndCandidates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_같은_단계에서_엇갈리면_거짓(self):
        c = _toy(self.mod, [_w(('U2', 12), ('LED', 'L1')), _w(('U1', 12), ('LED', 'L2'))],
                 leds=('L1', 'L2'))
        self.assertFalse(self.mod.place_r10_ok(c, {'U1': 5, 'U2': 17}, {'L1': 10, 'L2': 20}))

    def test_다른_단계면_안_엇갈린다(self):
        c = _toy(self.mod, [_w(('U2', 12), ('LED', 'L1'), 1, 1), _w(('U1', 12), ('LED', 'L2'), 2)],
                 leds=('L1', 'L2'))
        self.assertTrue(self.mod.place_r10_ok(c, {'U1': 5, 'U2': 17}, {'L1': 10, 'L2': 20}))

    def test_후보는_간극_간격_규칙을_지킨다(self):
        cands = self.mod.slot_candidates(('K1', 'K2', 'K3'))
        self.assertTrue(cands)
        gaps = self.mod.RAIL_GAP_ROWS
        for c in cands:
            rows = sorted(c.values())
            self.assertTrue(all(k not in gaps and k + 6 not in gaps for k in rows), c)
            self.assertTrue(all(7 + 3 <= b - a <= 7 + 6 for a, b in zip(rows, rows[1:])), c)
            self.assertIn(rows[0], self.mod.PLACE_STARTS)
        orders = {tuple(sorted(c, key=c.get)) for c in cands}
        self.assertEqual(len(orders), 6)      # 순열 3! 전부

    def test_근사는_LED_를_고르고_layout_을_낸다(self):
        c = _toy(self.mod, [_w(('U1', 12), ('U2', 13)), _w(('U2', 8), ('LED', 'L1'))])
        cost, lay = self.mod.place_proxy([c], {'K1': 5, 'K2': 17})
        self.assertEqual(lay['slots'], {'K1': 5, 'K2': 17})
        self.assertEqual(lay['bridge'], self.mod.bridge_rows({'K1': 5, 'K2': 17}))
        self.assertIn('L1', lay['leds']['toy'])
        self.assertGreater(cost, 0)


if __name__ == '__main__':
    unittest.main()
