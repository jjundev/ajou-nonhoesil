"""넷 모델과 규칙 H1~H15 를 검사한다.

**홀 좌표가 아니라 넷으로 비교한다.** 칩이 참조보다 한 행 위에 있어도 주변
배선이 같이 옮겨져 있으면 그림은 유효하다 — 2026-09-08 손그림 세 쪽이 전부
그랬다. `regen_compare` 가 결선도를 간선 집합으로 보는 것과 같은 이유다.

살아 있는 실험01 참조 결선도를 한 군데씩 망가뜨려 검사기가 그 자리를 짚는지
본다. 합성 픽스처로는 실물에서만 나오는 배치를 못 밟는다.
"""
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.lab import hand_compare as hc
from scripts.lab.hand_grid import load_renderer
from scripts.lab.hand_transcript import Diagram, chip_pins, parse_transcript


def _wire(a, b, kind='sig'):
    return {'kind': kind, 'desc': '', 'frm': ('hole', a), 'to': ('hole', b)}


def _shift_rows(d, delta):
    """그림 전체를 delta 행만큼 옮긴다. 레일 빈 행은 피하지 않으므로
    빈 행에 걸리지 않는 delta 만 쓴다."""
    def s(hole):
        return None if hole is None else (hole[0], hole[1], hole[2] + delta)

    for ch in d.chips:
        ch['pin1_row'] += delta
        ch['pins'] = {p: s(h) for p, h in ch['pins'].items()}
    for w in d.wires:
        for side in ('frm', 'to'):
            kind, val = w[side]
            w[side] = (kind, s(val)) if kind == 'hole' else (kind, val)
    for l in d.leds:
        l['anode'], l['cathode'] = s(l['anode']), s(l['cathode'])
    for r in d.resistors:
        r['top'], r['bottom'] = s(r['top']), s(r['bottom'])
    for c in d.chains:
        for k in ('signal', 'anode', 'cathode', 'res_top', 'res_bottom'):
            if k in c:
                c[k] = s(c[k])
    d.bridges = [(k, s(a), s(b)) for k, a, b in d.bridges]
    return d


_MIRROR = {'a': 'j', 'b': 'i', 'c': 'h', 'd': 'g', 'e': 'f',
           'f': 'e', 'g': 'd', 'h': 'c', 'i': 'b', 'j': 'a',
           'gnd': 'gnd', 'vcc': 'vcc',
           'mid_gnd': 'mid_gnd', 'mid_vcc': 'mid_vcc'}


def _flip_chip(d, index, wiring=True):
    """index 번째 칩을 뒤집는다(pin 1 이 f 열). `wiring=True` 면 그 칩 행에
    끝점이 있는 요소도 좌우 거울상으로 옮긴다 — 배선이 함께 뒤집힌 그림이다.
    `False` 면 칩만 뒤집고 배선은 참조 자리에 둔다."""
    ch = d.chips[index]
    rows = range(ch['pin1_row'], ch['pin1_row'] + 7)
    ch['pin1_col'] = 'f'
    ch['pins'] = chip_pins(ch['block'], ch['pin1_row'], 'f')
    if not wiring:
        return d

    def m(hole):
        if hole is None or hole[2] not in rows:
            return hole
        return (hole[0], _MIRROR[hole[1]], hole[2])

    for w in d.wires:
        for side in ('frm', 'to'):
            kind, val = w[side]
            w[side] = (kind, m(val)) if kind == 'hole' else (kind, val)
    for l in d.leds:
        l['anode'], l['cathode'] = m(l['anode']), m(l['cathode'])
    for r in d.resistors:
        r['top'], r['bottom'] = m(r['top']), m(r['bottom'])
    for c in d.chains:
        for k in ('signal', 'anode', 'cathode', 'res_top', 'res_bottom'):
            if k in c:
                c[k] = m(c[k])
    d.bridges = [(k, m(a), m(b)) for k, a, b in d.bridges]
    return d


class Nodes(unittest.TestCase):
    def test_같은_행_a부터e_는_한_노드다(self):
        self.assertEqual(hc.node_of(('left', 'a', 10)),
                         hc.node_of(('left', 'e', 10)))

    def test_같은_행이라도_f부터j_는_다른_노드다(self):
        self.assertNotEqual(hc.node_of(('left', 'a', 10)),
                            hc.node_of(('left', 'f', 10)))

    def test_레일은_행을_무시한다(self):
        self.assertEqual(hc.node_of(('left', 'gnd', 3)),
                         hc.node_of(('left', 'gnd', 40)))

    def test_좌우_중앙레일은_서로_다른_도체다(self):
        self.assertNotEqual(hc.node_of(('left', 'mid_gnd', 10)),
                            hc.node_of(('right', 'mid_gnd', 10)))


class Nets(unittest.TestCase):
    def test_점퍼가_두_스트립을_잇는다(self):
        d = Diagram(wires=[_wire(('left', 'a', 10), ('left', 'a', 20))])
        nets = hc.build_nets(d)
        self.assertEqual(nets[hc.node_of(('left', 'c', 10))],
                         nets[hc.node_of(('left', 'e', 20))])

    def test_LED_는_스트립을_잇지_않는다(self):
        d = Diagram(leds=[{'tag': 'L1', 'anode': ('left', 'c', 14),
                           'cathode': ('left', 'c', 15)}])
        nets = hc.build_nets(d)
        self.assertNotEqual(nets[hc.node_of(('left', 'c', 14))],
                            nets[hc.node_of(('left', 'c', 15))])


