"""손그림 모사 — 완성본 배선을 마커로 그은 것처럼 흔들어 그린다(2026-10-12 시험판).

흔들림은 그리기에만 걸리고 점유표·순서표·`verify()` 는 평소와 같아야 한다.
"""
import importlib.util
import random
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HandPolyline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _pts(self, seed=7):
        pts = [(100.0, 50.0), (100.0, 300.0), (400.0, 300.0)]
        return pts, self.mod._hand_polyline(pts, random.Random(seed))

    def test_끝점은_그대로다(self):
        pts, out = self._pts()
        self.assertEqual(out[0], pts[0])
        self.assertEqual(out[-1], pts[-1])

    def test_진폭은_2px_를_안_넘는다(self):
        # 원 경로(두 축 정렬 구간) 위 가장 가까운 점까지 축별 거리
        _, out = self._pts()
        for x, y in out:
            d = min(max(abs(x - 100), max(0, 50 - y, y - 300)),
                    max(abs(y - 300), max(0, 100 - x, x - 400)))
            self.assertLessEqual(d, 2.0 + 1e-9)

    def test_실제로_흔들린다(self):
        _, out = self._pts()
        self.assertTrue(any(abs(x - 100) > 0.5 for x, y in out if 80 < y < 280))

    def test_같은_시드는_같은_점(self):
        self.assertEqual(self._pts(3)[1], self._pts(3)[1])
        self.assertNotEqual(self._pts(3)[1], self._pts(4)[1])

    def test_짧은_선도_된다(self):
        out = self.mod._hand_polyline([(10.0, 10.0), (13.0, 10.0)], random.Random(1))
        self.assertEqual((out[0], out[-1]), ((10.0, 10.0), (13.0, 10.0)))

    def test_굵기는_0_7_에서_1_3_배(self):
        ws = {self.mod._hand_width(3, random.Random(s)) for s in range(200)}
        self.assertTrue(ws <= {2, 3, 4} and len(ws) > 1)
        self.assertGreaterEqual(self.mod._hand_width(1, random.Random(0)), 1)

    def test_도트는_반지름_1px_안에서_찌그러진다(self):
        boxes = [self.mod._hand_dot((50.0, 60.0), 3, random.Random(s)) for s in range(50)]
        for x0, y0, x1, y1 in boxes:
            self.assertAlmostEqual((x0 + x1) / 2, 50.0)
            self.assertAlmostEqual((y0 + y1) / 2, 60.0)
            self.assertTrue(2 <= (x1 - x0) / 2 <= 4 and 2 <= (y1 - y0) / 2 <= 4)
        self.assertGreater(len({tuple(b) for b in boxes}), 1)


class HandRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board(4)

    def _render(self, hand, guide=False):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        out = tmp / 'mux.png'
        bb = self.board.build_e4_mux(str(out), hand=hand, hand_guide=guide)
        return bb, out, tmp

    def test_hand_는_논리_상태를_안_바꾼다(self):
        a, _, _ = self._render(None)
        b, _, _ = self._render(42)
        self.assertEqual(a.steps, b.steps)
        self.assertEqual(a._segments, b._segments)
        self.assertEqual(a._leads, b._leads)

    def test_hand_export_는_PNG_만_쓴다(self):
        _, out, tmp = self._render(42)
        self.assertEqual(sorted(p.name for p in tmp.iterdir()), ['mux.png'])
        self.assertNotIn(self.mod.STAMP_KEY, Image.open(out).info)

    def test_같은_시드는_같은_PNG(self):
        _, a, _ = self._render(42)
        _, b, _ = self._render(42)
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_hand_없으면_도장이_정본과_같다(self):
        # 정본 PNG 와 새 렌더는 픽셀이 원래 다르다(글꼴·Pillow 판) — 저장소 계약인 도장으로 본다
        _, out, _ = self._render(None)
        ref = ROOT / '보고서/실험04/결선도/실험04_1-1_결선도_4x1MUX.png'
        key = self.mod.STAMP_KEY
        self.assertEqual(Image.open(out).info[key], Image.open(ref).info[key])

    def test_번호_원을_안_그린다(self):
        bb, _, _ = self._render(42)
        self.assertTrue(bb.marker_boxes)
        px = bb.overlay.load()
        for x0, y0, x1, y1 in bb.marker_boxes:
            cx, cy = int((x0 + x1) / 2 * self.mod.SCALE), int((y0 + y1) / 2 * self.mod.SCALE)
            self.assertNotEqual(px[cx, cy], (255, 255, 255, 245))

    def _count(self, bb, rgba):
        return sum(1 for p in bb.overlay.get_flattened_data() if p == rgba)

    def test_칩_LED_저항은_비워_둔다(self):
        # 사람이 그 자리에 직접 그린다 — 몸통 색이 한 픽셀도 없어야 한다
        plain, _, _ = self._render(None)
        bb, _, _ = self._render(42)
        for rgba in [(30, 33, 36, 255),       # 칩 몸통
                     (220, 20, 20, 240),      # LED 몸통
                     (225, 195, 145, 255)]:   # 저항 몸통
            self.assertGreater(self._count(plain, rgba), 0, rgba)
            self.assertEqual(self._count(bb, rgba), 0, rgba)

    def test_입력은_선만_두고_이름_배지는_비운다(self):
        plain, _, _ = self._render(None)
        bb, _, _ = self._render(42)
        self.assertGreater(self._count(bb, self.mod.INPUT), 0)    # 보라 점퍼선은 남는다
        segs = {i['seg'] for i in bb.inputs}
        boxes = [box for _, box, seg in bb.tag_boxes if seg in segs]
        self.assertTrue(boxes)
        S = self.mod.SCALE
        for name, img in (('plain', plain), ('hand', bb)):
            white = 0
            for x0, y0, x1, y1 in boxes:
                crop = img.overlay.crop((int(x0 * S) + 2, int(y0 * S) + 2, int(x1 * S) - 2, int(y1 * S) - 2))
                white += sum(1 for p in crop.get_flattened_data() if p == (255, 255, 255, 255))
            if name == 'plain':
                self.assertGreater(white, 0)       # 흰 글자·화살촉
            else:
                self.assertEqual(white, 0)

    def test_비워도_배치는_같다(self):
        a, _, _ = self._render(None)
        b, _, _ = self._render(42)
        for attr in ('chips', 'leds', 'resistors', 'tag_boxes', 'chip_label_boxes'):
            self.assertEqual(getattr(a, attr), getattr(b, attr), attr)

    def test_안내판은_선이_회색이고_부품은_색이다(self):
        bb, _, _ = self._render(42, guide=True)
        for col in self.mod.WIRE.values():
            self.assertEqual(self._count(bb, col), 0, col)
        self.assertGreater(self._count(bb, self.mod.KEEP), 0)
        for rgba in [(30, 33, 36, 255), (220, 20, 20, 240), (225, 195, 145, 255), self.mod.INPUT]:
            self.assertGreater(self._count(bb, rgba), 0, rgba)

    def test_안내판_회색선은_시험판_선과_같은_자리(self):
        # 팀원이 시험판과 안내판을 겹쳐 본다 — 흔들림이 같아야 한다
        blank, _, _ = self._render(42)
        guide, _, _ = self._render(42, guide=True)
        wire_cols = set(self.mod.WIRE.values()) | {self.mod.INPUT}
        a, b = blank.overlay.load(), guide.overlay.load()
        W, H = blank.overlay.size
        hits = [(x, y) for y in range(0, H, 2) for x in range(0, W, 2) if a[x, y] in wire_cols]
        same = sum(1 for x, y in hits if b[x, y] == self.mod.KEEP)
        self.assertGreater(same / len(hits), 0.99)

    def test_안내판도_배치는_같다(self):
        a, _, _ = self._render(42)
        b, _, _ = self._render(42, guide=True)
        for attr in ('_segments', 'tag_boxes', 'chips', 'leds', 'resistors', 'inputs'):
            self.assertEqual(getattr(a, attr), getattr(b, attr), attr)

    def test_안내판은_hand_없이_못_준다(self):
        with self.assertRaises(ValueError):
            self.mod.BreadboardRenderer(None, board='v1', hand_guide=True)

    def test_안내판_부품_밖_배지는_회색(self):
        bb = self.mod.BreadboardRenderer(None, board='v1', hand=1, hand_guide=True)
        bb.signal_tag('P', 300, 300, col=self.mod.PROBE)
        self.assertEqual(self._count(bb, self.mod.PROBE), 0)
        self.assertGreater(self._count(bb, self.mod.KEEP), 0)

    def test_기준선_이나_층과_못_섞는다(self):
        with self.assertRaises(ValueError):
            self.mod.BreadboardRenderer(None, layer=(1, 2), board='v1', hand=1)


