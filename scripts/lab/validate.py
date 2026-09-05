"""명세·결선도·보고서 검증. 예외를 던지지 않고 `Finding` 목록을 돌려준다.

⑤ `review-lab-report` 스킬이 이 모듈을 부른다. 검토는 반쯤 망가진 문서에도
동작해야 하므로, 여기서는 절대 예외로 중단하지 않는다.
"""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import config, md
from .boolexpr import eval_boolean
from .notation import DONT_CARE, normalize_cell
from .spec_parser import ENCODINGS, ROLES, derived_parts, split_columns

_BAD_CELL = {"\\|": "escape 된 파이프", "<br>": "<br> 태그", "\t": "탭 문자"}

# 관측 결과에 **방향을 붙이는** 문장. "~하면 ~를 의심한다", "~보다 크게
# 나오면 ~다". 교안에 원본이 없어 대조할 곳이 없고, 방향이 거꾸로여도
# 문법·서식 검사는 전부 통과하며 읽는 사람에게는 오히려 친절해 보인다.
# 실험02 명세가 이 형태로 두 번 거꾸로였고 둘 다 제출본까지 갔다.
#
# 실측으로 폭을 맞췄다 — 살아 있는 문서 10개에 33건, 최대 9건. 넓히면
# 목록이 못 읽을 만큼 길어지고, 좁히면(`나온다` 를 빼면) 실험02 의 원래
# 오문 하나가 빠진다.
_DIAGNOSTIC = re.compile(r"의심|나오면|나온다|보이면|어긋나면|빠뜨리면")

_MARKS = {"error": "✗", "warn": "!", "info": "ℹ"}


@dataclass
class Finding:
    level: str   # "error" | "warn" | "info"
    where: str
    message: str

    def __str__(self):
        return f"{_MARKS.get(self.level, '!')} {self.where} — {self.message}"


def _bit(cell, encoding):
    """평가용 비트로 읽는다. **데이터를 바꾸지 않는다** — 검산 중에만 쓴다."""
    c = normalize_cell(cell)
    if encoding == "H/L":
        return {"L": 0, "H": 1}.get(c)
    return {"0": 0, "1": 1}.get(c)


def check_table_integrity(spec) -> list:
    out = []
    for t in spec.tables:
        width = len(t.header)
        for i, row in enumerate(t.rows, start=1):
            where = f"{spec.path.name}:{t.id} 행{i}"
            if len(row) != width:
                out.append(Finding("error", where,
                    f"셀이 {len(row)}개인데 헤더는 {width}개다"))
            for cell in row:
                for bad, label in _BAD_CELL.items():
                    if bad in cell:
                        out.append(Finding("error", where, f"셀에 {label}가 있다: {cell!r}"))
    return out


def check_metadata(spec) -> list:
    out = []
    for t in spec.tables:
        where = f"{spec.path.name}:{t.id}"
        if not t.source:
            out.append(Finding("error", where, "source 가 없다 (예상값 출처는 항상 명시한다)"))
        if (t.source or "").strip().startswith("derived") and not derived_parts(t):
            # 형식이 깨지면 derived_parts 가 빈 리스트를 주는데, 그건 "derived 가
            # 아님" 과 구별되지 않는다. split_columns 가 조용히 잘못된 입출력
            # 분할을 내놓으므로 여기서 잡아야 한다.
            out.append(Finding("error", where,
                f"source 가 derived 인데 식을 읽지 못했다: {t.source!r}. "
                "`derived (Y = 식)` 또는 `derived (X = 식 ; Y = 식)` 형태여야 한다"))
        if t.role not in ROLES:
            out.append(Finding("error", where,
                f"role 이 {t.role!r} 이다. `record` 또는 `reference` 여야 한다"))
        if t.kind == "capture":
            if not t.expected:
                out.append(Finding("error", where,
                    "capture 표에 expected 산문이 없다 (예상값을 적을 곳이 여기다)"))
        elif t.encoding not in ENCODINGS:
            out.append(Finding("error", where,
                f"encoding 이 {t.encoding!r} 이다. `0/1` 또는 `H/L` 을 선언해야 한다"))
    return out


