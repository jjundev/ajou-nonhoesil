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
from pathlib import Path

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
            f"  echo \"export {TOKEN_ENV}='ntn_...'\" >> ~/.zshenv\n"
            "를 실행하고 **새 터미널**을 여세요 (zsh 는 대화형 셸에서만 rc "
            "파일을 읽어서, 하네스가 돌리는 비대화형 python3 는 그 값을 "
            "못 봅니다). 토큰은 저장소에 두지 않습니다."
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


RECORD_NAME = "notion.json"
RECORD_SCHEMA = "notion-uploads/v1"


def push_markdown(md_text, parent_page_id, token, title=None, timeout=120) -> dict:
    """마크다운으로 노션 페이지를 **새로** 만든다. 덮어쓰기는 제공하지 않는다.

    이 루프는 구조적으로 "사용자가 노션에서 고쳤지만 아직 되읽히지 않은 구간"을
    갖는다. 그 구간에 재업로드가 덮어쓰면 수정이 **경고 없이** 사라지고, 노션
    페이지 덮어쓰기는 되돌리기 어렵다. 그래서 이 모듈에는 갈아엎는 함수가 없다.

    `title` 을 주면 페이지 제목으로 그대로 쓴다. **주는 편이 안전하다** —
    안 주면 노션이 마크다운의 첫 `#` 헤딩을 제목으로 흡수하는데, 그 흡수는
    조건이 붙는다. 실제로 제목 헤딩 바로 뒤에 목차 블록을 두었더니 흡수가
    깨져 **제목이 빈 페이지**가 만들어졌다(v4). 사이드바에서 "Untitled" 로
    보이고 URL 에도 슬러그가 없어 사람이 찾지 못한다.

    **제목 끝에 버전을 붙여 넘긴다** (`… 예비보고서 v7`). 사용자는 노션
    사이드바에서 PDF 를 내보내 제출하는데 거기엔 `notion.json` 이 보이지
    않는다. 제목이 전부 같으면 옛 판본을 골라도 아무 데서도 오류가 나지
    않는다. 번호는 `next_version()` 으로 업로드 **전에** 구한다.
    """
    if not (parent_page_id or "").strip():
        raise NotionError(
            "부모 페이지 id 가 비어 있습니다. `.claude/과목정보.md` 의 "
            "notion_parent_page_id 를 채우고, 노션에서 그 페이지에 integration 을 "
            "Connect 했는지 확인하세요 (안 하면 404 object_not_found 가 납니다)."
        )
    payload = {"parent": {"page_id": parent_page_id}, "markdown": md_text}
    if title:
        payload["properties"] = {"title": [{"text": {"content": title}}]}
    data = _request("POST", "/pages", token, payload, timeout)
    if "id" not in data:
        raise NotionError(
            f"노션 응답에 페이지 id 가 없습니다. 응답의 키: {sorted(data)}"
        )
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


def next_version(output_dir, kind) -> int:
    """다음 업로드가 받을 버전 번호. `append_record` 가 붙일 번호와 같다.

    페이지 제목은 업로드 **전에** 만들어야 하는데 `append_record` 는 업로드
    **뒤에** 불린다. 두 곳에서 같은 식을 따로 쓰면 제목의 버전과 `notion.json`
    의 버전이 어긋나므로, 세는 자리를 여기 하나로 둔다.
    """
    return sum(1 for r in load_records(output_dir) if r.get("kind") == kind) + 1


def append_record(output_dir, kind, page_id, url, source, when) -> dict:
    """업로드 한 건을 `<실험NN>/output/notion.json` 에 덧붙인다.

    `when` 을 인자로 받는다. 이 값은 파일에 굳으므로 테스트가 고정값을 넣을 수
    있어야 한다.

    `version` 은 **같은 kind 안에서만** 센다 — 예비보고서와 결과보고서는 서로
    다른 문서라 카운터를 공유하면 "몇 번째 예보인지"를 알 수 없다.
    """
    version = next_version(output_dir, kind)
    records = load_records(output_dir)
    record = {
        "kind": kind,
        "version": version,
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


# 되읽기 응답에서 마크다운이 담긴 키. 첫 항목이 Task 1 프로브의 실측값이고,
# 나머지는 노션이 이름을 바꿨을 때를 위한 여유다.
_MARKDOWN_KEYS = ("markdown", "content")


def pull_markdown(page_id, token, timeout=120) -> str:
    """페이지 내용을 Notion-flavored Markdown 문자열로 되읽는다.

    **문자열을 못 찾으면 빈 문자열 대신 예외를 던진다.** 빈 문자열이 baseline
    으로 저장되면 이후 모든 diff 가 "전부 삭제됨" 으로 보여 거짓말이 된다.

    **`truncated` 가 참이어도 같은 이유로 예외를 던진다.** 이 함수의 반환값이
    그대로 baseline 파일이 되고, `check_notion_roundtrip(source_text,
    pulled_text)` 는 문자열 두 개만 받아 baseline 대비 **손실만** 본다.
    `truncated` 와 `unknown_block_ids` 는 이 되읽기 응답에만 실려 오는 신호라
    — 반환형이 `str` 뿐이라 — 여기서 버리면 파이프라인 어디서도 되살릴 수
    없다. 잘린 채로 baseline 이 굳으면, 잘려서 없어진 내용은 "원래 baseline
    에도 없었던 것"이 되어 이후 실제로 지워져도 손실로 안 잡힌다 — 빈 문자열을
    거부하는 것과 같은 이유로, 부분 문자열도 거부한다.
    """
    data = _request("GET", f"/pages/{page_id}/markdown", token, timeout=timeout)
    if data.get("truncated") is True:
        # 키가 아예 없거나 false 인 것은 "안 잘렸다" 다 — missing 을 참으로
        # 읽으면 대부분의 정상 응답을 오탐으로 거절하게 된다.
        unknown = data.get("unknown_block_ids") or []
        ids = ", ".join(str(x) for x in unknown)
        raise NotionError(
            "노션 되읽기 응답이 잘렸습니다 (truncated=true) — 이 상태로 "
            "baseline 을 저장하면 baseline 이 원본보다 짧아집니다. "
            "check_notion_roundtrip 은 baseline 대비 손실만 보고하므로, 잘린 "
            "baseline 은 이후의 진짜 손실을 가려 안 보이게 만듭니다."
            + (f" 되돌아오지 않은 블록: {ids}" if ids else " (unknown_block_ids 없음)")
        )
    for key in _MARKDOWN_KEYS:
        if isinstance(data.get(key), str):
            return data[key]
    raise NotionError(
        f"되읽기 응답에서 마크다운 문자열을 찾지 못했습니다. "
        f"응답의 키: {sorted(data)} — `_MARKDOWN_KEYS` 를 실측값에 맞추세요."
    )
