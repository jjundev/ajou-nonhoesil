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


class TestSuccessRule(unittest.TestCase):
    """성공 판정이 **파일 생성 여부**인지 고정한다. Chrome 은 macOS 에서 정상
    동작 중에도 stderr 로 `task_policy_set` 에러를 뱉으므로, 종료 코드나 stderr
    로 판정하면 멀쩡한 변환이 실패로 읽힌다.

    진짜 Chrome 은 그 조합(성공 + 잡음 + 비정상 종료코드)을 마음대로 만들어낼
    수 없으므로 그 동작을 흉내내는 스텁으로 규칙 자체를 시험한다. Chrome 이
    없는 환경에서도 돈다.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.html = Path(self.tmp.name) / "in.html"
        self.html.write_text("<h1>표지</h1>", encoding="utf-8")

    def _stub(self, script: str) -> str:
        path = Path(self.tmp.name) / "fake-chrome"
        path.write_text("#!/bin/sh\n" + script, encoding="utf-8")
        path.chmod(0o755)
        return str(path)

    def test_nonzero_exit_and_stderr_noise_still_succeed(self):
        chrome = self._stub(
            'for arg in "$@"; do\n'
            '  case "$arg" in --print-to-pdf=*) out="${arg#--print-to-pdf=}";; esac\n'
            "done\n"
            "printf '%s' '%PDF-1.4 stub' > \"$out\"\n"
            "echo 'task_policy_set TASK_CATEGORY_POLICY: (os/kern) invalid argument' >&2\n"
            "exit 1\n"
        )
        out = html_to_pdf(self.html, Path(self.tmp.name) / "ok.pdf", chrome=chrome)
        self.assertTrue(out.exists())

    def test_clean_exit_without_a_file_still_fails(self):
        chrome = self._stub("echo noise >&2\nexit 0\n")
        with self.assertRaises(PdfError):
            html_to_pdf(self.html, Path(self.tmp.name) / "none.pdf", chrome=chrome)


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
