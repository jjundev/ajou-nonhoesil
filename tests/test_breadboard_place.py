"""v2 배치기 — 칩 슬롯 행·LED 윗행·브리지 행 고르기.

설계: `docs/plans/2026-10-05-v2-배치기-설계.md`. 단위 시험은 작은 장난감 회로로, 시험판 시험은
`tests/fixtures/board_v2_e4/배치.py` 로 잰다.
"""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'
TRIAL_E5 = ROOT / 'tests/fixtures/board_v2_e5/배치.py'


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

    def test_모르는_칩이면_멈춘다(self):
        c = _toy(self.mod, [], models={'U1': '74HC04', 'U2': '74HC4511'})
        with self.assertRaisesRegex(ValueError, 'DIP_PINS'):
            self.mod.place_check(c)

    def test_16핀_칩은_받는다(self):
        self.mod.place_check(_toy(self.mod, [], models={'U1': '74HC42', 'U2': '74HC08'}))

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

    def test_지문은_순위_여유가_바뀌면_바뀐다(self):
        a = _toy(self.mod, [])
        self.assertNotEqual(self.mod.place_hash([a], ('K1', 'K2')),
                            self.mod.place_hash([a], ('K1', 'K2'), slack=1.05))


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


class PlacePick(unittest.TestCase):
    """N6 — 통과 후보 중 최단 L* 의 ×slack 안에서 (밀도, 꺾임, 길이, layout 키) 최소(2026-10-05 사용자)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    @staticmethod
    def row(n, length, density, bends=0):
        return {'rank': n, 'layout': {'slots': {'K1': n}}, 'length': length, 'density': density, 'bends': bends}

    def test_띠_안에서는_밀도가_낮은_것(self):
        a, b = self.row(1, 10.0, 9.0), self.row(2, 10.1, 1.0)
        chosen, band = self.mod.place_pick([a, b], 1.02)
        self.assertIs(chosen, b)
        self.assertAlmostEqual(band, 10.2)

    def test_띠_밖은_밀도가_낮아도_못_이긴다(self):
        a, b = self.row(1, 10.0, 9.0), self.row(2, 11.0, 1.0)
        self.assertIs(self.mod.place_pick([a, b], 1.02)[0], a)

    def test_띠_경계는_안이다(self):
        a, b = self.row(1, 100.0, 9.0), self.row(2, 102.0, 1.0)
        self.assertIs(self.mod.place_pick([a, b], 1.02)[0], b)

    def test_동률이면_꺾임이_적은_것(self):
        a, b = self.row(1, 10.0, 1.0, bends=5), self.row(2, 10.1, 1.0, bends=3)
        self.assertIs(self.mod.place_pick([a, b], 1.02)[0], b)

    def test_완전_동률은_layout_키(self):
        a, b = self.row(2, 10.0, 1.0), self.row(1, 10.0, 1.0)
        self.assertIs(self.mod.place_pick([a, b], 1.02)[0], b)      # {"K1": 1} < {"K1": 2}
        self.assertIs(self.mod.place_pick([b, a], 1.02)[0], b)


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

    def test_기준은_다음_라운드를_다_본_뒤에(self):
        """1라운드 후보가 verify 에서 떨어져도 기준으로 끝내지 않고 다음 라운드를 본다(2026-10-05 사용자)."""
        calls = []

        def measure(lay):
            return {'length': 100.0 if lay == self.base else float(_gap(lay)), 'bends': 0, 'density': 1.0}

        def verify(lay):
            calls.append(lay)
            return 'R11 번호 원 가림' if len(calls) == 1 else None
        got = self.mod.place_plan(self.module(), top=1, measure=measure, verify=verify)
        self.assertNotEqual(got['layout'], self.base)
        self.assertNotIn(self.base, calls)
        self.assertEqual(sum(1 for r in got['rows'] if r['status'] == '✔ 고름'), 1)
        self.assertEqual(len(calls), 2)

    def test_병렬_실측은_라운드마다_한_묶음(self):
        """`mapper` 로 받은 실측은 라운드마다 한 번에 — 1라운드 묶음에는 기준도 든다."""
        batches = []

        def mapper(fn, items):
            batches.append((fn, len(items)))
            return [fn(x) for x in items]

        def measure(lay):
            return {'length': 100.0 if lay == self.base else float(_gap(lay)), 'bends': 0, 'density': 1.0}
        self.mod.place_plan(self.module(), top=4, measure=measure, verify=lambda lay: None,
                            mapper=mapper, chunk=3)
        self.assertEqual(batches[0], (measure, 5))

    def test_verify_는_라운드_대상을_chunk_개씩_전부(self):
        """띠 판정에는 통과 집합이 필요하니 라운드의 verify 대상은 첫 통과에서 멈추지 않고 전부 본다
        — `chunk` 개씩 묶어서(2026-10-05 순위 기준 N6)."""
        key = self.mod.layout_key
        sizes, calls = [], []

        def verify(lay):
            calls.append(key(lay))
            return 'R3 가림' if len(calls) == 1 else None

        def mapper(fn, items):
            if fn is verify:
                sizes.append(len(items))
            return [fn(x) for x in items]

        def measure(lay):
            return {'length': 100.0 if lay == self.base else float(_gap(lay)), 'bends': 0, 'density': 1.0}
        got = self.mod.place_plan(self.module(), top=100, measure=measure, verify=verify,
                                  mapper=mapper, chunk=3)
        eligible = [r for r in got['rows'] if r['rank'] != '기준']
        self.assertEqual(sum(sizes), len(eligible))
        self.assertTrue(all(n <= 3 for n in sizes), sizes)
        status = {key(r['layout']): r['status'] for r in got['rows']}
        self.assertEqual(status[calls[0]], 'verify: R3 가림')
        self.assertEqual(key(got['layout']), calls[1])

    def test_통과한_것_중_띠_안에서_밀도가_낮은_것(self):
        """N6 — 최단 통과 L*=100 의 ×1.02 안(≤102)에서 밀도 최소. 띠 밖(103)은 밀도가 낮아도 못 이긴다."""
        length = {10: 100.0, 11: 101.0, 12: 101.5, 13: 103.0}
        density = {10: 9.0, 11: 3.0, 12: 1.0, 13: 0.5}

        def measure(lay):
            if lay == self.base:
                return {'length': 200.0, 'bends': 0, 'density': 10.0}
            return {'length': length[_gap(lay)], 'bends': 0, 'density': density[_gap(lay)]}
        got = self.mod.place_plan(self.module(), top=100, measure=measure, verify=lambda lay: None)
        self.assertEqual(_gap(got['layout']), 12)
        self.assertEqual(got['slack'], self.mod.PLACE_LENGTH_SLACK)
        status = {}
        for r in got['rows']:
            if r['rank'] != '기준':
                status.setdefault(_gap(r['layout']), set()).add(r['status'])
        self.assertEqual(status[10], {'통과 — 띠 안'})
        self.assertEqual(status[13], {'통과 — 띠 밖'})
        self.assertIn('✔ 고름', status[12])

    def test_slack_1_이면_가장_짧은_것(self):
        length = {10: 100.0, 11: 101.0, 12: 101.5, 13: 103.0}
        density = {10: 9.0, 11: 3.0, 12: 1.0, 13: 0.5}

        def measure(lay):
            if lay == self.base:
                return {'length': 200.0, 'bends': 0, 'density': 10.0}
            return {'length': length[_gap(lay)], 'bends': 0, 'density': density[_gap(lay)]}
        got = self.mod.place_plan(self.module(), top=100, measure=measure, verify=lambda lay: None,
                                  slack=1.0)
        self.assertEqual(_gap(got['layout']), 10)
        self.assertNotEqual(got['hash'], self.mod.place_module_hash(self.module()))

    def test_실측과_verify_는_늘_mapper_로(self):
        """작업 프로세스에만 상태가 있으니 기준의 마지막 verify 도 mapper 를 거친다."""
        inside = []

        def mapper(fn, items):
            inside.append(True)
            try:
                return [fn(x) for x in items]
            finally:
                inside.pop()

        def measure(lay):
            assert inside, 'mapper 밖에서 실측'
            return {'length': 100.0 if lay == self.base else float(_gap(lay)), 'bends': 0, 'density': 1.0}

        def verify(lay):
            assert inside, 'mapper 밖에서 verify'
            return None if lay == self.base else 'R2 겹침'
        got = self.mod.place_plan(self.module(), top=2, measure=measure, verify=verify,
                                  mapper=mapper, chunk=2)
        self.assertEqual(got['layout'], self.base)

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

    def test_고를_것이_없을_때는_기준의_verify_사유를_댄다(self):
        """마지막 후보의 상태(기준보다 김 따위)가 아니라 기준이 떨어진 이유를 댄다(2026-10-05 최종 검토)."""
        def verify(lay):
            return 'R2 기준 겹침' if lay == self.base else 'R3 후보 가림'
        with self.assertRaisesRegex(AssertionError, 'R2 기준 겹침'):
            self.mod.place_plan(self.module(), top=100, measure=self.measure, verify=verify)

    def test_기본_verify_는_그림_폴더를_남기지_않는다(self):
        """verify 한 번에 단계 그림 열여섯 장 — 임시 폴더를 안 지우면 탐색마다 수백 MB 가 쌓인다(2026-10-05
        최종 검토)."""
        dirs = []

        def fn(path, template_path=None, stage=None, baseline=None):
            dirs.append(os.path.dirname(path))
            Path(path).write_bytes(b'png')
            return SimpleNamespace(snapshot=lambda: None)
        m = self.module()
        m.BOARDS, m.FINALS, m.RESTART = [('a.png', fn, 1)], [], set()

        def measure(lay):
            return {'length': 100.0 if lay == self.base else float(_gap(lay)), 'bends': 0, 'density': 1.0}
        self.mod.place_plan(m, top=2, rounds=1, measure=measure)
        self.assertTrue(dirs)
        self.assertFalse([d for d in dirs if os.path.exists(d)])

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

    def test_보고서_머리에_순위_규칙(self):
        got = self.mod.place_plan(self.module(), top=100, measure=self.measure, verify=lambda lay: None)
        self.assertIn('×1.02', self.mod.place_report(got, '장난감'))
        fake = {'hash': 'abc', 'layout': _LAY, 'rows': []}           # slack 없는 옛 결과
        self.assertIn('×1.02', self.mod.place_report(fake, '장난감'))


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


    def test_jobs_면_프로세스_풀로_실측과_verify_를_나눈다(self):
        from scripts.lab import place_search as ps
        mod = _load()
        result = {'hash': 'abc', 'layout': _LAY,
                  'rows': [dict(rank='기준', proxy=None, layout=_LAY, length=1.0, bends=0,
                                density=0.0, status='✔ 고름')]}
        got = {}

        def fake_plan(board, top, **kw):
            got.update(kw)
            return result
        mod.place_plan = fake_plan
        d = Path(tempfile.mkdtemp())
        ps.run(mod, SimpleNamespace(), d / '배치.py', 3, jobs=4)
        self.assertEqual(got['chunk'], 4)
        self.assertIs(got['measure'], ps.worker_measure)
        self.assertIs(got['verify'], ps.worker_verify)
        self.assertTrue(callable(got['mapper']))

    def test_작업_프로세스_verify_는_그림_폴더를_지운다(self):
        from scripts.lab import place_search as ps
        dirs = []

        def place_verify(board, lay, out_dir):
            dirs.append(out_dir)
            Path(out_dir, 'a.png').write_bytes(b'png')
            return None
        saved = dict(ps._W)
        ps._W.update(mod=SimpleNamespace(place_verify=place_verify), board=SimpleNamespace())
        try:
            self.assertIsNone(ps.worker_verify(_LAY))
        finally:
            ps._W.clear()
            ps._W.update(saved)
        self.assertEqual(len(dirs), 1)
        self.assertFalse(os.path.exists(dirs[0]))

class InputRows(unittest.TestCase):
    """입력 점퍼가 꽂히는 핀 행이 레일 빈 행이면 점퍼가 옆 행으로 비켜 사선이 된다 — 후보에서 뺀다
    (2026-10-05 시험판 첫 탐색: S1·D1 이 j8·j14 에 꽂혀 사선이 셋 생겼다)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_입력_핀_행이_레일_빈_행이면_None(self):
        c = _toy(self.mod, [], inputs=[('U1', 9)])                 # pin 9 = k+5
        self.assertIsNone(self.mod.place_proxy([c], {'K1': 3, 'K2': 17}))    # 8행 = 빈 행
        self.assertIsNotNone(self.mod.place_proxy([c], {'K1': 5, 'K2': 17}))  # 10행

    def test_a쪽_입력도_같다(self):
        c = _toy(self.mod, [], inputs=[('U2', 4)])                 # pin 4 = k+3
        self.assertIsNone(self.mod.place_proxy([c], {'K1': 3, 'K2': 17}))    # 20행 = 빈 행
        self.assertIsNotNone(self.mod.place_proxy([c], {'K1': 3, 'K2': 18}))