class Signatures(unittest.TestCase):
    def _chip(self, row=10, label='74HC08'):
        from scripts.lab.hand_transcript import chip_pins
        return {'label': label, 'block': 'left', 'pin1_row': row,
                'pins': chip_pins('left', row)}

    def test_pin14_가_VCC_레일에_닿으면_서명에_VCC_가_있다(self):
        d = Diagram(chips=[self._chip()],
                    wires=[_wire(('left', 'g', 10), ('left', 'mid_vcc', 10), 'vcc')])
        sig = hc.signatures(d)
        self.assertIn(('RAIL', 'VCC'), sig[('74HC08', 14)])
        self.assertNotIn(('RAIL', 'GND'), sig[('74HC08', 14)])

    def test_레일_이름이_아니라_극성만_서명에_들어간다(self):
        """좌 GND 로 내렸든 중앙 GND 로 내렸든 같은 뜻이다 — 브리지 유무는
        H8 이 따로 본다. 한 결함을 두 번 보고하지 않는다."""
        a = Diagram(chips=[self._chip()],
                    wires=[_wire(('left', 'd', 16), ('left', 'gnd', 16), 'gnd')])
        b = Diagram(chips=[self._chip()],
                    wires=[_wire(('left', 'd', 16), ('left', 'mid_gnd', 16), 'gnd')])
        self.assertEqual(hc.signatures(a)[('74HC08', 7)],
                         hc.signatures(b)[('74HC08', 7)])

    def test_행이_통째로_밀려도_서명은_같다(self):
        """칩과 배선이 함께 옮겨지면 유효한 그림이다."""
        a = Diagram(chips=[self._chip(10)],
                    wires=[_wire(('left', 'g', 10), ('left', 'mid_vcc', 10), 'vcc')])
        b = Diagram(chips=[self._chip(9)],
                    wires=[_wire(('left', 'g', 9), ('left', 'mid_vcc', 9), 'vcc')])
        self.assertEqual(hc.signatures(a)[('74HC08', 14)],
                         hc.signatures(b)[('74HC08', 14)])

    def test_같은_종류_칩_둘이면_둘째에_샵2_가_붙는다(self):
        d = Diagram(chips=[self._chip(7, '74HC04'), self._chip(18, '74HC04')])
        keys = {k for k, _ in hc.signatures(d)}
        self.assertEqual(keys, {'74HC04', '74HC04#2'})

    def test_LED_애노드가_핀_서명에_들어간다(self):
        d = Diagram(chips=[self._chip()],
                    leds=[{'tag': 'L2', 'anode': ('left', 'c', 15),
                           'cathode': ('left', 'c', 16)}],
                    wires=[_wire(('left', 'd', 15), ('left', 'c', 15))])
        self.assertIn(('LED', 'L2', 'A'), hc.signatures(d)[('74HC08', 6)])


class Reference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nand = hc.reference_diagram('e1_nand')

    def test_참조가_Diagram_으로_나온다(self):
        self.assertEqual([c['label'] for c in self.nand.chips],
                         ['74HC08', '74HC00'])
        self.assertEqual([c['pin1_row'] for c in self.nand.chips], [7, 18])

    def test_참조_pin14_는_VCC_이고_pin7_은_GND_다(self):
        sig = hc.signatures(self.nand)
        for chip in ('74HC08', '74HC00'):
            self.assertIn(('RAIL', 'VCC'), sig[(chip, 14)])
            self.assertNotIn(('RAIL', 'GND'), sig[(chip, 14)])
            self.assertIn(('RAIL', 'GND'), sig[(chip, 7)])

    def test_참조_미사용_출력은_아무_데도_안_닿는다(self):
        sig = hc.signatures(self.nand)
        for chip, pin in [('74HC08', 6), ('74HC08', 8), ('74HC00', 11)]:
            self.assertEqual(sig[(chip, pin)], frozenset())

    def test_참조_LED_사슬은_캐소드와_저항_윗다리가_한_넷이다(self):
        nets = hc.build_nets(self.nand)
        for ch in self.nand.chains:
            self.assertEqual(nets[hc.node_of(ch['cathode'])],
                             nets[hc.node_of(ch['res_top'])])

    def test_참조_칩_사이_연결이_서명에_보인다(self):
        sig = hc.signatures(self.nand)
        self.assertIn(('PIN', '74HC00', 1), sig[('74HC08', 3)])

    def test_모르는_회로_ID_는_거절한다(self):
        with self.assertRaises(hc.CompareError):
            hc.reference_diagram('e9_없음')

    def test_다섯_회로가_모두_열린다(self):
        for cid in ('e1_and', 'e1_or', 'e1_nand', 'e1_nor', 'e1_comb'):
            d = hc.reference_diagram(cid)
            self.assertTrue(d.chips, cid)

    def test_from_wiring_은_입력_w의_resistors를_변형하지_않는다(self):
        w = {
            'chips': [], 'wires': [], 'inputs': [], 'leds': [],
            'resistors': [{'top': ('left', 'd', 15), 'bottom': ('left', 'd', 17), 'label': '330Ω'}],
            'chains': [{'tag': 'L1', 'res_top': ('left', 'd', 15)}],
            'unused_inputs': [], 'unused_outputs': [], 'bridges': [], 'overlaps': [],
        }
        r_before = dict(w['resistors'][0])
        d = hc._from_wiring(w, 'test')
        self.assertEqual(w['resistors'][0], r_before)
        self.assertNotIn('tag', w['resistors'][0])
        self.assertEqual(d.resistors[0]['tag'], 'L1')

    def test_참조_배선에는_브리지가_없다(self):
        """브리지가 wires 와 bridges 양쪽에 있으면 `check_holes` 가 같은 홀을
        두 번 세어 H2 가 헛난다."""
        ends = {frozenset((a, b)) for _k, a, b in self.nand.bridges}
        self.assertTrue(ends)
        for w in self.nand.wires:
            if w['frm'][0] == 'hole' and w['to'][0] == 'hole':
                self.assertNotIn(frozenset((w['frm'][1], w['to'][1])), ends)

    def test_배선_설명_문구가_바뀌어도_브리지가_남는다(self):
        """산문 대조를 쓰면 문구 한 글자에 참조 브리지가 통째로 사라지고,
        폴백이 1행을 주어 회로마다 H1 치명이 4건 헛난다."""
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            bb = hc.load_renderer().load_board(1).build_e1_nand(os.path.join(t, 'x.png'))
        w = bb.wiring()
        for x in w['wires']:
            if x.get('desc') == '레일 브리지':
                x['desc'] = '레일 브리지(전원 연결)'
        d = hc._from_wiring(w, 'e1_nand')
        self.assertEqual(len(d.bridges), 2)
        self.assertEqual([f for f in hc.check_holes(d, d) if f.rule == 'H1'], [])


