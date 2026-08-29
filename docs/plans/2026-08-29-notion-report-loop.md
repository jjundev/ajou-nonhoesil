# 노션 보고서 검토 루프 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 예비·결과보고서를 md 그대로 노션에 올리고 되읽어, 사용자가 노션에서 고친 내용을 하네스 규칙으로 되먹이는 루프를 만든다.

**Architecture:** 노션 API 는 `POST /v1/pages` 의 `markdown` 파라미터로 마크다운 문자열을 직접 받으므로(`Notion-Version: 2026-03-11`) md→블록 JSON 변환기가 필요 없다. `scripts/lab/notion.py` 가 표준 라이브러리 `urllib` 로 push/pull 만 담당하고, 검증은 기존 관행대로 `scripts/lab/validate.py` 에 `Finding` 을 돌려주는 함수로 붙인다. 절차는 새 스킬 `⑦ sync-report-to-notion` 이 갖고, 기존 보고서 스킬에서는 HTML·PDF 단계를 들어낸다.

**Tech Stack:** Python 3.14 표준 라이브러리(`urllib.request`, `json`, `unittest`), 노션 REST API v2026-03-11.

## Global Constraints

- **표준 라이브러리만 쓴다.** 이 환경에 `requests` 가 없다 — `python3 -c "import requests"` 가 `ModuleNotFoundError` 다. PyYAML 이 없어 `md.py` 가 프론트매터를 직접 파싱하는 것과 같은 제약이다. (`pypdf` 는 있으나 이 계획에서는 쓰지 않는다.)
- **테스트 실행:** `python3 -m unittest discover -s tests -t .` — `pytest` 가 없다. 착수 시점 기준 276개 통과.
- **테스트는 네트워크를 타지 않는다.** `unittest.mock.patch("scripts.lab.notion.urllib.request.urlopen")` 로 대체한다. 유일한 예외는 Task 1(프로브)이며, 그건 테스트가 아니라 실측 작업이다.
- **Notion-Version 헤더는 `2026-03-11` 고정.** `markdown` 파라미터가 이 버전부터 있다.
- **토큰은 환경변수 `NOTION_TOKEN` 에서만 읽는다.** 저장소 안 어떤 파일에도 쓰지 않는다 — `.claude/` 는 git 에 추적된다.
- **페이지를 절대 덮어쓰지 않는다.** 업로드는 항상 새 페이지다.
- **산출물 제목은 `config.document_title()` 이 유일한 형식이다.** 버전 번호를 제목에 넣지 않는다 — 몇 번째 업로드인지는 `notion.json` 이 안다.
- **주차↔실험 매핑은 `config.folder_for_week()` 만 쓴다.** 1:1 이 아니다(실험4 는 7주차).
- **주석·docstring·에러 메시지는 한국어로 쓰고, 기존 스타일을 따른다** — "무엇을 하는가"가 아니라 "왜 이렇게 했는가"와 실제로 있었던 실패를 적는다.
- **커밋 메시지는 한국어 `type: 요약` 형식** (기존 이력: `feat:`, `fix:`, `docs:`, `chore:`).

## 범위 밖 (별도 트랙)

실험02·05·06·10 의 `명세.md`·`netlist.md` 작성은 **이 계획에 포함하지 않는다.** 교안 PDF 를 vision 으로 읽는 콘텐츠 작업이라 TDD 대상이 아니고, 이 계획의 어떤 태스크도 그것에 의존하지 않는다(파일럿은 이미 완성된 실험01 을 쓴다). 두 트랙은 병렬로 진행한다.

## File Structure

**신규**

| 파일 | 책임 |
|---|---|
| `scripts/lab/notion.py` | 노션 API push/pull, 토큰 로딩, `notion.json` 이력. **HTTP 와 이력만** — 무엇을 올릴지 고르는 판단은 하지 않는다. |
| `tests/test_lab_notion.py` | 위 모듈 테스트. `urlopen` 을 mock 한다. |
| `tests/fixtures/notion_create_page.json` | Task 1 프로브가 실측한 `POST /v1/pages` 응답. |
| `tests/fixtures/notion_pull_markdown.json` | Task 1 프로브가 실측한 `GET /v1/pages/{id}/markdown` 응답. |
| `.claude/skills/sync-report-to-notion/SKILL.md` | ⑦ 스킬 절차 — push·pull·분류. |
| `docs/notion-feedback/README.md` | 분류 로그 규약. |

**수정**

| 파일 | 무엇을 |
|---|---|
| `scripts/lab/validate.py` | `Finding` 에 `info` 레벨 추가, `check_notion_markdown()`, `markdown_shape()`, `check_notion_roundtrip()` 신설. |
| `tests/test_lab_validate.py` | 위 세 함수 테스트. |
| `scripts/lab/config.py` | `load_course_info` 에 `notion_parent_page_id` 기본값. |
| `tests/test_lab_config.py` | 위 기본값 테스트. |
| `.claude/과목정보.md` | `notion_parent_page_id` 필드 + 노션 연동 설명 절. |
| `.claude/skills/write-pre-report/SKILL.md` | 8·8b·9·10단계 삭제, 표지 분리, 조 편성 안내문 제거, ⑦ 안내 추가. |
| `.claude/skills/write-result-report/SKILL.md` | 동일 수술. |

---

### Task 1: 노션 연결 준비와 API 실측 프로브

**Files:**
- Create: `tests/fixtures/notion_create_page.json`
- Create: `tests/fixtures/notion_pull_markdown.json`
- Create: `docs/plans/2026-08-29-notion-probe-결과.md`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 두 fixture 파일. Task 3·4·5 의 테스트가 이 JSON 의 **실제 키 이름**을 쓴다. 특히 `GET /v1/pages/{id}/markdown` 의 응답 최상위 키가 무엇인지(`markdown` 인지 다른 이름인지), 그리고 internal integration 으로 그 엔드포인트가 열리는지를 여기서 확정한다.

**왜 이 태스크가 먼저인가:** `GET /v1/pages/:page_id/markdown` 이 public integration 전용일 가능성이 있다. 막히면 되읽기(Task 4)와 왕복 검증(Task 7)의 전제가 무너지고, 스킬이 pull 대신 "사용자가 노션에서 Export → Markdown 해서 전달" 로 바뀐다. **코드를 쓰기 전에 알아야 한다.**

- [ ] **Step 1: 노션 integration 을 만들고 토큰을 환경변수에 넣는다 (사용자 수동 작업)**

사용자에게 아래를 그대로 안내하고, 끝났다는 확인을 받은 뒤 다음 스텝으로 간다.

1. https://www.notion.so/my-integrations 에서 **New integration**
   - Type: **Internal**
   - Name: `논회실 하네스`
   - 워크스페이스: 본인 것
2. **Internal Integration Secret** 복사 (`ntn_` 로 시작)
3. `~/.zshrc` 맨 아래에 추가하고 새 터미널을 연다:

```bash
echo "export NOTION_TOKEN='여기에_붙여넣기'" >> ~/.zshrc
```

4. 노션에서 페이지를 하나 만든다: 제목 `논리회로실험 2026-2`
5. 그 페이지 우상단 `⋯` → **Connections**(연결) → `논회실 하네스` 추가
   - **이 단계를 빠뜨리면 API 가 404 `object_not_found` 를 돌려준다.** 노션 integration 은 명시적으로 연결된 페이지에만 접근한다.
6. 페이지 URL 끝의 32자리 hex 를 확인한다. 예: `https://www.notion.so/논리회로실험-2026-2-1a2b3c4d5e6f7890abcdef1234567890` → id 는 `1a2b3c4d5e6f7890abcdef1234567890`

- [ ] **Step 2: 토큰이 셸에 보이는지 확인한다**

```bash
python3 -c "import os; t=os.environ.get('NOTION_TOKEN',''); print('길이', len(t), '접두', t[:4])"
```

기대: `길이 50` 내외, `접두 ntn_`. `길이 0` 이면 새 터미널을 열지 않은 것이다.

- [ ] **Step 3: 페이지 생성을 실측하고 응답을 fixture 로 저장한다**

`<PARENT_ID>` 를 Step 1-6 의 값으로 바꿔 실행한다.