class TrialMarkers(unittest.TestCase):
    """시험판의 엔진 고정 부품(전원선·LED 사슬·입력 점퍼) 번호 원은 단계 그림·완성본 어디서나 같은 자리다
    — `place_marker_hints`(superset 판에서 비킨 자리)를 빌더가 준다(2026-10-05 최종 검토)."""

    def test_고정_부품_원은_그림마다_같은_자리(self):
        mod = _load()
        b = mod.load_board_file(TRIAL, 'board_v2_e4')
        for draw, stages in ((b._mux_draw, [1, 2, 3, 4, 5, 6, 7, 8, None]), (b._dmux_draw, [1, 2, 3, 4, None])):
            seen = {}
            for st in stages:
                bb = mod.BreadboardRenderer(None, board='v2')
                bb.enable_steps()
                draw(bb, st)
                for key, at in bb.settled_markers.items():
                    seen.setdefault(key, set()).add(tuple(at))
            moved = {k: v for k, v in seen.items() if len(v) > 1}
            self.assertEqual(moved, {}, draw.__name__)

class PlaceEnforced(unittest.TestCase):
    """v2 주차(와 시험판)는 `배치탐색.md` 가 있고, 지문이 지금 배선표와 같고, `LAYOUT` 이 보고서가 고른
    것과 같다 — 배선표를 바꾸고 배치를 다시 안 찾으면 여기서 걸린다(SKILL §4, 2026-10-05)."""

    def test_v2_주차는_배치를_찾았다(self):
        mod = _load()
        checked = []
        for f in sorted(ROOT.glob('보고서/실험*/결선도/배치.py')) + [TRIAL, TRIAL_E5]:
            b = mod.load_board_file(f, f.parent.name)
            if getattr(b, 'BOARD', None) != 'v2':
                continue
            rel = f.relative_to(ROOT).as_posix()
            self.assertTrue(hasattr(b, 'PLACE'), f'{rel}: v2 주차는 PLACE·SLOTS·LAYOUT 을 둔다(SKILL §4)')
            rep = f.parent / mod.PLACE_REPORT
            self.assertTrue(rep.exists(), f'{rep.name} 없음 — python -m scripts.lab.place_search {rel}')
            got = mod.read_place_report(rep)
            self.assertEqual(got['hash'], mod.place_module_hash(b),
                             f'{rel}: 배선표가 바뀌었다 — python -m scripts.lab.place_search {rel}')
            self.assertEqual(b.LAYOUT, got['layout'], f'{rel}: LAYOUT 이 {rep.name} 과 다르다')
            checked.append(f)
        self.assertIn(TRIAL, checked)
        self.assertIn(TRIAL_E5, checked)


