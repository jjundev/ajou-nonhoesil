"""넷 모델과 규칙 13개를 검사한다.

**홀 좌표가 아니라 넷으로 비교한다.** 칩이 참조보다 한 행 위에 있어도 주변
배선이 같이 옮겨져 있으면 그림은 유효하다 — 2026-09-08 손그림 세 쪽이 전부
그랬다. `regen_compare` 가 결선도를 간선 집합으로 보는 것과 같은 이유다.

살아 있는 실험01 참조 결선도를 한 군데씩 망가뜨려 검사기가 그 자리를 짚는지
본다. 합성 픽스처로는 실물에서만 나오는 배치를 못 밟는다.
"""
import unittest

from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import Diagram


def _wire(a, b, kind='sig'):
    return {'kind': kind, 'desc': '', 'frm': ('hole', a), 'to': ('hole', b)}


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


if __name__ == '__main__':
    unittest.main()
