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


class _AutoClosingHTTPError(urllib.error.HTTPError):
    """`read()` 뒤에 스스로 닫는다. `HTTPError` 는 `tempfile.
    _TemporaryFileWrapper` 를 상속해서, 닫지 않은 채 버려지면 GC 때마다
    `ResourceWarning` 을 낸다. `notion._request` 는 이 예외를 딱 한 번만
    읽으므로 안전하다."""
    def read(self, *args, **kwargs):
        data = self.file.read(*args, **kwargs)
        self.close()
        return data


def http_error(code, body):
    return _AutoClosingHTTPError(
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
        self.assertIn("zshenv", str(ctx.exception))
        # `zshenv` 는 `zshrc` 를 부분문자열로 담지 않는다 — 옛 안내(대화형
        # 셸 전용 파일)로 되돌아가면 여기서 걸린다.
        self.assertNotIn("zshrc", str(ctx.exception))


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

    def test_title_을_주면_properties_로_함께_보낸다(self):
        """첫 `#` 헤딩의 자동 흡수는 조건이 붙는다 — 제목 헤딩 뒤에 목차 블록을
        두면 깨져서 제목이 빈 페이지가 만들어진다(실제로 v4 에서 났다). 제목은
        명시적으로 넘기는 쪽이 안전하다."""
        created = json.loads((FIXTURES / "notion_create_page.json").read_text("utf-8"))
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response(created)
            notion.push_markdown("# 제목\n\n본문", "PARENT", "ntn_abc",
                                 title="실험1 Basic Gates 예비보고서")
        sent = json.loads(opener.call_args[0][0].data.decode())
        self.assertEqual(
            sent["properties"]["title"][0]["text"]["content"],
            "실험1 Basic Gates 예비보고서")

    def test_title_이_없으면_properties_를_보내지_않는다(self):
        created = json.loads((FIXTURES / "notion_create_page.json").read_text("utf-8"))
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response(created)
            notion.push_markdown("# 제목\n\n본문", "PARENT", "ntn_abc")
        sent = json.loads(opener.call_args[0][0].data.decode())
        self.assertNotIn("properties", sent)

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

    def test_다음_버전은_이력이_없으면_1이다(self):
        self.assertEqual(notion.next_version(self.out, "예비보고서"), 1)

    def test_다음_버전은_같은_kind_만_센다(self):
        notion.append_record(self.out, "예비보고서", "p1", "u1", "s.md", "t")
        notion.append_record(self.out, "결과보고서", "p2", "u2", "s.md", "t")
        notion.append_record(self.out, "예비보고서", "p3", "u3", "s.md", "t")
        self.assertEqual(notion.next_version(self.out, "예비보고서"), 3)
        self.assertEqual(notion.next_version(self.out, "결과보고서"), 2)

    def test_다음_버전은_append_record_가_붙일_번호와_같다(self):
        # 제목은 업로드 전에, 기록은 업로드 후에 만들어진다. 둘이 어긋나면
        # 페이지 제목의 버전과 notion.json 의 버전이 달라진다.
        notion.append_record(self.out, "예비보고서", "p1", "u1", "s.md", "t")
        expected = notion.next_version(self.out, "예비보고서")
        rec = notion.append_record(self.out, "예비보고서", "p2", "u2", "s.md", "t")
        self.assertEqual(rec["version"], expected)

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

    def test_truncated_true_면_예외를_던지고_unknown_block_ids_를_알려준다(self):
        """잘린 채로 baseline 을 저장하면, 이후 진짜 손실이 '원래 baseline 에도
        없었던 것' 으로 흡수되어 손실만 보는 check_notion_roundtrip 에 안 잡힌다.
        markdown 키에 그럴듯한 문자열이 있어도 truncated 가 참이면 그걸 쓰지
        않고 예외부터 던져야 한다."""
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({
                "object": "page_markdown",
                "id": "PAGE",
                "markdown": "일부만 왔다",
                "truncated": True,
                "unknown_block_ids": ["blk_1", "blk_2"],
            })
            with self.assertRaises(notion.NotionError) as ctx:
                notion.pull_markdown("PAGE", "ntn_abc")
        msg = str(ctx.exception)
        self.assertIn("blk_1", msg)
        self.assertIn("blk_2", msg)

    def test_truncated_false_면_정상_반환한다(self):
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({
                "markdown": "본문",
                "truncated": False,
                "unknown_block_ids": [],
            })
            text = notion.pull_markdown("PAGE", "ntn_abc")
        self.assertEqual(text, "본문")

    def test_truncated_키가_아예_없어도_정상_반환한다(self):
        """키 부재를 '참으로 잘렸다' 로 잘못 읽으면 truncated 를 아예 안 실어
        주는 대다수의 정상 응답까지 거절하게 된다."""
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({"markdown": "본문"})
            text = notion.pull_markdown("PAGE", "ntn_abc")
        self.assertEqual(text, "본문")

    def test_빈_마크다운은_잘리지_않았으면_그대로_반환한다(self):
        """빈 문자열이 '존재'하는 것과 필드가 '없는' 것은 다르다 — 빈 노션
        페이지의 정직한 진실은 전자다. isinstance(..., str) 검사를 truthy
        검사로 바꾸면 이 둘을 혼동해, 내용이 진짜로 없을 뿐인 정상적인 빈
        페이지를 '못 찾음' 실패로 잘못 던지게 된다."""
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({
                "markdown": "",
                "truncated": False,
            })
            text = notion.pull_markdown("PAGE", "ntn_abc")
        self.assertEqual(text, "")

    def test_content_키로도_꺼낼_수_있다(self):
        """`markdown` 키가 없을 때의 대비책 — 노션이 이름을 바꿨을 때를 위한
        `_MARKDOWN_KEYS` 의 두 번째 후보 경로가 여태 테스트되지 않았었다."""
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({"content": "대체 키 본문"})
            text = notion.pull_markdown("PAGE", "ntn_abc")
        self.assertEqual(text, "대체 키 본문")


# 노션에 올린 그림은 되읽을 때 1시간짜리 presigned URL 로 돌아온다. 아래는
# 실제 되읽기(v7)에서 나온 모양을 줄여 옮긴 것이다.
SIGNED = (
    "https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9/dee1c66a/"
    "Breadboard.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256"
    "&X-Amz-Credential=ASIAZI2LB466SBQR5Q7N%2F20260830%2Fus-west-2%2Fs3"
    "&X-Amz-Date=20260830T053258Z&X-Amz-Expires=3600"
    "&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEK7"
    "&X-Amz-Signature=35b55f75f5d8c3a643ea24a40fe348697c30401aa3e1256b"
)
BARE = "https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9/dee1c66a/Breadboard.jpg"


class TestStripAssetSignatures(unittest.TestCase):
    def test_서명_쿼리를_떼고_객체_경로만_남긴다(self):
        got = notion.strip_asset_signatures(f"![브레드보드 작도 캔버스]({SIGNED})")
        self.assertEqual(got, f"![브레드보드 작도 캔버스]({BARE})")

    def test_뗀_결과에_자격증명_조각이_남지_않는다(self):
        # 저장소에 들어가면 안 되는 것들이다. 부분 문자열로 확인한다 —
        # 정규식이 한 조각만 놓쳐도 그것이 커밋된다.
        got = notion.strip_asset_signatures(f"![x]({SIGNED})")
        for leak in ("X-Amz-Signature", "X-Amz-Security-Token", "X-Amz-Credential"):
            self.assertNotIn(leak, got)

    def test_서명_없는_링크는_쿼리스트링까지_그대로_둔다(self):
        # 쿼리스트링을 통째로 떼면 사용자가 본문에 넣은 정상 링크가 망가진다.
        text = "[강의](https://youtu.be/abc?t=90) 와 [문서](https://x.io/a?b=1#c)"
        self.assertEqual(notion.strip_asset_signatures(text), text)

    def test_한_줄에_서명_링크와_정상_링크가_같이_있어도_각각_처리한다(self):
        text = f"![그림]({SIGNED}) 그리고 [영상](https://youtu.be/abc?t=90)"
        got = notion.strip_asset_signatures(text)
        self.assertEqual(got, f"![그림]({BARE}) 그리고 [영상](https://youtu.be/abc?t=90)")

    def test_되읽기가_서명을_떼고_돌려준다(self):
        # 이 함수의 반환값이 그대로 baseline 파일이 되어 git 에 들어간다.
        with mock.patch("scripts.lab.notion.urllib.request.urlopen") as opener:
            opener.return_value = fake_response({"markdown": f"![x]({SIGNED})"})
            text = notion.pull_markdown("PAGE", "ntn_abc")
        self.assertNotIn("X-Amz-Signature", text)
        self.assertIn(BARE, text)
