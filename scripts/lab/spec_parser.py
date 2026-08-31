"""`명세.md` → `LabSpec`. 필드 계약은 `docs/schema/lab-spec-v1.md` 가 정본이다.

이 파서는 **표현할 수 없는 것에만** 예외를 던진다 (알 수 없는 kind, 표 누락,
없는 표를 가리키는 항목). `source` 누락·`encoding` 누락 같은 의미 결함은
`validate.py` 가 findings 로 보고한다 — 반쯤 망가진 명세도 검토는 되어야 한다.
"""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import md

KINDS = ("truth-table", "stepped", "capture")
ENCODINGS = ("0/1", "H/L")
ROLES = ("record", "reference")

_T_HEAD = re.compile(r"^##\s+(T\d+)\s*·\s*(.+?)\s*$", re.M)
_DERIVED = re.compile(r"^derived\s*\((.+)\)\s*$", re.S)
_ASSIGN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$", re.S)
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_ATTR = re.compile(r"^-\s+([a-z_]+)\s*:\s*(.*)$")


class SpecError(ValueError):
    """명세를 구조적으로 읽을 수 없을 때."""


@dataclass
class SpecTable:
    id: str
    title: str
    kind: str
    encoding: Optional[str]
    source: Optional[str]
    expected: Optional[str]
    role: str            # "record" | "reference"
    header: list
    rows: list
    line: int


@dataclass
class SpecItem:
    id: str
    title: str
    device: list
    ics: list
    tables: list


@dataclass
class LabSpec:
    week: int
    experiment: int
    title: str
    source_manual: str
    power: dict
    items: list
    tables: list
    path: Path

    def table(self, table_id):
        for t in self.tables:
            if t.id == table_id:
                return t
        return None


