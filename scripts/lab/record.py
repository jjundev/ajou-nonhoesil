"""`LabSpec` → `기록.md`. 사람이 채워도 되고 vision 이 채워도 된다.

확인 칸 규약:
    ✓        예상값과 일치
    <값>     불일치 — 실제로 관찰한 값을 적는다
    (공란)   아직 확인하지 않음
표 전체를 진행하지 않았으면 표 아래에 `- 실험을 진행하지 않았음.` 을 적는다.

kind 마다 칸의 뜻이 다르다:
    truth-table  입력은 주어지고, 출력에 `예상` 을 병기한 뒤 확인 칸을 붙인다
    stepped      스텝·조작은 주어지고, 명세에서 **비어 있는 열**이 채울 칸이다.
                 확인 칸을 붙이지 않는다 — 대조할 예상값이 없다
    capture      셀 표가 아니라 스케치 격자 + 캡션 줄

`role: reference` 인 표는 건너뛴다. 교안에서 그대로 옮긴 참조표라 학생이
배선하지도 채우지도 않는다 (실험1 의 2입력 이론표 T6~T9). 확인 칸을 만들면
"2입력 AND 이론표를 실험실에서 채우시오" 라는 무의미한 빈 칸이 나온다.
"""

import datetime
import re
import unicodedata
from pathlib import Path

from .spec_parser import split_indices
from . import config, md
from .comparison import comparison_rows, GUIDE

PROMPTS = ("막혔던 것", "예상과 달랐던 것", "뭘 바꿔서 해결했나", "새로 안 것")

# 파생이 내는 고정 산문. 파생의 재료이자 "사람이 덧쓴 줄" 의 판별 기준이다 —
# 표도 목록도 아닌 맨 산문 줄이 여기 없으면 파생이 만든 줄이 아니다.
INTRO = (
    "진리표 — 확인 칸: `✓` 일치 / 값 = 불일치 시 실제 관찰값 / 공란 = 미확인.",
    "스텝표 — 빈 칸에 읽은 값을 **단위와 함께** 적는다. 확인 칸이 없다.",
    "파형 — 스케치에 그리고 판독 조건 줄을 채운다.",
    GUIDE,
    "표를 통째로 진행하지 않았으면 그 표 아래에 `- 실험을 진행하지 않았음.` 을 적는다.",
)

SKETCH_PLACEHOLDER = "스케치 — 파형을 여기에 그린다"
READING_LINE = ("- 판독 조건: CH1 __ V/div · CH2 __ V/div · time/div __ · "
                "프로브 __× · 모드 Y-T / X-Y")
# 콜론 뒤를 비운 채 파생되는 줄. 뒤가 채워져 있으면 사람이 적은 것이다.
BLANK_LABELS = ("메모", "캡션", "사진 파일", "예상과 다른 점") + PROMPTS
NOT_RUN = "실험을 진행하지 않았음"
CHECK_HEADER = "확인"
# `filled_by` 에 적혀도 "아직 안 채웠다" 는 뜻인 값들. 템플릿의 `~` 는 `md` 가
# `None` 으로 읽고, 주석에 보기로 적힌 `미기입` 을 그대로 옮겨 적는 사람도 있다.
UNFILLED_BY = (None, "", "~", "미기입")


