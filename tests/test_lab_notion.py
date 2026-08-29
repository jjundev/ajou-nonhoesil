import io
import json
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from scripts.lab import notion

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def fake_response(payload):
    """`urlopen` 의 컨텍스트 매니저 흉내. 실제 네트워크를 타지 않는다."""
    resp = mock.MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def http_error(code, body):
    return urllib.error.HTTPError(
        "https://api.notion.com/v1/pages", code, "err", {},
        io.BytesIO(json.dumps(body).encode("utf-8")))


class TestLoadToken(unittest.TestCase):
    def test_reads_the_environment_variable(self):
        with mock.patch.dict("os.environ", {notion.TOKEN_ENV: "ntn_abc"}):
            self.assertEqual(notion.load_token(), "ntn_abc")

    def test_빈_토큰은_설정_방법을_알려주며_거절한다(self):
        with mock.patch.dict("os.environ", {notion.TOKEN_ENV: "   "}):
            with self.assertRaises(notion.NotionError) as ctx:
                notion.load_token()
        self.assertIn("NOTION_TOKEN", str(ctx.exception))
        self.assertIn("zshrc", str(ctx.exception))


class TestRequest(unittest.TestCase):
    def test_sends_version_and_auth_headers(self):
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({"ok": True})
            notion._request("POST", "/pages", "ntn_abc", {"a": 1})
        req = opener.call_args[0][0]
        self.assertEqual(req.get_header("Authorization"), "Bearer ntn_abc")
        self.assertEqual(req.get_header("Notion-version"), notion.VERSION)
        self.assertEqual(json.loads(req.data.decode()), {"a": 1})

    def test_API_가_준_메시지를_그대로_실어_던진다(self):
        """상태 코드만 보고하면 첫 실패에서 아무것도 알 수 없다. 가장 흔한 첫
        실패가 'integration 을 부모 페이지에 연결하지 않음'인데, 그 이유는
        본문 message 에만 적혀 있다."""
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.side_effect = http_error(404, {
                "code": "object_not_found",
                "message": "Could not find page with ID. Make sure the "
                           "relevant pages are shared with your integration.",
            })
            with self.assertRaises(notion.NotionError) as ctx:
                notion._request("POST", "/pages", "ntn_abc", {})
        self.assertIn("shared with your integration", str(ctx.exception))
        self.assertIn("404", str(ctx.exception))

    def test_연결_실패도_NotionError_로_바꾼다(self):
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.side_effect = urllib.error.URLError("네트워크 없음")
            with self.assertRaises(notion.NotionError):
                notion._request("GET", "/pages/x", "ntn_abc")