```bash
mkdir -p tests/fixtures && python3 - <<'PY'
import json, os, urllib.request
PARENT = "<PARENT_ID>"
body = json.dumps({
    "parent": {"page_id": PARENT},
    "markdown": "# 프로브 테스트 페이지\n\n첫 문단이다.\n\n"
                "## 표 검사\n\n| A | B | C |\n|---|---|---|\n| 0 | 0 | 0 |\n| 1 | 1 | 1 |\n\n"
                "> 출처: 프로브\n\n"
                "수식 검사: $\\overline{A \\cdot B}$ 가 오버바로 보이는가?\n",
}).encode()
req = urllib.request.Request(
    "https://api.notion.com/v1/pages", data=body, method="POST",
    headers={"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
             "Notion-Version": "2026-03-11", "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    open("tests/fixtures/notion_create_page.json", "w", encoding="utf-8").write(
        json.dumps(data, ensure_ascii=False, indent=2))
    print("OK page_id =", data["id"])
    print("url =", data.get("url"))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode("utf-8", "replace"))
PY
```

기대: `OK page_id = ...` 와 노션 URL. `HTTP 404` 에 `object_not_found` 가 나오면 Step 1-5(Connections)를 안 한 것이다.

- [ ] **Step 4: 만들어진 페이지를 노션에서 눈으로 확인한다**

출력된 URL 을 열어 **세 가지**를 확인하고 결과를 적어 둔다:
1. 페이지 **제목**이 `프로브 테스트 페이지` 인가 (= 첫 `#` 헤딩이 제목으로 흡수되는가)
2. 표가 노션 **표 블록**으로 들어갔는가, 아니면 텍스트로 뭉갰는가
3. `$\overline{A \cdot B}$` 가 **오버바로 렌더되는가** — 이게 확인되면 질문 8의 (B)→(A) 전환(보수 `'` → LaTeX 승격)을 열 수 있다

- [ ] **Step 5: 되읽기를 실측하고 응답을 fixture 로 저장한다**

`<PAGE_ID>` 는 Step 3 이 출력한 값이다.

```bash
python3 - <<'PY'
import json, os, urllib.request, urllib.error
PAGE = "<PAGE_ID>"
req = urllib.request.Request(
    f"https://api.notion.com/v1/pages/{PAGE}/markdown", method="GET",
    headers={"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
             "Notion-Version": "2026-03-11"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    open("tests/fixtures/notion_pull_markdown.json", "w", encoding="utf-8").write(
        json.dumps(data, ensure_ascii=False, indent=2))
    print("최상위 키:", sorted(data))
    for k, v in data.items():
        if isinstance(v, str) and len(v) > 40:
            print(f"--- {k} ---"); print(v)
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode("utf-8", "replace"))
PY
```

**분기:**
- **성공하면** — 출력된 "최상위 키" 중 마크다운 문자열이 담긴 키 이름을 기록한다. Task 4 가 이 이름을 쓴다.
- **`HTTP 403` 또는 `restricted_resource` 가 나오면** — internal integration 에 막힌 것이다. **Task 4·7 을 건너뛰고**, Task 8 의 스킬을 "pull 은 사용자가 노션에서 `⋯ → Export → Markdown & CSV` 로 내보내 `<실험NN>/output/` 에 넣어 주면 그 파일을 읽는다" 로 쓴다. 이 경우 baseline 도 사용자가 업로드 직후 한 번 Export 해야 한다.

- [ ] **Step 6: 프로브 결과를 문서로 남긴다**

`docs/plans/2026-08-29-notion-probe-결과.md` 에 아래 항목을 채워 쓴다. 이후 태스크가 이 문서를 근거로 삼는다.

```markdown
# 노션 API 프로브 결과 (2026-08-29)

- `POST /v1/pages` + `markdown`: 성공/실패
- 응답의 page id 키: `id`
- 응답의 URL 키: `url`
- 첫 `#` 헤딩이 페이지 제목이 되는가: 예/아니오
- 표가 노션 표 블록이 되는가: 예/아니오
- `$\overline{A \cdot B}$` 가 오버바로 렌더되는가: 예/아니오
- `GET /v1/pages/{id}/markdown` (internal integration): 성공/403
- 되읽기 응답에서 마크다운이 담긴 키: `____`
- 되읽기에 첫 `#` 헤딩이 포함되는가: 예/아니오
```

- [ ] **Step 7: 프로브 페이지를 노션에서 지우고 커밋**

노션에서 `프로브 테스트 페이지` 를 삭제한다(휴지통으로 보내는 것으로 충분하다).

```bash
git add tests/fixtures docs/plans/2026-08-29-notion-probe-결과.md
git commit -m "chore: 노션 API 응답 형태 실측 및 fixture 고정"
```

---

### Task 2: `과목정보.md` 에 부모 페이지 id 를 둔다

**Files:**
- Modify: `.claude/과목정보.md`
- Modify: `scripts/lab/config.py:load_course_info`
- Test: `tests/test_lab_config.py`

**Interfaces:**
- Consumes: 없음
- Produces: `config.load_course_info(root)["notion_parent_page_id"]` — 값이 없으면 `None`. Task 8 의 스킬이 이걸 읽는다.

**왜 여기인가:** `과목정보.md` 는 스스로 "하네스 전체의 단일 메타데이터 소스"라고 선언한 파일이고, `chrome` 경로·`ai_usage_log` 가 이미 같은 방식(`~` = 미확정, 코드에서 `None`)으로 들어 있다. 토큰은 여기 두지 않는다 — 이 파일은 git 에 추적된다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_config.py` 의 `TestCourseInfo` 클래스 안에 추가한다.

```python
    def test_notion_parent_page_id_is_read(self):
        info = config.load_course_info(ROOT)
        self.assertIn("notion_parent_page_id", info)

    def test_notion_parent_page_id_defaults_when_the_key_is_absent(self):
        """미확정이면 지어내지 않는다. `ai_usage_log` 와 같은 규칙이다."""
        missing = Path(tempfile.mkdtemp())
        (missing / ".claude").mkdir()
        (missing / ".claude" / "과목정보.md").write_text(
            "---\ndepartment: 전자공학과\ncourse: 논리회로실험\n"
            "professor: 허용석 교수님\nclass_section: C082\n---\n",
            encoding="utf-8",
        )
        self.assertIsNone(config.load_course_info(missing)["notion_parent_page_id"])
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_config.TestCourseInfo -v 2>&1 | tail -12
```

기대: `test_notion_parent_page_id_is_read` 가 `KeyError`/`AssertionError` 로 FAIL.

- [ ] **Step 3: `config.load_course_info` 에 기본값을 넣는다**

`scripts/lab/config.py` 의 `load_course_info` 안, `info.setdefault("ai_usage_log", None)` 바로 아래에 한 줄 추가한다.

```python
    info.setdefault("ai_usage_log", None)
    # 노션 업로드 대상 부모 페이지. 토큰은 여기 두지 않는다 — 이 파일은 git 에
    # 추적된다. 토큰은 환경변수 NOTION_TOKEN 에서만 읽는다 (scripts/lab/notion.py).
    info.setdefault("notion_parent_page_id", None)
```

- [ ] **Step 4: `과목정보.md` 에 필드와 설명을 넣는다**

프론트매터의 `ai_usage_log: ~` 아래에 추가한다(`<PARENT_ID>` 는 Task 1 에서 확인한 값):

```yaml
# 노션 업로드 대상 부모 페이지. 여기에 integration 을 Connect 해 두어야 한다.
notion_parent_page_id: <PARENT_ID>
```

그리고 본문 `## PDF 변환` 절 **아래**에 절을 하나 더 붙인다:

```markdown
## 노션 업로드

예비·결과보고서는 md 를 그대로 노션에 올리고(⑦ `sync-report-to-notion`), 사용자가
노션에서 PDF 로 내보낸 뒤 ⑥ 이 만든 표지 PDF 를 앞에 손으로 붙여 제출한다.

**토큰은 이 파일에 두지 않는다.** 환경변수 `NOTION_TOKEN` 에서만 읽는다 —
`.claude/` 는 git 에 추적되므로 여기 두면 저장소에 비밀이 들어간다.

위 `notion_parent_page_id` 페이지에 노션에서 integration 을 **Connect** 해 두어야
한다. 안 하면 API 가 404 `object_not_found` 를 돌려준다.
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_config -v 2>&1 | grep -E "^(OK|FAILED|Ran )"
```

기대: `OK`

- [ ] **Step 6: 커밋**

```bash
git add .claude/과목정보.md scripts/lab/config.py tests/test_lab_config.py
git commit -m "feat: 과목정보에 노션 부모 페이지 id 추가"
```

---