def check_row_count(spec) -> list:
    """진리표 행 수 ↔ 입력 비트 수. `X` 가 있으면 축약된 표이므로 건너뛴다."""
    out = []
    for t in spec.tables:
        if t.kind != "truth-table" or not t.rows:
            continue
        if any(normalize_cell(c) == DONT_CARE for row in t.rows for c in row):
            continue
        inputs, _ = split_columns(t)
        if not inputs:
            continue
        expected = 2 ** len(inputs)
        if len(t.rows) != expected:
            out.append(Finding("warn", f"{spec.path.name}:{t.id}",
                f"입력 {len(inputs)}비트({', '.join(inputs)})면 {expected}행이어야 하는데 "
                f"{len(t.rows)}행이다"))
    return out


def check_boolean(spec) -> list:
    """`derived (...)` 로 선언된 표를 식으로 되짚는다. 출력이 여럿이면 전부."""
    out = []
    for t in spec.tables:
        pairs = derived_parts(t)
        if not pairs or not t.rows:
            continue
        where = f"{spec.path.name}:{t.id}"
        inputs, _ = split_columns(t)
        for target, expr in pairs:
            if target not in t.header:
                out.append(Finding("error", where,
                    f"source 의 출력 {target!r} 이 표 헤더에 없다: {t.header}"))
                continue
            out_col = t.header.index(target)
            seen_eval_errors = set()
            for i, row in enumerate(t.rows, start=1):
                if len(row) != len(t.header):
                    continue
                env, dont_care, bad_cells = {}, False, []
                for col, cell in zip(t.header, row):
                    bit = _bit(cell, t.encoding)
                    if bit is not None:
                        env[col] = bit
                    elif col in inputs and normalize_cell(cell) == DONT_CARE:
                        dont_care = True
                    elif col in inputs:
                        bad_cells.append(f"{col}={cell!r}")
                if dont_care:
                    # 입력이 don't-care 인 행은 구체적 식으로 검산할 수 없다.
                    # 행 수 검사가 X 있는 표를 건너뛰는 것과 같은 이유다.
                    continue
                got = _bit(row[out_col], t.encoding)
                if got is None:
                    continue
                try:
                    want = eval_boolean(expr, env)
                except ValueError as exc:
                    # 셀 하나가 해독 불가라고 표 전체(나머지 행)를 포기하지
                    # 않는다 — 이 행만 건너뛰고 검산을 계속한다. 같은 열이
                    # 통째로 깨지면 모든 행에서 같은 메시지가 반복되므로,
                    # 한 표에서 처음 한 번만 보고한다.
                    sig = str(exc)
                    if sig not in seen_eval_errors:
                        seen_eval_errors.add(sig)
                        cells = ", ".join(bad_cells) or "(식이 참조하지 않는 열)"
                        out.append(Finding("error", f"{where} 행{i}",
                            f"{target} 의 식 {expr!r} 을 평가할 수 없다: {exc} "
                            f"— 해독 못 한 셀: {cells}"))
                    continue
                if got != want:
                    inputs, _ = split_columns(t)
                    shown = ", ".join(f"{c}={row[t.header.index(c)]}" for c in inputs)
                    out.append(Finding("error", f"{where} 행{i}",
                        f"{shown} 일 때 {target} = {expr} = {want} 인데 "
                        f"표에는 {row[out_col]!r} 이다"))
    return out


def check_orphan_tables(spec) -> list:
    """본문에 있으나 어느 항목도 가리키지 않는 표.

    파서는 반대 방향(없는 표를 가리키는 항목)만 막는다. 고아 표는 구조적으로
    표현 가능하므로 여기서 잡는다 — 대개 항목의 `tables` 에 ID 를 빠뜨린 것이다.
    """
    referenced = {tid for item in spec.items for tid in item.tables}
    return [Finding("error", f"{spec.path.name}:{t.id}",
                    "어느 항목의 tables 도 이 표를 가리키지 않는다")
            for t in spec.tables if t.id not in referenced]


def check_diagnostic_claims(text, where) -> list:
    """방향을 붙인 문장을 `info` 로 **센다. 판정하지 않는다.**

    방향이 맞는지는 그 절차의 산술을 실제로 굴려 봐야 알 수 있고 그건 코드가
    못 한다. 여기서 하는 일은 "굴려 봐야 할 문장이 여기 N개 있다" 를 보이게
    만드는 것뿐이다 — 그래서 `error` 가 아니라 `info` 다. `error` 로 올리면
    방향이 맞는 문장까지 고치게 된다.
    """
    return [Finding("info", f"{where}:{i}",
                    f"방향을 붙인 문장이다 — 절차의 산술로 굴려 봤는가: "
                    f"{line.strip()[:60]}")
            for i, line in enumerate(text.split("\n"), start=1)
            if _DIAGNOSTIC.search(line)]


