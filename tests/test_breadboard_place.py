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


def _gap(lay):
    return abs(lay['slots']['K2'] - lay['slots']['K1'])


class Plan(unittest.TestCase):
    """선택 로직 — 실측·검증은 가짜로 주입한다(진짜는 시험판 시험이 잰다)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.toy = _toy(cls.mod, [_w(('U1', 12), ('U2', 13)), _w(('U2', 8), ('LED', 'L1'))])
        cls.base = {'slots': {'K1': 5, 'K2': 23}, 'leds': {'toy': {'L1': 23}}, 'bridge': [33, 34]}

    def module(self):
        return SimpleNamespace(PLACE=[self.toy], SLOTS=('K1', 'K2'), LAYOUT=self.base)

    @staticmethod
    def measure(lay):
        d = _gap(lay)
        if d == 10:
            return {'blocked': '경로 없음: x'}
        return {'length': float(d), 'bends': 0, 'density': 99.0 if d == 11 else 1.0}

    def test_막힘_밀도초과_verify실패를_건너뛰고_가장_짧은_것(self):
        seen = []

        def verify(lay):
            seen.append(_gap(lay))
            return 'R3 가림' if _gap(lay) == 12 else None
        got = self.mod.place_plan(self.module(), top=100, measure=self.measure, verify=verify)
        self.assertEqual(_gap(got['layout']), 13)
        self.assertNotIn(10, seen)
        self.assertNotIn(11, seen)
        self.assertEqual(seen[-1], 13)
        status = {r['status'] for r in got['rows']}
        self.assertIn('막힘: 경로 없음: x', status)
        self.assertIn('밀도 초과', status)
        self.assertIn('verify: R3 가림', status)
        self.assertIn('✔ 고름', status)
        self.assertEqual(got['hash'], self.mod.place_module_hash(self.module()))

    def test_기준이_가장_짧으면_기준(self):
        def measure(lay):
            return {'length': 0.0 if lay == self.base else 50.0, 'bends': 0, 'density': 1.0}
        got = self.mod.place_plan(self.module(), top=100, measure=measure, verify=lambda lay: None)
        self.assertEqual(got['layout'], self.base)
        self.assertEqual(got['rows'][0]['rank'], '기준')

    def test_후보가_없으면_기준(self):
        m = self.module()
        m.SLOTS = ('K1', 'K2')
        got = self.mod.place_plan(m, top=100, gmin=40, measure=self.measure, verify=lambda lay: None)
        self.assertEqual(got['layout'], self.base)
        self.assertEqual(len(got['rows']), 1)

    def test_기준이_막히면_멈춘다(self):
        with self.assertRaisesRegex(AssertionError, '기준 LAYOUT'):
            self.mod.place_plan(self.module(), measure=lambda lay: {'blocked': '경로 없음: y'},
                                verify=lambda lay: None)

    def test_고를_것이_없으면_멈춘다(self):
        with self.assertRaisesRegex(AssertionError, '고를 배치가 없다'):
            self.mod.place_plan(self.module(), top=100, measure=self.measure,
                                verify=lambda lay: 'R2 겹침')

    def test_보고서_왕복(self):
        got = self.mod.place_plan(self.module(), top=100, measure=self.measure,
                                  verify=lambda lay: None)
        text = self.mod.place_report(got, '장난감 — 한글 제목')
        d = tempfile.mkdtemp()
        p = os.path.join(d, self.mod.PLACE_REPORT)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)
        self.assertEqual(self.mod.read_place_report(p), {'hash': got['hash'], 'layout': got['layout']})
        self.assertIn('| 순위 |', text)


class Verify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_그리는_동안만_LAYOUT_을_바꾼다(self):
        seen = []
        m = SimpleNamespace(LAYOUT='원래', RESTART=set(), FINALS=[])

        def fn(path, template_path=None, stage=None, baseline=None):
            seen.append(m.LAYOUT)
            return SimpleNamespace(snapshot=lambda: None)
        m.BOARDS = [('a.png', fn, 1), ('b.png', fn, 2)]
        self.assertIsNone(self.mod.place_verify(m, '후보', tempfile.mkdtemp()))
        self.assertEqual(seen, ['후보', '후보'])
        self.assertEqual(m.LAYOUT, '원래')

    def test_막혀도_LAYOUT_을_되돌린다(self):
        m = SimpleNamespace(LAYOUT='원래', RESTART=set(), FINALS=[])

        def fn(path, template_path=None, stage=None, baseline=None):
            raise AssertionError('그림대로 꽂을 수 없다:\n  R3 끝점 가림: 좌 j7')
        m.BOARDS = [('a.png', fn, 1)]
        got = self.mod.place_verify(m, '후보', tempfile.mkdtemp())
        self.assertIn('a.png', got)
        self.assertIn('R3 끝점 가림', got)
        self.assertEqual(m.LAYOUT, '원래')


class Paths(unittest.TestCase):
    def test_자리마다_한_번_배선한다(self):
        mod = _load()
        calls = []

        def fake_route_plan(build_fixed, chips, wires, board='v2', density_weight=None):
            calls.append((chips, wires, density_weight))
            return [('경로', None)] * len(wires)
        mod.route_plan = fake_route_plan
        c = _toy(mod, [_w(('U2', 8), ('LED', 'L1'))])
        other = dict(_LAY, slots={'K1': 5, 'K2': 18})
        mod.place_paths(c, _LAY)
        mod.place_paths(c, _LAY)
        mod.place_paths(c, other)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1][0][4], ('LED', 7))
        self.assertEqual(calls[0][2], mod.DENSITY_WEIGHT)


class TrialInterface(unittest.TestCase):
    """시험판이 배치 계약(PLACE·SLOTS·LAYOUT)을 따른다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')

    def test_PLACE_는_두_회로다(self):
        self.assertEqual([c.name for c in self.board.PLACE], ['mux', 'dmux'])
        for c in self.board.PLACE:
            self.mod.place_check(c)

    def test_LED_끝은_태그다(self):
        ends = {e for c in self.board.PLACE for w in c.wires for e in (w[3], w[4]) if e[0] == 'LED'}
        self.assertTrue(ends)
        self.assertTrue(all(isinstance(e[1], str) for e in ends), ends)

    def test_LAYOUT_은_JSON_꼴이다(self):
        import json
        self.assertEqual(json.loads(json.dumps(self.board.LAYOUT)), self.board.LAYOUT)
        self.assertEqual(set(self.board.LAYOUT['slots']), set(self.board.SLOTS))


class SearchCli(unittest.TestCase):
    def test_run_은_배치_파일_옆에_보고서를_쓴다(self):
        from scripts.lab import place_search as ps
        mod = _load()
        result = {'hash': 'abc', 'layout': _LAY,
                  'rows': [dict(rank='기준', proxy=None, layout=_LAY, length=1.0, bends=0,
                                density=0.0, status='✔ 고름')]}
        got_args = []

        def fake_plan(board, top):
            got_args.append(top)
            return result
        mod.place_plan = fake_plan
        d = Path(tempfile.mkdtemp())
        out = ps.run(mod, SimpleNamespace(), d / '배치.py', 3)
        self.assertEqual(out, result)
        self.assertEqual(got_args, [3])
        self.assertEqual(mod.read_place_report(d / mod.PLACE_REPORT), {'hash': 'abc', 'layout': _LAY})


if __name__ == '__main__':
    unittest.main()
