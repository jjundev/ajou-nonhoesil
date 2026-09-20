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
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))
        cls.tmp = tempfile.mkdtemp()
        cls.and_bb = cls.b1.build_e1_and(os.path.join(cls.tmp, 'and.png'))
        cls.nand_bb = cls.b1.build_e1_nand(os.path.join(cls.tmp, 'nand.png'))

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

    def test_입력_점퍼가_이름으로_나온다(self):
        """손그림 검토 H15 가 참조의 신호 이름을 여기서 꺼낸다."""
        self.assertEqual([i['name'] for i in self.and_bb.wiring()['inputs']],
                         ['A', 'B', 'C'])

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
        self.assertEqual(slots, self.b1.E1_SLOTS)

    def test_모든_보드의_칩이_슬롯_위에_앉는다(self):
        seats = set(self.b1.E1_SLOTS.values())
        for name, fn, stage in self.b1.BOARDS:
            with self.subTest(board=name):
                bb = fn(os.path.join(self.tmp, name), stage=stage)
                for ch in bb.wiring()['chips']:
                    self.assertIn((ch['block'], ch['pin1_row']), seats)

    def test_보드_사슬은_9장_완성본은_4장이다(self):
        self.assertEqual(len(self.b1.BOARDS), 9)
        self.assertEqual(len(self.b1.FINALS), 4)
        names = [n for n, _f, _s in self.b1.BOARDS] + [n for n, _f in self.b1.FINALS]
        self.assertEqual(len(names), len(set(names)), '파일명이 겹친다')
        self.assertNotIn(self.b1.BOARDS[-1][0], [n for n, _f in self.b1.FINALS],
                         '마지막 단계 그림과 완성본은 다른 파일이어야 한다 — 완성본에는 회색이 없다')

    def test_OR_전환은_새_배선이_0가닥이다(self):
        """1-1→1-2 는 칩만 갈아끼운다 — 이 계획의 존재 이유다."""
        base = self.b1.build_e1_and(os.path.join(self.tmp, 'a.png')).snapshot()
        bb = self.b1.build_e1_or(os.path.join(self.tmp, 'o.png'), baseline=base)
        self.assertEqual([s['desc'] for s in bb.steps], ['좌 7행 칩 교체'])
        self.assertEqual(bb.removed(), [])


