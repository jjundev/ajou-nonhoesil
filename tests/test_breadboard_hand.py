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


def _seg_dist(p, a, b):
    """점 p 에서 선분 ab 까지 거리."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class HandPolyline(unittest.TestCase):
    """손그림 획 모델 — 구간마다 활 하나 + 미세 떨림, 수직 방향만(2026-10-15)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    PATH = [(100.0, 50.0), (100.0, 300.0), (400.0, 300.0)]

    def _out(self, seed=7, pts=None):
        return self.mod._hand_polyline(pts or self.PATH, random.Random(seed))

    def test_끝점은_그대로다(self):
        out = self._out()
        self.assertEqual(out[0], self.PATH[0])
        self.assertEqual(out[-1], self.PATH[-1])

    def test_모서리는_그대로다(self):
        # 모서리점이 결과에 정확히 들어 있다 — L 자 경로의 꺾임이 홀·경로점에 남는다
        for s in range(20):
            self.assertIn(self.PATH[1], self._out(s))

    def test_오프셋은_활_더하기_떨림을_안_넘는다(self):
        bound = self.mod.HAND_BOW_MAX + self.mod.HAND_TREMOR + 1e-9
        for s in range(50):
            for p in self._out(s):
                d = min(_seg_dist(p, self.PATH[0], self.PATH[1]), _seg_dist(p, self.PATH[1], self.PATH[2]))
                self.assertLessEqual(d, bound)

    def test_긴_직선은_가운데가_한쪽으로만_휜다(self):
        # 출렁이지 않는다 — 옛 모델(사인 셋)은 2~8칸마다 부호가 바뀌었다
        a, b = (0.0, 100.0), (400.0, 100.0)
        for s in range(50):
            mid = [y - 100.0 for x, y in self._out(s, [a, b]) if 80 <= x <= 320]
            self.assertTrue(all(v > 0 for v in mid) or all(v < 0 for v in mid), s)
            self.assertGreater(max(abs(v) for v in mid), 0.7, s)   # 활 ≥ 1.0 − 떨림 0.25

    def test_수직_방향으로만_움직인다(self):
        # 가로선 위 점들의 x 는 단조 증가 — 축별로 따로 흔들던 옛 모델과 다르다
        xs = [x for x, _ in self._out(3, [(0.0, 10.0), (200.0, 10.0)])]
        self.assertEqual(xs, sorted(xs))

    def test_같은_시드는_같은_점(self):
        self.assertEqual(self._out(3), self._out(3))
        self.assertNotEqual(self._out(3), self._out(4))

    def test_짧은_선은_휘지_않는다(self):
        out = self.mod._hand_polyline([(10.0, 10.0), (20.0, 10.0)], random.Random(1))
        self.assertEqual((out[0], out[-1]), ((10.0, 10.0), (20.0, 10.0)))
        self.assertTrue(all(abs(y - 10.0) <= self.mod.HAND_TREMOR + 1e-9 for _, y in out))

    def test_길이_0_구간도_된다(self):
        # 같은 점이 연달아 와도 0 나누기 없이 끝점이 그대로다
        pts = [(10.0, 10.0), (10.0, 10.0), (60.0, 10.0)]
        out = self.mod._hand_polyline(pts, random.Random(2))
        self.assertEqual((out[0], out[-1]), (pts[0], pts[-1]))

    def test_굵기는_상수다(self):
        self.assertEqual(self.mod.HAND_WIDTH, 2.0)
        self.assertFalse(hasattr(self.mod, '_hand_width'))

    def test_도트는_반지름_10퍼센트_안에서_찌그러진다(self):
        r = self.mod.HAND_DOT_R
        boxes = [self.mod._hand_dot((50.0, 60.0), random.Random(s)) for s in range(50)]
        for x0, y0, x1, y1 in boxes:
            self.assertAlmostEqual((x0 + x1) / 2, 50.0)
            self.assertAlmostEqual((y0 + y1) / 2, 60.0)
            self.assertTrue(0.9 * r - 1e-9 <= (x1 - x0) / 2 <= 1.1 * r + 1e-9)
            self.assertTrue(0.9 * r - 1e-9 <= (y1 - y0) / 2 <= 1.1 * r + 1e-9)
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

    def _ink(self, bb, rgba):
        """획 레이어에서 그 색으로 꽉 찬 픽셀 수 — 가장자리(반투명)는 안 센다."""
        return sum(1 for p in bb.hand_layer.get_flattened_data() if p == rgba)

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
        self.assertGreater(self._ink(bb, self.mod.INPUT), 0)    # 보라 점퍼선은 남는다(획 레이어)
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
            self.assertEqual(self._ink(bb, col), 0, col)
        self.assertGreater(self._ink(bb, self.mod.KEEP), 0)
        for rgba in [(30, 33, 36, 255), (220, 20, 20, 240), (225, 195, 145, 255), self.mod.INPUT]:
            self.assertGreater(self._count(bb, rgba), 0, rgba)

    def test_안내판_회색선은_시험판_선과_같은_자리(self):
        # 팀원이 시험판과 안내판을 겹쳐 본다 — 같은 시드면 획 좌표가 같아야 한다
        blank, _, _ = self._render(42)
        guide, _, _ = self._render(42, guide=True)
        self.assertTrue(blank.hand_strokes)
        self.assertEqual([(s['points'], s['dots']) for s in blank.hand_strokes],
                         [(s['points'], s['dots']) for s in guide.hand_strokes])
        self.assertEqual({s['color'] for s in guide.hand_strokes}, {self.mod.KEEP})

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

    def test_손그림_overlay_는_비어_있다(self):
        # 배선은 획 레이어로 갔다 — 부품·배지·번호 원은 비웠으니 overlay 에 아무것도 없어야 한다
        bb, _, _ = self._render(42)
        self.assertIsNone(bb.overlay.getbbox())

    def test_모든_배선이_획이다(self):
        bb, _, _ = self._render(42)
        self.assertEqual(len(bb.hand_strokes), len(bb._segments))
        self.assertEqual({s['width'] for s in bb.hand_strokes}, {self.mod.HAND_WIDTH})

    def test_획_끝점은_구간_끝점(self):
        bb, _, _ = self._render(42)
        for s, (_, pts, _) in zip(bb.hand_strokes, bb._segments):
            self.assertEqual(s['points'][0], tuple(map(float, pts[0])))
            self.assertEqual(s['points'][-1], tuple(map(float, pts[-1])))

    def test_hand_없으면_획도_레이어도_없다(self):
        bb, _, _ = self._render(None)
        self.assertEqual(bb.hand_strokes, [])
        self.assertIsNone(bb.hand_layer)

    def test_획_레이어는_안티앨리어싱(self):
        bb, _, _ = self._render(42)
        self.assertEqual(bb.hand_layer.size, bb.im.size)
        alphas = {p[3] for p in bb.hand_layer.get_flattened_data()}
        self.assertGreater(len(alphas), 20)       # 0·255 말고도 중간 알파가 많다

    def test_가장자리_색은_획_색(self):
        # MuPDF 알파 표본은 premultiplied — 그대로 읽으면 가장자리가 검게 번진다
        bb, _, _ = self._render(42)
        cols = {s['color'][:3] for s in bb.hand_strokes}
        edge = [p for p in bb.hand_layer.get_flattened_data() if 64 <= p[3] < 255]
        self.assertTrue(edge)
        near = sum(1 for p in edge if min(max(abs(p[i] - c[i]) for i in range(3)) for c in cols) <= 30)
        self.assertGreater(near / len(edge), 0.9)


