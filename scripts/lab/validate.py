"""명세·결선도·보고서 검증. 예외를 던지지 않고 `Finding` 목록을 돌려준다.

⑤ `review-lab-report` 스킬이 이 모듈을 부른다. 검토는 반쯤 망가진 문서에도
동작해야 하므로, 여기서는 절대 예외로 중단하지 않는다.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import md
from .boolexpr import eval_boolean
from .notation import DONT_CARE, normalize_cell
from .spec_parser import derived_parts, split_columns

_BAD_CELL = {"\\|": "escape 된 파이프", "<br>": "<br> 태그", "\t": "탭 문자"}


@dataclass
class Finding:
    level: str   # "error" | "warn"
    where: str
    message: str

    def __str__(self):
        mark = "✗" if self.level == "error" else "!"
        return f"{mark} {self.where} — {self.message}"


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
        if t.role not in ("record", "reference"):
            out.append(Finding("error", where,
                f"role 이 {t.role!r} 이다. `record` 또는 `reference` 여야 한다"))
        if t.kind == "capture":
            if not t.expected:
                out.append(Finding("error", where,
                    "capture 표에 expected 산문이 없다 (예상값을 적을 곳이 여기다)"))
        elif t.encoding not in ("0/1", "H/L"):
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
        if not derived_parts(t):
            continue
        inputs, _ = split_columns(t)
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
            for i, row in enumerate(t.rows, start=1):
                if len(row) != len(t.header):
                    continue
                env, dont_care = {}, False
                for col, cell in zip(t.header, row):
                    bit = _bit(cell, t.encoding)
                    if bit is not None:
                        env[col] = bit
                    elif col in inputs and normalize_cell(cell) == DONT_CARE:
                        dont_care = True
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
                    out.append(Finding("error", where,
                        f"{target} 의 식 {expr!r} 을 평가할 수 없다: {exc}"))
                    break
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


def check_report_sections(report_path, sections) -> list:
    """`.claude/보고서양식.md` 기준으로 섹션 유무·순서를 본다.

    하드코딩된 목차와 대조하지 않는다 — 양식이 연도마다 다르기 때문이다 (R1).
    """
    path = Path(report_path)
    if not path.exists():
        return [Finding("error", str(report_path), "보고서 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    headings = [re.sub(r"^#+\s*(?:\d+[.)]\s*)?", "", ln).strip()
                for ln in text.split("\n") if ln.startswith("#")]
    out, last = [], -1
    for sec in sections:
        if not sec.generate:
            continue
        pos = next((i for i, h in enumerate(headings) if sec.name in h), None)
        if pos is None:
            out.append(Finding("error", path.name, f"양식이 요구하는 섹션 '{sec.name}' 이 없다"))
            continue
        if pos < last:
            out.append(Finding("warn", path.name,
                f"섹션 '{sec.name}' 의 순서가 양식과 다르다"))
        last = max(last, pos)
    return out
