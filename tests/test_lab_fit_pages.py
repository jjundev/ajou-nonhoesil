import tempfile
import unittest
from pathlib import Path

from scripts.lab.fit_pages import FIT_OPEN, FIT_PLAIN, fit_pages, page_box, strip, tag, fit_style
from scripts.lab.html2pdf import PdfError, html_to_pdf, resolve_chrome

_PAGE = "<style>@page { size: 210mm 420mm; margin: 12mm 10mm; }</style>"


def _chrome_available() -> bool:
    try:
        resolve_chrome()
        return True
    except PdfError:
        return False


class TestPageBox(unittest.TestCase):
    def test_기본_쪽의_폭과_여백을_HTML_에서_읽는다(self):
        self.assertEqual(page_box(_PAGE), (210, 12, 10))

    def test_기본_쪽_규칙이_없으면_알린다(self):
        with self.assertRaises(ValueError):
            page_box("<p>x</p>")


class TestTag(unittest.TestCase):
    def test_단계_블록마다_차례_번호를_단다(self):
        html = f"{FIT_OPEN}a</div><p>b</p>{FIT_OPEN}c</div>"
        self.assertEqual(tag(html),
                         '<div class="stage" data-fit="0">a</div><p>b</p>'
                         '<div class="stage" data-fit="1">c</div>')

    def test_두_번_돌려도_같다(self):
        html = _PAGE + f"{FIT_OPEN}a</div>{FIT_OPEN}c</div>"
        once = tag(html) + fit_style([10.0, 20.0], (210, 12, 10))
        self.assertEqual(tag(strip(once)), tag(html))
    def test_fit_래퍼도_단계와_한_번호열이다(self):
        html = f"{FIT_PLAIN}a</div>{FIT_OPEN}b</div>{FIT_PLAIN}c</div>"
        once = tag(html)
        self.assertEqual(once,
                         '<div class="fit" data-fit="0">a</div>'
                         '<div class="stage" data-fit="1">b</div>'
                         '<div class="fit" data-fit="2">c</div>')
        self.assertEqual(tag(once), once)


class TestFitStyle(unittest.TestCase):
    def test_블록마다_제_높이의_쪽을_준다(self):
        css = fit_style([100.0, 250.4], (210, 12, 10))
        # 높이 = 블록 + 위아래 여백 + 여유 4mm, 올림
        self.assertIn("@page fit-0 { size: 210mm 128mm; margin: 12mm 10mm; }", css)
        self.assertIn("@page fit-1 { size: 210mm 279mm; margin: 12mm 10mm; }", css)
        self.assertIn('[data-fit="1"] { page: fit-1; }', css)


@unittest.skipUnless(_chrome_available(), "Chrome 이 없는 환경")
class TestChromeFit(unittest.TestCase):
    """2026-09-28 사용자: 쪽 길이를 내용에 맞춰(wrap_content). 단계 블록 하나 = 쪽 하나."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.html = Path(self.tmp.name) / "in.html"
        self.html.write_text(
            _PAGE + "<p>공통면</p>"
            f'{FIT_OPEN}<div style="height:150mm">짧은 단계</div></div>'
            f'{FIT_OPEN}<div style="height:300mm">긴 단계</div></div>'
            "<p>기록표</p>", encoding="utf-8")

    def test_단계는_제_높이의_쪽_하나에_들고_나머지는_기본_쪽이다(self):
        from pypdf import PdfReader
        heights = fit_pages(self.html)
        self.assertEqual([round(h) for h in heights], [150, 300])
        pdf = html_to_pdf(self.html, Path(self.tmp.name) / "out.pdf")
        pages = [(round(float(p.mediabox.height) / 72 * 25.4), p.extract_text().strip())
                 for p in PdfReader(str(pdf)).pages]
        self.assertEqual(pages, [(420, "공통면"), (178, "짧은 단계"),
                                 (328, "긴 단계"), (420, "기록표")])