### Task 3: `notion.py` — 토큰 로딩과 HTTP 래퍼

**Files:**
- Create: `scripts/lab/notion.py`
- Test: `tests/test_lab_notion.py`

**Interfaces:**
- Consumes: Task 1 의 `tests/fixtures/notion_create_page.json`
- Produces:
  - `notion.NotionError` — 이 모듈의 유일한 예외 타입
  - `notion.API = "https://api.notion.com/v1"`, `notion.VERSION = "2026-03-11"`, `notion.TOKEN_ENV = "NOTION_TOKEN"`
  - `notion.load_token() -> str`
  - `notion._request(method: str, path: str, token: str, payload: dict | None = None, timeout: int = 120) -> dict`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_notion.py` 를 새로 만든다.

```python
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
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_notion -v 2>&1 | tail -6
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.notion'`

- [ ] **Step 3: `scripts/lab/notion.py` 를 만든다**

```python
"""노션 API 클라이언트. **표준 라이브러리만 쓴다** — 이 환경에 `requests` 가 없다
(PyYAML 이 없어 `md.py` 가 프론트매터를 직접 파싱하는 것과 같은 제약이다).

**이 모듈은 md→블록 JSON 변환기를 갖지 않는다.** 노션 API 가 `POST /v1/pages` 의
`markdown` 파라미터로 마크다운 문자열을 그대로 받기 때문이다
(`Notion-Version: 2026-03-11`). 구식 경로인 `PATCH /v1/blocks/{id}/children` 은
블록 JSON 전용이고 100블록/요청·중첩 2단 제한이 있는데, 우리는 그 경로를 쓰지 않는다.

이 모듈은 **HTTP 와 업로드 이력만** 다룬다. 무엇을 올릴지 고르는 판단과 되읽은
diff 를 해석하는 판단은 ⑦ `sync-report-to-notion` 스킬의 몫이다.
"""

import json
import os
import urllib.error
import urllib.request

API = "https://api.notion.com/v1"
VERSION = "2026-03-11"          # `markdown` 파라미터가 이 버전부터 있다
TOKEN_ENV = "NOTION_TOKEN"


class NotionError(RuntimeError):
    pass


def load_token() -> str:
    """토큰은 환경변수에서만 읽는다.

    저장소 안 어디에도 두지 않는 이유는, `.claude/` 가 git 에 추적되기 때문이다.
    `.gitignore` 에 의존하는 방식(`.env` 등)은 한 줄만 어긋나도 비밀이 GitHub 에
    올라가는데, **비밀이 존재할 경로 자체를 안 만드는 편**이 안전하다.
    """
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise NotionError(
            f"환경변수 {TOKEN_ENV} 가 비어 있습니다.\n"
            f"  echo \"export {TOKEN_ENV}='ntn_...'\" >> ~/.zshrc\n"
            "를 실행하고 **새 터미널**을 여세요. 토큰은 저장소에 두지 않습니다."
        )
    return token


def _request(method, path, token, payload=None, timeout=120) -> dict:
    """노션 API 호출. 실패하면 API 가 준 `message` 를 그대로 실어 던진다.

    상태 코드만 보고하면 첫 실패에서 아무것도 알 수 없다. 이 하네스에서 가장
    흔한 첫 실패는 **integration 을 부모 페이지에 Connect 하지 않은 것**인데,
    그건 404 로 오고 이유는 본문 `message` 에만 적혀 있다.
    """
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(raw).get("message", raw)
        except json.JSONDecodeError:
            detail = raw
        raise NotionError(f"{method} {path} 실패 (HTTP {e.code}): {detail}") from None
    except urllib.error.URLError as e:
        raise NotionError(f"{method} {path} 연결 실패: {e.reason}") from None
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_notion -v 2>&1 | grep -E "^(OK|FAILED|Ran )"
```

기대: `OK`

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/notion.py tests/test_lab_notion.py
git commit -m "feat: 노션 API HTTP 래퍼와 토큰 로딩"
```

---

### Task 4: `push_markdown` 과 `notion.json` 업로드 이력

**Files:**
- Modify: `scripts/lab/notion.py`
- Test: `tests/test_lab_notion.py`

**Interfaces:**
- Consumes: Task 3 의 `_request`, `NotionError`
- Produces:
  - `notion.RECORD_NAME = "notion.json"`
  - `notion.push_markdown(md_text: str, parent_page_id: str, token: str, timeout: int = 120) -> dict` — `{"page_id": str, "url": str}`
  - `notion.load_records(output_dir) -> list[dict]`
  - `notion.append_record(output_dir, kind: str, page_id: str, url: str, source: str, when: str) -> dict` — 저장된 레코드를 돌려준다. `version` 은 같은 `kind` 의 기존 레코드 수 + 1.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_notion.py` 아래에 붙인다.

```python
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
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_notion -v 2>&1 | tail -8
```

기대: `AttributeError: module 'scripts.lab.notion' has no attribute 'push_markdown'`

- [ ] **Step 3: 구현한다**

`scripts/lab/notion.py` 아래에 붙인다. `from pathlib import Path` 를 import 절에 추가한다.