class SelfCompare(unittest.TestCase):
    def test_참조를_그대로_손그림으로_넣으면_결함_0건(self):
        """정답을 정답과 견주어 결함이 나오면 검사기가 틀린 것이다."""
        for cid in ('e1_and', 'e1_or', 'e1_nand', 'e1_nor'):
            ref = hc.reference_diagram(cid)
            hand = hc.reference_diagram(cid)
            hand.title = cid
            bad = [f for f in hc.compare(ref, hand) if f.grade != '표기']
            self.assertEqual(bad, [], f"{cid}: {[str(x) for x in bad]}")


class Physical(unittest.TestCase):
    def _hand(self, cid='e1_nand'):
        d = hc.reference_diagram(cid)
        return d

    def test_H1_레일_빈_행에_꽂은_끝점을_잡는다(self):
        hand = self._hand()
        hand.wires.append({'kind': 'gnd', 'desc': '',
                           'frm': ('hole', ('left', 'gnd', 14)),
                           'to': ('hole', ('left', 'b', 14))})
        rules = {f.rule for f in hc.compare(hc.reference_diagram('e1_nand'), hand)}
        self.assertIn('H1', rules)

    def test_H1_63행_밖은_잡는다(self):
        hand = self._hand()
        hand.wires.append({'kind': 'sig', 'desc': '',
                           'frm': ('hole', ('left', 'a', 70)),
                           'to': ('hole', ('left', 'b', 70))})
        rules = {f.rule for f in hc.compare(hc.reference_diagram('e1_nand'), hand)}
        self.assertIn('H1', rules)

    def test_H2_한_홀에_리드_둘을_잡는다(self):
        hand = self._hand()
        chip = hand.chips[0]
        hand.wires.append({'kind': 'sig', 'desc': '',
                           'frm': ('hole', chip['pins'][1]),
                           'to': ('hole', ('left', 'a', 30))})
        found = [f for f in hc.compare(hc.reference_diagram('e1_nand'), hand)
                 if f.rule == 'H2']
        self.assertTrue(found)
        self.assertIn('e7', found[0].where)

    def test_H2_는_참조에서는_안_난다(self):
        ref = hc.reference_diagram('e1_nand')
        self.assertEqual([f for f in hc.check_holes(ref, ref) if f.rule == 'H2'], [])


class Power(unittest.TestCase):
    """2026-09-08 손그림 3쪽은 뒷단 74HC00 오른쪽이 통째로 비어 있었다 —
    pin 14 전원과 pin 9·10·12·13 접지 다섯 가닥이 없었다. 위 칩과 나란히
    놓고 봐야 보이는 결함이라 사람 눈으로는 놓치기 쉽다."""

    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        return ref, hand

    def _drop_wires_touching(self, d, hole):
        node = hc.node_of(hole)
        d.wires = [w for w in d.wires
                   if hc._endpoint_node(w['frm']) != node
                   and hc._endpoint_node(w['to']) != node]

    def test_H3_pin14_전원이_없으면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[1]['pins'][14])
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H3']
        self.assertTrue(found)
        self.assertIn('74HC00', found[0].where)
        self.assertEqual(found[0].grade, '치명')

    def test_H3_pin7_접지가_없으면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[1]['pins'][7])
        rules = {f.rule for f in hc.compare(ref, hand)}
        self.assertIn('H3', rules)

    def test_H3_pin14_를_GND_에_물리면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[1]['pins'][14])
        hand.wires.append({'kind': 'gnd', 'desc': '',
                           'frm': ('hole', ('left', 'g', 18)),
                           'to': ('hole', ('left', 'mid_gnd', 18))})
        msgs = ' '.join(f.message for f in hc.compare(ref, hand) if f.rule == 'H3')
        self.assertIn('GND', msgs)

    def test_H4_미사용_입력_접지가_빠지면_잡는다(self):
        """참조가 `rail: 'gnd'` 로 접지한 미사용 입력이 손그림에 없으면 H4 다
        (실험02 처럼 교안이 접지를 지시한 주차)."""
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[0]['pins'][9])
        ref.unused_inputs = [{'chip': '74HC08', 'pin': 9, 'rail': 'gnd',
                              'block': 'left', 'pin1_row': ref.chips[0]['pin1_row']}]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H4']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '기능')

    def test_H4_개방_미사용_입력은_아무것도_요구하지_않는다(self):
        """`rail: None` 은 접지 생략(실험01 규칙)이다. 손그림에 선이 없어도 H4 가 아니다."""
        ref, hand = self._pair()
        ref.unused_inputs = [{'chip': '74HC08', 'pin': 9, 'rail': None,
                              'block': 'left', 'pin1_row': ref.chips[0]['pin1_row']}]
        self.assertEqual([f for f in hc.compare(ref, hand) if f.rule == 'H4'], [])

    def test_H5_미사용_출력을_접지하면_잡는다(self):
        ref, hand = self._pair()
        hand.wires.append({'kind': 'gnd', 'desc': '',
                           'frm': ('hole', ('left', 'g', 10)),
                           'to': ('hole', ('left', 'mid_gnd', 10))})
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H5']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')
        self.assertIn('개방', found[0].message)

    def test_H3_참조_칩이_손그림에_없으면_잡는다(self):
        ref, hand = self._pair()
        hand.chips = [hand.chips[0]]  # 74HC00 제거
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H3']
        self.assertTrue(found)
        missing_chip = [f for f in found if f.where == '74HC00']
        self.assertTrue(missing_chip)
        self.assertEqual(missing_chip[0].grade, '치명')
        self.assertIn('참조에 있는 칩이 손그림에 없다', missing_chip[0].message)