def _width(text: str) -> int:
    """한글·한자는 2칸을 차지한다. 손으로 채울 표라 정렬이 실제로 중요하다."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, target: int) -> str:
    return text + " " * max(0, target - _width(text))


def _grid(header, rows) -> str:
    widths = [max([_width(header[i])] + [_width(r[i]) for r in rows])
              for i in range(len(header))]
    lines = ["| " + " | ".join(_pad(h, widths[i]) for i, h in enumerate(header)) + " |",
             "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    lines += ["| " + " | ".join(_pad(c, widths[i]) for i, c in enumerate(r)) + " |"
              for r in rows]
    return "\n".join(lines)


def _truth_table(table) -> str:
    # 셀은 이름이 아니라 자리로 찾는다 — 입력과 출력이 같은 글자인 표가 있다
    # (실험3 반감산기 `A B D B`). 출력에 `예상` 이 붙어 기록에서는 갈린다.
    inputs, outputs = split_indices(table)
    header = ([table.header[i] for i in inputs]
              + [f"{table.header[i]}예상" for i in outputs] + ["확인"])
    rows = [[row[i] for i in inputs] + [row[i] for i in outputs] + [""]
            for row in table.rows]
    return _grid(header, rows)


def _stepped(table, leds=()) -> str:
    """명세에서 비어 있는 열이 실험실에서 채울 칸이다.

    `예상` 도 `확인` 도 붙이지 않는다. `확인` 은 "✓ 일치 / 값 = 불일치" 규약이라
    **예상값이 있어야** 뜻이 있는데 스텝표에는 없다. 인쇄본(`render._stepped_html`)
    이 같은 이유로 뺐다 — 두 문서는 쌍이라 규약이 갈리면 전사에서 어긋난다.

    빈 열이 하나도 없는 표에만 `기록` 열을 만든다.
    """
    if getattr(table, 'comparison', None):
        header, rows = comparison_rows(table, leds)
        return _grid(header, rows)
    header = list(table.header)
    rows = [list(row) for row in table.rows]
    if not any(not c.strip() for row in rows for c in row):
        header.append("기록")
        rows = [row + [""] for row in rows]
    return _grid(header, rows)


def _capture(table) -> str:
    """파형은 셀 표가 아니다. 판독 조건을 함께 적는다 — V/div 를 모르면
    결과보고서에서 화면의 칸을 볼트로 환산할 수 없다."""
    return (f"> 예상: {table.expected or '(명세에 expected 가 없다)'}\n\n"
            f"```\n  {SKETCH_PLACEHOLDER}\n\n\n\n\n```\n\n"
            f"{READING_LINE}\n"
            "- 캡션:\n- 사진 파일:\n- 예상과 다른 점:")


_RENDER = {"truth-table": _truth_table, "stepped": _stepped, "capture": _capture}


def derive_record(spec) -> str:
    comparison_leds = ()
    if any(getattr(t, 'comparison', None) for t in spec.tables):
        from .netlist_parser import parse_netlist
        from .leds import board_leds
        path = spec.path.parent.parent / '결선도' / 'netlist.md'
        if path.exists():
            netlist = parse_netlist(path)
            comparison_leds = {c.item: board_leds(path.parent / c.diagram)
                               for c in netlist.circuits if c.diagram}
    out = [
        "---", "schema: lab-record/v2",
        f"experiment: {spec.experiment}", "spec: 명세.md",
        "filled_by: ~          # hand | vision | 미기입", "---", "",
        f"# {config.document_title(spec.experiment, spec.title, '기록')}", "",
        *[line for line in INTRO if (line != GUIDE or any(getattr(t, "comparison", None) for t in spec.tables))
          and not (line.startswith("스텝표 —") and all(getattr(t, "comparison", None) for t in spec.tables))], "",
    ]
    for item in spec.items:
        out += [f"## {item.id} · {item.title}",
                f"IC: {', '.join(item.ics)} · 판독: {', '.join(item.device)}", ""]
        for table_id in item.tables:
            table = spec.table(table_id)
            if table.role == "reference":
                continue          # 교안 참조표다. 실험실에서 채우지 않는다
            if getattr(table, 'comparison', None) and table.outputs == [f'BIT{i}' for i in range(1,7)]:
                out += ["> 실제 여섯 비트는 BIT1→BIT6 이름 순서로 적는다. 1=켜짐, 0=소등. 예: 001101.", ""]
            out += [f"### {table.id} · {table.title}", ""]
            if getattr(table, "purpose", None):
                out += ["\n".join("> " + line for line in table.purpose.splitlines()), ""]
            out += [(_stepped(table, comparison_leds.get(item.id, ()) if comparison_leds else ())
                     if getattr(table, "comparison", None) else _RENDER[table.kind](table)), "", "- 메모:", ""]
    out += ["# 실험 종료 메모", ""] + [f"- {p}:" for p in PROMPTS] + [""]
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────
# 채워진 기록 보호
#
# 파생은 항상 **빈** 템플릿을 낸다. 그래서 체크리스트를 다시 뽑는 것만으로
# 실험 당일에만 알 수 있는 값이 통째로 사라질 수 있다 — 2026-09-20 실험03
# 재생성이 `filled_by: vision` · 확인 칸 16개 · 종료 메모 4문항을 덮었다.
# 작업자가 알아채고 `git checkout` 으로 되돌렸지만, 못 봤으면 조용히 없어졌다.
#
# 그래서 쓰기는 `write_record` 한 곳을 지난다. 판정은 `filled_by` 가 아니라
# **실제로 채워진 자리**로 한다 (④ 결과보고서 스킬과 같은 규칙) — 메타데이터는
# 갱신을 잊을 수 있어도 빈 칸은 거짓말을 못 한다.

_LABEL = re.compile(r"^- ([^:]+):[ \t]*(.*)$")
_HEADING = re.compile(r"^#{1,6} +(\S+)")
_FENCE = re.compile(r"^\s*```")


class RecordExistsError(Exception):
    """이미 채워진 `기록.md` 를 덮으려 했다."""


def _tables_by_id(body: str) -> dict:
    """표를 바로 앞 `### <표ID> ·` 제목에 묶는다. 제목이 없는 표는 버린다."""
    lines = body.split("\n")
    heads = {}
    for i, line in enumerate(lines, start=1):
        m = _HEADING.match(line)
        if m:
            heads[i] = m.group(1)
    out = {}
    for table in md.parse_tables(body):
        prior = [i for i in heads if i < table.line]
        if prior:
            out.setdefault(heads[max(prior)], table)
    return out


def _filled_cells(table, blank_cell) -> int:
    """`blank_cell(row_index, column_index)` 이 참인 자리 중 채워진 칸 수."""
    return sum(1 for r, row in enumerate(table.rows)
               for c, cell in enumerate(row)
               if cell.strip() and blank_cell(r, c))


def record_marks(text: str, template: str = None) -> list:
    """`text` 에서 사람이 남긴 흔적을 찾아 사람이 읽을 근거 목록으로 낸다.

    빈 목록이면 손대지 않은 템플릿이다 — 그때만 덮어써도 잃을 것이 없다.

    `template` 을 주면 그 템플릿에서 **비어 있던** 칸까지 본다. 스텝표는
    확인 열이 없고 명세가 비워 둔 열이 기록 칸이라, 템플릿 없이는 어느 칸이
    기록인지 알 수 없다 (실험02 는 진리표가 아예 없어 확인 칸도 0 개다).
    """
    try:
        front, body = md.split_frontmatter(text)
    except ValueError:
        # 프론트매터가 깨진 파일은 누군가 손으로 만진 것이다. 판정을 포기하고
        # 보호하는 쪽으로 기운다 — 조용히 덮는 것보다 시끄럽게 멈추는 게 낫다.
        return ["프론트매터를 읽을 수 없다 (`---` 짝이 맞지 않음)"]

    marks = []
    filled_by = front.get("filled_by")
    if filled_by is not None and str(filled_by).strip() not in UNFILLED_BY:
        marks.append(f"프론트매터 `filled_by: {filled_by}`")

    tmpl_tables = _tables_by_id(md.split_frontmatter(template)[1]) if template else {}
    checks = cells = 0
    for tid, table in _tables_by_id(body).items():
        check_cols = {i for i, h in enumerate(table.header)
                      if h.strip() in (CHECK_HEADER, "실제 결과")}
        checks += _filled_cells(table, lambda r, c: c in check_cols)
        tmpl = tmpl_tables.get(tid)
        if template and (tmpl is None or tmpl.header != table.header):
            marks.append(f"{tid}: 기존 기록과 템플릿의 표 머리가 달라 기록 보존이 필요하다")
        if tmpl is None or tmpl.header != table.header:
            continue      # 명세가 바뀌어 짝이 안 맞는다. 확인 열까지만 본다
        if len(table.rows) != len(tmpl.rows) or any(
                len(row) != len(tmpl.rows[r]) for r, row in enumerate(table.rows)
                if r < len(tmpl.rows)):
            marks.append(f"{tid}: 기존 기록의 행·셀 구조가 템플릿과 달라 기록 보존이 필요하다")
        elif any(cell.strip() != tmpl.rows[r][c].strip()
                 for r, row in enumerate(table.rows) for c, cell in enumerate(row)
                 if tmpl.rows[r][c].strip() and c not in check_cols):
            marks.append(f"{tid}: 기존 기록의 고정 입력·조작·예상값이 달라 기록 보존이 필요하다")
        cells += _filled_cells(
            table,
            lambda r, c: (c not in check_cols and r < len(tmpl.rows)
                          and c < len(tmpl.rows[r]) and not tmpl.rows[r][c].strip()))
    if checks:
        marks.append(f"확인 칸 {checks}개")
    if cells:
        marks.append(f"기록 칸 {cells}개")

    labels, prompts, sketches, prose, not_run = [], [], 0, 0, 0
    fenced = False
    for line in body.split("\n"):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            if line.strip() and line.strip() != SKETCH_PLACEHOLDER:
                sketches += 1
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if NOT_RUN in stripped:
            # 고정 산문 넷째 줄이 이 표기를 **설명**한다. 본문 전체에서 세면
            # 손대지 않은 템플릿이 자기 안내문 때문에 채워진 것으로 보인다.
            not_run += stripped not in INTRO
            continue
        m = _LABEL.match(line)
        if m:
            label, value = m.group(1).strip(), m.group(2).strip()
            if label in PROMPTS and value:
                prompts.append(label)
            elif label in BLANK_LABELS and value:
                labels.append(label)
            elif label == "판독 조건" and stripped != READING_LINE:
                labels.append(label)
            continue
        if (stripped.startswith(("#", "|", ">", "IC:"))
                or stripped in INTRO):
            continue
        prose += 1      # 표도 목록도 아닌 산문. 파생은 이런 줄을 만들지 않는다
    if labels:
        marks.append(f"메모·캡션 줄 {len(labels)}개")
    if prompts:
        marks.append(f"종료 메모 {len(prompts)}문항")
    if sketches:
        marks.append(f"스케치 {sketches}줄")
    if prose:
        marks.append(f"덧쓴 산문 {prose}줄")
    if not_run:
        marks.append(f"`{NOT_RUN}` 표시 {not_run}개")
    return marks


def backup_path(path, now=None) -> Path:
    """`기록.md` → `기록.md.bak-20260920-143102`. 같은 초에 두 번이면 번호를 붙인다."""
    path = Path(path)
    stamp = (now or datetime.datetime.now()).strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.name}.bak-{stamp}")
    n = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak-{stamp}-{n}")
        n += 1
    return candidate


def write_record(path, text: str, *, force: bool = False, now=None, previous_template=None) -> dict:
    """`기록.md` 를 쓴다. **이미 채워진 기록은 덮지 않는다.**

    - 파일이 없으면 그냥 만든다 (`created`). 첫 체크리스트는 지금까지와 같다.
    - 손대지 않은 템플릿이면 다시 낸다 (`regenerated`). 명세가 고쳐졌을 때
      체크리스트를 다시 뽑는 평범한 경로다 — 잃을 것이 없다.
    - 흔적이 있으면 `RecordExistsError` 로 **거절한다**. 부르는 쪽(②)이 근거를
      사용자에게 보이고 판단을 받는다.
    - `force=True` 면 옮겨 적을 수 없는 판단이 섰다는 뜻이다. 그때도 지우지
      않고 `기록.md.bak-<시각>` 백업을 먼저 남긴 뒤 덮는다 (`overwritten`).

    `previous_template` 은 변경 전 명세에서 파생한 신뢰할 수 있는 이전 템플릿이다.
    형식 이행에서 기존 빈 기록을 확인할 때만 전달한다. 기존 파일 자체를 전달하지 않는다.

    `force` 는 **사용자가 그렇게 하라고 한 뒤에만** 준다. 스킬이 스스로 켜면
    이 가드는 없는 것과 같다.
    """
    path = Path(path)
    if not path.exists():
        path.write_text(text, encoding="utf-8")
        return {"status": "created", "backup": None, "marks": []}

    old = path.read_text(encoding="utf-8")
    marks = record_marks(old, previous_template if previous_template is not None else text)
    if not marks:
        path.write_text(text, encoding="utf-8")
        return {"status": "regenerated", "backup": None, "marks": []}
    if not force:
        raise RecordExistsError(
            f"{path} 는 이미 채워진 기록입니다 — 덮어쓰지 않았습니다.\n"
            + "".join(f"  · {m}\n" for m in marks)
            + "실험 당일에만 알 수 있는 값이라 파생으로 되살릴 수 없습니다. "
            "기록은 그대로 두고 체크리스트(html·pdf)만 다시 내면 됩니다.\n"
            "정말 빈 템플릿으로 되돌려야 한다면 사용자에게 확인을 받은 뒤 "
            f"`force=True` 로 다시 부르세요 — 그때는 `{path.name}.bak-<시각>` "
            "백업을 먼저 남깁니다."
        )
    backup = backup_path(path, now)
    backup.write_text(old, encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    return {"status": "overwritten", "backup": backup, "marks": marks}
