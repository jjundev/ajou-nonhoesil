"""렌더러가 **자기가 그린 것**을 기호 좌표로 내놓는지 검사한다.

손그림 검토(`review-hand-diagram`)는 이 출력을 정답으로 삼는다. 픽셀이 아니라
(블록, 열, 행) 으로 내는 이유는 손그림 전사가 '좌 b10' 같은 주소로 적히기
때문이다 — 양쪽을 같은 말로 맞춰야 비교가 된다.

문자열을 파싱해서 알아내지 않는다. `_leads` 에는 '74HC08 pin 3' 같은 뜻풀이가
들어 있지만 그건 사람이 읽는 말이지 계약이 아니다. 그리는 쪽이 사실을 그대로
적어 두게 한다.
"""
import importlib.util
import os
import shutil
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.tmp = tempfile.mkdtemp()
        cls.and_bb = cls.mod.build_e1_and(os.path.join(cls.tmp, 'and.png'))
        cls.nand_bb = cls.mod.build_e1_nand(os.path.join(cls.tmp, 'nand.png'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_빌더가_렌더러를_돌려준다(self):
        self.assertIsInstance(self.and_bb, self.mod.BreadboardRenderer)

    def test_sym_은_픽셀_x_를_열_이름으로_바꾼다(self):
        bb = self.and_bb
        c = bb.cols['left']
        self.assertEqual(bb.sym(c['b'], 10), ('left', 'b', 10))
        self.assertEqual(bb.sym(c['mid_vcc'], 3), ('left', 'mid_vcc', 3))
        self.assertIsNone(bb.sym(95, 10))

    def test_칩은_라벨과_pin1_행과_핀_배치를_남긴다(self):
        chips = self.and_bb.wiring()['chips']
        self.assertEqual([c['label'] for c in chips], ['74HC08'])
        chip = chips[0]
        self.assertEqual(chip['pin1_row'], 7)
        self.assertEqual(chip['block'], 'left')
        # pin 1~7 은 e 열, pin 8~14 는 f 열. draw_chip 이 그렇게 꽂는다
        self.assertEqual(chip['pins'][1], ('left', 'e', 7))
        self.assertEqual(chip['pins'][7], ('left', 'e', 13))
        self.assertEqual(chip['pins'][14], ('left', 'f', 7))
        self.assertEqual(chip['pins'][8], ('left', 'f', 13))

    def test_배선은_양_끝을_기호_좌표로_남긴다(self):
        wires = self.and_bb.wiring()['wires']
        ends = {(w['frm'], w['to']) for w in wires}
        # pin 14 -> 중앙 VCC 레일 (connect_power)
        self.assertIn((('hole', ('left', 'g', 7)),
                       ('hole', ('left', 'mid_vcc', 7))), ends)

    def test_전원잭_끝점은_홀이_아니라_잭으로_남는다(self):
        wires = self.and_bb.wiring()['wires']
        jacks = {w['frm'] for w in wires if w['frm'][0] == 'jack'}
        self.assertEqual(jacks, {('jack', 'red'), ('jack', 'gray')})

    def test_LED_사슬은_네_홀을_한_묶음으로_남긴다(self):
        chains = {ch['tag']: ch for ch in self.and_bb.wiring()['chains']}
        self.assertEqual(set(chains), {'L1', 'L2'})
        l2 = chains['L2']
        # led_chain(c['a'], 25, "L2", ...) — 도착 a25, LED 는 옆 열, 저항은 그 다음
        self.assertEqual(l2['anode'][2], 25)
        self.assertEqual(l2['cathode'][2], 26)
        self.assertEqual(l2['res_top'][2], 26)
        self.assertEqual(l2['res_bottom'][2], 28)
        self.assertEqual(l2['anode'][1], l2['cathode'][1])
        self.assertNotEqual(l2['anode'][1], l2['res_top'][1])

    def test_미사용_입력과_출력이_따로_남는다(self):
        w = self.and_bb.wiring()
        self.assertEqual({(u['chip'], u['pin']) for u in w['unused_inputs']},
                         {('74HC08', 9), ('74HC08', 10), ('74HC08', 12), ('74HC08', 13)})
        self.assertEqual({(u['chip'], u['pin']) for u in w['unused_outputs']},
                         {('74HC08', 8), ('74HC08', 11)})
        self.assertTrue(all(u['rail'] is None for u in w['unused_inputs']))

    def test_레일_브리지가_열_이름_쌍으로_남는다(self):
        bridges = self.and_bb.wiring()['bridges']
        pairs = {(k, a[1], b[1]) for k, a, b in bridges}
        self.assertIn(('gnd', 'gnd', 'mid_gnd'), pairs)
        self.assertIn(('vcc', 'vcc', 'mid_vcc'), pairs)

    def test_레일_브리지가_실제로_꽂힌_행을_담는다(self):
        """1행을 박아 두면 레일 빈 행이라 손그림 검토가 H1 을 헛낸다.

        `_bridged` 는 중복 방지 키라 행이 없다. 행을 따로 기록해야 한다.
        """
        for kind, a, b in self.and_bb.wiring()['bridges']:
            self.assertEqual(a[2], b[2], kind)
            self.assertNotIn(a[2], self.mod.RAIL_GAP_ROWS)
        rows = {k: a[2] for k, a, _b in self.and_bb.wiring()['bridges']}
        self.assertEqual(rows, {'gnd': 29, 'vcc': 30})

    def test_칩이_둘인_회로는_둘_다_남는다(self):
        chips = self.nand_bb.wiring()['chips']
        self.assertEqual([c['label'] for c in chips], ['74HC08', '74HC00'])
        self.assertEqual([c['pin1_row'] for c in chips], [7, 18])

    def test_빌더_칩_자리가_netlist_자리표와_같다(self):
        """슬롯 정본은 netlist 의 `kind: layout` 표다. 빌더 상수는 그 사본이라
        여기서 맞댄다 — 한쪽만 고치면 체크리스트 자리표와 그림이 갈린다."""
        import re
        from scripts.lab import config, md
        from scripts.lab.netlist_parser import parse_netlist
        netlist = parse_netlist(os.path.join(REPO_ROOT, config.experiment_dir(1), '결선도', 'netlist.md'))
        layouts = netlist.of_kind('layout')
        self.assertEqual(len(layouts), 1, 'netlist 에 kind: layout 절이 하나 있어야 한다')
        table = md.parse_tables(layouts[0].body)[0]
        slots = {}
        for row in table.rows:
            m = re.match(r'(좌|우)\s*(\d+)행', row[1])
            self.assertIsNotNone(m, row)
            slots[row[0]] = ({'좌': 'left', '우': 'right'}[m.group(1)], int(m.group(2)))
        self.assertEqual(slots, self.mod.E1_SLOTS)

    def test_모든_보드의_칩이_슬롯_위에_앉는다(self):
        seats = set(self.mod.E1_SLOTS.values())
        for name, fn, stage in self.mod.E1_BOARDS:
            with self.subTest(board=name):
                bb = fn(os.path.join(self.tmp, name), stage=stage)
                for ch in bb.wiring()['chips']:
                    self.assertIn((ch['block'], ch['pin1_row']), seats)

    def test_보드_사슬은_9장_완성본은_4장이다(self):
        self.assertEqual(len(self.mod.E1_BOARDS), 9)
        self.assertEqual(len(self.mod.E1_FINALS), 4)
        names = [n for n, _f, _s in self.mod.E1_BOARDS] + [n for n, _f in self.mod.E1_FINALS]
        self.assertEqual(len(names), len(set(names)), '파일명이 겹친다')
        self.assertNotIn(self.mod.E1_BOARDS[-1][0], [n for n, _f in self.mod.E1_FINALS],
                         '마지막 단계 그림과 완성본은 다른 파일이어야 한다 — 완성본에는 회색이 없다')

    def test_OR_전환은_새_배선이_0가닥이다(self):
        """1-1→1-2 는 칩만 갈아끼운다 — 이 계획의 존재 이유다."""
        base = self.mod.build_e1_and(os.path.join(self.tmp, 'a.png')).snapshot()
        bb = self.mod.build_e1_or(os.path.join(self.tmp, 'o.png'), baseline=base)
        self.assertEqual([s['desc'] for s in bb.steps], ['좌 7행 칩 교체'])
        self.assertEqual(bb.removed(), [])


class WiringE2(unittest.TestCase):
    """실험02 — 같은 규약(슬롯·기준선·단계)을 따르는지. 정본은
    `보고서/실험02/결선도/netlist.md` 다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.tmp = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_빌더_칩_자리가_netlist_자리표와_같다(self):
        import re
        from scripts.lab import config, md
        from scripts.lab.netlist_parser import parse_netlist
        netlist = parse_netlist(os.path.join(REPO_ROOT, config.experiment_dir(2), '결선도', 'netlist.md'))
        layouts = netlist.of_kind('layout')
        self.assertEqual(len(layouts), 1)
        table = md.parse_tables(layouts[0].body)[0]
        slots = {}
        for row in table.rows:
            m = re.match(r'(좌|우)\s*(\d+)행', row[1])
            self.assertIsNotNone(m, row)
            slots[row[0]] = ({'좌': 'left', '우': 'right'}[m.group(1)], int(m.group(2)))
        self.assertEqual(slots, self.mod.E2_SLOTS)

    def test_모든_보드의_칩이_슬롯_위에_앉는다(self):
        seats = set(self.mod.E2_SLOTS.values())
        for name, fn, stage in self.mod.E2_BOARDS:
            with self.subTest(board=name):
                bb = fn(os.path.join(self.tmp, name), stage=stage)
                for ch in bb.wiring()['chips']:
                    self.assertIn((ch['block'], ch['pin1_row']), seats)

    def test_보드_사슬은_4장_완성본은_2장이다(self):
        self.assertEqual(len(self.mod.E2_BOARDS), 4)
        self.assertEqual(len(self.mod.E2_FINALS), 2)
        names = [n for n, _f, _s in self.mod.E2_BOARDS] + [n for n, _f in self.mod.E2_FINALS]
        self.assertEqual(len(names), len(set(names)), '파일명이 겹친다')
        self.assertNotIn(self.mod.E2_BOARDS[-1][0], [n for n, _f in self.mod.E2_FINALS])

    def test_그림_이름이_netlist_의_diagram_과_단계표를_덮는다(self):
        """netlist 가 가리키는 파일을 빌더가 전부 만든다 — 한쪽만 고치면 인쇄본에
        빈 브레드보드가 들어간다."""
        from scripts.lab import config
        from scripts.lab.netlist_parser import parse_netlist
        netlist = parse_netlist(os.path.join(REPO_ROOT, config.experiment_dir(2), '결선도', 'netlist.md'))
        wanted = set()
        for c in netlist.circuits:
            if c.diagram:
                wanted.add(c.diagram)
            for st in c.stages:
                wanted.add(st['diagram'])
        made = {n for n, _f, _s in self.mod.E2_BOARDS} | {n for n, _f in self.mod.E2_FINALS}
        self.assertEqual(wanted, made)

    def test_슈미트_전환은_새_배선이_0가닥이다(self):
        """교안 p11: "앞선 회로 구성 및 설정을 유지하고, IC를 74HC14로 교체한다"."""
        base = self.mod.build_e2_inv(os.path.join(self.tmp, 'i.png')).snapshot()
        bb = self.mod.build_e2_schmitt(os.path.join(self.tmp, 's.png'), baseline=base)
        self.assertEqual([s['desc'] for s in bb.steps], ['좌 7행 칩 교체'])
        self.assertEqual(bb.removed(), [])

    def test_tpd_1단계는_C2_의_pull_선_다섯_가닥을_걷는다(self):
        """U1 은 여섯 게이트를 전부 쓰므로 C2 의 미사용 입력 pull 선이 전부 걷힌다."""
        base = self.mod.build_e2_schmitt(os.path.join(self.tmp, 's.png')).snapshot()
        bb = self.mod.build_e2_tpd(os.path.join(self.tmp, 't1.png'), stage=1, baseline=base)
        removed = bb.removed()
        self.assertEqual(sum('미사용 입력' in r for r in removed), 5, removed)
        # 같은 자리(S1)의 칩 교체는 removed 가 아니라 순서표 첫 줄이다
        self.assertEqual(bb.steps[0]['desc'], '좌 7행 칩 교체')


class WiringE3(unittest.TestCase):
    """실험03 — 같은 규약(슬롯·기준선·단계)을 따르는지. 정본은
    `보고서/실험03/결선도/netlist.md` 다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.tmp = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _netlist(self):
        from scripts.lab import config
        from scripts.lab.netlist_parser import parse_netlist
        return parse_netlist(os.path.join(REPO_ROOT, config.experiment_dir(3), '결선도', 'netlist.md'))

    def test_빌더_칩_자리가_netlist_자리표와_같다(self):
        import re
        from scripts.lab import md
        layouts = self._netlist().of_kind('layout')
        self.assertEqual(len(layouts), 1)
        table = md.parse_tables(layouts[0].body)[0]
        slots = {}
        for row in table.rows:
            m = re.match(r'(좌|우)\s*(\d+)행', row[1])
            self.assertIsNotNone(m, row)
            slots[row[0]] = ({'좌': 'left', '우': 'right'}[m.group(1)], int(m.group(2)))
        self.assertEqual(slots, self.mod.E3_SLOTS)

    def test_모든_보드의_칩이_슬롯_위에_앉는다(self):
        seats = set(self.mod.E3_SLOTS.values())
        for name, fn, stage in self.mod.E3_BOARDS:
            with self.subTest(board=name):
                bb = fn(os.path.join(self.tmp, name), stage=stage)
                for ch in bb.wiring()['chips']:
                    self.assertIn((ch['block'], ch['pin1_row']), seats)

    def test_보드_사슬은_8장_완성본은_4장이다(self):
        self.assertEqual(len(self.mod.E3_BOARDS), 8)
        self.assertEqual(len(self.mod.E3_FINALS), 4)
        names = [n for n, _f, _s in self.mod.E3_BOARDS] + [n for n, _f in self.mod.E3_FINALS]
        self.assertEqual(len(names), len(set(names)), '파일명이 겹친다')
        self.assertNotIn(self.mod.E3_BOARDS[-1][0], [n for n, _f in self.mod.E3_FINALS])

    def test_그림_이름이_netlist_의_diagram_과_단계표를_덮는다(self):
        netlist = self._netlist()
        wanted = set()
        for c in netlist.circuits:
            if c.diagram:
                wanted.add(c.diagram)
            for st in c.stages:
                wanted.add(st['diagram'])
        made = {n for n, _f, _s in self.mod.E3_BOARDS} | {n for n, _f in self.mod.E3_FINALS}
        self.assertEqual(wanted, made)

    def test_전감산기_1단계는_반감산기를_뜯지_않는다(self):
        """C3→C4 는 네 칩이 전부 자리에 있다 — 뽑는 칩도 걷는 인버터 배선도 없다.
        처음 저작에서 74HC04·74HC32 가 "뽑는다" 로 나왔던 결함의 회귀 방지다."""
        base = self.mod.build_e3_hs(os.path.join(self.tmp, 'hs.png')).snapshot()
        bb = self.mod.build_e3_fs(os.path.join(self.tmp, 'fs1.png'), stage=1, baseline=base)
        removed = bb.removed()
        self.assertFalse(any('뽑는다' in r for r in removed), removed)
        self.assertEqual(len(removed), 1, removed)   # LED1 급전선 하나만 옮긴다

    def test_반감산기_1단계는_전가산기_확장_여덟_가닥을_걷는다(self):
        base = self.mod.build_e3_fa(os.path.join(self.tmp, 'fa.png')).snapshot()
        bb = self.mod.build_e3_hs(os.path.join(self.tmp, 'hs1.png'), stage=1, baseline=base)
        self.assertEqual(len(bb.removed()), 8, bb.removed())


if __name__ == '__main__':
    unittest.main()
