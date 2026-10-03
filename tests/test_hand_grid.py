"""손그림 PDF 에서 판형을 꺼내 렌더러 좌표표에 맞추는 부분을 검사한다.

판형 좌표를 **사람이 뜨지 않는다.** 배포본은 정본 `Breadboard.jpg` 와 같은
그림인데 가로가 5% 넓다 (`breadboard-diagram/SKILL.md` §2). 눈대중으로 새로
뜨면 배선 끝점이 홀 안에 안 들어가고, 그림은 멀쩡해 보여서 눈으로는 안 잡힌다.
그래서 검출한 격자를 렌더러의 권위 있는 좌표표에 1차식으로 맞추고, 잔차가
크면 소리를 내며 멈춘다.
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.lab import hand_grid

ROOT = Path(__file__).resolve().parents[1]
HANDOUT = ROOT / "강의노트/공지사항/Breadboard.pdf"
V2_DIR = ROOT / ".claude/assets/breadboard_v2"
V2_PDF = V2_DIR / "Breadboard_v2.pdf"


class BoardExtraction(unittest.TestCase):
    def test_배포본에서_판형_래스터를_꺼낸다(self):
        board = hand_grid.board_image(HANDOUT)
        self.assertGreater(board.width, 400)
        self.assertGreater(board.height, 400)
        self.assertEqual(len(board.md5), 32)

    def test_없는_쪽을_부르면_거절한다(self):
        with self.assertRaises(hand_grid.GridError):
            hand_grid.board_image(HANDOUT, page_index=99)

    def test_추가_사진이나_스탬프가_있어도_타일_판형을_정상_추출한다(self):
        import io
        import tempfile
        import fitz
        from PIL import Image

        doc = fitz.open(str(HANDOUT))
        page = doc[0]
        stamp = Image.new("RGB", (60, 60), (200, 0, 0))
        buf = io.BytesIO()
        stamp.save(buf, format="PNG")
        page.insert_image(fitz.Rect(10, 10, 70, 70), stream=buf.getvalue())
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            doc.save(tmp.name)
            doc.close()
            board = hand_grid.board_image(tmp.name)
            self.assertEqual(board.width, 998)
            self.assertEqual(board.height, 1345)


class GridDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = hand_grid.board_image(HANDOUT)

    def test_열_28개와_행_63개를_찾는다(self):
        cols, rows = hand_grid.detect_grid(self.board.data)
        self.assertEqual(len(cols), 28)
        self.assertEqual(len(rows), 63)

    def test_검출된_열은_왼쪽에서_오른쪽_순이다(self):
        cols, _ = hand_grid.detect_grid(self.board.data)
        self.assertEqual(cols, sorted(cols))


class Fit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cal = hand_grid.calibrate(hand_grid.board_image(HANDOUT))

    def test_잔차가_3px_아래다(self):
        self.assertLess(self.cal.res_x, 3.0)
        self.assertLess(self.cal.res_y, 3.0)

    def test_렌더러_홀이_페이지_픽셀로_옮겨진다(self):
        mod = hand_grid.load_renderer()
        px, py = self.cal.to_px(239, mod.ROW0)   # 좌 a열 1행
        self.assertGreater(px, 0)
        self.assertGreater(py, 0)

    def test_좌표표를_렌더러에서_읽는다(self):
        """숫자를 베껴 적으면 한쪽만 고쳤을 때 갈린다."""
        cols = hand_grid._reference_cols(hand_grid.load_renderer())
        self.assertEqual(len(cols), 28)
        self.assertEqual(len(set(cols)), 28)

    def test_행_간격이_단조_증가한다(self):
        ys = [self.cal.to_px(0, hand_grid.load_renderer().ROW0 + i * 16.345)[1]
              for i in range(10)]
        self.assertEqual(ys, sorted(ys))


class BorderLine(unittest.TestCase):
    """인쇄된 판형 테두리가 홀 행으로 잡히면 63행으로 안 모인다.

    학생 PDF 에서 실제로 일어난 고장이다 — 아래 테두리 한 줄 때문에 구간이
    94개로 튀었다. 그 PDF 는 저장소 밖에 있으므로 배포본에 같은 줄을 합성한다.
    합성하지 않으면 이 필터는 배포본에서 무동작이라 시험대에 오르지 않는다.
    """

    @classmethod
    def setUpClass(cls):
        cls.board = hand_grid.board_image(HANDOUT)
        cls.clean_cols, cls.clean_rows = hand_grid.detect_grid(cls.board.data)

    def _with_line(self, ratio=0.98):
        """홀 행 **사이**에 폭 `ratio` 만큼 꽉 찬 검은 줄을 그은 래스터."""
        import io
        from PIL import Image, ImageDraw

        im = Image.open(io.BytesIO(self.board.data)).convert("RGB")
        w, _h = im.size
        # 홀 행 두 개의 한가운데 — 진짜 행을 덮지 않는 자리다
        y = int((self.clean_rows[-3] + self.clean_rows[-2]) / 2)
        ImageDraw.Draw(im).rectangle(
            [int(w * 0.02), y, int(w * ratio), y + 2], fill=(0, 0, 0))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()

    def test_꽉_찬_가로줄이_있어도_63행_28열을_찾는다(self):
        cols, rows = hand_grid.detect_grid(self._with_line())
        self.assertEqual(len(rows), 63)
        self.assertEqual(len(cols), 28)

    def test_가로줄이_행_위치를_밀지_않는다(self):
        """개수만 맞고 자리가 밀리면 맞춤 잔차가 관문을 넘는다."""
        _cols, rows = hand_grid.detect_grid(self._with_line())
        for clean, got in zip(self.clean_rows, rows):
            self.assertLess(abs(clean - got), 1.0)

    def test_홀_행은_거르지_않는다(self):
        """홀 행의 어둠 비율은 0.33 을 넘지 않는다 — 문턱 0.45 아래다."""
        self.assertEqual(len(self.clean_rows), 63)


class Overlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = hand_grid.board_image(HANDOUT)
        cls.cal = hand_grid.calibrate(cls.board)
        cls.page = hand_grid.render_page(HANDOUT, 0)
        cls.tmp = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_쪽을_300dpi_로_그린다(self):
        # A4 세로 594.75x841.5pt -> 300dpi 면 약 2478x3506
        self.assertGreater(self.page.width, 2000)
        self.assertGreater(self.page.height, 3000)

    def test_격자를_덮은_그림이_원본과_크기가_같다(self):
        from PIL import Image
        out = os.path.join(self.tmp, 'grid.png')
        hand_grid.overlay_grid(self.page, self.cal, out)
        self.assertEqual(Image.open(out).size, self.page.size)

    def test_크롭은_요청한_행_범위만큼_잘라_확대한다(self):
        from PIL import Image
        out = os.path.join(self.tmp, 'crop.png')
        hand_grid.crop_rows(self.page, self.cal, 10, 20, out, scale=2)
        im = Image.open(out)
        self.assertGreater(im.width, 0)
        self.assertGreater(im.height, 0)

    def test_거꾸로_된_행_범위는_거절한다(self):
        out = os.path.join(self.tmp, 'x.png')
        with self.assertRaises(hand_grid.GridError):
            hand_grid.crop_rows(self.page, self.cal, 20, 10, out)


class V2Grid(unittest.TestCase):
    """v2 판형 — 26열·63행, geometry.json 과 1px 안. 배포본은 PNG 를 그대로 얹어 보정이 항등이다."""

    @classmethod
    def setUpClass(cls):
        cls.g = json.loads((V2_DIR / "geometry.json").read_text(encoding="utf-8"))

    def _check(self, data):
        cols, rows = hand_grid.detect_grid(data, 'v2')
        self.assertEqual((len(cols), len(rows)), (26, 63))
        for got, c in zip(cols, self.g["columns"]):
            self.assertLessEqual(abs(got - c["x"]), 1.0, c["name"])
        for i, y in enumerate(rows):
            want = self.g["row1_center_y"] + i * self.g["row_pitch"]
            self.assertLessEqual(abs(y - want), 1.0, f"{i + 1}행")

    def test_PNG_에서_26열_63행을_찾는다(self):
        self._check((V2_DIR / "Breadboard_v2.png").read_bytes())

    def test_배포본_PDF_에서_26열_63행을_찾는다(self):
        self._check(hand_grid.board_image(V2_PDF).data)

    def test_배포본_보정은_항등에_가깝다(self):
        """v1 배포본은 가로가 5% 넓었다. v2 배포본은 PNG 를 그대로 얹었다."""
        cal = hand_grid.calibrate(hand_grid.board_image(V2_PDF), 'v2')
        self.assertEqual(cal.version, 'v2')
        self.assertAlmostEqual(cal.ax, 1.0, delta=0.01)
        self.assertAlmostEqual(cal.ay, 1.0, delta=0.01)
        self.assertLess(max(cal.res_x, cal.res_y), 1.0)

    def test_기준_열은_중복_없이_26개다(self):
        cols = hand_grid._reference_cols(hand_grid.load_renderer(), 'v2')
        self.assertEqual((len(cols), len(set(cols))), (26, 26))

    def test_격자_그림을_v2_로_덮는다(self):
        cal = hand_grid.calibrate(hand_grid.board_image(V2_PDF), 'v2', dpi=100)
        page = hand_grid.render_page(V2_PDF, 0, dpi=100)
        with tempfile.TemporaryDirectory() as d:
            out = hand_grid.overlay_grid(page, cal, os.path.join(d, "p1.png"))
            self.assertTrue(os.path.exists(out))


    def test_우_블록_크롭은_가운데_레일을_품는다(self):
        """우 LED 사슬의 GND 는 가운데 레일에 꽂힌다. 그 열은 소속이 left 라 block='right' 필터에서
        빠지면 크롭 여백에만 기대게 된다 — 두 블록이 나눠 쓰는 열은 늘 넣는다."""
        cal = hand_grid.calibrate(hand_grid.board_image(V2_PDF), 'v2', dpi=100)
        page = hand_grid.render_page(V2_PDF, 0, dpi=100)
        mod = hand_grid.load_renderer()
        spec = mod.board_spec('v2')
        mid = cal.to_px(spec.cols['right']['mid_gnd'], spec.row0)[0]
        right = cal.to_px(spec.cols['right']['vcc'], spec.row0)[0]
        with tempfile.TemporaryDirectory() as d:
            out = hand_grid.crop_rows(page, cal, 10, 20, os.path.join(d, "c.png"), scale=1, block='right')
            from PIL import Image
            with Image.open(out) as im:
                width = im.width
        self.assertEqual(width, int(right + 40) - int(mid - 80))


class BoardMismatch(unittest.TestCase):
    """승인 결선의 판형과 제출 PDF 의 판형이 다르면 추측으로 넘어가지 않고 멈춘다."""

    def test_승인본_v2_에_v1_배포본이면_멈춘다(self):
        with self.assertRaisesRegex(hand_grid.GridError, "판형 버전 불일치"):
            hand_grid.calibrate(hand_grid.board_image(HANDOUT), 'v2')

    def test_옛_호출처럼_v1_로_v2_배포본을_보정하면_멈춘다(self):
        """Review Focus 4 — 옛 스킬 문서의 `calibrate(b)` 는 기본 v1 이다."""
        with self.assertRaisesRegex(hand_grid.GridError, "판형 버전 불일치"):
            hand_grid.calibrate(hand_grid.board_image(V2_PDF))

    def test_기대_판형은_주차_배치_py_에서_읽는다(self):
        self.assertEqual(hand_grid.expected_board(1), 'v1')


if __name__ == '__main__':
    unittest.main()