def validate_spec(spec) -> list:
    # 진단 문장 info 는 **맨 끝**에 붙인다 — 앞에 끼우면 `findings[0]` 이
    # error 라고 단언하는 검사들이 조용히 깨진다.
    return (check_table_integrity(spec) + check_metadata(spec)
            + check_row_count(spec) + check_boolean(spec)
            + check_orphan_tables(spec)
            + check_diagnostic_claims(
                spec.path.read_text(encoding="utf-8"), spec.path.name))


def check_folder_convention(spec_path, spec) -> list:
    """명세가 놓인 폴더의 **이름과 위치** 가 `experiment` 필드와 맞는지 본다.

    폴더는 `<보고서>/<실험NN>/체크리스트/명세.md` 구조다. 리네임을 한 번 하고
    끝내면 다음 주차에 다시 어긋나므로, ⑤ 가 매 검토마다 이것을 부른다.

    **이름과 위치를 따로 본다.** 기대값은 `config.experiment_dir`(경로)이
    아니라 `config.experiment_folder_name`(이름)이다 — 조부모 폴더의 `.name`
    과 견주는 자리라 경로를 넣으면 옳게 놓인 명세까지 전부 error 가 된다.
    위치는 그 위 한 칸(`EXPERIMENT_BASE`)을 따로 확인한다. 이름만 보던 시절엔
    실험 폴더가 통째로 루트에서 `보고서/` 로 옮겨간 것을 이 검사가 못 봤다.
    """
    path = Path(spec_path).resolve()
    parents = path.parents
    if len(parents) < 3:
        return [Finding("error", str(spec_path),
                        "명세 경로가 "
                        f"`{config.EXPERIMENT_BASE}/<실험NN>/체크리스트/명세.md` "
                        "형태가 아니다")]
    actual = parents[1].name
    actual_base = parents[2].name
    try:
        expected = config.experiment_folder_name(spec.experiment)
    except (TypeError, ValueError) as e:
        # ⑤ 는 반쯤 망가진 문서에도 돌아야 한다. 여기서 죽으면 검토가 멈춘다.
        return [Finding("error", actual,
                        f"명세의 experiment 값을 폴더 이름으로 바꿀 수 없다: {e}")]
    out = []
    if actual != expected:
        out.append(Finding("error", actual,
            f"폴더 이름이 `{actual}` 인데 명세의 `experiment: {spec.experiment}` 는 "
            f"`{expected}` 를 요구한다 — 둘 중 하나가 틀렸다"))
    # 이름이 틀렸어도 위치는 마저 본다. 한 번에 하나씩만 알려주면 고친 뒤
    # 다시 돌려야 나머지가 드러난다.
    if actual_base != config.EXPERIMENT_BASE:
        out.append(Finding("error", f"{actual_base}/{actual}",
            f"실험 폴더가 `{actual_base}/` 아래에 있다 — "
            f"`{config.EXPERIMENT_BASE}/{actual}` 이어야 한다"))
    return out