class HandRenderE5(unittest.TestCase):
    """v2 판형(실험05~)에서도 같은 약속 — 2026-10-12 `make-hand-sim`."""
    BUILDERS = ('build_e5_bcd', 'build_e5_xs3')

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board(5)

    def _render(self, name, hand, guide=False):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        return getattr(self.board, name)(str(tmp / 'x.png'), hand=hand, hand_guide=guide)

    def _count(self, bb, rgba):
        return sum(1 for p in bb.overlay.get_flattened_data() if p == rgba)

    def test_실험05_hand_는_배치를_안_바꾼다(self):
        for name in self.BUILDERS:
            a, b = self._render(name, None), self._render(name, 42)
            for attr in ('steps', '_segments', '_leads', 'tag_boxes', 'chips', 'leds', 'resistors', 'inputs'):
                self.assertEqual(getattr(a, attr), getattr(b, attr), (name, attr))

    def test_실험05_단계에_hand_는_거절(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        with self.assertRaises(ValueError):
            self.board.build_e5_bcd(str(tmp / 'x.png'), stage=1, hand=1)

    def test_실험05_부품과_입력_이름은_비운다(self):
        for name in self.BUILDERS:
            plain, bb = self._render(name, None), self._render(name, 42)
            for rgba in [(30, 33, 36, 255), (220, 20, 20, 240), (225, 195, 145, 255)]:
                self.assertGreater(self._count(plain, rgba), 0, (name, rgba))
                self.assertEqual(self._count(bb, rgba), 0, (name, rgba))
            self.assertGreater(sum(1 for p in bb.hand_layer.get_flattened_data()
                                   if p == self.mod.INPUT), 0, name)

    def test_실험05_안내판_선은_회색(self):
        for name in self.BUILDERS:
            bb = self._render(name, 42, guide=True)
            for col in self.mod.WIRE.values():
                self.assertEqual(self._count(bb, col), 0, (name, col))
            self.assertEqual({s['color'] for s in bb.hand_strokes}, {self.mod.KEEP}, name)
            self.assertGreater(self._count(bb, (30, 33, 36, 255)), 0, name)   # 칩은 색

    def test_실험05_손그림_overlay_는_비어_있다(self):
        for name in self.BUILDERS:
            self.assertIsNone(self._render(name, 42).overlay.getbbox(), name)


class HandSimScript(unittest.TestCase):
    def test_시드는_파일이름으로_정해진다(self):
        from scripts.lab.hand_sim import hand_seed
        self.assertEqual(hand_seed('a.png'), hand_seed('a.png'))
        self.assertNotEqual(hand_seed('a.png'), hand_seed('b.png'))

    def _run(self, *args):
        from scripts.lab import hand_sim
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self._last_tmp = tmp
        return hand_sim.main([*args, '--out-dir', str(tmp)]), tmp

    def test_기본_출력은_팀원전달용(self):
        # 기본 경로를 계산만 한다 — 시험이 커밋된 PDF 를 덮으면 안 된다(036f6a3 같은 사고)
        from scripts.lab import hand_sim
        base = ROOT / '보고서/실험05/결선도/팀원전달용'
        self.assertEqual(hand_sim.output_paths(5),
                         (base / '실험05_손그림모사.pdf', base / '실험05_부품그리기.pdf'))

    def test_hand_sim_은_trace_guide_를_안_불러온다(self):
        import subprocess, sys
        out = subprocess.run(
            [sys.executable, '-c',
             "import sys, scripts.lab.hand_sim; print('scripts.lab.trace_guide' in sys.modules)"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(out, 'False')

    def test_출력_폴더는_따라그리기와_같다(self):
        # 두 스킬의 PDF 가 같은 폴더로 간다 — 이름이 두 곳에 적혀 있어 시험만 둘을 함께 안다
        from scripts.lab import hand_sim, trace_guide
        self.assertEqual(hand_sim.OUT_DIR, '팀원전달용')
        self.assertEqual(hand_sim.OUT_DIR, trace_guide.OUT_DIR)

    def test_실험04_MUX_한_장(self):
        from pypdf import PdfReader
        (sim, guide), tmp = self._run('--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png')
        self.assertEqual(sorted(p.name for p in tmp.iterdir()),
                         ['실험04_부품그리기.pdf', '실험04_손그림모사.pdf'])
        self.assertEqual([len(p.images) for p in PdfReader(str(sim)).pages], [1])
        pages = PdfReader(str(guide)).pages
        self.assertEqual([len(p.images) for p in pages], [1])
        text = pages[0].extract_text()
        for s in ('회색 선은 이미 그려져 있어요', '다리', '74HC04'):   # 부품 다리도 회색이다 — 빠뜨리지 않게
            self.assertIn(s, text)

    def test_실험05_PDF_둘은_완성본마다_한_쪽(self):
        from pypdf import PdfReader
        (sim, guide), _ = self._run('--experiment', '5')
        self.assertEqual([len(p.images) for p in PdfReader(str(sim)).pages], [1, 1])
        pages = PdfReader(str(guide)).pages
        self.assertEqual([len(p.images) for p in pages], [1, 1])
        self.assertIn('74HC42', pages[0].extract_text())
        self.assertIn('74HC20', pages[1].extract_text())
        # Windows 글꼴에서 25행 표의 마지막 입력만 다음 쪽으로 밀리던 회귀.
        self.assertIn('Bit3', pages[0].extract_text())
        self.assertIn('레일 쪽 끝 중앙GND레일7행 옆', pages[0].extract_text())

    def test_실험05_손그림모사는_브레드보드_PDF_판에_글자_없이(self):
        # 작성자가 실험 이름을 손으로 적는다 — 쪽 크기·그림 자리가 빈 판형 PDF 와 같아야 홀이 겹친다
        import pymupdf
        (sim, _), _ = self._run('--experiment', '5')
        ref = pymupdf.open(str(ROOT / '.claude/assets/breadboard_v2/Breadboard_v2.pdf'))[0]
        ref_rect = ref.get_image_rects(ref.get_images()[0][0])[0]
        doc = pymupdf.open(str(sim))
        self.assertEqual(len(doc), 2)
        for page in doc:
            self.assertEqual(page.rect, ref.rect)
            self.assertEqual(page.get_text().strip(), '')
            rect = page.get_image_rects(page.get_images()[0][0])[0]
            for got, want in ((rect.x0, ref_rect.x0), (rect.y0, ref_rect.y0), (rect.x1, ref_rect.x1)):
                self.assertAlmostEqual(got, want, places=2)

    def test_PDF_검사가_실패하면_아무것도_안_쓴다(self):
        from unittest import mock
        from scripts.lab import hand_sim
        with mock.patch.object(hand_sim, 'check_pdf', side_effect=ValueError('넘침')):
            with self.assertRaises(SystemExit) as cm:
                self._run('--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png')
        self.assertIn('넘침', str(cm.exception))
        self.assertEqual(list(self._last_tmp.iterdir()), [])

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
            hand_sim.check_pdf(tmp / 'two.pdf', 1)

    def test_결선도_없는_완성본_이름은_거절(self):
        # 두 PNG 이름이 같아져 안내판이 손그림모사를 덮는다 — 쪽 검사로는 못 잡는다
        from scripts.lab import hand_sim
        calls = []
        with self.assertRaises(ValueError):
            hand_sim.render_final(lambda *a, **k: calls.append(a), 'x.png', Path('/nonexistent'))
        self.assertEqual(calls, [])

    def _handout(self, experiment, builder, final_name, tamper=None):
        """실제 빌더로 임시 손그림모사 PDF 와 해당 획 모델을 만든다."""
        from scripts.lab import hand_sim
        board = _load().load_board(experiment)
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        _, sim_bb, _ = hand_sim.render_final(getattr(board, builder), final_name, tmp)
        if tamper:
            tamper(sim_bb)
        return hand_sim.make_handout_pdf(sim_bb.spec, [sim_bb], tmp / 'sim.pdf'), sim_bb

    def test_손그림모사_쪽은_빈_판형_그대로다(self):
        from scripts.lab import hand_grid
        pdf, _ = self._handout(5, 'build_e5_bcd', '실험05_1-2_결선도_BCD디코더.png')
        tpl = hand_grid.board_image(ROOT / '.claude/assets/breadboard_v2/Breadboard_v2.pdf', 0)
        self.assertEqual(hand_grid.board_image(pdf, 0).md5, tpl.md5)

    def test_손그림모사는_격자_보정이_된다(self):
        from scripts.lab import hand_grid
        pdf, _ = self._handout(5, 'build_e5_bcd', '실험05_1-2_결선도_BCD디코더.png')
        cal = hand_grid.calibrate(hand_grid.board_image(pdf, 0), 'v2')
        self.assertLessEqual(max(cal.res_x, cal.res_y), 0.5)

    def test_배선은_벡터_획이다(self):
        import pymupdf
        pdf, bb = self._handout(5, 'build_e5_bcd', '실험05_1-2_결선도_BCD디코더.png')
        with pymupdf.open(pdf) as doc:
            lines = [d for d in doc[0].get_drawings() if d['type'] == 's']
        self.assertEqual(len(lines), len(bb.hand_strokes))
        # 빈 판형 이미지 자리와 논리 판 크기에서 독립적으로 기대 좌표를 계산한다.
        with pymupdf.open(ROOT / '.claude/assets/breadboard_v2/Breadboard_v2.pdf') as tpl:
            slot = tpl[0].get_image_rects(tpl[0].get_images()[0][0])[0]
        sx, sy = slot.width / bb.spec.size[0], slot.height / bb.spec.size[1]
        for d, s in zip(lines, bb.hand_strokes):
            for got, point in ((d['items'][0][1], s['points'][0]),
                               (d['items'][-1][2], s['points'][-1])):
                self.assertAlmostEqual(got.x, slot.x0 + point[0] * sx, delta=0.05)
                self.assertAlmostEqual(got.y, slot.y0 + point[1] * sy, delta=0.05)
            self.assertAlmostEqual(d['width'], s['width'] * sx, delta=0.01)

    def test_실험04_v1_도_벡터_획(self):
        import pymupdf
        pdf, bb = self._handout(4, 'build_e4_mux', '실험04_1-1_결선도_4x1MUX.png')
        with pymupdf.open(pdf) as doc:
            page = doc[0]
            self.assertEqual(len(page.get_images()), 1)
            self.assertEqual(len([d for d in page.get_drawings() if d['type'] == 's']), len(bb.hand_strokes))

    def test_overlay_에_남은_그림은_거절(self):
        def tamper(bb):
            bb.overlay.putpixel((10, 10), (255, 0, 0, 255))
        with self.assertRaisesRegex(ValueError, 'overlay'):
            self._handout(4, 'build_e4_mux', '실험04_1-1_결선도_4x1MUX.png', tamper=tamper)

    def test_hand_를_못_받는_빌더는_이름을_다_대고_멈춘다(self):
        # 그리기 전에 전부 본다 — 앞 완성본만 뽑고 터지지 않는다
        with self.assertRaises(SystemExit) as cm:
            self._run('--experiment', '4')          # FINALS 중 DMUX 가 hand 를 안 받는다
        self.assertIn('build_e4_dmux', str(cm.exception))
        self.assertIn('make-hand-sim', str(cm.exception))
        self.assertEqual(list(self._last_tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
