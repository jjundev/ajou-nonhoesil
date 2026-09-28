"""따라 그리기 PDF 생성기 (`scripts/lab/trace_guide.py`, 2026-09-28)."""
import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from scripts.lab import trace_guide
from scripts.lab.hand_grid import load_renderer
from scripts.lab.html2pdf import PdfError, resolve_chrome

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/board_layers/배치.py"


def _chrome():
    try:
        resolve_chrome()
        return True
    except PdfError:
        return False


class CheckLayers(unittest.TestCase):
    def test_맞으면_조용하다(self):
        trace_guide.check_layers('x', [(1, 3, 'a'), (4, 6, 'b')], 6)

    def test_빈틈이_있으면_번호를_말한다(self):
        with self.assertRaisesRegex(trace_guide.LayerError, '4번'):
            trace_guide.check_layers('x', [(1, 3, 'a'), (5, 6, 'b')], 6)

    def test_겹치면_번호를_말한다(self):
        with self.assertRaisesRegex(trace_guide.LayerError, '4번'):
            trace_guide.check_layers('x', [(1, 3, 'a'), (3, 6, 'b')], 6)

    def test_모자라면_개수를_말한다(self):
        with self.assertRaisesRegex(trace_guide.LayerError, '7개'):
            trace_guide.check_layers('x', [(1, 3, 'a'), (4, 6, 'b')], 7)

    def test_끝이_시작보다_작으면_거절(self):
        with self.assertRaises(trace_guide.LayerError):
            trace_guide.check_layers('x', [(1, 0, 'a')], 1)


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = load_renderer().load_board_file(FIXTURE, 'board_layers')

    def test_완성본_한_쪽과_층마다_한_쪽(self):
        with tempfile.TemporaryDirectory() as d:
            pages = trace_guide.build_pages(self.board, d)
            self.assertEqual(len(pages), 3)
            self.assertEqual([[r['n'] for r in p.rows] for p in pages], [[], [1], [2]])
            self.assertEqual(pages[0].notes, ['입력 <A> & 메모'])
            self.assertEqual([bool(p.legend) for p in pages], [False, True, True])
            self.assertNotIn('처음부터', pages[1].legend)   # 픽스처는 잭 두 가닥뿐 — 칩·LED 가 없다
            self.assertIn('1/2 · +5V 잭 (1~1번)', pages[1].heading)
            for p in pages:
                self.assertTrue(os.path.exists(os.path.join(d, p.image)))

    def test_LAYERS_가_없으면_멈춘다(self):
        board = load_renderer().load_board_file(ROOT / "tests/fixtures/board_min/배치.py", 'board_min')
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(trace_guide.LayerError, 'LAYERS'):
            trace_guide.build_pages(board, d)


class Guards(unittest.TestCase):
    def test_layer_를_안_받는_빌더는_이름을_말한다(self):
        mini = load_renderer().load_board_file(ROOT / "tests/fixtures/board_min/배치.py", 'board_min')
        board = types.SimpleNamespace(FINALS=mini.FINALS, LAYERS={'min.png': [(1, 2, '잭')]})
        with tempfile.TemporaryDirectory() as d, \
                self.assertRaisesRegex(trace_guide.LayerError, r'build_min.*layer=None'):
            trace_guide.build_pages(board, d)

    def test_층_보드_출력을_삼킨다(self):
        board = load_renderer().load_board_file(FIXTURE, 'board_layers')
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(buf):
            trace_guide.build_pages(board, d)
        self.assertEqual(buf.getvalue(), '')