class Signals(unittest.TestCase):
    """4쪽은 74HC02 pin 3 으로 가는 입력 C 가 없었고, 5쪽은 74HC32 pin 1 로
    가는 A 갈래가 없었다. 둘 다 '있어야 할 것이 없다' 라 원도만 보고는
    안 보인다 — 5쪽 갈래는 참조 그림에서 초록 선 아래 깔려 있기까지 했다."""

    def _pair(self, cid='e1_nor'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        return ref, hand

    def test_레일_넷은_극성_토큰_하나로_접힌다(self):
        """입력은 GND 레일 홀에서 들어오도록 그려져 입력 핀이 GND 넷에 앉는다.
        실험01 NAND 에서 그 넷 부착물이 21개다 — 접지 않으면 레일 어디가
        흔들려도 입력 핀 전부가 H6 을 낸다."""
        ref = hc.reference_diagram('e1_nand')
        sig = hc.signatures(ref)
        self.assertEqual(sig[('74HC08', 1)], frozenset({('RAIL', 'GND')}))
        self.assertEqual(sig[('74HC08', 7)], frozenset({('RAIL', 'GND')}))
        self.assertEqual(sig[('74HC08', 14)], frozenset({('RAIL', 'VCC')}))

    def test_레일이_없는_넷은_그대로_열거된다(self):
        """칩 사이 연결은 접으면 안 된다 — 거기가 신호선이다."""
        ref = hc.reference_diagram('e1_nand')
        sig = hc.signatures(ref)
        self.assertIn(('PIN', '74HC00', 1), sig[('74HC08', 3)])

    def test_미사용_입력_접지가_빠져도_입력핀은_조용하다(self):
        """접기 전에는 이 한 가닥 때문에 H6 이 3건 헛났다.

        슬롯 고정 이후 실험01 실측 규칙(2026-09-11)으로 미사용 입력은 더
        접지하지 않는다(rail=None, `mark_unused_inputs`) — 실물 e1_nand 에는
        이제 이 배선 자체가 없다. 폴딩 로직은 여전히 검증해야 하므로 그 규칙이
        살아 있던 시절의 배선(공유 GND 레일에 미사용 입력 한 가닥)을 참조
        위에 합성해 재현한다.
        """
        def _prep():
            d = hc.reference_diagram('e1_nand')
            pin9 = d.chips[0]['pins'][9]
            d.unused_inputs = [dict(u, rail='gnd') if (u['chip'], u['pin']) == ('74HC08', 9)
                               else dict(u) for u in d.unused_inputs]
            d.wires = list(d.wires) + [_wire(pin9, (d.chips[0]['block'], 'gnd', pin9[2]))]
            return d
        ref = _prep()
        hand = _prep()
        node = hc.node_of(hand.chips[0]['pins'][9])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        fs = hc.compare(ref, hand)
        self.assertEqual([f for f in fs if f.rule == 'H6'], [])
        self.assertTrue([f for f in fs if f.rule == 'H4'])

    def test_입력이_통째로_빠지면_접은_뒤에도_잡는다(self):
        """접기가 진짜 결함까지 삼키면 안 된다 — 4쪽의 실제 결함이다."""
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        node = hc.node_of(hand.chips[1]['pins'][2])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H6']
        self.assertTrue(found)
        self.assertIn('74HC00 pin 2', found[0].where)
        self.assertIn('GND 레일', found[0].message)

    def test_H6_입력이_빠지면_잡는다(self):
        ref, hand = self._pair()
        node = hc.node_of(hand.chips[1]['pins'][3])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H6']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')

    def test_H6_칩_사이_연결이_빠지면_잡는다(self):
        ref, hand = self._pair('e1_nand')
        node = hc.node_of(hand.chips[1]['pins'][1])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        msgs = ' '.join(f.message for f in hc.compare(ref, hand) if f.rule == 'H6')
        self.assertIn('74HC08', msgs)

    def test_H6_출력_둘이_한_넷이면_잡는다(self):
        """5쪽에서 Z 선과 A·B 선이 한 홀에서 만났다 — 출력끼리 맞물린다."""
        ref, hand = self._pair('e1_comb')
        a = hand.chips[0]['pins'][4]      # 74HC04 출력
        b = hand.chips[1]['pins'][3]      # 74HC08 출력
        hand.wires.append({'kind': 'mid', 'desc': '',
                           'frm': ('hole', (a[0], 'd', a[2])),
                           'to': ('hole', (b[0], 'd', b[2]))})
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H6']
        self.assertTrue(found)

    def test_H6_행이_통째로_밀린_그림은_통과한다(self):
        """칩과 배선이 함께 한 행 내려간 그림은 유효하다."""
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H6']
        self.assertEqual([str(x) for x in found], [])

    def test_H6_참조_숨김_배선은_칩과_핀_모두_일치할_때만_알린다(self):
        """오버랩 경고가 다른 칩의 같은 번호 핀에 오탐으로 붙지 않는다."""
        ref = hc.reference_diagram('e1_comb')
        ref.overlaps = ['가로 c10~c20 — [신호선] 74HC32 pin 1 / [신호선] 기타']
        self.assertIn('참조 그림에서', hc._reference_hidden(ref, '74HC32', 1))
        self.assertEqual(hc._reference_hidden(ref, '74HC08', 1), '')
        self.assertEqual(hc._reference_hidden(ref, '74HC32', 2), '')


class LedChain(unittest.TestCase):
    """**1차 검토가 통째로 건너뛴 검사다.** 3·4쪽 L1 저항이 LED 캐소드 행이
    아니라 애노드 행에서 시작해 LED 가 아예 안 켜지는데, 칩 배선만 보면
    멀쩡해 보인다. 그래서 코드로 강제한다."""

    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        return ref, hand

    def _chain(self, d, tag):
        return next(c for c in d.chains if c['tag'] == tag)

    def test_H7_저항이_한_행_위면_잡는다(self):
        ref, hand = self._pair()
        ch = self._chain(hand, 'L1')
        top = ch['res_top']
        ch['res_top'] = (top[0], top[1], top[2] - 1)
        for r in hand.resistors:
            if r['tag'] == 'L1':
                r['top'] = ch['res_top']
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H7']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')
        self.assertIn('캐소드', found[0].message)

    def test_H7_저항_아랫다리가_GND_에_안_닿으면_잡는다(self):
        ref, hand = self._pair()
        ch = self._chain(hand, 'L1')
        node = hc.node_of(ch['res_bottom'])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H7']
        self.assertTrue(found)
        self.assertIn('GND', found[0].message)

    def test_H7_사슬이_통째로_없으면_잡는다(self):
        ref, hand = self._pair()
        hand.chains = [c for c in hand.chains if c['tag'] != 'L2']
        hand.leds = [l for l in hand.leds if l['tag'] != 'L2']
        hand.resistors = [r for r in hand.resistors if r.get('tag') != 'L2']
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H7']
        self.assertTrue(found)
        self.assertIn('L2', found[0].where)


