"""결과보고서 재생성물을 승인본과 대조한다.

`specdiff` 가 명세의 계약 필드를, `regen_compare` 가 결선도의 간선 집합을 보는
것과 짝이다 — 여기는 **보고서 md** 를 본다. 문장 동일성은 요구하지 않는다(요구하면
승인본 문장을 규칙에 베끼는 과적합으로 간다). 보는 것은 여섯 갈래다.

- `structure` — 헤딩 수열(레벨·이름), 절마다 표 수·행 수·그림 자리·앞 여백 블록 수
- `cell`      — 표 셀(헤더 포함). `**` 굵게 표시는 벗기고 본다
- `references`— 참고문헌 항목의 다중집합
- `style`     — `validate.check_body_style` 이 재생성물에서 잡은 것(승인본은 0건)
- `fact`      — 절마다 문장에서 뽑은 사실 토큰의 다중집합 차
- `wording`   — 절마다 문장 집합 일치율. **보고만 하고 세지 않는다**

표는 파이프 표와 노션이 되돌려주는 HTML `<table>` 을 같은 셀 목록으로 읽는다 —
승인본(파이프)과 baseline(HTML)을 대조해 0건이 나와야 이 도구를 믿을 수 있다
(`tests/test_lab_report_compare.py`).
"""

import difflib
import html
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import config, md, validate

_HEADING = re.compile(r"^(#{1,2})\s+(.*)$")
_EMPTY = re.compile(r"^\s*<empty-block\s*/>\s*$")
_TOC = re.compile(r"^\s*<table_of_contents\b")
_TR = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_TD = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_BOLD = re.compile(r"\*\*(.*?)\*\*")
_ESCAPED = re.compile(r"\\([{}_*\[\]])")
_SENT_SPLIT = re.compile(r"(?<=[.。!?])\s+")
# 노션은 본문의 맨 URL 을 `[url](url)` 자기참조 링크로 되돌린다(참고문헌 절의
# 데이터시트 URL 이 baseline v5 에서 전부 이 꼴이다). 텍스트와 대상이 같을 때만
# 벗긴다 — 실제 링크 텍스트(`[강의노트](...)` 처럼 텍스트가 다른 경우)는 건드리지
# 않는다.
_SELF_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass
class Section:
    heading: str
    level: int
    tables: list = field(default_factory=list)     # [(header, rows)]
    images: list = field(default_factory=list)     # alt 텍스트
    sentences: list = field(default_factory=list)
    empty_blocks: int = 0
    parent: str = ""    # 가장 가까운 앞 `#` 대절 이름. 대절 자신은 ""


@dataclass
class ReportShape:
    title: str
    sections: list
    references: list


