"""`scripts/lab/figure_export.py` — 캡처용 사본, PNG 추출, 그림 속 숫자 검사.

Chrome 을 부르는 경로는 `subprocess.run` 을 가로채 명령과 사본 내용을 본다.
Chrome 이 있는 기계에서만 실측 하나를 돈다.
"""

import contextlib
import io
import struct
import subprocess
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from scripts.lab import figure_export as fx
from scripts.lab.html2pdf import PdfError, resolve_chrome


def _chrome_available() -> bool:
    try:
        resolve_chrome()
        return True
    except PdfError:
        return False


def _uri_path(uri) -> Path:
    return Path(urllib.parse.unquote(urllib.parse.urlparse(uri).path))


class CaptureCopy(unittest.TestCase):
    def test_사본에_doctype_과_charset_이_붙는다(self):
        out = fx.wrap_for_capture("<title>t</title><p>한글</p>")
        self.assertTrue(out.startswith("<!doctype html>"))
        self.assertIn('<meta charset="utf-8">', out)
        self.assertIn("<p>한글</p>", out)

    def test_dump_dom_은_원본이_아니라_사본을_연다(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        html = Path(tmp.name) / "그림.html"
        html.write_text("<title>t</title><p>한글</p>", encoding="utf-8")
        seen = {}

        def fake_run(cmd, **kw):
            seen["cmd"] = cmd
            seen["text"] = _uri_path(cmd[-1]).read_text(encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, '<html data-fig-heights="10">', "")

        with mock.patch.object(fx, "resolve_chrome", return_value="chrome"), \
             mock.patch.object(fx.subprocess, "run", side_effect=fake_run):
            dom = fx.dump_dom(html)
        self.assertIn("--dump-dom", seen["cmd"])
        self.assertIn('<meta charset="utf-8">', seen["text"])
        self.assertNotEqual(_uri_path(seen["cmd"][-1]), html)
        self.assertEqual(dom, '<html data-fig-heights="10">')

    def test_없는_html_은_거절한다(self):
        with self.assertRaises(fx.FigureError):
            fx.dump_dom(Path("/없는/그림.html"))


class Heights(unittest.TestCase):
    def test_높이를_읽는다(self):
        self.assertEqual(fx.parse_heights('<html lang="ko" data-fig-heights="510,636">'), [510, 636])

    def test_기록이_없으면_멈춘다(self):
        with self.assertRaises(fx.FigureError):
            fx.parse_heights("<html>")


class Export(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.html = self.dir / "그림.html"
        self.html.write_text("<title>t</title>", encoding="utf-8")
        self.calls = []

    def _fake(self, write=True):
        def run(cmd, **kw):
            self.calls.append(cmd)
            if write:
                for a in cmd:
                    if a.startswith("--screenshot="):
                        Path(a.split("=", 1)[1]).write_bytes(b"\x89PNG")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return run

    def test_그림마다_높이와_번호로_찍는다(self):
        with mock.patch.object(fx, "resolve_chrome", return_value="chrome"), \
             mock.patch.object(fx.subprocess, "run", side_effect=self._fake()):
            out = fx.export_pngs(self.html, self.dir, ["가.png", "나.png"], [400, 520])
        self.assertEqual([p.name for p in out], ["가.png", "나.png"])
        first, second = self.calls
        self.assertIn("--window-size=1000,400", first)
        self.assertIn("--window-size=1000,520", second)
        self.assertIn("--force-device-scale-factor=3", first)
        self.assertTrue(first[-1].endswith("?fig=1"))
        self.assertTrue(second[-1].endswith("?fig=2"))

    def test_파일이_안_생기면_실패한다_옛_파일이_있어도(self):
        (self.dir / "가.png").write_bytes(b"old")
        with mock.patch.object(fx, "resolve_chrome", return_value="chrome"), \
             mock.patch.object(fx.subprocess, "run", side_effect=self._fake(write=False)):
            with self.assertRaises(fx.FigureError):
                fx.export_pngs(self.html, self.dir, ["가.png"], [400])

    def test_이름과_높이_수가_다르면_멈춘다(self):
        with self.assertRaises(fx.FigureError):
            fx.export_pngs(self.html, self.dir, ["가.png"], [400, 500])


class Numbers(unittest.TestCase):
    DOM = ('<svg><text x="1" class="tick">0.5</text>'
           '<text x="2">V<tspan dy="5">T+</tspan><tspan dy="-5">​</tspan> 2.75 V</text>'
           '<text class="label tick">7.25</text>'
           '<text>폭 1.30 V</text></svg>')

    def test_눈금은_빼고_소수값을_모은다(self):
        self.assertEqual(fx.figure_numbers(self.DOM), ["2.75", "1.30"])

    def test_본문에_같은_글자로_있으면_통과한다(self):
        self.assertEqual(fx.check_figure_numbers(self.DOM, "문턱은 2.75V, 폭은 1.30V 다."), [])

    def test_자릿수를_바꾼_값도_잡는다(self):
        found = fx.check_figure_numbers(self.DOM, "문턱은 2.75V, 폭은 1.3V 다.")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].level, "error")
        self.assertIn("1.30", found[0].message)

    def test_정수는_보지_않는다(self):
        self.assertEqual(fx.figure_numbers("<svg><text>5 V</text></svg>"), [])


class Cli(unittest.TestCase):
    def test_capture_표가_없는_주차는_한_줄을_내고_끝난다(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
             mock.patch.object(fx, "dump_dom", side_effect=AssertionError("Chrome 을 부르면 안 된다")):
            code = fx.main(["1"])
        self.assertEqual(code, 0)
        self.assertIn("capture 표가 없어", buf.getvalue())


@unittest.skipUnless(_chrome_available(), "Chrome 이 없는 환경")
class ChromeRoundTrip(unittest.TestCase):
    def test_높이를_읽고_3배로_찍는다(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        html = d / "그림.html"
        html.write_text(
            '<title>t</title><div style="width:1000px;height:120px">한글</div>'
            '<script>document.documentElement.setAttribute("data-fig-heights","120");</script>',
            encoding="utf-8")
        heights = fx.parse_heights(fx.dump_dom(html))
        self.assertEqual(heights, [120])
        (png,) = fx.export_pngs(html, d, ["out.png"], heights)
        w, h = struct.unpack(">II", png.read_bytes()[16:24])
        self.assertEqual((w, h), (3000, 360))


if __name__ == "__main__":
    unittest.main()
