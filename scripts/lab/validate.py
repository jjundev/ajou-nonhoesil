"""명세·결선도·보고서 검증. 예외를 던지지 않고 `Finding` 목록을 돌려준다.

⑤ `review-lab-report` 스킬이 이 모듈을 부른다. 검토는 반쯤 망가진 문서에도
동작해야 하므로, 여기서는 절대 예외로 중단하지 않는다.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import config, md
from .boolexpr import eval_boolean
from .notation import DONT_CARE, normalize_cell
from .spec_parser import ENCODINGS, ROLES, derived_parts, split_columns

_BAD_CELL = {"\\|": "escape 된 파이프", "<br>": "<br> 태그", "\t": "탭 문자"}


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


def validate_spec(spec) -> list:
    return (check_table_integrity(spec) + check_metadata(spec)
            + check_row_count(spec) + check_boolean(spec)
            + check_orphan_tables(spec))


def check_folder_convention(spec_path, spec) -> list:
    """명세가 놓인 폴더 이름이 `experiment` 필드와 맞는지 본다.

    폴더는 `<실험NN>/체크리스트/명세.md` 구조다. 리네임을 한 번 하고 끝내면
    다음 주차에 다시 어긋나므로, ⑤ 가 매 검토마다 이것을 부른다.
    """
    path = Path(spec_path).resolve()
    parents = path.parents
    if len(parents) < 2:
        return [Finding("error", str(spec_path),
                        "명세 경로가 `<실험NN>/체크리스트/명세.md` 형태가 아니다")]
    actual = parents[1].name
    try:
        expected = config.experiment_dir(spec.experiment)
    except (TypeError, ValueError) as e:
        # ⑤ 는 반쯤 망가진 문서에도 돌아야 한다. 여기서 죽으면 검토가 멈춘다.
        return [Finding("error", actual,
                        f"명세의 experiment 값을 폴더 이름으로 바꿀 수 없다: {e}")]
    if actual != expected:
        return [Finding("error", actual,
            f"폴더 이름이 `{actual}` 인데 명세의 `experiment: {spec.experiment}` 는 "
            f"`{expected}` 를 요구한다 — 둘 중 하나가 틀렸다")]
    return []


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

    업로드 직후 되읽어 baseline 을 저장하는 이 왕복이 곧 업로드 검증이다 — 추가
    API 호출 없이. 텍스트가 아니라 헤딩·표 개수·표 행 수·인용 블록 수만 비교하는
    이유는 `markdown_shape` 와 같다: 노션이 만드는 노이즈(문단 병합, 표 정렬
    마커 소실)를 결함으로 세면 진짜 손실이 그 안에 파묻힌다.

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
