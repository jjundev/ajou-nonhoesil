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
        self.assertEqual(chip['pin1_row'], 10)
        self.assertEqual(chip['block'], 'left')
        # pin 1~7 은 e 열, pin 8~14 는 f 열. draw_chip 이 그렇게 꽂는다
        self.assertEqual(chip['pins'][1], ('left', 'e', 10))
        self.assertEqual(chip['pins'][7], ('left', 'e', 16))
        self.assertEqual(chip['pins'][14], ('left', 'f', 10))
        self.assertEqual(chip['pins'][8], ('left', 'f', 16))

    def test_배선은_양_끝을_기호_좌표로_남긴다(self):
        wires = self.and_bb.wiring()['wires']
        ends = {(w['frm'], w['to']) for w in wires}
        # pin 14 -> 중앙 VCC 레일 (connect_power)
        self.assertIn((('hole', ('left', 'g', 10)),
                       ('hole', ('left', 'mid_vcc', 10))), ends)

    def test_전원잭_끝점은_홀이_아니라_잭으로_남는다(self):
        wires = self.and_bb.wiring()['wires']
        jacks = {w['frm'] for w in wires if w['frm'][0] == 'jack'}
        self.assertEqual(jacks, {('jack', 'red'), ('jack', 'gray')})

    def test_LED_사슬은_네_홀을_한_묶음으로_남긴다(self):
        chains = {ch['tag']: ch for ch in self.and_bb.wiring()['chains']}
        self.assertEqual(set(chains), {'L1', 'L2'})
        l2 = chains['L2']
        # led_chain(c['c'], 19, "L2", ...) — 도착 c19, LED 는 옆 열, 저항은 그 다음
        self.assertEqual(l2['anode'][2], 19)
        self.assertEqual(l2['cathode'][2], 20)
        self.assertEqual(l2['res_top'][2], 20)
        self.assertEqual(l2['res_bottom'][2], 22)
        self.assertEqual(l2['anode'][1], l2['cathode'][1])
        self.assertNotEqual(l2['anode'][1], l2['res_top'][1])

    def test_미사용_입력과_출력이_따로_남는다(self):
        w = self.and_bb.wiring()
        self.assertEqual({(u['chip'], u['pin']) for u in w['unused_inputs']},
                         {('74HC08', 9), ('74HC08', 10), ('74HC08', 12), ('74HC08', 13)})
        self.assertEqual({(u['chip'], u['pin']) for u in w['unused_outputs']},
                         {('74HC08', 8), ('74HC08', 11)})

    def test_레일_브리지가_열_이름_쌍으로_남는다(self):
        bridges = self.and_bb.wiring()['bridges']
        pairs = {(k, a[1], b[1]) for k, a, b in bridges}
        self.assertIn(('gnd', 'gnd', 'mid_gnd'), pairs)
        self.assertIn(('vcc', 'vcc', 'mid_vcc'), pairs)

    def test_칩이_둘인_회로는_둘_다_남는다(self):
        chips = self.nand_bb.wiring()['chips']
        self.assertEqual([c['label'] for c in chips], ['74HC08', '74HC00'])
        self.assertEqual([c['pin1_row'] for c in chips], [7, 18])


if __name__ == '__main__':
    unittest.main()