```python
RECORD_NAME = "notion.json"
RECORD_SCHEMA = "notion-uploads/v1"


def push_markdown(md_text, parent_page_id, token, timeout=120) -> dict:
    """마크다운으로 노션 페이지를 **새로** 만든다. 덮어쓰기는 제공하지 않는다.

    이 루프는 구조적으로 "사용자가 노션에서 고쳤지만 아직 되읽히지 않은 구간"을
    갖는다. 그 구간에 재업로드가 덮어쓰면 수정이 **경고 없이** 사라지고, 노션
    페이지 덮어쓰기는 되돌리기 어렵다. 그래서 이 모듈에는 갈아엎는 함수가 없다.

    페이지 제목은 마크다운의 첫 `#` 헤딩에서 온다 — 즉 **제목에 버전이 없다.**
    몇 번째 업로드인지는 `notion.json` 이 안다.
    """
    if not (parent_page_id or "").strip():
        raise NotionError(
            "부모 페이지 id 가 비어 있습니다. `.claude/과목정보.md` 의 "
            "notion_parent_page_id 를 채우고, 노션에서 그 페이지에 integration 을 "
            "Connect 했는지 확인하세요 (안 하면 404 object_not_found 가 납니다)."
        )
    data = _request("POST", "/pages", token, {
        "parent": {"page_id": parent_page_id},
        "markdown": md_text,
    }, timeout)
    return {"page_id": data["id"], "url": data.get("url", "")}


def _record_file(output_dir) -> Path:
    return Path(output_dir) / RECORD_NAME


def load_records(output_dir) -> list:
    """업로드 이력을 읽는다. 없으면 빈 목록, 깨졌으면 시끄럽게 실패한다.

    조용히 빈 목록으로 되돌리면 이후 업로드가 version 1 부터 다시 세면서 기존
    이력을 통째로 덮어쓴다 — 어느 노션 페이지가 몇 번째였는지 영영 알 수 없어진다.
    """
    path = _record_file(output_dir)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("uploads", [])
    except json.JSONDecodeError as e:
        raise NotionError(
            f"{path} 를 읽을 수 없습니다 ({e}). 손으로 고치거나 지우세요 — "
            "조용히 덮어쓰면 업로드 이력이 사라집니다."
        ) from None


def append_record(output_dir, kind, page_id, url, source, when) -> dict:
    """업로드 한 건을 `<실험NN>/output/notion.json` 에 덧붙인다.

    `when` 을 인자로 받는다. 이 값은 파일에 굳으므로 테스트가 고정값을 넣을 수
    있어야 한다.

    `version` 은 **같은 kind 안에서만** 센다 — 예비보고서와 결과보고서는 서로
    다른 문서라 카운터를 공유하면 "몇 번째 예보인지"를 알 수 없다.
    """
    records = load_records(output_dir)
    record = {
        "kind": kind,
        "version": sum(1 for r in records if r.get("kind") == kind) + 1,
        "page_id": page_id,
        "url": url,
        "source": source,
        "uploaded_at": when,
    }
    records.append(record)
    path = _record_file(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema": RECORD_SCHEMA, "uploads": records},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return record
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_notion -v 2>&1 | grep -E "^(OK|FAILED|Ran )"
```

기대: `OK`

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/notion.py tests/test_lab_notion.py
git commit -m "feat: 노션 페이지 업로드와 notion.json 이력"
```

---

### Task 5: `pull_markdown` — 되읽기

> **Task 1 Step 5 가 `403`/`restricted_resource` 였으면 이 태스크를 건너뛴다.** 그 경우 Task 7 도 건너뛰고, Task 8 의 스킬에서 pull 을 "사용자가 노션에서 Export → Markdown 한 파일을 읽는다" 로 쓴다.

**Files:**
- Modify: `scripts/lab/notion.py`
- Test: `tests/test_lab_notion.py`

**Interfaces:**
- Consumes: Task 3 의 `_request`, Task 1 의 `tests/fixtures/notion_pull_markdown.json`
- Produces: `notion.pull_markdown(page_id: str, token: str, timeout: int = 120) -> str`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_notion.py` 아래에 붙인다.

```python
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
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_notion.TestPullMarkdown -v 2>&1 | tail -6
```

기대: `AttributeError: ... has no attribute 'pull_markdown'`

- [ ] **Step 3: 구현한다**

`scripts/lab/notion.py` 아래에 붙인다. `_MARKDOWN_KEYS` 의 첫 항목을 **Task 1 Step 5 가 출력한 실제 키 이름**으로 맞춘다(실측값이 `markdown` 이면 그대로 둔다).

```python
# 되읽기 응답에서 마크다운이 담긴 키. 첫 항목이 Task 1 프로브의 실측값이고,
# 나머지는 노션이 이름을 바꿨을 때를 위한 여유다.
_MARKDOWN_KEYS = ("markdown", "content")


def pull_markdown(page_id, token, timeout=120) -> str:
    """페이지 내용을 Notion-flavored Markdown 문자열로 되읽는다.

    **문자열을 못 찾으면 빈 문자열 대신 예외를 던진다.** 빈 문자열이 baseline
    으로 저장되면 이후 모든 diff 가 "전부 삭제됨" 으로 보여 거짓말이 된다.
    """
    data = _request("GET", f"/pages/{page_id}/markdown", token, timeout=timeout)
    for key in _MARKDOWN_KEYS:
        if isinstance(data.get(key), str):
            return data[key]
    raise NotionError(
        f"되읽기 응답에서 마크다운 문자열을 찾지 못했습니다. "
        f"응답의 키: {sorted(data)} — `_MARKDOWN_KEYS` 를 실측값에 맞추세요."
    )
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_notion -v 2>&1 | grep -E "^(OK|FAILED|Ran )"
```

기대: `OK`

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/notion.py tests/test_lab_notion.py
git commit -m "feat: 노션 페이지 마크다운 되읽기"
```

---

### Task 6: `check_notion_markdown` — 업로드 전 검사

**Files:**
- Modify: `scripts/lab/validate.py`
- Test: `tests/test_lab_validate.py`

**Interfaces:**
- Consumes: `md.split_frontmatter`, `md.parse_tables`, `validate.Finding`
- Produces: `validate.check_notion_markdown(md_path) -> list[Finding]` — 레벨 `error` / `info`

**무엇을 대신하는가:** 보고서에서 HTML 을 안 만들게 되면서 `check_rendered_html`·`check_embedded_images` 는 보고서 경로에서 호출되지 않는다(체크리스트 경로에서는 계속 쓰이므로 **지우지 않는다**). 이 함수가 그 자리를 대신한다 — 대상이 렌더된 HTML 에서 md 자체로 바뀌었을 뿐, "조용히 망가지고 눈으로는 안 보이는 결함"을 잡는다는 목적은 같다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_validate.py` 아래에 붙인다. 파일 상단에 `from scripts.lab import validate` 가 이미 있다.

```python
def md_file(text):
    tmp = Path(tempfile.mkdtemp()) / "보고서.md"
    tmp.write_text(text, encoding="utf-8")
    return tmp


class TestCheckNotionMarkdown(unittest.TestCase):
    def test_실제_실험1_예비보고서는_깨끗하다(self):
        path = ROOT / "실험01/output/실험01_예비보고서.md"
        errors = [f for f in validate.check_notion_markdown(path)
                  if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_h5_이상은_error_다(self):
        """NFM 은 h5·h6 를 h4 로 강등한다. 절 깊이가 무너지면 ⑤ 의 섹션 검증이
        보는 헤딩 구조도 같이 무너진다."""
        findings = validate.check_notion_markdown(
            md_file("# 제목\n\n##### 다섯째 단계\n"))
        self.assertTrue(any(f.level == "error" and "h5" in f.message
                            for f in findings), findings)

    def test_각주는_error_다(self):
        findings = validate.check_notion_markdown(
            md_file("# 제목\n\n본문[^1]\n\n[^1]: 각주\n"))
        self.assertTrue(any(f.level == "error" and "각주" in f.message
                            for f in findings), findings)

    def test_열_수가_어긋난_표는_error_다(self):
        """깨진 표는 노션에서 통째로 뭉개진다."""
        findings = validate.check_notion_markdown(md_file(
            "# 제목\n\n| A | B |\n|---|---|\n| 0 | 0 |\n| 1 |\n"))
        self.assertTrue(any(f.level == "error" and "헤더는 2개" in f.message
                            for f in findings), findings)

    def test_상대경로_이미지는_error_가_아니라_info_다(self):
        """상대경로 이미지가 노션에서 깨지는 것은 결함이 아니라 설계다 — 사진은
        사용자가 노션에서 직접 끼워 넣는다. 그래서 '고쳐라'가 아니라 '무엇을 몇 장
        넣어야 하는지'를 알린다."""
        findings = validate.check_notion_markdown(md_file(
            "# 제목\n\n![브레드보드](../../.claude/assets/Breadboard.jpg)\n"))
        self.assertEqual([f.level for f in findings], ["info"])
        self.assertIn("Breadboard.jpg", findings[0].message)
        self.assertIn("1장", findings[0].message)

    def test_원격_이미지는_알리지_않는다(self):
        findings = validate.check_notion_markdown(md_file(
            "# 제목\n\n![x](https://example.com/a.png)\n"))
        self.assertEqual(findings, [])

    def test_파일이_없으면_error_한_건이다(self):
        findings = validate.check_notion_markdown(Path("/없는/경로.md"))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].level, "error")
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_validate.TestCheckNotionMarkdown -v 2>&1 | tail -6
```

기대: `AttributeError: ... has no attribute 'check_notion_markdown'`

- [ ] **Step 3: `Finding` 에 `info` 레벨을 더한다**

`scripts/lab/validate.py` 의 `Finding` 을 아래로 바꾼다. 기존 `error`/`warn` 동작은 그대로다 — 이미 있는 호출부는 전부 `f.level == "error"` 로 거르므로 영향이 없다.

```python
_MARKS = {"error": "✗", "warn": "!", "info": "ℹ"}


@dataclass
class Finding:
    level: str   # "error" | "warn" | "info"
    where: str
    message: str

    def __str__(self):
        return f"{_MARKS.get(self.level, '!')} {self.where} — {self.message}"