def check_netlist(netlist_path, spec) -> list:
    """플로팅 입력은 이 과목의 대표 실패 원인이다. 누락을 error 로 잡는다."""
    path = Path(netlist_path)
    if not path.exists():
        return [Finding("error", str(netlist_path), "결선도 netlist 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    out = []
    for token, label in (("VCC", "VCC 연결"), ("GND", "GND 연결"),
                         ("미사용", "미사용 입력핀 처리")):
        if token not in text:
            out.append(Finding("error", path.name, f"{label} 언급이 통째로 없다"))
    for item in spec.items:
        for ic in item.ics:
            if ic not in text:
                out.append(Finding("warn", path.name,
                    f"항목 {item.id} 의 IC {ic} 가 netlist 에 없다"))
    # 결선도 쪽이 명세보다 진단 문장이 많다 (실험10: 9 대 1). 명세만
    # 검사하면 절반을 놓친다. **끝에** 붙인다 — 파일 부재 error 는 위에서
    # 이미 돌아갔고, 여기 info 가 앞에 끼면 `findings[0]` 단언이 깨진다.
    out += check_diagnostic_claims(text, path.name)
    return out


_STRAY_MARKDOWN = (("`", "백틱"), ("**", "굵게 표기"))
_TAG = re.compile(r"<[^>]+>")

# 화면·인쇄에 아무것도 찍지 않는 영역. 검사 전에 통째로 들어낸다 — CSS 주석에
# `position: fixed` 처럼 백틱을 쓰는 건 자연스러운 저작이고, 실제로 프리뷰
# 템플릿에서 두 번 반복됐다. 이걸 잡으면 매번 오탐이 떠서 검사 자체를 못 믿게
# 된다. 잡아야 할 것은 표 셀에 남은 마크다운이지 주석 속 백틱이 아니다.
_NON_RENDERING = re.compile(
    r"<!--.*?-->"
    r"|<style\b[^>]*>.*?</style>"
    r"|<script\b[^>]*>.*?</script>",
    re.DOTALL | re.IGNORECASE,
)


def check_rendered_html(html_path) -> list:
    """렌더된 HTML 본문에 마크다운 표기가 남았는지 본다.

    보고서 본문은 사람(또는 에이전트)이 마크다운에서 HTML 로 옮기는데,
    산문의 코드 스팬만 `<code>` 로 바꾸고 **표 셀을 빠뜨리는** 실수가 실제로
    일어났다 — 제출본 표 대부분에 백틱이 그대로 찍혔다. 눈으로는 잘 안 보인다.

    `<style>`·`<script>`·HTML 주석은 렌더되지 않으므로 검사에서 뺀다.
    """
    path = Path(html_path)
    if not path.exists():
        return [Finding("error", str(html_path), "렌더된 HTML 파일이 없다")]
    text = _TAG.sub(" ", _NON_RENDERING.sub(" ", path.read_text(encoding="utf-8")))
    out = []
    for token, label in _STRAY_MARKDOWN:
        count = text.count(token)
        if count:
            out.append(Finding("error", path.name,
                f"본문에 {label}({token!r})가 {count}개 남았다 — "
                "마크다운을 HTML 로 옮길 때 표 셀을 빠뜨리면 인쇄본에 그대로 찍힌다"))
    return out


def check_embedded_images(html_path) -> list:
    """`<img src=...>` 이 실제로 가리키는 파일이 있는지 본다.

    상대 경로는 **HTML 이 놓인 위치** 기준으로 풀린다. 다른 디렉토리에서
    렌더하면 그림이 깨진 채 PDF 로 굳는데, 텍스트 추출로는 안 보인다 —
    실제로 예비보고서의 브레드보드 그림이 그렇게 깨진 채 커밋됐다.
    """
    path = Path(html_path)
    if not path.exists():
        return [Finding("error", str(html_path), "렌더된 HTML 파일이 없다")]
    out = []
    for src in re.findall(r'<img[^>]+src="([^"]+)"', path.read_text(encoding="utf-8")):
        if src.startswith(("http://", "https://", "data:")):
            continue
        if not (path.parent / src).resolve().exists():
            out.append(Finding("error", path.name,
                f"이미지를 찾을 수 없다: {src!r} "
                f"(HTML 위치 {path.parent} 기준으로 푼다)"))
    return out


# NFM(Notion-flavored Markdown) 이 손실시키는 문법들. 실측 근거는
# docs/plans/2026-08-29-notion-probe-결과.md 에 있다.
# NFM 이 **입력으로도** 받는 자체 블록 태그. 원시 HTML 이 아니라 노션의 문법이다 —
# 목차 블록과 여백 블록은 학생이 노션에서 잡은 레이아웃을 소스 md 에 되돌려 넣기
# 위해 필요하고, 이것들까지 "원시 HTML" 로 잡으면 그 레이아웃을 올릴 수 없다.
# 입력 수용 여부는 실측했다 (docs/plans/2026-08-29-notion-probe-결과.md).
# 긴 이름을 먼저 둔다 — `table` 이 앞에 오면 `table_of_contents` 가 가려진다.
_NFM_BLOCK_TAGS = ("table_of_contents", "empty-block", "table", "tr", "td", "th",
                   "toggle", "callout", "columns", "column", "span")
_NFM_TAG_ALT = "|".join(_NFM_BLOCK_TAGS)

_NFM_LOSSY = (
    (re.compile(r"^#{5,}\s", re.M), "h5·h6 헤딩", "노션이 h4 로 강등한다"),
    (re.compile(r"^\[\^[^\]]+\]:", re.M), "각주 정의", "NFM 이 지원하지 않는다"),
    # 각주 정의 줄 안의 `[^n]` 을 참조로 이중 계수하지 않기 위해 `:` 로 끝나는
    # 형태(정의)는 제외한다 — 정의는 위 패턴이 이미 센다.
    (re.compile(r"(?<!\!)\[\^[^\]]+\](?!:)"), "각주 참조", "NFM 이 지원하지 않는다"),
    (re.compile(rf"^<(?!/?(?:{_NFM_TAG_ALT})\b)[a-zA-Z][^>]*>", re.M),
     "열 0 의 원시 HTML 블록", "NFM 은 일부 태그만 받는다"),
)
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

# 대상이 비어도 잡고 alt 도 함께 뽑는다. `_IMAGE` 는 `[^)]+` 라 빈 링크를
# 아예 못 잡는다 — 그 함수가 세는 것이 "넣어야 할 그림" 이기 때문이다.
_IMAGE_ANY = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")

# 노션 왕복은 파이프 표를 HTML `<table>` 로 바꿔 돌려준다 — 실측 근거는
# docs/plans/2026-08-29-notion-probe-결과.md. `md.parse_tables()` 는 파이프 표만
# 인식하므로, 되읽은 문서의 표를 `markdown_shape` 가 이 패턴으로도 세지 않으면
# 왕복마다 "표가 통째로 사라졌다"는 거짓 경보가 뜬다. 속성 순서·공백·대소문자에
# 흔들리지 않게 느슨히 잡는다.
_HTML_TABLE = re.compile(r"<table\b([^>]*)>(.*?)</table>", re.IGNORECASE | re.DOTALL)
_HTML_TABLE_HEADER_ROW = re.compile(r"\bheader-row\s*=\s*[\"']true[\"']", re.IGNORECASE)
_HTML_TR = re.compile(r"<tr\b", re.IGNORECASE)


def check_pulled_images(pulled_text) -> list:
    """되읽은 본문에서 **아직 안 끼운 그림**을 잡는다.

    올릴 때 상대경로 이미지는 노션에서 반드시 깨진다 — 그래서
    `check_notion_markdown` 이 올리기 **전에** "몇 장 넣어야 한다" 를 info 로
    알린다. 그런데 사용자가 실제로 넣었는지는 여태 아무도 확인하지 않았다.
    실험01 v7 에서 브레드보드 그림이 빈 링크로 올라갔고 왕복 검사는 조용했다 —
    `check_notion_roundtrip` 은 헤딩·표·인용 **개수**만 보므로 그림은 안 센다.

    **되읽기 쪽에만 건다.** 올린 직후에는 그림이 비어 있는 것이 정상이므로
    (사용자가 노션에서 끼우기로 한 설계다) push 에 걸면 매번 거짓 경보가 된다.
    """
    out = []
    for alt, target in _IMAGE_ANY.findall(pulled_text):
        if target.strip():
            continue
        out.append(Finding("error", "노션 그림",
            f"그림 '{alt}' 이 빈 링크다 — 노션에서 아직 끼우지 않았다. "
            "이대로 PDF 를 내보내면 그 자리가 빈 채로 제출된다"))
    return out


# 문단 흐름 밖에 있는 줄머리. 표·헤딩·펜스·인용·노션 태그는 줄바꿈이 의미다.
_FLOW_OUT = ("\t", "|", "#", "<", "```", ">")
# 번호 목록도 목록이다. 이것을 산문으로 보면 연달아 오는 단계가 통째로 잡힌다
# — ⑦ 14단계 재생성이 실제로 이 오탐에 걸려 불릿으로 우회했다.
_ORDERED = re.compile(r"^\d+\.\s")
# 그림은 블록이다. 앞 산문과 붙어 있어도 "문장이 토막 났다" 가 아니다.
_IMAGE_ONLY = re.compile(r"^!\[[^\]]*\]\([^)]*\)\s*$")


def _flow_kind(line):
    """줄이 문단 흐름의 어디에 속하는지. 흐름 밖이면 `keep`."""
    if not line.strip():
        return "blank"
    if line.startswith(_FLOW_OUT) or _IMAGE_ONLY.match(line):
        return "keep"
    if line.startswith("  "):
        return "cont"
    if line.startswith(("- ", "* ")) or _ORDERED.match(line):
        return "bullet"
    return "prose"


def check_report_wrapping(md_text) -> list:
    """본문 문단이 여러 줄로 쪼개져 있는지 본다.

    **노션은 원본의 줄바꿈을 하나하나 그대로 렌더한다.** 그래서 76열에 맞춰
    감싼 본문은 노션에서 문장 중간이 토막 난 채 보이고, 그대로 PDF 로 나간다.
    실험02 초판이 그렇게 올라갔고 **사용자가 v2 를 고치려다 눈으로 찾았다** —
    그때까지 아무 검사도 이것을 안 봤다.

    76열 규칙은 `.claude/skills/*/SKILL.md` 에만 걸린다. 보고서 본문에는 걸리지
    않는데 ③ 이 그 경계를 말해 주지 않아서, 격리 생성이 관행을 산출물에까지
    옮겨 적용했다. 판단이 아니라 기계적 서식이라 규칙을 고치지 않으면 주차마다
    재발한다.

    **폭을 재지 않는다.** 신호는 구조다 — 제대로 쓴 보고서는 문단 하나가 줄
    하나라, 산문 줄 바로 뒤에 또 산문 줄이 오는 일이 없다. 실측: 실험01
    승인본 0곳, 감싸인 실험02 초판 160곳. 임계값이 필요 없을 만큼 갈린다.

    한 줄로 요약해서 낸다. 160곳이면 160줄을 뱉는 검사는 아무도 안 읽는다.

    **올리기 전 원본에만 쓴다. 되읽은 baseline 에는 쓰지 않는다.** 원본은 빈
    줄이 문단을 가르므로 산문이 연달아 오면 반드시 쪼개진 것이다. 그런데
    노션 되읽기는 문단 사이의 빈 줄을 지워서, 각자 완결된 문단이 나란히
    붙는다 — 실험01 의 승인본은 0곳인데 그 v7 되읽기는 10곳이 잡힌다.
    `check_notion_markdown` 이 부르는 자리가 곧 그 범위다(⑦ push 2단계,
    올릴 원본). 되읽기에 이 함수를 대는 것은 범위를 벗어난 것이다.
    """
    lines = md_text.splitlines()
    hits = []
    for i in range(len(lines) - 1):
        here, nxt = lines[i], lines[i + 1]
        kind, kind_next = _flow_kind(here), _flow_kind(nxt)
        joined = ((kind_next == "prose" and kind == "prose")
                  or (kind_next == "cont" and kind in ("bullet", "cont")))
        if not joined:
            continue
        # 콜론·마침표 뒤에 수식을 따로 놓은 것은 저자의 배치다. 잡으면 거짓 경보다.
        if nxt.strip().startswith("`") and here.rstrip().endswith((":", ".")):
            continue
        hits.append(i + 1)
    if not hits:
        return []
    return [Finding("error", "본문 줄바꿈",
        f"문단이 {len(hits)}곳에서 줄로 쪼개져 있다 (첫 자리 {hits[0]}행) — "
        "노션은 원본의 줄바꿈을 그대로 렌더해서 문장 중간이 토막 난 채 올라간다. "
        "76열 규칙은 스킬 문서에만 걸린다 — 보고서 문단은 한 줄로 쓴다")]


_HEADING = re.compile(r"(?m)^(#{1,6})\s+(.*)$")


def check_heading_backticks(md_text) -> list:
    """헤딩 텍스트 안의 코드 스팬을 잡는다.

    **노션 목차 블록이 헤딩 텍스트를 그대로 가져간다.** 그래서 헤딩에 백틱이
    있으면 목차에까지 코드 배경이 번진다. 라운드 1 에서 학생이 실험02 의
    헤딩 두 개에서 직접 백틱을 지웠고, 남은 두 개를 어떻게 볼지 물었더니
    **체계적**이라고 확인해 주었다(실험01 승인본에는 백틱 헤딩이 0개다).

    기호를 백틱으로 감싸는 것 자체는 §절대 규칙이 시키는 일이다 — **본문
    안에서만** 그렇게 한다. 그래서 헤딩 줄만 본다.
    """
    hits = [i for i, line in enumerate(md_text.splitlines(), 1)
            if _HEADING.match(line) and "`" in _HEADING.match(line).group(2)]
    if not hits:
        return []
    return [Finding("error", "헤딩 표기",
        f"헤딩 {len(hits)}개에 백틱이 있다 (첫 자리 {hits[0]}행) — 노션 목차 "
        "블록이 헤딩 텍스트를 그대로 가져가 목차에까지 코드 배경이 번진다. "
        "기호는 본문에서만 백틱으로 감싼다")]


# A4 한 장에 들어가는 표의 최대 열 수. 실측값이지 유도값이 아니다 —
# 실험05 v1 을 노션에서 A4 PDF 로 내보내 세었다(11열 셋 온전, 13·14열 잘림).
NOTION_A4_MAX_COLUMNS = 11

_SEP_ROW = re.compile(r"^\|[\s:|-]*-{2,}[\s:|-]*\|?$")


def _split_row(line):
    """`| a | b |` → `['a', 'b']`. 앞뒤 들여쓰기와 바깥 파이프를 뗀다."""
    s = line.strip()
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s[1:].split("|")]


def check_table_width(md_text) -> list:
    """A4 한 장에서 오른쪽이 잘릴 표를 잡는다.

    **노션 PDF 내보내기는 넓은 표를 경고 없이 자른다.** 노션 화면에서는 가로
    스크롤로 전부 보이므로 눈으로는 드러나지 않고, 제출본에서만 열이 사라진다.
    실험05 v1 에서 실제로 났다 — `BCD to Decimal 예상 진리표`(14열)에서 `Y7`·
    `Y8`·`Y9` 가, `8X3 우선순위 인코더 예상 진리표`(13열)에서 `GS`·`EO` 가
    빠진 채로 PDF 가 나왔다. 하필 `GS`·`EO` 는 같은 보고서의 본문이 "두 신호가
    함께 갈라 준다"고 설명하는 대상이라, 근거만 사라지고 주장이 남았다.

    **한계 11열은 실측이다.** 같은 PDF 에서 11열 표 셋(`3X8 디코더 이론표`·
    `8X3 인코더 이론표`·`Excess-3 예상 진리표`)은 온전했다. 12열은 시험하지
    않았으므로 안전한 쪽으로 11 에서 끊는다.

    **구분선이 있어야 표로 센다.** 본문에 `A|B` 같은 파이프가 섞여도 구분선이
    없으면 표가 아니다. 들여쓴 표도 센다 — §절대 규칙 13 이 불릿 아래 표를
    탭으로 들여쓰라고 시키므로, 들여쓰기를 빼면 진리표 대부분을 놓친다.
    """
    out, lines = [], md_text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|") or i + 1 >= len(lines):
            continue
        if not _SEP_ROW.match(lines[i + 1].strip()):
            continue                      # 구분선이 뒤따라야 헤더다
        header = _split_row(line)
        n = len(header)
        if n <= NOTION_A4_MAX_COLUMNS:
            continue
        cut = header[NOTION_A4_MAX_COLUMNS:]
        out.append(Finding("error", "표 너비",
            f"{i + 1}행의 표가 {n}열이라 A4 PDF 에서 오른쪽 {len(cut)}열이 "
            f"잘린다 — {', '.join(cut)}. 노션 화면에서는 가로 스크롤로 다 "
            f"보이므로 내보내기 전에는 드러나지 않는다. "
            f"{NOTION_A4_MAX_COLUMNS}열 이하로 나눈다"))
    return out


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
    out.extend(check_report_wrapping(body))
    out.extend(check_heading_backticks(body))
    out.extend(check_table_width(body))
    local = [s for s in _IMAGE.findall(body)
             if not s.startswith(("http://", "https://", "data:"))]
    if local:
        out.append(Finding("info", path.name,
            f"노션에서 직접 넣어야 할 그림 {len(local)}장: " + ", ".join(local)))
    return out


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

    표는 **파이프 표와 HTML `<table>` 을 함께** 센다 — 노션 되읽기가 파이프 표를
    HTML 로 바꿔 돌려주기 때문이다(`_HTML_TABLE` 주석 참고). 원본(파이프)과
    되읽기(HTML)를 같은 잣대로 세지 않으면 형태만 바뀐 표가 손실로 보인다.
    """
    _, body = md.split_frontmatter(text)
    lines = body.split("\n")
    tables = md.parse_tables(body)
    html_tables = list(_HTML_TABLE.finditer(body))
    html_table_rows = 0
    for m in html_tables:
        attrs, inner = m.group(1), m.group(2)
        tr_count = len(_HTML_TR.findall(inner))
        if _HTML_TABLE_HEADER_ROW.search(attrs):
            # MdTable.rows 는 헤더 행을 빼고 세므로, HTML 표의 헤더 <tr> 도
            # 여기서 빼야 두 형태의 행 수가 같은 기준으로 비교된다.
            tr_count = max(tr_count - 1, 0)
        html_table_rows += tr_count
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
        table_count=len(tables) + len(html_tables),
        table_rows=sum(len(t.rows) for t in tables) + html_table_rows,
        quote_blocks=quote_blocks,
    )


def check_notion_roundtrip(source_text, pulled_text) -> list:
    """올린 md 와 되읽은 md 의 구조를 대조한다. **손실만 본다.**

    업로드 직후 되읽어 baseline 을 저장하는 이 왕복이 곧 업로드 검증이다 — 추가
    API 호출 없이. 텍스트가 아니라 헤딩·표 개수·표 행 수·인용 블록 수만 비교하는
    이유는 `markdown_shape` 와 같다: 노션이 만드는 노이즈(문단 병합, 표 정렬
    마커 소실)를 결함으로 세면 진짜 손실이 그 안에 파묻힌다.

    늘어난 것은 보고하지 않는다 — 사용자가 노션에서 절이나 표를 더한 것은 손실이
    아니라 이 루프가 원하는 바로 그 입력이다.
    """
    src, got = markdown_shape(source_text), markdown_shape(pulled_text)
    out = []
    # 집합 포함이 아니라 **다중집합 차**로 비교한다 — 같은 이름이 두 번 나오는데
    # 하나만 남았을 때, `in` 검사는 "이름이 존재하긴 한다"만 보고 손실을 놓친다.
    # 항목반복형 프리셋(`결선도`·`구성한 회로`·`실험 결과`·`고찰`을 항목마다
    # 반복)이 이 상황을 실제로 만든다.
    missing = list((Counter(src.headings) - Counter(got.headings)).elements())
    # 첫 헤딩은 노션이 페이지 제목으로 흡수하므로 되읽기에 없을 수 있다.
    # **정확히 한 번만** 면제한다 — 같은 이름이 여러 번 나오는 양식에서 나머지
    # 누락까지 덮어 주면, 이 함수의 존재 이유인 "절이 통째로 안 올라간 것"을
    # 놓친다.
    if src.headings and src.headings[0] in missing:
        missing.remove(src.headings[0])
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


def check_report_sections(report_path, sections, item_count=None) -> list:
    """`.claude/보고서양식.md` 기준으로 섹션 유무·순서를 본다.

    하드코딩된 목차와 대조하지 않는다 — 양식이 연도마다 다르기 때문이다 (R1).

    `item_count` 를 주면 `repeat: per-item` 섹션이 항목 수만큼 나오는지도 본다.
    항목반복형 프리셋(결보 29편 중 14편의 실제 구조)이 이걸 요구한다.
    """
    path = Path(report_path)
    if not path.exists():
        return [Finding("error", str(report_path), "보고서 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    headings = [re.sub(r"^#+\s*(?:\d+[.)]\s*)?", "", ln).strip()
                for ln in text.split("\n") if ln.startswith("#")]
    # 부분 문자열로 맞추면 `# 실험 결과 분석` 한 줄이 `실험 결과` 와 `결과 분석`
    # 두 요구 섹션을 동시에 만족시켜 버린다. 정확히 일치해야 한다.
    out, last = [], -1
    for sec in sections:
        if not sec.generate:
            continue
        hits = [i for i, h in enumerate(headings) if h == sec.name]
        pos = hits[0] if hits else None
        if pos is None:
            out.append(Finding("error", path.name, f"양식이 요구하는 섹션 '{sec.name}' 이 없다"))
            continue
        if sec.repeat == "per-item" and item_count is not None and len(hits) != item_count:
            out.append(Finding("error", path.name,
                f"섹션 '{sec.name}' 은 항목마다 반복돼야 한다 — "
                f"항목 {item_count}개인데 {len(hits)}번 나온다"))
        if pos < last:
            out.append(Finding("warn", path.name,
                f"섹션 '{sec.name}' 의 순서가 양식과 다르다"))
        last = max(last, pos)
    return out
