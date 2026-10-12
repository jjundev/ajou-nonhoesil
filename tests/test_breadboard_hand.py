"""손그림 모사 — 완성본 배선을 마커로 그은 것처럼 흔들어 그린다(2026-10-12 시험판).

흔들림은 그리기에만 걸리고 점유표·순서표·`verify()` 는 평소와 같아야 한다.
"""
import importlib.util
import math
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


class HandShapes(unittest.TestCase):
    """칩·LED·저항 윤곽용 닫힌 도형과 손글씨 글꼴 갈아끼우기(2단계)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_원은_닫혀_있고_반지름_안에서_떨린다(self):
        pts = self.mod._hand_circle((50.0, 60.0), 8, random.Random(1), amp=1.0)
        self.assertEqual(pts[0], pts[-1])
        for x, y in pts:
            d = math.hypot(x - 50.0, y - 60.0)
            self.assertTrue(8 - 2.0 <= d <= 8 + 1.5, d)

    def test_사각형_윤곽은_첫_꼭짓점에서_닫힌다(self):
        box = [(10.0, 10.0), (40.0, 10.0), (40.0, 90.0), (10.0, 90.0)]
        pts = self.mod._hand_loop(box, random.Random(2), amp=1.0)
        self.assertEqual(pts[0], box[0])
        self.assertEqual(pts[-1], box[0])

    def test_홈은_아래_반원이다(self):
        pts = self.mod._hand_arc([10, 0, 30, 12], random.Random(3), amp=1.0)
        for got, want in ((pts[0], (30, 6)), (pts[-1], (10, 6))):    # sin(π) 잔차 — 근사로 본다
            self.assertAlmostEqual(got[0], want[0])
            self.assertAlmostEqual(got[1], want[1])
        self.assertTrue(max(y for _, y in pts) > 10)

    def test_손글씨_글꼴은_Bradley_Hand_다(self):
        self.assertTrue(self.mod.font_path('hand').endswith('Bradley Hand Bold.ttf'))

    def test_hand_real_은_en_글꼴만_바꾼다(self):
        d = self.mod._ScaledDraw(Image.new('RGBA', (100, 100)), hand_font_path=self.mod.font_path('hand'))
        self.assertIsNotNone(d.hand_real(self.mod._font('en', 10)))
        self.assertIsNone(d.hand_real(self.mod._font('kr', 10)))
        self.assertIsNone(self.mod._ScaledDraw(Image.new('RGBA', (100, 100))).hand_real(self.mod._font('en', 10)))

    def test_text_는_원래_상자_중심에_그린다(self):
        for kw in ({}, {'anchor': 'mm'}):
            im = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
            d = self.mod._ScaledDraw(im, hand_font_path=self.mod.font_path('hand'))
            f = self.mod._font('en', 12)
            b = d.textbbox((50, 40), '74HC20', font=f, **kw)
            d.text((50, 40), '74HC20', fill=(0, 0, 0, 255), font=f, **kw)
            ink = im.getbbox()                                   # 실픽셀
            cx = (ink[0] + ink[2]) / 2 / self.mod.SCALE
            cy = (ink[1] + ink[3]) / 2 / self.mod.SCALE
            self.assertAlmostEqual(cx, (b[0] + b[2]) / 2, delta=2)
            self.assertAlmostEqual(cy, (b[1] + b[3]) / 2, delta=2)


class HandRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board(4)

    def _render(self, hand):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        out = tmp / 'mux.png'
        bb = self.board.build_e4_mux(str(out), hand=hand)
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


if __name__ == "__main__":
    unittest.main()