class WiringE2(unittest.TestCase):
    """실험02 — 같은 규약(슬롯·기준선·단계)을 따르는지. 정본은
    `보고서/실험02/결선도/netlist.md` 다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))
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
        self.assertEqual(slots, self.b2.E2_SLOTS)

    def test_모든_보드의_칩이_슬롯_위에_앉는다(self):
        seats = set(self.b2.E2_SLOTS.values())
        for name, fn, stage in self.b2.BOARDS:
            with self.subTest(board=name):
                bb = fn(os.path.join(self.tmp, name), stage=stage)
                for ch in bb.wiring()['chips']:
                    self.assertIn((ch['block'], ch['pin1_row']), seats)

    def test_보드_사슬은_2장_완성본은_1장이다(self):
        """교안 실험 2(AC 특성)는 조교 공지 `_350547_1` 로 하지 않는다 — 사슬에 없다."""
        self.assertEqual(len(self.b2.BOARDS), 2)
        self.assertEqual(len(self.b2.FINALS), 1)
        names = [n for n, _f, _s in self.b2.BOARDS] + [n for n, _f in self.b2.FINALS]
        self.assertEqual(len(names), len(set(names)), '파일명이 겹친다')
        self.assertNotIn(self.b2.BOARDS[-1][0], [n for n, _f in self.b2.FINALS])
        self.assertFalse(any('tpd' in n for n in names), names)

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
        made = {n for n, _f, _s in self.b2.BOARDS} | {n for n, _f in self.b2.FINALS}
        self.assertEqual(wanted, made)

    def test_슈미트_전환은_새_배선이_0가닥이다(self):
        """교안 p11: "앞선 회로 구성 및 설정을 유지하고, IC를 74HC14로 교체한다"."""
        base = self.b2.build_e2_inv(os.path.join(self.tmp, 'i.png')).snapshot()
        bb = self.b2.build_e2_schmitt(os.path.join(self.tmp, 's.png'), baseline=base)
        self.assertEqual([s['desc'] for s in bb.steps], ['좌 7행 칩 교체'])
        self.assertEqual(bb.removed(), [])


class WiringE3(unittest.TestCase):
    """실험03 — 같은 규약(슬롯·기준선·단계)을 따르는지. 정본은
    `보고서/실험03/결선도/netlist.md` 다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))
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
        self.assertEqual(slots, self.b3.E3_SLOTS)

    def test_모든_보드의_칩이_슬롯_위에_앉는다(self):
        seats = set(self.b3.E3_SLOTS.values())
        for name, fn, stage in self.b3.BOARDS:
            with self.subTest(board=name):
                bb = fn(os.path.join(self.tmp, name), stage=stage)
                for ch in bb.wiring()['chips']:
                    self.assertIn((ch['block'], ch['pin1_row']), seats)

    def test_그림_이름이_netlist_의_diagram_과_단계표를_덮는다(self):
        netlist = self._netlist()
        wanted = set()
        for c in netlist.circuits:
            if c.diagram:
                wanted.add(c.diagram)
            for st in c.stages:
                wanted.add(st['diagram'])
        made = {n for n, _f, _s in self.b3.BOARDS} | {n for n, _f in self.b3.FINALS}
        self.assertEqual(wanted, made)

    def test_보드_사슬은_8장_완성본은_2장이다(self):
        """2026-09-20 단계 세분화: C2 가 다섯 단계, C4 가 걷기 + 두 단계다."""
        self.assertEqual(len(self.b3.BOARDS), 8)
        self.assertEqual(len(self.b3.FINALS), 2)
        names = [n for n, _f, _s in self.b3.BOARDS] + [n for n, _f in self.b3.FINALS]
        self.assertEqual(len(names), len(set(names)), '파일명이 겹친다')
        self.assertNotIn(self.b3.BOARDS[-1][0], [n for n, _f in self.b3.FINALS])
        self.assertFalse(any(k in n for n in names for k in ('반가산기', '반감산기')), names)
        self.assertEqual(self.b3.BOARDS[5][0], '실험03_2-2_결선도_전감산기_0단계_걷기.png')

    def _chain(self):
        """`build_all` 과 같은 순서로 사슬을 이어 그린 렌더러 목록."""
        out, base = [], None
        for name, fn, stage in self.b3.BOARDS:
            bb = fn(os.path.join(self.tmp, name), stage=stage, baseline=base)
            out.append(bb)
            base = bb.snapshot()
        return out

    def test_단계마다_새_신호선이_셋_이하다(self):
        """단계 세분화의 전부다 — 확인이 실패하면 용의자가 방금 꽂은 셋이다."""
        for bb, (name, _fn, _stage) in zip(self._chain(), self.b3.BOARDS):
            with self.subTest(board=name):
                self.assertLessEqual(len(bb.new_signal), self.mod.STAGE_WIRE_BUDGET,
                                     f'{name}: {[k[1:] for k in bb.new_signal]}')

    def test_걷기_보드는_세_가닥이_유령이고_새_선이_없다(self):
        """LED2 최종 급전선도 걷는다 — 1단계에 그것이 A'·B 를 보는 프로브가 된다."""
        g = self._chain()[5]
        self.assertEqual([(r['n'], r['addr']) for r in g.removals()],
                         [(1, '좌 d7 → 우 a10'), (2, '좌 a9 → 우 c13'), (3, '우 c23 → 우 c29')])
        self.assertEqual(g.steps, [])
        self.assertTrue(g.partial)
        self.assertFalse(g.submit)
        # 걷기 보드가 뽑는 선은 "새 선" 이 아니다 — 렌더러의 계수 줄이 유령선 분기
        # 위로 올라가면 조용히 새 선으로 세어진다. 그 회귀를 여기서 막는다.
        self.assertEqual(g.new_signal, [])
        self.assertEqual([c['label'] for c in g.wiring()['chips']],
                         ['74HC86', '74HC08', '74HC32'])

    def test_주차_파일에_걷기_보드_build_래퍼가_없다(self):
        """`build_*` 래퍼는 `all_builders` 에 잡혀 가독성 검사 `steps > 0` 에 걸린다."""
        _name, fn, _stage = self.b3.BOARDS[5]
        self.assertEqual(fn.__module__, self.mod.__name__)

    def test_전가산기_1단계는_맨바닥에서_XOR1_과_임시_급전선만_꽂는다(self):
        _name, fn, stage = self.b3.BOARDS[0]
        self.assertEqual((fn, stage), (self.b3.build_e3_fa, 1))
        bb = fn(os.path.join(self.tmp, 'fa1.png'), stage=stage)
        self.assertEqual([c['label'] for c in bb.wiring()['chips']], ['74HC86'])
        self.assertEqual(bb.removed(), [])
        self.assertEqual(len(bb.new_signal), 3)
        self.assertTrue(any('임시 급전' in s['desc'] for s in bb.steps), bb.steps)

    def test_단계마다_임시_급전선을_한_가닥씩_걷는다(self):
        """2·4·5단계와 전감산기 2단계는 앞 단계의 프로브를 걷는다. 3단계는 걷지 않는다."""
        chain = self._chain()
        self.assertEqual([len(bb.removals()) for bb in chain], [0, 1, 0, 1, 1, 3, 0, 1])
        # 번호가 몇 개 붙는가 — `new_signal <= 3` 은 상한만 잰다. 1단계 16 은 맨바닥이라
        # 전원·레일·LED 사슬까지 세고, 걷기 보드 0 은 새 선도 순서표도 없다는 뜻이다.
        self.assertEqual([len(bb.steps) for bb in chain], [16, 3, 4, 3, 6, 0, 6, 3])

    def test_반감산기에는_단계가_없다(self):
        """반감산기는 조교 공지 `_350547_1` 로 하지 않는다 — 완성본만 남는다."""
        with self.assertRaises(ValueError):
            self.b3.build_e3_hs(os.path.join(self.tmp, 'x.png'), stage=1)
        with self.assertRaises(ValueError):
            self.b3.build_e3_fa(os.path.join(self.tmp, 'x.png'), stage=6)

    def test_전감산기_완성은_전가산기에서_두_가닥을_바꾼다(self):
        """AND1 pin 1 의 A 갈래와 AND2 pin 4 의 A⊕B. Ci 점퍼·LED 사슬은 그대로다 —
        기준선은 끝점으로 비교하므로 이름이 Ci→Bi 로 바뀌어도 회색으로 남는다."""
        base = self.b3.build_e3_fa(os.path.join(self.tmp, 'fa.png')).snapshot()
        bb = self.b3.build_e3_fs(os.path.join(self.tmp, 'fs.png'), baseline=base)
        removed = bb.removed()
        self.assertEqual(len(removed), 2, removed)
        self.assertTrue(any('74HC08 pin 1' in r for r in removed), removed)
        self.assertTrue(any('74HC08 pin 4' in r for r in removed), removed)
        self.assertFalse(any('뽑는다' in r for r in removed), removed)

    def test_전감산기_74HC86_은_왼쪽에_11리드_오른쪽에_1리드다(self):
        """R7(2026-09-20)의 근거 숫자. 실험03 은 게이트 1·2 만 써서 배선이 칩 왼쪽
        a~d 열 7행에 몰렸다 — 실험실에서 꽂기도 확인도 힘들었다. 승인본은 legacy 로
        고정하고 이 숫자를 회귀로 남긴다."""
        bb = self.b3.build_e3_fs(os.path.join(self.tmp, 'fs_density.png'))
        by = {(s['chip'], s['side']): s for s in bb.side_leads()}
        self.assertEqual(by[('74HC86', 'a')]['count'], 11)
        self.assertEqual(by[('74HC86', 'f')]['count'], 1)
        self.assertEqual(by[('74HC86', 'f')]['addrs'], ['좌 g7'])
        self.assertEqual(by[('74HC08', 'a')]['count'], 7)
        self.assertEqual(by[('74HC08', 'f')]['count'], 1)
        # 칩마다 (a, f) 두 항목, self.chips 순서
        self.assertEqual([(s['chip'], s['side']) for s in bb.side_leads()],
                         [('74HC86', 'a'), ('74HC86', 'f'), ('74HC08', 'a'), ('74HC08', 'f'),
                          ('74HC04', 'a'), ('74HC04', 'f'), ('74HC32', 'a'), ('74HC32', 'f')])
        # 칩 핀(e·f 열)은 세지 않는다 — 74HC86 좌 e7~e13 은 리드지만 지표 밖이다
        self.assertNotIn('좌 e7', by[('74HC86', 'a')]['addrs'])


if __name__ == '__main__':
    unittest.main()