def _layout_table_mismatches(mod, root):
    """`root` 아래 v2 주차마다 netlist `kind: layout` 표의 슬롯 행을 `LAYOUT['slots']` 와 맞댄다.
    돌려주는 값은 (맞댄 `배치.py` 목록, 어긋남 문장 목록)."""
    import re
    from scripts.lab import md
    from scripts.lab.netlist_parser import parse_netlist
    checked, errors = [], []
    for f in sorted(root.glob('보고서/실험*/결선도/배치.py')):
        net = f.parent / 'netlist.md'
        if not net.exists():
            continue
        b = mod.load_board_file(f, f.parent.parent.name)
        if getattr(b, 'BOARD', None) != 'v2':
            continue
        layouts = parse_netlist(net).of_kind('layout')
        if not layouts:
            continue
        rel = net.relative_to(root).as_posix()
        fix = f'{mod.PLACE_REPORT} 의 layout 을 netlist `kind: layout` 표에 옮겨 적는다(SKILL §4)'
        checked.append(f)
        if len(layouts) > 1:
            errors.append(f'{rel}: kind: layout 절이 {len(layouts)}개다 — 하나만 둔다')
            continue
        tables = md.parse_tables(layouts[0].body)
        if not tables:
            errors.append(f'{rel}: kind: layout 절에 `| 슬롯 | 자리 | 회로별 칩 |` 표가 없다 — {fix}')
            continue
        table = {}
        for row in tables[0].rows:
            m = re.fullmatch(r'(?:좌|우)\s*(\d+)행', row[1].strip())
            table[row[0]] = int(m.group(1)) if m else row[1]
        want = b.LAYOUT['slots']

        def say(v, missing):
            if v is None:
                return missing
            return f'{v}행' if isinstance(v, int) else f'`{v}`(`좌 <행>행` 꼴이 아니다)'

        for slot in sorted(set(table) | set(want)):
            got, row = table.get(slot), want.get(slot)
            if got != row:
                errors.append(f'{rel}: 슬롯 {slot} — 표는 {say(got, "표에 없음")}, '
                              f'LAYOUT 은 {say(row, "LAYOUT 에 없음")} — {fix}')
    return checked, errors


