"""손그림 PDF 에서 판형을 꺼내 렌더러 좌표표에 맞추는 부분을 검사한다.

판형 좌표를 **사람이 뜨지 않는다.** 배포본은 정본 `Breadboard.jpg` 와 같은
그림인데 가로가 5% 넓다 (`breadboard-diagram/SKILL.md` §2). 눈대중으로 새로
뜨면 배선 끝점이 홀 안에 안 들어가고, 그림은 멀쩡해 보여서 눈으로는 안 잡힌다.
그래서 검출한 격자를 렌더러의 권위 있는 좌표표에 1차식으로 맞추고, 잔차가
크면 소리를 내며 멈춘다.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.lab import hand_grid

ROOT = Path(__file__).resolve().parents[1]
HANDOUT = ROOT / "강의노트/공지사항/Breadboard.pdf"


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


if __name__ == '__main__':
    unittest.main()