class Rails(unittest.TestCase):
    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        return ref, hand

    def test_H8_브리지가_없으면_잡는다(self):
        ref, hand = self._pair()
        hand.bridges = []
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H8']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')

    def test_H8_브리지가_있으면_안_난다(self):
        ref, hand = self._pair()
        self.assertEqual([f for f in hc.compare(ref, hand) if f.rule == 'H8'], [])


class BridgeRows(unittest.TestCase):
    """H9 는 행만 말하므로 행만 비교해야 한다."""

    def _pair(self):
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        hand.title = '2-1 NAND Gate'
        return ref, hand

    def test_종류가_없어도_행이_같으면_조용하다(self):
        """전사가 kind 를 빠뜨리면 '[29,30]인데 [29,30]이다' 가 나왔다."""
        ref, hand = self._pair()
        hand.bridges = [('', a, b) for _k, a, b in hand.bridges]
        self.assertEqual([f for f in hc.compare(ref, hand) if f.rule == 'H9'], [])

    def test_아래로_내려간_브리지에는_경고를_붙인다(self):
        ref, hand = self._pair()
        hand.bridges = [(k, (a[0], a[1], a[2] + 4), (b[0], b[1], b[2] + 4))
                        for k, a, b in hand.bridges]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H9']
        self.assertTrue(found)
        self.assertIn('아래', found[0].message)
        self.assertIn('[33, 34]', found[0].message)

    def test_위로_올라간_브리지에는_경고를_안_붙인다(self):
        """round2 는 28·29행인데 '30행 아래' 경고를 받았다."""
        ref, hand = self._pair()
        hand.bridges = [(k, (a[0], a[1], a[2] - 1), (b[0], b[1], b[2] - 1))
                        for k, a, b in hand.bridges]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H9']
        self.assertTrue(found)
        self.assertNotIn('아래', found[0].message)
        self.assertIn('영향이 없다', found[0].message)


class UnshiftedRailEndpoints(unittest.TestCase):
    """레일 끝점의 **행**은 "따라왔는가" 판정에 들어가지 않는다.

    `node_of` 가 레일 홀을 `('R', block, col)` 로 접는다 — 같은 레일이면 몇
    행에 꽂았든 한 노드다. 그런데 `_unshifted_elements` 는 배선을 홀 쌍으로
    맞추므로, 레일 행까지 되돌려 비교하면 **부품 쪽만 따라 옮기고 레일 홀은
    원래 자리에 둔 그림**을 "안 따라온 것" 으로 짚는다. 레일은 길어서 아무
    데나 꽂는 것이 정상이라 이건 오탐이다.

    이 검사는 `compare()` 가 아니라 `_unshifted_elements` 를 직접 겨눈다.
    통합 레벨에서는 `check_chip_follow` 의 충돌 검사가 이 차이를 흡수해
    판정이 똑같이 나온다 — 실측으로 참조 회로 둘 × delta 셋 × 레일 고정·동반
    12개 시나리오 전부 출력이 같았다. 그래서 여기서만 붙들 수 있다.
    """

    def test_레일_끝점의_행은_따라옴_판정에_안_들어간다(self):
        # 참조: d10 은 GND 5행에, d11 은 GND 9행에 물려 있다.
        # 손그림(delta=1): d11-GND9 를 그대로 뒀다 — 참조 좌표와 같으니
        # 홀 쌍으로만 보면 "안 따라온 배선" 이다. 그러나 되돌린 d10 이
        # 참조에서 같은 GND 레일에 물려 있으므로 따라온 것으로 봐야 한다.
        d10, d11 = ('left', 'd', 10), ('left', 'd', 11)
        ref = Diagram(wires=[_wire(d10, ('left', 'gnd', 5)),
                             _wire(d11, ('left', 'gnd', 9))])
        hand = Diagram(wires=[_wire(d11, ('left', 'gnd', 9))])
        self.assertEqual(hc._unshifted_elements(ref, hand, delta=1), [])

    def test_레일이_아닌_끝점은_행이_다르면_안_따라온_것이다(self):
        # 위 관용이 레일 밖으로 새면 진짜 소실을 놓친다. 같은 배치에서
        # 레일 자리를 보통 홀(g 열)로 바꾸면 그대로 짚혀야 한다.
        d10, d11 = ('left', 'd', 10), ('left', 'd', 11)
        ref = Diagram(wires=[_wire(d10, ('left', 'g', 5)),
                             _wire(d11, ('left', 'g', 9))])
        hand = Diagram(wires=[_wire(d11, ('left', 'g', 9))])
        self.assertEqual(
            [h for _, h in hc._unshifted_elements(ref, hand, delta=1)],
            [d11, ('left', 'g', 9)])