class PlaceLayoutTable(unittest.TestCase):
    """v2 주차 netlist `kind: layout` 표의 행은 배치기가 고른 `LAYOUT['slots']` 를 옮겨 적은 것이다
    (SKILL §4 배치기 문단·§4a 슬롯). v1 주차는 `test_breadboard_wiring` 이 빌더 슬롯 상수와 맞댄다."""

    _BOARD = "BOARD = 'v2'\nSLOTS = ('K1', 'K2')\nLAYOUT = {'slots': {'K1': 6, 'K2': 16}, 'leds': {}, 'bridge': [48, 49]}\n"
    _NETLIST = ('---\nschema: lab-netlist/v2\nexperiment: 99\nspec: ../체크리스트/명세.md\n---\n\n'
                '# 칩 자리표\n\n- kind: layout\n\n{table}\n'
                '# C1 · 장난감\n\n- kind: circuit\n- id: C1\n- item: E99.P1\n- tables: [T1]\n')

    def _week(self, k2='좌 16행', k1=True, table=True):
        """K1·K2 두 슬롯 주차. `k2` 는 K2 의 `자리` 칸, `k1=False` 면 K1 행을 빼고, `table=False` 면 표가 없다."""
        rows = ['| 슬롯 | 자리 | 회로별 칩 |', '|---|---|---|']
        rows += ['| K1 | 좌 6행 | C1 74HC04 |'] if k1 else []
        rows += [f'| K2 | {k2} | C1 74HC20 |']
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        d = tmp / '보고서/실험99/결선도'
        d.mkdir(parents=True)
        (d / '배치.py').write_text(self._BOARD, encoding='utf-8')
        body = '\n'.join(rows) + '\n' if table else '표 없이 산문만 있다.\n'
        (d / 'netlist.md').write_text(self._NETLIST.format(table=body), encoding='utf-8')
        return tmp, d / '배치.py'

    def _errors(self, **week):
        root, f = self._week(**week)
        checked, errors = _layout_table_mismatches(_load(), root)
        self.assertEqual(checked, [f])
        return errors

    def test_표_행이_LAYOUT_과_다르면_걸린다(self):
        errors = self._errors(k2='좌 17행')
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('슬롯 K2 — 표는 17행, LAYOUT 은 16행', errors[0])
        self.assertIn('배치탐색.md', errors[0])

    def test_표_행이_LAYOUT_과_같으면_통과한다(self):
        self.assertEqual(self._errors(), [])

    def test_표에_없는_슬롯도_걸린다(self):
        errors = self._errors(k1=False)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('슬롯 K1 — 표는 표에 없음, LAYOUT 은 6행', errors[0])

    def test_자리_칸_꼴이_틀리면_원문을_댄다(self):
        errors = self._errors(k2='좌 16')
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('표는 `좌 16`(`좌 <행>행` 꼴이 아니다)', errors[0])

    def test_표가_없는_layout_절도_걸린다(self):
        errors = self._errors(table=False)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('표가 없다', errors[0])

    def test_v2_주차_netlist_자리표는_LAYOUT_을_옮겨_적는다(self):
        checked, errors = _layout_table_mismatches(_load(), ROOT)
        if not checked:
            self.skipTest('netlist kind: layout 이 있는 v2 주차가 아직 없다 — 첫 v2 주차가 생기면 여기서 잰다')
        self.assertEqual(errors, [], '\n'.join(errors))