```

- [ ] **Step 4: `check_notion_markdown` 을 구현한다**

`scripts/lab/validate.py` 의 `check_embedded_images` 아래에 붙인다.

```python
# NFM(Notion-flavored Markdown) 이 손실시키는 문법들. 실측 근거는
# docs/plans/2026-08-29-notion-probe-결과.md 에 있다.
_NFM_LOSSY = (
    (re.compile(r"^#{5,}\s", re.M), "h5·h6 헤딩", "노션이 h4 로 강등한다"),
    (re.compile(r"^\[\^[^\]]+\]:", re.M), "각주 정의", "NFM 이 지원하지 않는다"),
    # 각주 정의 줄 안의 `[^n]` 을 참조로 이중 계수하지 않기 위해 `:` 로 끝나는
    # 형태(정의)는 제외한다 — 정의는 위 패턴이 이미 센다.
    (re.compile(r"(?<!\!)\[\^[^\]]+\](?!:)"), "각주 참조", "NFM 이 지원하지 않는다"),
    (re.compile(r"^<[a-zA-Z][^>]*>", re.M), "열 0 의 원시 HTML 블록",
     "NFM 은 일부 태그만 받는다"),
)
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def check_notion_markdown(md_path) -> list:
    """노션에 올리기 전에 md 자체를 본다.

    보고서에서 HTML 을 안 만들게 되면서 `check_rendered_html` 이 보고서 경로에서
    호출되지 않는다. 이 함수가 그 자리를 대신한다 — 대상이 렌더된 HTML 에서 md 로
    바뀌었을 뿐, "조용히 망가지고 눈으로는 안 보이는 결함"을 잡는 목적은 같다.

    **상대경로 이미지는 error 가 아니라 info 다.** 노션 API 의 마크다운은 URL 만
    받으므로 상대경로는 반드시 깨지는데, 그건 결함이 아니라 설계다 — 사진은
    사용자가 노션에서 직접 끼워 넣기로 했다(자동 첨부는 파일 업로드 후 1시간 내
    블록 삽입 + 위치 수술이 필요해 v1 의 복잡도가 아니다). 그래서 "고쳐라"가 아니라
    "무엇을 몇 장 넣어야 하는지"를 알린다.
    """
    path = Path(md_path)
    if not path.exists():
        return [Finding("error", str(md_path), "보고서 md 파일이 없다")]
    _, body = md.split_frontmatter(path.read_text(encoding="utf-8"))
    out = []
    for pattern, label, why in _NFM_LOSSY:
        hits = pattern.findall(body)
        if hits:
            out.append(Finding("error", path.name,
                f"{label} 이 {len(hits)}개 있다 — {why}"))
    for t in md.parse_tables(body):
        width = len(t.header)
        for i, row in enumerate(t.rows, start=1):
            if len(row) != width:
                out.append(Finding("error", f"{path.name}:{t.line}",
                    f"표 {i}행의 셀이 {len(row)}개인데 헤더는 {width}개다 — "
                    "노션에서 표가 통째로 뭉개진다"))
    local = [s for s in _IMAGE.findall(body)
             if not s.startswith(("http://", "https://", "data:"))]
    if local:
        out.append(Finding("info", path.name,
            f"노션에서 직접 넣어야 할 그림 {len(local)}장: " + ", ".join(local)))
    return out
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"
```

기대: `Ran 29x tests` / `OK` — 기존 276개도 함께 통과해야 한다. `Finding` 을 고쳤으니 전체를 돌린다.

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/validate.py tests/test_lab_validate.py
git commit -m "feat: 업로드 전 노션 마크다운 검사"
```

---

### Task 7: `check_notion_roundtrip` — 업로드 후 구조 불변량

> **Task 5 를 건너뛰었으면 이 태스크도 건너뛴다.**

**Files:**
- Modify: `scripts/lab/validate.py`
- Test: `tests/test_lab_validate.py`

**Interfaces:**
- Consumes: `md.split_frontmatter`, `md.parse_tables`, `validate.Finding`
- Produces:
  - `validate.MarkdownShape` — 필드 `headings: list[str]`, `table_count: int`, `table_rows: int`, `quote_blocks: int`
  - `validate.markdown_shape(text: str) -> MarkdownShape`
  - `validate.check_notion_roundtrip(source_text: str, pulled_text: str) -> list[Finding]`

**왜 텍스트 동일성을 안 보는가:** 노션 왕복은 문단 병합·표 정렬 마커 소실 같은 노이즈를 **반드시** 만든다. 그걸 결함으로 세면 진짜 손실(표가 통째로 사라짐, 절이 안 올라감)이 그 안에 파묻힌다. 구조 불변량만 본다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
SRC = """# 실험1 Basic Gates 예비보고서

## 1. 실험 목적

목적 문장.

> 출처: 교안 p.2

## 2. 실험 이론

| A | B | C |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 1 | 1 |

> 출처: 교안 p.4
"""


class TestMarkdownShape(unittest.TestCase):
    def test_구조만_센다(self):
        shape = validate.markdown_shape(SRC)
        self.assertEqual(shape.headings,
                         ["실험1 Basic Gates 예비보고서", "1. 실험 목적", "2. 실험 이론"])
        self.assertEqual(shape.table_count, 1)
        self.assertEqual(shape.table_rows, 2)
        self.assertEqual(shape.quote_blocks, 2)

    def test_이어진_인용_줄은_한_블록이다(self):
        """여러 줄 인용이 한 줄로 합쳐지는 것은 노이즈지 손실이 아니다. 줄로 세면
        그 노이즈가 매번 error 로 올라온다."""
        self.assertEqual(validate.markdown_shape("> 가\n> 나\n").quote_blocks, 1)
        self.assertEqual(validate.markdown_shape("> 가\n\n> 나\n").quote_blocks, 2)


class TestCheckNotionRoundtrip(unittest.TestCase):
    def test_노이즈만_있으면_아무것도_보고하지_않는다(self):
        noisy = SRC.replace("|---|---|---|", "| --- | --- | --- |")
        self.assertEqual(validate.check_notion_roundtrip(SRC, noisy), [])

    def test_첫_헤딩이_없어도_보고하지_않는다(self):
        """노션이 첫 `#` 헤딩을 페이지 제목으로 흡수하므로 되읽기에 없을 수 있다."""
        without_h1 = SRC.split("\n", 1)[1]
        self.assertEqual(validate.check_notion_roundtrip(SRC, without_h1), [])

    def test_사라진_절을_error_로_보고한다(self):
        pulled = SRC.replace("## 2. 실험 이론", "")
        findings = validate.check_notion_roundtrip(SRC, pulled)
        self.assertTrue(any(f.level == "error" and "2. 실험 이론" in f.message
                            for f in findings), findings)

    def test_사라진_표를_error_로_보고한다(self):
        pulled = "\n".join(ln for ln in SRC.split("\n") if not ln.startswith("|"))
        findings = validate.check_notion_roundtrip(SRC, pulled)
        self.assertTrue(any(f.level == "error" and "표" in f.message
                            for f in findings), findings)

    def test_사라진_출처_인용을_error_로_보고한다(self):
        pulled = SRC.replace("> 출처: 교안 p.4", "")
        findings = validate.check_notion_roundtrip(SRC, pulled)
        self.assertTrue(any(f.level == "error" and "인용" in f.message
                            for f in findings), findings)

    def test_늘어난_것은_error_가_아니다(self):
        """사용자가 노션에서 절이나 표를 더한 것은 손실이 아니다."""
        pulled = SRC + "\n## 3. 추가한 절\n\n내용\n"
        self.assertEqual(validate.check_notion_roundtrip(SRC, pulled), [])
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_validate.TestMarkdownShape -v 2>&1 | tail -6
```

기대: `AttributeError: ... has no attribute 'markdown_shape'`

- [ ] **Step 3: 구현한다**

`scripts/lab/validate.py` 의 `check_notion_markdown` 아래에 붙인다.

```python
@dataclass
class MarkdownShape:
    headings: list
    table_count: int
    table_rows: int
    quote_blocks: int


def markdown_shape(text) -> MarkdownShape:
    """구조 불변량만 뽑는다. **텍스트 동일성은 보지 않는다.**

    노션 왕복은 문단 병합·표 정렬 마커 소실 같은 노이즈를 반드시 만든다. 그걸
    결함으로 세면 진짜 손실(표가 통째로 사라짐, 절이 안 올라감)이 파묻힌다.

    인용은 **줄이 아니라 블록**으로 센다 — 여러 줄 인용이 한 줄로 합쳐지는 것은
    노이즈지 손실이 아닌데, 줄로 세면 매번 error 로 올라온다.
    """
    _, body = md.split_frontmatter(text)
    lines = body.split("\n")
    tables = md.parse_tables(body)
    quote_blocks, in_quote = 0, False
    for line in lines:
        if line.startswith(">"):
            if not in_quote:
                quote_blocks += 1
            in_quote = True
        else:
            in_quote = False
    return MarkdownShape(
        headings=[re.sub(r"^#+\s*", "", ln).strip()
                  for ln in lines if ln.startswith("#")],
        table_count=len(tables),
        table_rows=sum(len(t.rows) for t in tables),
        quote_blocks=quote_blocks,
    )