class Html(unittest.TestCase):
    def _pages(self):
        return [
            trace_guide.Page('실험04_완성.png', '완성본', [], ['n.c. <핀> & 메모'], ''),
            trace_guide.Page('실험04_층1.png', '1/1 · 층', [
                {'n': 3, 'kind': 'mid', 'from': '좌 d23', 'to': '우 a30',
                 'desc': "(E'·S1'·S0'·D0)' (U1 pin 6) -> U3 pin 1", 'count': 1}], [], '안내 <한 줄>'),
        ]

    def test_쪽마다_섹션_하나(self):
        out = trace_guide.render_html(self._pages(), '제목')
        self.assertEqual(out.count('<section class="page">'), 2)
        self.assertIn('size: 210mm 420mm', out)

    def test_한글_파일명은_인코딩한다(self):
        out = trace_guide.render_html(self._pages(), '제목')
        self.assertNotIn('src="실험04', out)
        self.assertIn('src="%EC%8B%A4', out)

    def test_설명의_특수문자를_이스케이프한다(self):
        out = trace_guide.render_html(self._pages(), '제목')
        self.assertIn('-&gt; U3 pin 1', out)
        self.assertIn('n.c. &lt;핀&gt; &amp; 메모', out)
        self.assertIn('class="n kind-mid"', out)

    def test_안내는_이스케이프해_싣는다(self):
        self.assertIn('<p class="legend">안내 &lt;한 줄&gt;</p>', trace_guide.render_html(self._pages(), '제목'))

    def test_안내는_있는_부품만_먼저_그리라고_한다(self):
        """칩·LED·저항은 모든 층에 색으로 그려진다 — 그 보드에 있는 것만 말한다(실험02 는 LED 가 없다)."""
        ns = types.SimpleNamespace
        self.assertTrue(trace_guide.legend_for(ns(chips=[1], led_chains=[1]))
                        .endswith('칩·LED·저항은 처음부터 그려 두세요.'))
        chip_only = trace_guide.legend_for(ns(chips=[1], led_chains=[]))
        self.assertTrue(chip_only.endswith('칩은 처음부터 그려 두세요.'))
        self.assertNotIn('LED', chip_only)
        self.assertEqual(trace_guide.legend_for(ns(chips=[], led_chains=[])), trace_guide.LEGEND)

    def test_층_쪽에만_안내가_있다(self):
        out = trace_guide.render_html(self._pages(), '제목')
        self.assertEqual(out.count('class="legend"'), 1)


@unittest.skipUnless(_chrome(), 'Chrome 없음')
class Pdf(unittest.TestCase):
    def test_PDF_는_쪽마다_그림_하나(self):
        from pypdf import PdfReader
        board = load_renderer().load_board_file(FIXTURE, 'board_layers')
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / '따라그리기.pdf'
            n = trace_guide.make_pdf(board, out)
            reader = PdfReader(str(out))
            self.assertEqual(n, 3)
            self.assertEqual(len(reader.pages), 3)
            for page in reader.pages:
                self.assertEqual(len(page.images), 1)
                self.assertAlmostEqual(float(page.mediabox.height), 420 / 25.4 * 72, delta=2)

    def test_실험04_는_층마다_한_쪽(self):
        """DMUX 2층(표 14행)이 제일 길다 — 넘치면 그림 없는 쪽이 생긴다(2026-09-28 16쪽)."""
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as d:
            out, n = trace_guide.make_guide(4, Path(d) / 'e4.pdf')
            reader = PdfReader(str(out))
            self.assertEqual(n, 15)
            self.assertEqual([len(p.images) for p in reader.pages], [1] * n)


@unittest.skipUnless(_chrome(), 'Chrome 없음')
class Overflow(unittest.TestCase):
    def test_쪽이_넘치면_층을_말하고_PDF_를_지운다(self):
        board = load_renderer().load_board_file(FIXTURE, 'board_layers')
        row = {'n': 1, 'kind': 'sig', 'from': '좌 a1', 'to': '좌 b2', 'desc': '넘치는 줄', 'count': 1}

        build = trace_guide.build_pages     # 패치 전 원본

        def fake(_board, d):
            real = build(board, d)
            return [real[0], trace_guide.Page(real[1].image, '긴 층', [row] * 80, [], trace_guide.LEGEND), real[2]]

        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'x.pdf'
            with mock.patch.object(trace_guide, 'build_pages', side_effect=fake), \
                    self.assertRaisesRegex(trace_guide.LayerError, '긴 층'):
                trace_guide.make_pdf(board, out)
            self.assertFalse(out.exists())


class Main(unittest.TestCase):
    def test_시간초과는_종료코드_1(self):
        with mock.patch.object(trace_guide, 'make_guide',
                               side_effect=subprocess.TimeoutExpired('chrome', 120)), \
             mock.patch('sys.stderr'):
            self.assertEqual(trace_guide.main(['4']), 1)

    def test_PDF_실패는_종료코드_1(self):
        with mock.patch.object(trace_guide, 'make_guide', side_effect=PdfError('Chrome 없음')), \
             mock.patch('sys.stderr') as err:
            self.assertEqual(trace_guide.main(['4']), 1)
        self.assertIn('[ERROR]', ''.join(c.args[0] for c in err.write.call_args_list))

    def test_출력_경로(self):
        p = trace_guide.output_path(4)
        self.assertEqual(p.parts[-3:], ('결선도', '팀원전달용', '실험04_따라그리기.pdf'))


if __name__ == "__main__":
    unittest.main()