class PlacedTrial(unittest.TestCase):
    """시험판 LAYOUT 은 손 배치(2026-10-03)보다 superset 신호선 총길이가 짧고 밀도 합은 안 늘었다.
    손 배치 실측(2026-10-05, λ=0.5): MUX 길이 658.7·밀도 45.2, DMUX 303.9·6.3칸. 반올림한 값을 더하면
    손 배치 자신(962.58)이 통과하므로 px 그대로 적는다 — 길이 12515 + 5774 px, 밀도 859 + 119.5 px."""
    HAND_LENGTH = (12515 + 5774) / 19
    HAND_DENSITY = (859 + 119.5) / 19

    def test_손_배치보다_짧고_밀도는_안_는다(self):
        mod = _load()
        b = mod.load_board_file(TRIAL, 'board_v2_e4')
        m = mod._place_measure(list(b.PLACE), b.LAYOUT)
        self.assertNotIn('blocked', m)
        self.assertLess(m['length'], self.HAND_LENGTH)
        self.assertLessEqual(m['density'], self.HAND_DENSITY + 1e-9)


class Dip16Place(unittest.TestCase):
    """배치기의 DIP-16 — 슬롯 높이·레일 빈 행·브리지·핀 기하(설계 #6)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _one(self, model, wires=(), leds=(), inputs=()):
        return self.mod.PlaceCircuit('d', {'U1': 'K1'}, {'U1': model}, tuple(leds), tuple(wires),
                                     lambda bb, stage, superset, layout: None, tuple(inputs))

    def test_슬롯_행_수는_그_슬롯의_칩들(self):
        a = _toy(self.mod, [], models={'U1': '74HC42', 'U2': '74HC08'})
        b = self.mod.PlaceCircuit('b', {'U9': 'K1'}, {'U9': '74HC04'}, (), (),
                                  lambda bb, stage, superset, layout: None)
        self.assertEqual(self.mod.slot_rows([a, b], ('K1', 'K2', 'K3')),
                         {'K1': {7, 8}, 'K2': {7}, 'K3': {7}})

    def test_섞인_슬롯은_두_GND_행을_다_본다(self):
        # 3..8 중 k·k+6·k+7 이 레일 빈 행(8·14)이 아닌 것. 7 은 k+7 = 14, 8 은 k = 8
        ks = [c['K1'] for c in self.mod.slot_candidates(('K1',), rows={'K1': {7, 8}})]
        self.assertEqual(ks, [3, 4, 5, 6])
        self.assertIn(7, [c['K1'] for c in self.mod.slot_candidates(('K1',))])   # 14핀이면 7 도 된다

    def test_16핀_간격은_8행_더하기_빈_행(self):
        for c in self.mod.slot_candidates(('K1', 'K2'), rows={'K1': {8}, 'K2': {7}}):
            if c['K1'] < c['K2']:
                self.assertTrue(8 + 3 <= c['K2'] - c['K1'] <= 8 + 6, c)
            else:
                self.assertTrue(7 + 3 <= c['K1'] - c['K2'] <= 7 + 6, c)

    def test_브리지는_16핀_마지막_행_아래(self):
        self.assertEqual(self.mod.bridge_rows({'K1': 36}, {'K1': {8}}), [46, 47])   # 36+7+3
        self.assertEqual(self.mod.bridge_rows({'K1': 36}), [45, 46])                # 36+6+3

    def test_비용은_16핀_기하(self):
        f = self.mod.place_wire_cost({'U1': 10}, _w(('U1', 9), ('LED', 17)), {'U1': 16})   # 행 17, f쪽
        a = self.mod.place_wire_cost({'U1': 10}, _w(('U1', 8), ('LED', 17)), {'U1': 16})   # 행 17, a쪽
        self.assertGreaterEqual(a - f, 400)

    def test_가운데_레일_입력_행은_16핀_기하(self):
        c = self._one('74HC42', inputs=[('U1', 15), ('U1', 12)])    # 행 4, 7
        self.assertEqual(self.mod.mid_rail_rows(c, {'K1': 3}, [15, 16]), {3, 4, 7, 15, 16})

    def test_R10_은_16핀_행으로(self):
        w9, w11 = _w(('U1', 9), ('LED', 'L1')), _w(('U1', 11), ('LED', 'L2'))   # 행 k+7, k+5
        bad = self._one('74HC42', [w9, w11], leds=('L1', 'L2'))
        self.assertFalse(self.mod.place_r10_ok(bad, {'U1': 3}, {'L1': 10, 'L2': 20}))
        good = self._one('74HC42', [w11, w9], leds=('L2', 'L1'))
        self.assertTrue(self.mod.place_r10_ok(good, {'U1': 3}, {'L2': 10, 'L1': 20}))

    def test_근사는_16핀_슬롯의_브리지를_쓴다(self):
        c = self._one('74HC42', [_w(('U1', 9), ('LED', 'L1'))], leds=('L1',))
        _cost, lay = self.mod.place_proxy([c], {'K1': 3})
        self.assertEqual(lay['bridge'], self.mod.bridge_rows({'K1': 3}, {'K1': {8}}))


if __name__ == '__main__':
    unittest.main()