class HandSimScript(unittest.TestCase):
    def test_시드는_파일이름으로_정해진다(self):
        from scripts.lab.hand_sim import hand_seed
        self.assertEqual(hand_seed('a.png'), hand_seed('a.png'))
        self.assertNotEqual(hand_seed('a.png'), hand_seed('b.png'))

    def test_완성본_한_장을_뽑는다(self):
        from scripts.lab import hand_sim
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        out = hand_sim.main(['--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png',
                             '--out', str(tmp)])
        self.assertEqual(out.name, '실험04_1-1_손그림모사_4x1MUX.png')
        self.assertEqual([p.name for p in tmp.iterdir()], [out.name])

    def test_없는_완성본은_목록과_함께_멈춘다(self):
        from scripts.lab import hand_sim
        with self.assertRaises(SystemExit) as cm:
            hand_sim.main(['--experiment', '4', '--final', '없음.png'])
        self.assertIn('실험04_1-1_결선도_4x1MUX.png', str(cm.exception))

    def _guide_board(self):
        mod = _load()
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        return mod.load_board(4).build_e4_mux(str(tmp / 'g.png'), hand=1, hand_guide=True)

    def test_부품표에_칩_LED_저항_입력이_다_있다(self):
        from scripts.lab import hand_sim
        bb = self._guide_board()
        rows = hand_sim.guide_rows(bb)
        kinds = [k for k, _, _ in rows]
        self.assertEqual(kinds, sorted(kinds, key=['칩', 'LED', '저항', '입력'].index))
        self.assertEqual(kinds.count('칩'), len(bb.chips))
        self.assertEqual(kinds.count('LED'), len(bb.led_chains))
        self.assertEqual(kinds.count('저항'), len(bb.resistors))
        self.assertEqual([n for k, n, _ in rows if k == '입력'], [i['name'] for i in bb.inputs])

    def test_부품표_입력은_레일_쪽_끝(self):
        # 팀원이 이름을 적는 자리는 0/1 을 바꿀 때 옮겨 꽂는 레일 쪽 끝이다
        from scripts.lab import hand_sim
        bb = self._guide_board()
        first = bb.inputs[0]
        rail_end = bb.addr(*bb._segments[first['seg']][1][0])
        row = next(r for r in hand_sim.guide_rows(bb) if r[0] == '입력')
        self.assertIn(rail_end, row[2])
        self.assertNotIn(bb._sym_addr(('hole', first['at'])), row[2])

    def test_안내_PDF_는_한_쪽에_그림_하나(self):
        from pypdf import PdfReader
        from scripts.lab import hand_sim
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        sim, guide_png, pdf = hand_sim.main(['--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png',
                                             '--out', str(tmp), '--guide'])
        self.assertEqual(sim.name, '실험04_1-1_손그림모사_4x1MUX.png')
        self.assertEqual(guide_png.name, '실험04_1-1_부품그리기_4x1MUX.png')
        self.assertEqual(pdf.name, '실험04_1-1_부품그리기_4x1MUX.pdf')
        pages = PdfReader(str(pdf)).pages
        self.assertEqual([len(p.images) for p in pages], [1])
        text = pages[0].extract_text()
        self.assertIn('회색 선은 이미 그려져 있어요', text)
        self.assertIn('다리', text)    # 부품 다리도 회색이다 — 빠뜨리지 않게
        self.assertIn('74HC04', text)

    def test_넘친_PDF_는_거절한다(self):
        from pypdf import PdfWriter
        from scripts.lab import hand_sim
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        w = PdfWriter()
        w.add_blank_page(595, 842)
        w.add_blank_page(595, 842)
        w.write(str(tmp / 'two.pdf'))
        with self.assertRaises(ValueError):
            hand_sim.check_guide_pdf(tmp / 'two.pdf')

    def test_안내판을_못_받는_빌더는_이름과_함께_멈춘다(self):
        from scripts.lab import hand_sim
        with self.assertRaises(SystemExit) as cm:
            hand_sim.main(['--experiment', '4', '--final', '실험04_2-1_결선도_1x4DMUX.png', '--guide'])
        self.assertIn('hand_guide', str(cm.exception))


if __name__ == "__main__":
    unittest.main()
