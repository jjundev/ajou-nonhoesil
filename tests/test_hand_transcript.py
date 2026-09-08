"""전사 파일의 문법과 그것이 만드는 `Diagram` 을 검사한다.

주소는 렌더러 `addr()` 이 내는 말과 **똑같이** 쓴다 ('좌 b10',
'좌 GND레일10행'). 양쪽이 다른 말을 쓰면 비교 자체가 성립하지 않는다.
"""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.lab import hand_transcript as ht


def _write(obj):
    p = Path(tempfile.mkdtemp()) / "p3.json"
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return p


MINIMAL = {
    "page": 3, "circuit": "e1_nand", "title": "2-1 NAND Gate", "signed": False,
    "chips": [{"label": "74HC08", "block": "left", "pin1_row": 7}],
    "wires": [{"color": "빨강", "from": "좌 g7", "to": "좌 중앙VCC레일7행"}],
    "leds": [{"tag": "L1", "anode": "좌 c14", "cathode": "좌 c15"}],
    "resistors": [{"tag": "L1", "top": "좌 d15", "bottom": "좌 d17"}],
    "uncertain": [],
}


class Address(unittest.TestCase):
    def test_단자대_주소를_읽는다(self):
        self.assertEqual(ht.parse_address("좌 b10"), ('hole', ('left', 'b', 10)))
        self.assertEqual(ht.parse_address("우 j15"), ('hole', ('right', 'j', 15)))

    def test_레일_주소를_읽는다(self):
        self.assertEqual(ht.parse_address("좌 GND레일10행"),
                         ('hole', ('left', 'gnd', 10)))
        self.assertEqual(ht.parse_address("좌 중앙VCC레일7행"),
                         ('hole', ('left', 'mid_vcc', 7)))
        self.assertEqual(ht.parse_address("우 중앙GND레일29행"),
                         ('hole', ('right', 'mid_gnd', 29)))

    def test_전원잭을_읽는다(self):
        self.assertEqual(ht.parse_address("전원잭(빨강)"), ('jack', 'red'))
        self.assertEqual(ht.parse_address("전원잭(회색)"), ('jack', 'gray'))

    def test_렌더러가_내는_주소를_그대로_읽는다(self):
        """`addr()` 출력과 문법이 갈리면 비교가 성립하지 않는다."""
        from scripts.lab.hand_grid import load_renderer
        mod = load_renderer()
        bb = mod.BreadboardRenderer()
        c = bb.cols['left']
        for x, row in [(c['b'], 10), (c['gnd'], 10), (c['mid_vcc'], 7)]:
            got = ht.parse_address(bb.addr(x, bb.r_y(row)))
            self.assertEqual(got, ('hole', bb.sym(x, row)))

    def test_모르는_주소는_거절한다(self):
        for bad in ["보드밖(입력)", "분기점", "좌 k10", "가운데 b10", "좌 b0"]:
            with self.assertRaises(ht.TranscriptError, msg=bad):
                ht.parse_address(bad)


class ChipPins(unittest.TestCase):
    def test_핀_배치가_렌더러와_같다(self):
        """`draw_chip` 이 꽂는 자리와 한 글자도 갈리면 안 된다."""
        from scripts.lab.hand_grid import load_renderer
        import os
        import tempfile as tf
        mod = load_renderer()
        bb = mod.build_e1_nand(os.path.join(tf.mkdtemp(), 'x.png'))
        for chip in bb.wiring()['chips']:
            self.assertEqual(ht.chip_pins(chip['block'], chip['pin1_row']),
                             chip['pins'])


class Parse(unittest.TestCase):
    def test_최소_전사를_읽는다(self):
        d = ht.parse_transcript(_write(MINIMAL))
        self.assertEqual(d.circuit, "e1_nand")
        self.assertEqual(d.page, 3)
        self.assertFalse(d.signed)
        self.assertEqual(len(d.wires), 1)
        self.assertEqual(d.chips[0]['pins'][1], ('left', 'e', 7))

    def test_LED_와_저항을_꼬리표로_묶어_사슬을_만든다(self):
        d = ht.parse_transcript(_write(MINIMAL))
        self.assertEqual(len(d.chains), 1)
        ch = d.chains[0]
        self.assertEqual(ch['tag'], 'L1')
        self.assertEqual(ch['cathode'], ('left', 'c', 15))
        self.assertEqual(ch['res_top'], ('left', 'd', 15))
        self.assertEqual(ch['res_bottom'], ('left', 'd', 17))

    def test_짝_없는_저항은_거절한다(self):
        obj = json.loads(json.dumps(MINIMAL))
        obj['resistors'][0]['tag'] = 'L9'
        with self.assertRaisesRegex(ht.TranscriptError, 'L9'):
            ht.parse_transcript(_write(obj))

    def test_uncertain_은_주소로_보관된다(self):
        obj = json.loads(json.dumps(MINIMAL))
        obj['uncertain'] = ["좌 d17"]
        d = ht.parse_transcript(_write(obj))
        self.assertEqual(d.uncertain, {('left', 'd', 17)})

    def test_필수_열쇠가_없으면_거절한다(self):
        obj = json.loads(json.dumps(MINIMAL))
        del obj['circuit']
        with self.assertRaisesRegex(ht.TranscriptError, 'circuit'):
            ht.parse_transcript(_write(obj))

    def test_브리지를_읽는다(self):
        obj = json.loads(json.dumps(MINIMAL))
        obj['bridges'] = [{"kind": "gnd", "from": "좌 중앙GND레일31행", "to": "좌 GND레일31행"}]
        d = ht.parse_transcript(_write(obj))
        self.assertEqual(d.bridges, [("gnd", ("left", "mid_gnd", 31), ("left", "gnd", 31))])

    def test_칩_내부_필수_열쇠가_없으면_TranscriptError(self):
        for key in ('label', 'pin1_row'):
            obj = json.loads(json.dumps(MINIMAL))
            del obj['chips'][0][key]
            with self.assertRaises(ht.TranscriptError):
                ht.parse_transcript(_write(obj))

    def test_배선_내부_필수_열쇠가_없으면_TranscriptError(self):
        for key in ('from', 'to'):
            obj = json.loads(json.dumps(MINIMAL))
            del obj['wires'][0][key]
            with self.assertRaises(ht.TranscriptError):
                ht.parse_transcript(_write(obj))


if __name__ == '__main__':
    unittest.main()