def check_notion_roundtrip(source_text, pulled_text) -> list:
    """올린 md 와 되읽은 md 의 구조를 대조한다. **손실만 본다.**

    늘어난 것은 보고하지 않는다 — 사용자가 노션에서 절이나 표를 더한 것은 손실이
    아니라 이 루프가 원하는 바로 그 입력이다.
    """
    src, got = markdown_shape(source_text), markdown_shape(pulled_text)
    out = []
    missing = [h for h in src.headings if h not in got.headings]
    # 첫 헤딩은 노션이 페이지 제목으로 흡수하므로 되읽기에 없을 수 있다.
    if missing and src.headings and missing[0] == src.headings[0]:
        missing = missing[1:]
    for name in missing:
        out.append(Finding("error", "노션 왕복",
            f"절 '{name}' 이 되읽기에 없다 — 노션에 올라가지 않았을 수 있다"))
    if got.table_count < src.table_count:
        out.append(Finding("error", "노션 왕복",
            f"표가 {src.table_count}개에서 {got.table_count}개로 줄었다"))
    if got.table_rows < src.table_rows:
        out.append(Finding("error", "노션 왕복",
            f"표 행이 {src.table_rows}개에서 {got.table_rows}개로 줄었다"))
    if got.quote_blocks < src.quote_blocks:
        out.append(Finding("error", "노션 왕복",
            f"인용 블록이 {src.quote_blocks}개에서 {got.quote_blocks}개로 줄었다 — "
            "이 보고서의 인용은 전부 `> 출처:` 근거 표기라 하나가 사라지면 "
            "근거가 사라진 것이다"))
    return out
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"
```

기대: `OK`

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/validate.py tests/test_lab_validate.py
git commit -m "feat: 노션 왕복 구조 불변량 검사"
```

---

### Task 8: ⑦ `sync-report-to-notion` 스킬

**Files:**
- Create: `.claude/skills/sync-report-to-notion/SKILL.md`
- Create: `docs/notion-feedback/README.md`

**Interfaces:**
- Consumes: `notion.load_token`, `notion.push_markdown`, `notion.pull_markdown`, `notion.append_record`, `notion.load_records`, `validate.check_notion_markdown`, `validate.check_notion_roundtrip`, `config.load_course_info`, `config.folder_for_week`, `config.experiment_dir`
- Produces: 사용자가 부르는 명령 `/sync-report-to-notion`

- [ ] **Step 1: `docs/notion-feedback/README.md` 를 쓴다**

```markdown
# 노션 피드백 로그

⑦ `sync-report-to-notion` 이 되읽은 diff 를 분류한 결과를 회차별로 남기는 곳이다.

## 왜 남기는가

분류의 기본값은 **체계적**이다 — 사용자가 노션에서 고치는 것은 대체로 하네스를
고치려는 의도적 개선이기 때문이다. 그런데 그 기본값은 **과적합 위험**을 안고
간다: 이번 주 사정에 불과한 것을 규칙으로 박으면, 그 규칙은 다음 주부터 조용히
나쁜 결과를 내면서 오래 산다.

이 로그는 그걸 되돌리기 위한 것이다. 규칙을 박은 뒤 다음 라운드에서 "그 규칙
때문에 오히려 고쳐야 했던" 수정이 나오면, 여기서 어느 라운드의 어느 항목이
그 규칙을 만들었는지 찾아 걷어낸다.

## 파일 이름

`round<N>-<실험NN>-<종류>.md` — 예: `round1-실험01-예비보고서.md`

## 형식

    # 라운드 1 · 실험01 예비보고서

    - 올린 것: `실험01/output/실험01_예비보고서.md`
    - 노션: <URL>
    - baseline: `실험01/output/실험01_예비보고서_notion_baseline_v1.md`
    - 되읽음: `실험01/output/실험01_예비보고서_notion_v1.md`

    | # | 무엇이 바뀌었나 | 분류 | 반영 대상 | 반영함? |
    |---|---|---|---|---|
    | 1 | … | 체계적 | `.claude/skills/write-pre-report/SKILL.md` §섹션별 재료 | 예 |
    | 2 | … | 일회성 | 이번 md 만 | 예 |
    | 3 | … | 애매 | (사용자 확인 대기) | 아니오 |
```

- [ ] **Step 2: 스킬 문서를 쓴다**

`.claude/skills/sync-report-to-notion/SKILL.md` 를 아래 내용으로 만든다.

`````markdown
---
name: sync-report-to-notion
description: 논리회로실험 예비·결과보고서 md 를 노션에 올리고, 사용자가 노션에서 고친 내용을 되읽어 하네스 개선 규칙으로 분류한다. 사용자가 "노션에 올려줘", "2주차 예보 노션에 올려", "다 고쳤어 읽어와", "노션에서 가져와" 등을 요청하거나 /sync-report-to-notion 을 호출할 때 사용한다. 제출용 PDF 는 사용자가 노션에서 직접 내보내고 ⑥ 이 만든 표지를 앞에 손으로 붙인다.
---

# sync-report-to-notion

## 절대 규칙

1. **페이지를 절대 덮어쓰지 않는다.** 업로드는 항상 새 페이지다. 사용자가
   노션에서 고쳤지만 아직 되읽지 않은 구간이 구조적으로 존재하고, 그 구간에
   덮어쓰면 수정이 경고 없이 사라진다.
2. **토큰을 저장소에 쓰지 않는다.** 환경변수 `NOTION_TOKEN` 에서만 읽는다.
   토큰 값을 로그·커밋·대화 어디에도 그대로 옮기지 않는다.
3. **사진을 자동으로 올리지 않는다.** 상대경로 이미지는 노션에서 깨지는 게
   정상이고, 사용자가 직접 끼워 넣는다. 몇 장을 어디에 넣어야 하는지만 알린다.
4. **분류를 지어내지 않는다.** diff 에 실제로 있는 변경만 표에 올린다.
   애매하면 "애매"로 표시하고 사용자에게 묻는다.
5. **예비·결과보고서만 다룬다.** 체크리스트·표지·프리뷰는 이 스킬의 대상이
   아니다 — 인쇄용 A4 레이아웃 자체가 산출물이라 노션이 재현하지 못한다.

## push — 노션에 올리기

0. **주차로 불렸으면 폴더를 코드로 옮긴다.** 매핑은 1:1 이 아니다(실험4 는 7주차).

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.folder_for_week(<N>))
   "
   ```

   사용자가 `실험N` 으로 불렀으면 `config.experiment_dir(<N>)` 을 쓴다.

1. **올릴 파일을 정한다.** `<실험NN>/output/<실험NN>_예비보고서.md` 또는
   `..._결과보고서.md`. 없으면 ③ `write-pre-report` / ④ `write-result-report`
   를 먼저 돌리도록 안내하고 멈춘다.

2. **업로드 전 검사.** error 가 있으면 **올리지 않고** 보고한 뒤 사용자 판단을
   기다린다. info 는 그대로 사용자에게 전한다 — 노션에서 손으로 넣어야 할
   사진 목록이다.

   ```bash
   python3 -c "
   from scripts.lab import validate
   for f in validate.check_notion_markdown('<실험NN>/output/<파일명>.md'):
       print(f)
   "
   ```

3. **부모 페이지 id 를 읽는다.** `~` 면 `.claude/과목정보.md` 를 채우고 노션에서
   그 페이지에 integration 을 Connect 하도록 안내한 뒤 멈춘다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   info = config.load_course_info(config.find_project_root(Path('.')))
   print(info['notion_parent_page_id'])
   "
   ```

4. **올리고, 이력을 남기고, baseline 을 뜬다.** 세 가지가 한 덩어리다 —
   **baseline 없이 업로드만 하면 다음 pull 의 diff 가 왕복 노이즈로 뒤덮인다.**

   ```bash
   python3 - <<'PY'
   from datetime import datetime
   from pathlib import Path
   from scripts.lab import config, notion
   OUT, NAME, KIND = Path('<실험NN>/output'), '<파일명>.md', '<예비보고서|결과보고서>'
   root = config.find_project_root(Path('.'))
   info = config.load_course_info(root)
   token = notion.load_token()
   text = (OUT / NAME).read_text(encoding='utf-8')
   page = notion.push_markdown(text, info['notion_parent_page_id'], token)
   rec = notion.append_record(OUT, KIND, page['page_id'], page['url'], NAME,
                              datetime.now().strftime('%Y-%m-%d %H:%M'))
   base = OUT / f"{NAME[:-3]}_notion_baseline_v{rec['version']}.md"
   base.write_text(notion.pull_markdown(page['page_id'], token), encoding='utf-8')
   print('v', rec['version'], page['url'])
   print('baseline', base)
   PY
   ```

5. **왕복 손실을 확인한다.** 방금 뜬 baseline 과 올린 원본을 대조한다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import validate
   src = Path('<실험NN>/output/<파일명>.md').read_text(encoding='utf-8')
   got = Path('<실험NN>/output/<파일명 접미사>_notion_baseline_v<N>.md').read_text(encoding='utf-8')
   for f in validate.check_notion_roundtrip(src, got):
       print(f)
   "
   ```

   기대: 출력 없음. 절·표·인용이 줄었다고 나오면 **노션에 온전히 올라가지
   않은 것이다** — 사용자에게 보고하고, 그 페이지로 검토를 진행할지 다시 올릴지
   판단을 받는다.