def _attrs(block: str) -> dict:
    """`- key: value` 속성 목록을 읽는다. 들여쓴 줄은 앞 값에 이어 붙인다."""
    out, key = {}, None
    for line in block.split("\n"):
        if line.lstrip().startswith("|"):
            break
        m = _ATTR.match(line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif key and line.startswith("  ") and line.strip():
            out[key] = (out[key] + " " + line.strip()).strip()
        elif not line.strip():
            key = None
    return out


def _parse_table(table_id, title, block, path) -> SpecTable:
    attrs = _attrs(block)
    kind = attrs.get("kind")
    if kind not in KINDS:
        raise SpecError(
            f"{path}: {table_id} 의 kind 가 {kind!r} 입니다. 허용: {', '.join(KINDS)}"
        )
    found = md.parse_tables(block)
    if kind == "capture":
        if found:
            # 버리면 아무도 못 잡는다 — LabSpec 이 만들어지는 순간 증거가 사라진다.
            raise SpecError(
                f"{path}: {table_id} 는 capture 인데 마크다운 표가 {len(found)}개 있다. "
                "capture 표는 셀 표 대신 expected 산문을 갖는다"
            )
        header, rows, line = [], [], 0
    else:
        if not found:
            raise SpecError(f"{path}: {table_id}({kind}) 에 마크다운 표가 없습니다")
        header, rows, line = found[0].header, found[0].rows, found[0].line
    dup = sorted(c for c, n in Counter(header).items() if n > 1)
    if dup:
        raise SpecError(
            f"{path}: {table_id} 의 헤더에 같은 이름의 열이 두 번 있다: {dup}. "
            "`header.index()` 가 조용히 첫 번째만 주므로 역검산이 엉뚱한 열을 "
            "본다 — 교안이 입력과 출력에 같은 글자를 쓰는 실물이 있다"
            "(실험3 반감산기 `A B D B`). 출력 쪽 이름을 구분해 적고, 그 자리에 "
            "교안 표기를 밝힌다"
        )
    return SpecTable(
        id=table_id, title=title, kind=kind,
        encoding=attrs.get("encoding"), source=attrs.get("source"),
        expected=attrs.get("expected"), role=attrs.get("role", "record"),
        header=header, rows=rows, line=line,
    )


def parse_spec(path) -> LabSpec:
    path = Path(path)
    front, body = md.split_frontmatter(path.read_text(encoding="utf-8"))
    if front.get("schema") != "lab-spec/v1":
        raise SpecError(
            f"{path}: schema 가 lab-spec/v1 이 아닙니다 ({front.get('schema')!r})"
        )
    for required in ("week", "experiment", "title", "source_manual", "power", "items"):
        if front.get(required) is None:
            raise SpecError(f"{path}: 프론트매터에 {required} 가 없습니다")

    heads = list(_T_HEAD.finditer(body))
    tables = []
    for n, m in enumerate(heads):
        end = heads[n + 1].start() if n + 1 < len(heads) else len(body)
        tables.append(_parse_table(m.group(1), m.group(2), body[m.end():end], path))

    seen = set()
    for t in tables:
        if t.id in seen:
            raise SpecError(
                f"{path}: 표 ID {t.id} 가 두 번 정의됐다. "
                "ID 는 문서 전체에서 유일해야 한다 (`.table()` 이 조용히 첫 번째만 준다)"
            )
        seen.add(t.id)

    known = {t.id for t in tables}
    items = []
    seen_items = set()
    for raw in front["items"]:
        for required in ("id", "title", "device", "ics", "tables"):
            if raw.get(required) is None:
                raise SpecError(f"{path}: 항목 {raw.get('id')!r} 에 {required} 가 없습니다")
        if raw["id"] in seen_items:
            raise SpecError(
                f"{path}: 항목 ID {raw['id']} 가 두 번 정의됐다. "
                "ID 는 문서 전체에서 유일해야 한다 (`specdiff.compare_specs` 의 "
                "`{i.id: i for i in items}` 가 나중 것만 남기고 앞 항목을 조용히 "
                "지운다)"
            )
        seen_items.add(raw["id"])
        missing = [t for t in raw["tables"] if t not in known]
        if missing:
            raise SpecError(
                f"{path}: 항목 {raw['id']} 가 없는 표 {missing} 를 가리킵니다. "
                f"정의된 표: {sorted(known)}"
            )
        items.append(SpecItem(id=raw["id"], title=raw["title"],
                              device=raw["device"], ics=raw["ics"], tables=raw["tables"]))

    return LabSpec(week=front["week"], experiment=front["experiment"],
                   title=front["title"], source_manual=front["source_manual"],
                   power=front["power"], items=items, tables=tables, path=path)


def derived_parts(table):
    """`source: derived (...)` 의 출력별 `(이름, 식)` 목록. 아니면 빈 리스트.

        derived (Y = A·B·C)                     -> [("Y", "A·B·C")]
        derived (X = A+B ; Y = A' ; Z = (A·B)') -> 쌍 3개

    한 표가 출력을 여럿 갖는 경우가 실재한다 (실험1 p13 복합회로).
    """
    m = _DERIVED.match((table.source or "").strip())
    if not m:
        return []
    pairs = []
    for chunk in m.group(1).split(";"):
        assign = _ASSIGN.match(chunk)
        if not assign:
            return []          # 형식이 깨졌다 — validate 가 findings 로 잡는다
        pairs.append((assign.group(1), assign.group(2)))
    return pairs


def split_columns(table):
    """표의 (입력 컬럼, 출력 컬럼).

    `derived` 식이 있으면 식이 참조하는 컬럼이 입력, 대입 대상이 출력이다.
    없으면 마지막 열 하나를 출력으로 본다 — 확인 칸을 어디에 둘지 정하는 데 쓴다.
    """
    pairs = derived_parts(table)
    if pairs:
        targets = [name for name, _ in pairs]
        referenced = set()
        for _, expr in pairs:
            referenced |= set(_NAME.findall(expr))
        inputs = [c for c in table.header if c in referenced and c not in targets]
        if inputs:
            outputs = [c for c in table.header if c in targets]
            return inputs, outputs or [c for c in table.header if c not in inputs]
    if len(table.header) < 2:
        return list(table.header), []
    return list(table.header[:-1]), [table.header[-1]]
