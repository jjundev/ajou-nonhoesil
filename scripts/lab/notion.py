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