6. **결과 안내.** 노션 URL, 버전 번호, 손으로 넣어야 할 사진 목록, 왕복 검사
   결과를 한 묶음으로. 그리고 **다 고치면 "읽어와"라고 말해 달라**고 알린다.

## pull — 노션에서 되읽고 분류하기

사용자가 "다 고쳤어, 읽어와" 라고 할 때 실행한다.

7. **가장 최근 업로드를 찾는다.**

   ```bash
   python3 -c "
   from scripts.lab import notion
   for r in notion.load_records('<실험NN>/output'):
       print(r['kind'], 'v%d' % r['version'], r['page_id'], r['uploaded_at'])
   "
   ```

8. **되읽어 저장한다.** baseline 을 덮어쓰지 않는다 — 파일 이름이 다르다.

   ```bash
   python3 - <<'PY'
   from pathlib import Path
   from scripts.lab import notion
   OUT, PAGE, STEM, V = Path('<실험NN>/output'), '<page_id>', '<파일명 접미사>', <N>
   text = notion.pull_markdown(PAGE, notion.load_token())
   (OUT / f'{STEM}_notion_v{V}.md').write_text(text, encoding='utf-8')
   print('저장:', OUT / f'{STEM}_notion_v{V}.md', len(text), '자')
   PY
   ```

9. **baseline 과 diff 를 뜬다.** **원본이 아니라 baseline 과 비교한다** — 노션
   변환기의 노이즈가 양쪽에 똑같이 들어가 상쇄되므로, 남는 차이가 순수하게
   사용자가 고친 것이다.

   ```bash
   diff -u '<실험NN>/output/<접미사>_notion_baseline_v<N>.md' \
           '<실험NN>/output/<접미사>_notion_v<N>.md'
   ```

10. **분류 표를 낸다.** diff 의 각 덩어리를 한 행으로.

    | # | 무엇이 바뀌었나 | 분류 | 반영 대상 |
    |---|---|---|---|

    - **기본값은 `체계적`** 이다. 사용자는 하네스를 고치려는 의도로 편집한다.
    - **애매하면 기본값으로 넘기지 않는다.** `애매` 로 표시하고 물어본다.
    - `일회성` 은 그 md 만 고친다. `체계적` 은 **어느 파일의 어느 절에** 박을지를
      반드시 함께 적는다 — 적을 수 없으면 그건 아직 체계적이 아니다.
    - **여러 실험에서 같은 수정이 나오면 논쟁 없이 체계적이다.** 라운드로 여러
      보고서를 한꺼번에 돌린 경우 이 대조를 먼저 한다.

11. **사용자 확인을 받는다.** 분류가 틀린 행만 사용자가 짚는다.

12. **로그를 남긴다.** `docs/notion-feedback/round<N>-<실험NN>-<종류>.md` 에
    §형식대로 쓴다. **반영하지 않기로 한 항목도 남긴다** — 나중에 과적합으로
    드러난 규칙을 되짚어 걷어내려면 어느 라운드의 무엇이 그 규칙을 만들었는지
    알아야 한다.

13. **하네스를 고친다.** `체계적` 로 확정된 항목만.

14. **재생성 대조.** 체계적 규칙을 하나라도 박았으면, 같은 입력으로 보고서를
    다시 만들어 사용자 수정본과 대조한다. **새 주차로 넘어가서 확인하지 않는다**
    — 내용이 달라 규칙이 먹힌 것인지 그냥 다른 내용이 나온 것인지 구분되지 않는다.
    일회성 수정만 있었던 라운드는 재생성하지 않는다.

## 제출

이 스킬은 **PDF 를 만들지 않는다.** 사용자가 노션에서 `⋯ → Export → PDF` 로
본문을 내려받고, ⑥ `make-lab-report-cover` 가 만든 표지 PDF 를 앞에 손으로
붙여 제출한다.

## 비-목표

- 사진을 API 로 첨부하지 않는다 (§절대 규칙 3).
- 노션 페이지를 지우거나 갈아엎지 않는다 (§절대 규칙 1).
- 체크리스트·표지·프리뷰를 올리지 않는다 (§절대 규칙 5).
- 부울식을 오버바로 승격하지 않는다 — 지금은 보수 `'` 그대로 올린다. 프로브에서
  `$\overline{A \cdot B}$` 렌더가 확인되면 그때 승격 규칙을 연다.
`````

- [ ] **Step 3: 스킬이 인식되는지 확인한다**

```bash
head -4 .claude/skills/sync-report-to-notion/SKILL.md
```

기대: 프론트매터의 `name: sync-report-to-notion` 과 `description:` 한 줄.

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/sync-report-to-notion docs/notion-feedback
git commit -m "feat: 노션 push/pull 스킬과 피드백 로그 규약 추가"
```

---

### Task 9: 기존 보고서 스킬에서 HTML·PDF 단계를 들어낸다

**Files:**
- Modify: `.claude/skills/write-pre-report/SKILL.md`
- Modify: `.claude/skills/write-result-report/SKILL.md`

**Interfaces:**
- Consumes: Task 8 의 스킬 이름 `sync-report-to-notion`
- Produces: 없음 (문서 변경)

**주의:** `write-pre-report/template.html` 과 `write-result-report/template.html` 은 **지우지 않는다.** 노션 렌더가 기대에 못 미쳐 되돌릴 가능성이 남아 있고, 파일이 남아 있다고 해를 끼치지 않는다. 되돌릴 때 다시 만드는 비용이 남겨 두는 비용보다 크다.

- [ ] **Step 1: `write-pre-report` 의 7단계에서 본문 안내문을 없앤다**

7단계의 "하나라도 `~` 면(조 편성 미확정)" 항목을 아래로 바꾼다.

```markdown
   - **`미확정: 없음` 이면(조 편성 확정):** ⑥ `make-lab-report-cover` 로 표지를
     만들 수 있다고 알린다. **이 스킬은 표지를 만들지도 합치지도 않는다.**
   - **하나라도 `~` 면(조 편성 미확정):** 조 편성이 확정돼야 표지를 만들 수
     있다고 알린다. **본문에는 아무 안내문도 넣지 않는다** — 이 md 는 그대로
     노션에 올라가고 그대로 제출본이 되므로, 하네스 사정을 적은 문장이 제출
     문서 첫 페이지에 찍힌다.
```

- [ ] **Step 2: 8·8b·9·10단계를 통째로 지우고 하나로 대체한다**

`8. **HTML 렌더 + PDF 변환 (본문).**` 부터 `10.` 단락 끝까지(즉 `11. **⑤ 로 검증하고`
직전까지) 전부 지우고 아래를 넣는다. 번호는 그대로 8 을 쓴다.

```markdown
8. **PDF 를 만들지 않는다.** 이 스킬의 산출물은 `.md` 하나다.

   제출본은 사용자가 ⑦ `sync-report-to-notion` 으로 노션에 올린 뒤 노션에서
   PDF 로 내보내고, ⑥ `make-lab-report-cover` 가 만든 표지를 앞에 손으로 붙여
   만든다. **표지는 이 스킬의 관심사가 아니다.**

   예전에는 여기서 `template.html` 을 채워 Chrome 헤드리스로 PDF 를 내고
   `pypdf` 로 표지를 합쳤다. 그 경로에는 "본문 재렌더가 방금 합친 표지를 조용히
   덮어쓴다" 는 함정이 있었는데, PDF 를 아예 만들지 않게 되면서 함정 자체가
   사라졌다. `template.html` 은 되돌릴 경우를 위해 남겨 두지만 이 절차는
   쓰지 않는다.
```

- [ ] **Step 3: 남은 단계 번호와 참조를 맞춘다**

- 기존 `11.` → `9.`, `12.` → `10.`, `13.` → `11.` 로 번호를 당긴다.
- 9단계(구 11) 안의 *"8단계부터 다시 돌면 10단계(표지 병합)도 다시 돌아야 한다는 뜻이다"* 문장을 **지운다.**
- 마지막 단계(구 13 결과 안내)를 아래로 바꾼다.

```markdown
11. **결과 안내.** md 경로, 섹션 검증 결과(error 0 여부), 그리고 **다음 할 일**을
    한 줄로: `⑦ sync-report-to-notion` 으로 노션에 올린다.
```

