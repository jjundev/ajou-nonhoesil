"""사진 결선 검토 — 격자 맞춤과 단계 판정.

격자는 합성 호모그래피로, 판정은 살아 있는 실험08 단계 참조를 사진 전사 모양으로 옮겨
한 군데씩 망가뜨려 본다. 사진 전사는 참조 꼬리표(Y0…)와 LED 극성을 모르므로 그
두 가지를 지운 채 넣는다.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.lab import hand_compare as hc
from scripts.lab import photo_wiring as pw

JACK = {'red': '빨강', 'yellow': '노랑', 'gray': '회색'}
H_TRUE = np.array([[38.0, 4.0, 300.0], [-3.0, 41.0, 120.0], [0.0004, 0.0009, 1.0]])


def _px(col, row):
    return [float(v) for v in pw.project(H_TRUE, [(pw.COL_X[col], row)])[0]]


def _anchors(holes):
    return [{'px': _px(h[0], int(h[1:])), 'hole': f'우 {h}'} for h in holes]


class GridFit(unittest.TestCase):
    def test_합성_호모그래피를_되찾는다(self):
        g = pw.fit_grid('x.png', _anchors(['a1', 'j1', 'a30', 'j30', 'f15']))
        for col, row in (('c', 20), ('h', 7), ('e', 29)):
            got, want = np.array(g.pixel(col, row)), np.array(_px(col, row))
            self.assertLess(np.linalg.norm(got - want), 0.05)
        self.assertEqual(g.block, 'right')
        self.assertLess(g.residual, 0.01)

    def test_라벨이_한_행_틀린_앵커를_거절한다(self):
        a = _anchors(['a1', 'j1', 'a30', 'j30', 'f15', 'c10'])
        a[-1]['hole'] = '우 c11'
        with self.assertRaisesRegex(pw.PhotoGridError, '벗어난다'):
            pw.fit_grid('x.png', a)

    def test_앵커가_셋이면_거절한다(self):
        with self.assertRaisesRegex(pw.PhotoGridError, '네 개 이상'):
            pw.fit_grid('x.png', _anchors(['a1', 'j1', 'a30']))

    def test_블록이_섞이면_거절한다(self):
        a = _anchors(['a1', 'j1', 'a30', 'j30'])
        a[0]['hole'] = '좌 a1'
        with self.assertRaisesRegex(pw.PhotoGridError, '여러 블록'):
            pw.fit_grid('x.png', a)

    def test_한_행에_몰리면_거절한다(self):
        with self.assertRaisesRegex(pw.PhotoGridError, '하나뿐'):
            pw.fit_grid('x.png', _anchors(['a5', 'c5', 'f5', 'j5']))

    def test_레일은_앵커가_못_된다(self):
        with self.assertRaisesRegex(pw.PhotoGridError, '단자대'):
            pw.logical('중앙GND레일5행')

    def test_격자와_맨_그림을_한_쌍_쓴다(self):
        with tempfile.TemporaryDirectory() as t:
            photo = Path(t) / 'p.png'
            Image.new('RGB', (900, 1700), (230, 230, 220)).save(photo)
            g = pw.fit_grid(str(photo), _anchors(['a1', 'j1', 'a30', 'j30']))
            a, b = pw.overlay(g, t, 'p1', rows=(1, 12))
            self.assertTrue(Path(a).exists() and Path(b).exists())
            self.assertEqual(Image.open(a).size, Image.open(b).size)

    def test_눈금_그림을_쓴다(self):
        with tempfile.TemporaryDirectory() as t:
            photo = Path(t) / 'p.png'
            Image.new('RGB', (400, 300)).save(photo)
            out = pw.ruler(str(photo), str(Path(t) / 'r.png'), crop=(0, 0, 200, 150))
            self.assertTrue(Path(out).exists())


def _addr(hole):
    return hc._addr(hole, 'v2')


def _end(ep):
    kind, v = ep
    return f'전원잭({JACK[v]})' if kind == 'jack' else _addr(v)


def _photo_transcript(ref):
    """참조 -> 사진 전사 모양. 꼬리표는 P1.. 로, LED 극성은 지운다(legs)."""
    order = sorted(ref.chains, key=lambda c: c['anode'][2])
    rename = {c['tag']: f'P{i + 1}' for i, c in enumerate(order)}
    return {
        'photos': ['p1.jpg'],
        'chips': [{'label': c['label'], 'block': '좌' if c['block'] == 'left' else '우',
                   'pin1_row': c['pin1_row'], 'pin1_col': c['pins'][1][1]} for c in ref.chips],
        'wires': [{'from': _end(w['frm']), 'to': _end(w['to'])} for w in ref.wires],
        'leds': [{'tag': rename[l['tag']], 'legs': [_addr(l['cathode']), _addr(l['anode'])]} for l in ref.leds],
        'resistors': [{'tag': rename[r['tag']], 'top': _addr(r['top']), 'bottom': _addr(r['bottom'])}
                      for r in ref.resistors],
        'bridges': [{'kind': k, 'from': _addr(a), 'to': _addr(b)} for k, a, b in ref.bridges],
        'uncertain': [],
    }


class StageJudge(unittest.TestCase):
    STAGE = '실험08_1_결선도_2단2진카운터_5단계_Y3'

    @classmethod
    def setUpClass(cls):
        cls.ref = pw.stage_reference(8, cls.STAGE)

    def _judge(self, obj):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / '전사.json'
            p.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
            return pw.judge(8, '5단계_Y3', p, t)

    def test_단계_이름을_뒤꼬리로_찾는다(self):
        self.assertEqual(pw.resolve_stage(8, '2단계_Y0'), '실험08_1_결선도_2단2진카운터_2단계_Y0')

    def test_여럿과_맞으면_후보를_들고_거절한다(self):
        with self.assertRaisesRegex(hc.CompareError, '여럿'):
            pw.resolve_stage(8, '1단계')

    def test_준비_보드도_단계다(self):
        self.assertIn('실험08_1_결선도_2단2진카운터_1준비_2', pw.stage_names(8))

    def test_참조를_사진_전사로_옮기면_통과다(self):
        name, findings, notes = self._judge(_photo_transcript(self.ref))
        self.assertEqual(name, self.STAGE)
        self.assertEqual([str(f) for f in findings], [])
        self.assertEqual(pw.photo_verdict(findings), '통과')
        self.assertTrue(any('극성 미확인' in n for n in notes))

    def test_꼬리표를_칩_핀으로_되찾는다(self):
        obj = _photo_transcript(self.ref)
        obj['leds'].reverse()          # 적은 순서와 무관해야 한다
        _name, findings, notes = self._judge(obj)
        self.assertEqual([str(f) for f in findings], [])
        self.assertTrue(any('칩 핀이 같다' in n for n in notes))

    def test_저항이_한_행_밀리면_H7_로_잡는다(self):
        obj = _photo_transcript(self.ref)
        r = obj['resistors'][0]
        block, rest = r['top'].split(' ')
        r['top'] = f'{block} {rest[0]}{int(rest[1:]) + 1}'
        _name, findings, _notes = self._judge(obj)
        self.assertEqual(pw.photo_verdict(findings), '수정 필요')
        self.assertIn('H7', {f.rule for f in findings})

    def test_확신_못_한_끝점은_재촬영이다(self):
        obj = _photo_transcript(self.ref)
        obj['uncertain'] = [obj['wires'][-1]['to']]
        _name, findings, _notes = self._judge(obj)
        self.assertEqual(pw.photo_verdict(findings), '재촬영 필요')

    def test_보드_밖_입력은_참조_레일_입력으로_바꾼다(self):
        obj = _photo_transcript(self.ref)
        rail = self.ref.photo_inputs['CLK']
        clk = next(w for w in obj['wires'] if w['from'] == hc._addr(rail, 'v2'))
        obj['wires'].remove(clk)
        obj['external'] = [{'name': 'CLK', 'at': clk['to']}]
        _name, findings, notes = self._judge(obj)
        self.assertEqual([str(f) for f in findings], [])
        self.assertTrue(any('보드 밖 신호원' in n for n in notes))

    def test_참조에_없는_보드_밖_신호는_보류다(self):
        obj = _photo_transcript(self.ref)
        obj['external'] = [{'name': 'XYZ', 'at': '우 j40'}]
        _name, findings, _notes = self._judge(obj)
        self.assertEqual(pw.photo_verdict(findings), '재촬영 필요')

    def test_판정문을_쓴다(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / '전사.json'
            p.write_text(json.dumps(_photo_transcript(self.ref), ensure_ascii=False), encoding='utf-8')
            pw.judge(8, '5단계_Y3', p, t)
            text = (Path(t) / '판정.md').read_text(encoding='utf-8')
            self.assertIn('**판정: 통과**', text)
            self.assertTrue((Path(t) / '전사_판정용.json').exists())


if __name__ == '__main__':
    unittest.main()
