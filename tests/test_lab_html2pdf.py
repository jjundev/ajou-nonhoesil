import tempfile
import unittest
from pathlib import Path

from scripts.lab.html2pdf import DEFAULT_CHROME, PdfError, html_to_pdf


@unittest.skipUnless(Path(DEFAULT_CHROME).exists(), "Chrome 이 없는 환경")
class TestChromeConversion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.html = Path(self.tmp.name) / "in.html"
        self.html.write_text(
            "<style>@page{size:A4}</style><h1>표지</h1>", encoding="utf-8"
        )

    def test_produces_a_pdf(self):
        out = html_to_pdf(self.html, Path(self.tmp.name) / "out.pdf")
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 1000)

    def test_succeeds_despite_macos_stderr_noise(self):
        """Chrome 은 정상 동작 중에도 task_policy_set 에러를 stderr 로 뱉는다.

        종료 코드나 stderr 로 판정하면 멀쩡한 변환을 실패로 읽는다.
        """
        out = html_to_pdf(self.html, Path(self.tmp.name) / "noise.pdf")
        self.assertTrue(out.exists())

    def test_overwrites_and_refreshes_mtime(self):
        target = Path(self.tmp.name) / "twice.pdf"
        html_to_pdf(self.html, target)
        first = target.stat().st_mtime
        import time
        time.sleep(1.1)
        html_to_pdf(self.html, target)
        self.assertGreater(target.stat().st_mtime, first)

    def test_creates_missing_output_directory(self):
        out = html_to_pdf(self.html, Path(self.tmp.name) / "새폴더" / "out.pdf")
        self.assertTrue(out.exists())


class TestErrors(unittest.TestCase):
    def test_missing_input_raises(self):
        with self.assertRaises(PdfError) as ctx:
            html_to_pdf("/없는/입력.html", "/tmp/x.pdf")
        self.assertIn("입력 HTML", str(ctx.exception))

    def test_missing_chrome_raises_with_config_hint(self):
        tmp = tempfile.mkdtemp()
        src = Path(tmp) / "in.html"
        src.write_text("<h1>x</h1>", encoding="utf-8")
        with self.assertRaises(PdfError) as ctx:
            html_to_pdf(src, Path(tmp) / "out.pdf", chrome="/없는/크롬")
        self.assertIn("과목정보.md", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