- [ ] **Step 4: `write-pre-report` 의 §비-목표에 한 줄 더한다**

```markdown
- PDF 를 만들지 않는다. 제출본은 노션 내보내기 + ⑥ 표지의 수동 병합이다 (⑦ 참조).
```

- [ ] **Step 5: `write-result-report` 에 같은 수술을 한다**

`write-result-report/SKILL.md` 의 단계 번호는 예보와 다르다. 정확한 대상은 아래와 같다.

- **10단계**(`조 편성 확인 → 표지 여부 분기`, 236행 부근)를 Step 1 과 같은 내용으로
  바꾼다 — 표지 판정만 알리고, **본문에 안내문을 넣지 않는다.**
- **11단계**(HTML 렌더 + PDF 변환, 261행 부근)·**11b**(렌더 HTML 검사, 314행 부근)·
  **12단계**(A4 실측, 332행 부근)·**13단계**(표지 병합, 344행 부근)를 **통째로 지우고**,
  Step 2 의 문단 하나로 대체한다. 번호는 `11.` 을 쓰고, 문단 안의
  `⑥ make-lab-report-cover`·`template.html` 언급은 그대로 둔다.
- **14 → 12, 15 → 13, 16 → 14** 로 번호를 당긴다.
- 12단계(구 14) 안의 *"11단계부터 다시 돌면 13단계(표지 병합)도 다시 돌아야 한다는
  뜻이다"* 문장을 **지운다** (392행 부근).
- 14단계(구 16) 결과 안내를 `md 경로 + 섹션 검증 결과 + "⑦ sync-report-to-notion 으로
  노션에 올린다"` 로 바꾼다. **`pdf 링크`·`표지 결합 여부`를 지운다.**
- **§사진 배치(423행 부근)의 `<figure class="photo-block"><img src="../실험사진/...">`
  지시(438행)를 마크다운 이미지 문법으로 바꾼다:**

```markdown
  상대경로 이미지로 넣는다: `![T1 row5 — 불일치 행 재현](../실험사진/T1 row5.jpg)`

  **노션에서는 이 이미지가 깨져 보이는 것이 정상이다.** 노션 API 의 마크다운은
  URL 만 받으므로 상대경로는 반드시 깨진다. 캡션이 그 자리에 무슨 사진이
  들어가야 하는지 알려주고, 사용자가 노션에서 직접 끼워 넣는다. ⑦ 의 업로드 전
  검사가 넣어야 할 목록을 세어 알린다.
```

- §비-목표에 Step 4 와 같은 줄을 더한다.
- **414행의 "그 항목의 완성 회로 사진(§사진 배치)을 싣는다" 는 그대로 둔다** —
  사진을 *싣는다*는 지시는 유효하고, 바뀐 것은 문법과 삽입 주체뿐이다.

- [ ] **Step 6: 지운 절차가 남아 있지 않은지 기계로 확인한다**

```bash
grep -n "html_to_pdf\|PdfWriter\|mediabox\|check_rendered_html\|check_embedded_images\|표지 병합\|photo-block" \
  .claude/skills/write-pre-report/SKILL.md .claude/skills/write-result-report/SKILL.md
```

기대: **출력 없음.** 남아 있으면 그 줄을 지운다.

- [ ] **Step 7: 다른 스킬은 건드리지 않았는지 확인한다**

```bash
grep -ln "html_to_pdf" .claude/skills/*/SKILL.md
```

기대: `prep-lab-checklist`, `make-lab-report-cover`, `explain-lab-preview` 세 개만.
이들은 인쇄용 A4 산출물이라 PDF 경로를 그대로 유지한다.

- [ ] **Step 8: 전체 테스트가 여전히 통과하는지 확인하고 커밋**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"
```

```bash
git add .claude/skills/write-pre-report/SKILL.md .claude/skills/write-result-report/SKILL.md
git commit -m "refactor: 보고서 스킬에서 HTML·PDF·표지 병합 단계 제거"
```

---

### Task 10: 파일럿 — 실험01 예비보고서를 노션에 올린다

**Files:**
- Modify: `실험01/output/실험01_예비보고서.md` (조 편성 안내문 제거)
- Create: `실험01/output/notion.json` (스킬이 생성)
- Create: `실험01/output/실험01_예비보고서_notion_baseline_v1.md` (스킬이 생성)
- Delete: `실험01/output/실험01_예비보고서.html`, `실험01/output/실험01_예비보고서.pdf`

**Interfaces:**
- Consumes: Task 8 의 스킬 전체
- Produces: 노션 페이지 1개와 baseline. 사용자 검토의 입력.

**왜 파일럿인가:** 하네스는 노션 루프로 한 번도 검증된 적이 없다. 5개를 다 만들어 올리면 체계적 결함 하나가 있을 때 **같은 수정을 노션에서 5번** 하게 된다. 실험01 은 md 가 이미 완성돼 있어 파일럿 비용이 0 이고, netlist·명세 작성(별도 트랙)과 병렬로 돌아간다.

- [ ] **Step 1: 조 편성 안내문을 지운다**

`실험01/output/실험01_예비보고서.md` 의 4~9행(`> **표지 관련 안내:**` 로 시작하는
인용 블록 전체)을 지운다. Task 9 Step 1 에서 정한 규칙 — 하네스 사정을 적은
문장이 제출 문서에 찍히면 안 된다 — 을 기존 산출물에도 적용하는 것이다.

```bash
python3 -c "
from pathlib import Path
p = Path('실험01/output/실험01_예비보고서.md')
lines = p.read_text(encoding='utf-8').split('\n')
keep = [ln for ln in lines if not ln.startswith('>') or '표지' not in ln]
print('지울 후보 줄:')
for ln in lines:
    if ln.startswith('>'):
        print(' ', ln[:60])
"
```

출력을 보고 표지 안내 인용 블록만 손으로 지운다 — `> 출처:` 인용은 **남긴다.**

- [ ] **Step 2: 업로드 전 검사를 돌린다**

```bash
python3 -c "
from scripts.lab import validate
for f in validate.check_notion_markdown('실험01/output/실험01_예비보고서.md'):
    print(f)
"
```

기대: `ℹ ... 노션에서 직접 넣어야 할 그림 1장: ../../.claude/assets/Breadboard.jpg`
한 줄만. `✗` 가 있으면 고치고 다시 돌린다.

- [ ] **Step 3: 스킬로 올린다**

`/sync-report-to-notion` 을 실험01 예비보고서에 대해 실행한다 (§push 1~6단계).
`실험01/output/notion.json` 과 `..._notion_baseline_v1.md` 가 생겨야 한다.

- [ ] **Step 4: 왕복 검사 결과를 확인한다**

§push 5단계의 출력이 비어 있어야 한다. 절·표·인용이 줄었다고 나오면 무엇이
사라졌는지 노션에서 눈으로 확인하고 사용자에게 보고한다.

- [ ] **Step 5: 낡은 HTML·PDF 를 지운다**

보고서 경로에서 더는 만들지 않는 산출물이다. 남겨 두면 어느 것이 최신인지
헷갈린다. (체크리스트의 `.html`·`.pdf` 는 **그대로 둔다** — 인쇄용이다.)

```bash
git rm 실험01/output/실험01_예비보고서.html 실험01/output/실험01_예비보고서.pdf
```

- [ ] **Step 6: 커밋하고 사용자에게 넘긴다**

```bash
git add 실험01/output
git commit -m "chore: 실험1 예비보고서 노션 업로드(파일럿) 및 HTML·PDF 산출물 제거"
```

사용자에게 전한다:
- 노션 URL
- 브레드보드 그림 1장을 §5.5 자리에 직접 넣어야 한다는 것
- **크게 거슬리는 것 위주로** 훑어 달라는 것 — 이 파일럿의 목적은 완벽한 보고서가
  아니라 나머지 4개를 만들기 전에 잡을 체계적 결함이다
- 다 고치면 **"읽어와"** 라고 말해 달라는 것

---

## 이 계획이 끝나면

- 실험01 예비보고서가 노션에 있고, 사용자 검토를 기다린다.
- 사용자 수정 → `/sync-report-to-notion` pull → 분류 표 → 하네스 수정 → **그 다음에**
  실험02·05·06·10 을 생성한다 (별도 트랙에서 명세·netlist 가 준비된 뒤).
- 라운드 2에서는 5개를 전부 재생성해 라운드 1 수정본과 대조한다.