class ChipFollow(unittest.TestCase):
    """2026-09-09 시험 PDF: 74HC00 을 한 행 위(17행)에 그리고 아래 배선은 전부
    따라갔는데 L1 저항만 참조 자리(e15→e17)에 남았다. H7 이 증상을, H10 이
    행 차이를 각각 냈지만 둘을 잇는 줄은 사람이 요약할 때 만들었다. 그 줄이
    H14 다 — 칩 이름·이동량·남은 요소를 한 줄에 낸다.

    2026-09-12 슬롯 고정 이후 실험01 결선도의 L1 사슬은 c/d 열이 아니라
    d/e 열을 쓴다 — 픽스처도 그 열로 다시 낸다(`hand_e1_nand_chip_up_one.json`).
    """

    FIXTURE = Path(__file__).parent / 'fixtures' / 'hand_e1_nand_chip_up_one.json'

    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.title = '2-1 NAND Gate'
        return ref, hand

    def test_H14_실물_전사에서_칩이_올라가고_L1_저항이_남으면_잡는다(self):
        hand = parse_transcript(self.FIXTURE)
        ref = hc.reference_diagram(hand.circuit)
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual(len(found), 1)
        f = found[0]
        self.assertEqual(f.grade, '치명')
        self.assertEqual(f.where, '74HC00')
        self.assertIn('-1행', f.message)
        self.assertIn('L1 저항 아랫다리 좌 e17', f.message)
        self.assertIn('pin 1 행', f.message)
        # 74HC08 은 참조 자리 그대로다 — 줄이 없다
        self.assertNotIn('74HC08', f.message)

    def test_H14_는_증상_줄을_지우지_않는다(self):
        """H7 은 여전히 저항 아랫다리를 짚는다. H14 는 원인 줄이다."""
        hand = parse_transcript(self.FIXTURE)
        ref = hc.reference_diagram(hand.circuit)
        rules = {f.rule for f in hc.compare(ref, hand)}
        self.assertIn('H7', rules)
        self.assertIn('H10', rules)
        self.assertIn('H14', rules)

    def test_전체가_함께_밀린_그림에는_H14_가_없다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual([str(x) for x in found], [])

    def test_권장_수정을_적용하면_H14_와_H7_이_사라진다(self):
        """실물 전사에서 저항 아랫다리만 e17 → e16 으로 올린다. L1 LED(d14·d15)와
        저항 윗다리(e15)는 여전히 참조 자리 그대로지만 74HC00 은 17~23행이라
        충돌이 없다 — 참조 좌표에 남았다는 것만으로는 H14 를 내지 않는다.
        2026-09-09 요약이 권한 수정이 정확히 이것이다."""
        hand = parse_transcript(self.FIXTURE)
        ref = hc.reference_diagram(hand.circuit)
        fixed = ('left', 'e', 16)
        for r in hand.resistors:
            if r['tag'] == 'L1':
                r['bottom'] = fixed
        for c in hand.chains:
            if c['tag'] == 'L1':
                c['res_bottom'] = fixed
        # 이 픽스처는 2026-09-09 전사라 labels 가 없다 — 여기서 보려는 것은 H14·H7 이다
        hand.labels = list(ref.labels)
        found = hc.compare(ref, hand)
        self.assertEqual([str(f) for f in found if f.rule in ('H14', 'H7')], [])
        self.assertEqual([str(f) for f in found if f.grade in hc.BLOCKING], [])
        self.assertEqual(hc.verdict(found), '제출 가능')

    def test_칩만_뒤집고_배선을_두면_H14_가_난다(self):
        ref, hand = self._pair()
        _flip_chip(hand, 1, wiring=False)
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].where, '74HC00')
        self.assertIn('f 열', found[0].message)
        self.assertIn('배선 끝점', found[0].message)

    def test_배선까지_함께_뒤집으면_H14_없이_H10_표기만_난다(self):
        """넷이 같으면 유효한 그림이다 — 행 밀림과 같은 원리."""
        ref, hand = self._pair()
        _flip_chip(hand, 1, wiring=True)
        found = hc.compare(ref, hand)
        self.assertEqual([str(f) for f in found if f.rule == 'H14'], [])
        self.assertEqual([str(f) for f in found if f.grade == '치명'], [])
        h10 = [f for f in found if f.rule == 'H10']
        self.assertEqual(len(h10), 1)
        self.assertIn('f 열', h10[0].message)


class Paperwork(unittest.TestCase):
    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.title = '2-1 NAND Gate'
        return ref, hand

    def test_H9_브리지_행이_다르면_표기로_알린다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        hand.title = '2-1 NAND Gate'
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H9']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '표기')

    def test_H10_칩이_밀리면_표기로만_알린다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        hand.title = '2-1 NAND Gate'
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H10']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '표기')

    def test_H10_칩이_뒤집히면_표기로_알린다(self):
        """노치가 아래를 보게 그린 칩. 배선이 함께 뒤집혀 있으면 회로는 맞다."""
        ref, hand = self._pair()
        ch = hand.chips[1]
        ch['pin1_col'] = 'f'
        ch['pins'] = chip_pins(ch['block'], ch['pin1_row'], 'f')
        found = [f for f in hc.check_placement(ref, hand) if f.rule == 'H10']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].grade, '표기')
        self.assertEqual(found[0].where, '74HC00')
        self.assertIn('f 열', found[0].message)

    def test_서명이_없어도_H12_를_내지_않는다(self):
        ref, hand = self._pair()
        self.assertNotIn('H12', [f.rule for f in hc.compare(ref, hand)])

    def test_H11_제목이_회로와_다르면_잡는다(self):
        ref, hand = self._pair()
        hand.title = '2-2 NAND Gate'
        hand.circuit = 'e1_nor'
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H11']
        self.assertTrue(found)

    def test_H13_uncertain_은_보류로_나온다(self):
        ref, hand = self._pair()
        hand.uncertain = {('left', 'd', 17)}
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H13']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '보류')


