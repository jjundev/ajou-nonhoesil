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


import tempfile


class TestPushMarkdown(unittest.TestCase):
    def test_부모_페이지와_마크다운을_그대로_보낸다(self):
        created = json.loads((FIXTURES / "notion_create_page.json").read_text("utf-8"))
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response(created)
            out = notion.push_markdown("# 제목\n\n본문", "PARENT", "ntn_abc")
        sent = json.loads(opener.call_args[0][0].data.decode())
        self.assertEqual(sent["parent"], {"page_id": "PARENT"})
        self.assertEqual(sent["markdown"], "# 제목\n\n본문")
        self.assertEqual(out["page_id"], created["id"])

    def test_부모_페이지가_비면_Connect_안내와_함께_거절한다(self):
        with self.assertRaises(notion.NotionError) as ctx:
            notion.push_markdown("# 제목", "", "ntn_abc")
        self.assertIn("notion_parent_page_id", str(ctx.exception))
        self.assertIn("Connect", str(ctx.exception))


class TestRecords(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())

    def test_없으면_빈_목록이다(self):
        self.assertEqual(notion.load_records(self.out), [])

    def test_version_은_같은_kind_안에서만_증가한다(self):
        """예보와 결보는 서로 다른 문서다. 한 카운터를 공유하면 '예보 v2' 다음이
        '결보 v3' 이 되어, 몇 번째 예보인지 알 수 없어진다."""
        a = notion.append_record(self.out, "예비보고서", "P1", "u1", "s.md", "2026-08-29 10:00")
        b = notion.append_record(self.out, "결과보고서", "P2", "u2", "s.md", "2026-08-29 11:00")
        c = notion.append_record(self.out, "예비보고서", "P3", "u3", "s.md", "2026-08-29 12:00")
        self.assertEqual((a["version"], b["version"], c["version"]), (1, 1, 2))

    def test_기존_이력을_지우지_않는다(self):
        notion.append_record(self.out, "예비보고서", "P1", "u1", "s.md", "2026-08-29 10:00")
        notion.append_record(self.out, "예비보고서", "P2", "u2", "s.md", "2026-08-29 12:00")
        records = notion.load_records(self.out)
        self.assertEqual([r["page_id"] for r in records], ["P1", "P2"])

    def test_깨진_JSON_은_조용히_덮어쓰지_않는다(self):
        """이력이 사라지면 어느 노션 페이지가 몇 번째 업로드인지 영영 알 수 없다.
        손으로 고칠 수 있게 시끄럽게 실패한다."""
        (self.out / notion.RECORD_NAME).write_text("{깨짐", encoding="utf-8")
        with self.assertRaises(notion.NotionError):
            notion.load_records(self.out)


class TestPullMarkdown(unittest.TestCase):
    def test_실측_응답에서_마크다운_문자열을_꺼낸다(self):
        payload = json.loads((FIXTURES / "notion_pull_markdown.json").read_text("utf-8"))
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response(payload)
            text = notion.pull_markdown("PAGE", "ntn_abc")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        req = opener.call_args[0][0]
        self.assertTrue(req.full_url.endswith("/pages/PAGE/markdown"))
        self.assertEqual(req.get_method(), "GET")

    def test_모르는_응답_형태는_키_목록과_함께_실패한다(self):
        """노션이 응답 형태를 바꾸면 빈 문자열을 돌려주는 대신 시끄럽게 죽어야
        한다. 빈 문자열이 baseline 으로 저장되면 이후 모든 diff 가 거짓말이 된다."""
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({"object": "page", "id": "x"})
            with self.assertRaises(notion.NotionError) as ctx:
                notion.pull_markdown("PAGE", "ntn_abc")
        self.assertIn("id", str(ctx.exception))