def _norm(s: str) -> str:
    s = _BOLD.sub(r"\1", s)
    s = _SELF_LINK.sub(lambda m: m.group(1) if m.group(1) == m.group(2) else m.group(0), s)
    s = _ESCAPED.sub(r"\1", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _html_to_pipe(m) -> str:
    """HTML 표 하나를 파이프 표 문자열로. 첫 `<tr>` 을 헤더로 본다 — 노션 되읽기는
    항상 `header-row="true"` 를 붙이고, 안 붙은 표는 이 저장소에 없다."""
    indent = re.match(r"\s*", m.group(0)).group(0).replace("\n", "")
    rows = [[_norm(c) for c in _TD.findall(tr)] for tr in _TR.findall(m.group(2))]
    if not rows:
        return ""
    width = len(rows[0])
    lines = [indent + "| " + " | ".join(rows[0]) + " |",
             indent + "|" + "---|" * width]
    lines += [indent + "| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _pipe_tables_only(text: str) -> str:
    return validate._HTML_TABLE.sub(_html_to_pipe, text)


def report_shape(text: str) -> ReportShape:
    """구조를 뽑는다. 첫 `# ` 헤딩은 문서 제목이라 절이 아니다 — 노션이 페이지
    제목으로 흡수해 되읽기에는 없다. 절은 그 다음부터, `#`·`##` 두 단계다."""
    _, body = md.split_frontmatter(_pipe_tables_only(text))
    lines = body.split("\n")
    title, sections, pending_empty = "", [], 0
    cur, parent_name = None, ""
    i = 0
    while i < len(lines):
        line = lines[i]
        table, nxt = md.parse_table_at(lines, i)
        if table is not None:
            if cur is not None:
                cur.tables.append(([_norm(c) for c in table.header],
                                   [[_norm(c) for c in r] for r in table.rows]))
            i = nxt
            continue
        hm = _HEADING.match(line)
        if hm:
            level, name = len(hm.group(1)), _norm(hm.group(2))
            # 문서 제목은 "바로 다음 비어 있지 않은 줄이 목차 블록" 인 `#` 헤딩뿐이다.
            # 되읽기(baseline)는 제목이 흡수돼 `<table_of_contents>` 로 시작하므로
            # 그 첫 `# 실험 결과` 를 제목으로 먹으면 절 수열이 승인본과 어긋난다.
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if level == 1 and cur is None and not title and j < len(lines) and _TOC.match(lines[j]):
                title = name
            else:
                if level == 1:
                    parent_name = name
                cur = Section(heading=name, level=level, empty_blocks=pending_empty,
                              parent=parent_name if level == 2 else "")
                sections.append(cur)
            pending_empty = 0
            i += 1
            continue
        if _EMPTY.match(line):
            pending_empty += 1
            i += 1
            continue
        if _TOC.match(line) or not line.strip():
            i += 1
            continue
        if cur is not None:
            imgs = validate._IMAGE_ANY.findall(line)
            if imgs:
                cur.images += [_norm(alt) for alt, _ in imgs]
                line = validate._IMAGE_ANY.sub("", line)
            prose = _norm(re.sub(r"^\s*[-*+]\s+", "", line))
            cur.sentences += [s for s in _SENT_SPLIT.split(prose) if len(s) >= 5]
        i += 1
    ref_lines, _ = validate._reference_block(body)
    refs = [_norm(re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", e))
            for e in validate._reference_entries(ref_lines)]
    return ReportShape(title=title, sections=sections, references=refs)


def _key(s):
    return (s.parent, s.heading)


def _pair_sections(a, b):
    """(대절 이름, 소절 이름) 으로 짝짓는다. 같은 이름의 소절이 대절마다 하나씩 있는
    문서(실험 결과·실험 사진)라 대절을 붙여야 짝이 유일하다. 누락·추가는 structure 의
    헤딩 수열 차이가 알린다."""
    by_key = {}
    for s in b:
        by_key.setdefault(_key(s), s)
    return [(s, by_key.get(_key(s))) for s in a]


def _structure(a: ReportShape, b: ReportShape) -> list:
    out = []
    ha, hb = [f"{'#' * s.level} {s.heading}" for s in a.sections], \
             [f"{'#' * s.level} {s.heading}" for s in b.sections]
    if ha != hb:
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ha, b=hb).get_opcodes():
            if tag == "equal":
                continue
            out.append(f"헤딩 {tag}: 원본 {ha[i1:i2]} / 재생성 {hb[j1:j2]}")
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        if len(x.tables) != len(y.tables):
            out.append(f"절 '{x.heading}': 표 {len(x.tables)}개 / 재생성 {len(y.tables)}개")
        for k, (tx, ty) in enumerate(zip(x.tables, y.tables), 1):
            if len(tx[1]) != len(ty[1]):
                out.append(f"절 '{x.heading}' 표 {k}: 행 {len(tx[1])} / 재생성 {len(ty[1])}")
        if x.images != y.images:
            out.append(f"절 '{x.heading}': 그림 {x.images} / 재생성 {y.images}")
        if x.empty_blocks != y.empty_blocks:
            out.append(f"절 '{x.heading}': 앞 여백 블록 {x.empty_blocks} / 재생성 {y.empty_blocks}")
    return out


def _cells(a: ReportShape, b: ReportShape) -> list:
    out = []
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        for k, (tx, ty) in enumerate(zip(x.tables, y.tables), 1):
            grid_x = [tx[0]] + tx[1]
            grid_y = [ty[0]] + ty[1]
            for r, (rx, ry) in enumerate(zip(grid_x, grid_y)):
                for c, (cx, cy) in enumerate(zip(rx, ry), 1):
                    if cx != cy:
                        where = "헤더" if r == 0 else f"행{r}"
                        out.append(f"절 '{x.heading}' 표 {k} {where} 열{c}: 원본 '{cx}' / 재생성 '{cy}'")
                if len(rx) != len(ry):
                    out.append(f"절 '{x.heading}' 표 {k} 행{r}: 셀 {len(rx)}개 / 재생성 {len(ry)}개")
    return out


def _references(a: ReportShape, b: ReportShape) -> list:
    ca, cb = Counter(a.references), Counter(b.references)
    out = [f"원본에만 — {r}" for r in (ca - cb).elements()]
    out += [f"재생성에만 — {r}" for r in (cb - ca).elements()]
    return out


# 문장이 달라도 사실이 같으면 같은 보고서다 — 그래서 문장이 아니라 토큰을 센다.
# 수치+단위, IC 이름, 벡터 집합, 입력 조건, 핀 번호, 고착 표기, (미확인).
_FACT = re.compile(
    r"\d+(?:\.\d+)?(?:V|mA|μA|µA|Ω|kΩ|ns/V|ns|°C)"
    r"|74[A-Z]*\d{2,3}"
    r"|\{[01,\s]+\}"
    r"|[A-Z]=(?:[A-Z]=)*[01]"          # A=1, A=B=1, C=0
    r"|\d+번 핀|핀\s?\d+"
    r"|고착-[01]"
    r"|\(미확인\)")
_PIN_KO = re.compile(r"^(\d+)번 핀$")


def fact_tokens(sentences) -> Counter:
    """`1번 핀` 과 `핀 1` 은 같은 사실이라 `핀 1` 로 모은다."""
    c = Counter()
    for s in sentences:
        for tok in _FACT.findall(s):
            tok = re.sub(r"\s+", " ", tok).strip()
            m = _PIN_KO.match(tok)
            if m:
                tok = f"핀 {m.group(1)}"
            c[tok] += 1
    return c


def _facts(a: ReportShape, b: ReportShape) -> list:
    out = []
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        cx, cy = fact_tokens(x.sentences), fact_tokens(y.sentences)
        only_x = sorted((cx - cy).items())
        only_y = sorted((cy - cx).items())
        if only_x or only_y:
            fmt = lambda items: ", ".join(f"{t}×{n}" if n > 1 else t for t, n in items) or "—"
            out.append(f"절 '{x.heading}': 원본에만 {fmt(only_x)} / 재생성에만 {fmt(only_y)}")
    return out


def _wording(a: ReportShape, b: ReportShape) -> list:
    out = []
    for x, y in _pair_sections(a.sections, b.sections):
        if y is None:
            continue
        sx, sy = set(x.sentences), set(y.sentences)
        union = sx | sy
        j = (len(sx & sy) / len(union)) if union else 1.0
        out.append(f"절 '{x.heading}': 문장 일치율 {j:.2f} (원본 {len(sx)} / 재생성 {len(sy)} / 공통 {len(sx & sy)})")
    return out


def compare_reports(approved_text: str, regen_text: str) -> dict:
    a, b = report_shape(approved_text), report_shape(regen_text)
    return {
        "structure": _structure(a, b),
        "cell": _cells(a, b),
        "references": _references(a, b),
        "style": [f.message for f in validate.check_body_style(regen_text)],
        "fact": _facts(a, b),
        "wording": _wording(a, b),
    }


def counted(diffs: dict) -> int:
    return sum(len(v) for k, v in diffs.items() if k != "wording")


_ROOT = Path(__file__).resolve().parents[2]   # scripts/lab/report_compare.py → 저장소 루트


def approved_report_path(experiment: int) -> Path:
    """승인본 경로. 저장소 루트 기준 절대경로라 어느 CWD 에서 불러도 같다."""
    return (_ROOT / config.experiment_dir(experiment) / "output"
            / f"{config.experiment_folder_name(experiment)}_결과보고서.md")


def judgment_markdown(experiment: int, regen_md, leak_hits=(), agent_report: str = "") -> str:
    """판정 초안. 도구가 셀 수 있는 것만 센다 — `fact` 의 세 갈래 분류(규칙 없음 /
    검사 없음 / 환경)와 산문은 사람이 원본과 나란히 읽고 표시한다."""
    leak_hits = list(leak_hits)
    approved = approved_report_path(experiment).read_text(encoding="utf-8")
    regen = Path(regen_md).read_text(encoding="utf-8")
    d = compare_reports(approved, regen)
    L = [f"# 실험{experiment} 결과보고서 격리 재생성 판정 초안", "",
         "이 회차는 세션 메모리 주입 아래서 돌았다.", "",
         f"## 1. 구조 {len(d['structure'])}건"] + [f"- {x}" for x in d["structure"]]
    L += ["", f"## 2. 표 셀 {len(d['cell'])}건"] + [f"- {x}" for x in d["cell"]]
    L += ["", f"## 3. 참고문헌 {len(d['references'])}건"] + [f"- {x}" for x in d["references"]]
    L += ["", f"## 4. 문체 {len(d['style'])}건 (재생성물, `check_body_style`)"] + [f"- {x}" for x in d["style"]]
    L += ["", f"## 5. 사실 토큰 {len(d['fact'])}건 — 한 줄마다 하나에 표시한다"]
    L += [f"- {x}\n    - [ ] 규칙 없음  [ ] 검사 없음  [ ] 환경(데이터시트 못 열음 등)" for x in d["fact"]]
    L += ["", "## 6. 산문 일치율 (기준 밖 — 나란히 읽는다)"] + [f"- {x}" for x in d["wording"]]
    L += ["", "사람이 볼 것:",
          "- 사실 토큰 차이마다 위 세 칸 중 하나에 표시한다. `규칙 없음`·`검사 없음` 만 규칙 제안의 재료다.",
          "- 산문은 절마다 원본과 나란히 읽는다 — 사실이 같고 문장만 다른 것은 결함이 아니다.",
          "- 에이전트 보고 3항(⑤ 첫 실행 error/warn/info)으로 **규칙이 막았나 / 검사가 잡았나** 를 가른다.",
          "", f"## 7. 구조적 누출 {len(leak_hits)}건"] + [f"- {x}" for x in leak_hits]
    L += ["", "> 구조 대조가 0건이라는 것은 같은 틀이라는 뜻이고, 같은 보고서라는 뜻이 아니다.", ""]
    if agent_report:
        L += ["## 에이전트 보고 (원문)", "", agent_report, ""]
    return "\n".join(L)