class Labels(unittest.TestCase):
    """H15. 2026-09 실험01 예보 조교 감점(-1) — 손그림에 입력 A·B·C 표기가 없었다."""

    def _pair(self, cid='e1_and'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.title = '1-1 AND Gate'
        return ref, hand

    def test_참조는_입력과_LED_꼬리표를_이름으로_갖는다(self):
        self.assertEqual([lb['name'] for lb in hc.reference_diagram('e1_and').labels],
                         ['A', 'B', 'C', 'L1', 'L2'])
        self.assertEqual([lb['name'] for lb in hc.reference_diagram('e1_comb').labels],
                         ['A', 'B', 'Z', 'X', 'Y'])

    def test_계측_지점_이름도_참조_이름이_된다(self):
        """입력 점퍼도 LED 도 없는 주차(실험02) — 교안 회로도의 신호원·출력·채널 이름이
        H15 대상이다."""
        for cid, want in (('e2_inv', ['VIN', 'VOUT']), ('e2_tpd', ['VIN', 'CH1', 'CH2'])):
            with self.subTest(cid=cid):
                self.assertEqual([lb['name'] for lb in hc.reference_diagram(cid).labels],
                                 want)

    def test_이름이_하나_빠지면_기능으로_잡는다(self):
        ref, hand = self._pair()
        hand.labels = [lb for lb in hand.labels if lb['name'] != 'B']
        found = hc.compare(ref, hand)
        self.assertEqual([(f.grade, f.where) for f in found if f.rule == 'H15'],
                         [('기능', 'B')])
        self.assertIn('연결 대상을 판독할 수 없다',
                      next(f.message for f in found if f.rule == 'H15'))
        self.assertEqual(hc.verdict(found), '수정 필요')

    def test_이름이_다_있으면_조용하다(self):
        ref, hand = self._pair()
        self.assertEqual([f for f in hc.compare(ref, hand) if f.rule == 'H15'], [])

    def test_반감산기_참조는_입력_B_와_출력_B_를_둘_다_갖는다(self):
        """실험3 반감산기는 교안 p6 그대로 입력과 출력이 같은 글자 `B` 다."""
        self.assertEqual([lb['name'] for lb in hc.reference_diagram('e3_hs').labels],
                         ['A', 'B', 'D', 'B'])

    def test_같은_글자의_둘째가_빠지면_개수로_잡는다(self):
        ref, hand = self._pair('e3_hs')
        hand.title = '2-1 반감산기'
        drop = max(i for i, lb in enumerate(hand.labels) if lb['name'] == 'B')
        hand.labels = [lb for i, lb in enumerate(hand.labels) if i != drop]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H15']
        self.assertEqual([(f.grade, f.where) for f in found], [('기능', 'B')])
        self.assertIn('참조 2 · 그림 1', found[0].message)

    def test_이름표가_없는_전사는_이름마다_잡힌다(self):
        """2026-09 실험01 제출 손그림이 이 상태였다 — A·B·C 가 한 글자도 없었다."""
        ref, hand = self._pair()
        hand.labels = []
        self.assertEqual([f.where for f in hc.compare(ref, hand) if f.rule == 'H15'],
                         ['A', 'B', 'C', 'L1', 'L2'])

    def test_대소문자는_가리지_않는다(self):
        ref, hand = self._pair()
        hand.labels = [{'name': lb['name'].lower(), 'at': None} for lb in hand.labels]
        self.assertEqual([f for f in hc.compare(ref, hand) if f.rule == 'H15'], [])


class NewWeeks(unittest.TestCase):
    """실험02·03 회로를 참조로 꺼내 자기 대조한다 — 서명만 채우면 finding 이 없어야 한다.

    2026-09-14 전에는 `CIRCUITS` 에 e1 만 있어 두 주차 손그림을 검토할 수 없었다.
    같은 날 조교 공지 `_350547_1` 로 실험02 AC 특성·실험03 반가산기·반감산기의 단계
    그림 ID 가 빠졌다.
    """

    def test_실험02_03_회로가_자기_대조에서_조용하다(self):
        cids = [c for c in hc.CIRCUITS if c.startswith(('e2_', 'e3_'))]
        # 2026-09-20 단계 세분화: 실험03 절차 래퍼가 셋에서 일곱으로 늘어 11 → 15 다.
        self.assertEqual(len(cids), 15)
        for cid in cids:
            with self.subTest(cid=cid):
                ref = hc.reference_diagram(cid)
                hand = hc.reference_diagram(cid)
                self.assertEqual([str(f) for f in hc.compare(ref, hand)], [])

    def test_전원핀이_모서리가_아닌_칩도_자기_대조에서_조용하다(self):
        """74HC76(VCC 5·GND 13)·7490(VCC 5·GND 10) 은 DIP 모서리 규칙이 안 맞는다.

        2026-11-07 전에는 `power_pins` 가 (n, n/2) 를 박아 실험08 참조끼리 대조해도
        `74HC76 pin 8 — 전원 단락` 치명 2건이 났다. 렌더러 `dip_power` 표를 따른다.
        """
        for cid in ('e6_jk', 'e8_counter', 'e8_bcd'):
            with self.subTest(cid=cid):
                ref = hc.reference_diagram(cid)
                hand = hc.reference_diagram(cid)
                self.assertEqual([str(f) for f in hc.compare(ref, hand)], [])

    def test_74HC76_전원핀은_5와_13이다(self):
        ref = hc.reference_diagram('e8_counter')
        self.assertEqual(hc.power_pins(ref)['74HC76'], (5, 13))


class Verdict(unittest.TestCase):
    def test_치명이_있으면_수정_필요(self):
        f = [hc.HandFinding('H3', '치명', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '수정 필요')

    def test_기능이_있으면_수정_필요(self):
        f = [hc.HandFinding('H4', '기능', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '수정 필요')

    def test_표기만_있으면_제출_가능(self):
        """표기는 막지 않는다 — 별도 줄로만 알린다."""
        f = [hc.HandFinding('H11', '표기', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '제출 가능')

    def test_보류만_있으면_제출_가능(self):
        f = [hc.HandFinding('H13', '보류', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '제출 가능')


class Judgment(unittest.TestCase):
    def test_판정문에_쪽별_결함과_총평이_들어간다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        hand.title = '2-2 NAND Gate'
        hand.circuit = 'e1_nor'
        hand.page = 3
        md = hc.judgment_markdown([(3, 'e1_nand', hc.compare(ref, hand), hand)],
                                  round_no=1)
        self.assertIn('round1', md)
        self.assertIn('3쪽', md)
        self.assertIn('제출 가능', md)
        self.assertIn('H11', md)

    def test_치명이_있으면_총평이_수정_필요다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        node = hc.node_of(hand.chips[1]['pins'][14])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        md = hc.judgment_markdown([(3, 'e1_nand', hc.compare(ref, hand), hand)], 1)
        self.assertIn('수정 필요', md)


class RuleRegistry(unittest.TestCase):
    def test_check_로_시작하는_함수는_전부_규칙_목록에_있다(self):
        """함수만 만들고 `_RULES` 에 안 올리면 검사가 조용히 빠진다.
        2026-09-08 1차 검토가 LED 사슬을 건너뛴 것이 바로 그 실패였다."""
        defined = {v for k, v in vars(hc).items()
                   if k.startswith('check_') and callable(v)}
        self.assertEqual(defined, set(hc._RULES))

    def test_규칙_코드가_H12_만_빼고_H1부터_H15까지_빠짐없다(self):
        import inspect
        src = inspect.getsource(hc)
        for n in range(1, 16):
            if n == 12:
                self.assertNotIn("'H12'", src)
            else:
                self.assertIn(f"'H{n}'", src, f'H{n} 규칙이 없다')


class V2Compare(unittest.TestCase):
    """판형이 다르면 견주지 않고, v2 가운데 레일은 한 레일로 본다."""

    def test_판형이_다르면_견주지_않는다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = replace(hc.reference_diagram('e1_nand'), board='v2')
        with self.assertRaisesRegex(hc.CompareError, '판형 버전 불일치'):
            hc.compare(ref, hand)

    def test_참조는_빌더의_판형을_싣는다(self):
        self.assertEqual(hc.reference_diagram('e1_nand').board, 'v1')

    def test_v2_가운데_레일_주소는_접두어가_없다(self):
        self.assertEqual(hc._addr(('left', 'mid_gnd', 9), 'v2'), '중앙GND레일9행')
        self.assertEqual(hc._addr(('left', 'mid_gnd', 9)), '좌 중앙GND레일9행')

    def test_v2_연기_시험판은_자기_자신과_넷이_같다(self):
        root = Path(__file__).resolve().parents[1]
        board = load_renderer().load_board_file(root / 'tests/fixtures/board_v2/배치.py', 'board_v2')
        with tempfile.TemporaryDirectory() as d:
            bb = board.build_v2_smoke(os.path.join(d, 'x.png'))
        ref = hc._from_wiring(bb.wiring(), 'v2_smoke', bb.board)
        for rule in (hc.check_holes, hc.check_power, hc.check_signals,
                     hc.check_led_chains, hc.check_rails):
            self.assertEqual(rule(ref, ref), [], rule.__name__)


class Dip16Negative(unittest.TestCase):
    """실험05 74HC42(DIP-16) + Negative LED 10벌 시험판을 자기 자신과 견준다.

    전원 핀은 칩 레코드 핀 수에서 읽는다 — DIP-16 은 VCC 16 · GND 8 이고 pin 7·14 는
    신호(Y6·B)다. Negative 사슬은 신호 → 330Ω → LED 캐소드 → 애노드 → +5V 라 보통 사슬의
    '캐소드 ↔ 저항 윗다리 · 아랫다리 ↔ GND' 를 그대로 대면 10벌 전부가 헛난다.
    """

    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        board = load_renderer().load_board_file(
            root / 'tests/fixtures/board_v2_e5/배치.py', 'board_v2_e5')
        with tempfile.TemporaryDirectory() as d:
            bb = board.build_trial_bcd(os.path.join(d, 'x.png'))
        cls.wiring = bb.wiring()
        cls.board = bb.board

    def _pair(self):
        ref = hc._from_wiring(self.wiring, 'e5_trial', self.board)
        hand = hc._from_wiring(self.wiring, 'e5_trial', self.board)
        return ref, hand

    def _drop_wires_touching(self, d, hole):
        node = hc.node_of(hole)
        d.wires = [w for w in d.wires
                   if hc._endpoint_node(w['frm']) != node
                   and hc._endpoint_node(w['to']) != node]

    def _chain(self, d, tag):
        return next(c for c in d.chains if c['tag'] == tag)

    def _rules(self, ref, hand, rule):
        return [f for f in hc.compare(ref, hand) if f.rule == rule]

    def test_참조를_그대로_넣으면_결함_0건(self):
        ref, hand = self._pair()
        bad = [str(f) for f in hc.compare(ref, hand) if f.grade != '표기']
        self.assertEqual(bad, [])

    def test_H3_pin16_전원이_없으면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[0]['pins'][16])
        found = self._rules(ref, hand, 'H3')
        self.assertEqual([f.where for f in found], ['74HC42 pin 16'])
        self.assertIn('VCC', found[0].message)

    def test_H3_pin8_접지가_없으면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[0]['pins'][8])
        found = self._rules(ref, hand, 'H3')
        self.assertEqual([f.where for f in found], ['74HC42 pin 8'])
        self.assertIn('GND', found[0].message)

    def test_H6_pin14_는_신호라_빠지면_잡는다(self):
        """DIP-16 pin 14 는 입력 B 다. 14핀 전원 자리로 보고 건너뛰면 안 된다."""
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[0]['pins'][14])
        self.assertIn('74HC42 pin 14', [f.where for f in self._rules(ref, hand, 'H6')])
        self.assertEqual(self._rules(ref, hand, 'H3'), [])

    def test_H7_Negative_저항_아랫다리가_캐소드_줄이_아니면_잡는다(self):
        ref, hand = self._pair()
        ch = self._chain(hand, 'Y3')
        b = ch['res_bottom']
        ch['res_bottom'] = (b[0], b[1], b[2] + 1)
        for r in hand.resistors:
            if r['tag'] == 'Y3':
                r['bottom'] = ch['res_bottom']
        found = self._rules(ref, hand, 'H7')
        self.assertEqual(len(found), 1, [str(f) for f in found])
        self.assertIn('Y3', found[0].where)
        self.assertIn('캐소드', found[0].message)
        self.assertIn('저항 아랫다리', found[0].message)

    def test_H7_Negative_애노드가_5V_에_안_닿으면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, self._chain(hand, 'Y7')['anode'])
        found = self._rules(ref, hand, 'H7')
        self.assertEqual(len(found), 1, [str(f) for f in found])
        self.assertIn('Y7', found[0].where)
        self.assertIn('+5V', found[0].message)

    def test_H7_Negative_애노드를_GND_에_물리면_잡는다(self):
        ref, hand = self._pair()
        anode = self._chain(hand, 'Y7')['anode']
        self._drop_wires_touching(hand, anode)
        hand.wires.append(_wire(('right', 'e', anode[2]), ('right', 'gnd', anode[2]), 'gnd'))
        found = self._rules(ref, hand, 'H7')
        self.assertTrue(found)
        self.assertIn('GND', found[0].message)

    def test_Negative_신호가_저항_윗다리에_안_닿으면_H6_이_잡는다(self):
        """신호 ↔ 저항 윗다리는 보통 사슬의 신호 ↔ 애노드처럼 칩 핀 서명(H6)에 든다."""
        ref, hand = self._pair()
        ch = self._chain(hand, 'Y0')
        t = ch['res_top']
        ch['res_top'] = (t[0], t[1], t[2] - 1)
        for r in hand.resistors:
            if r['tag'] == 'Y0':
                r['top'] = ch['res_top']
        found = self._rules(ref, hand, 'H6')
        self.assertIn('74HC42 pin 1', [f.where for f in found])
        self.assertIn('Y0 저항 윗다리', next(f for f in found if f.where == '74HC42 pin 1').message)


if __name__ == '__main__':
    unittest.main()

