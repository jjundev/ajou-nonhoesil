"""`명세.md` → `LabSpec`. 필드 계약은 `docs/schema/lab-spec-v2.md` 가 정본이다.

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
    outputs: Optional[list] = None   # `- outputs: [S, C]`. 없으면 None
    comparison: Optional[str] = None  # stepped opt-in: led
    figure: Optional[str] = None     # `- figure: ../output/x.png`. 명세 파일 위치 기준 상대경로


@dataclass
class SpecItem:
    id: str
    title: str
    device: list
    ics: list
    tables: list
    pages: Optional[list] = None   # 강의노트 쪽 번호 `[11]`. 없으면 None — 형태(양의 정수
                                    # 리스트)는 파서가 거절하고, 쪽 존재·이름 대조는 validate 몫
    schematic: Optional[list] = None   # 강의노트 회로도 PNG `[실험03_1-2_회로도.png]`. 명세 파일
                                        # 위치 기준 상대경로. 파일 존재는 validate 몫


@dataclass
class LabSpec:
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
    table = SpecTable(
        id=table_id, title=title, kind=kind,
        encoding=attrs.get("encoding"), source=attrs.get("source"),
        expected=attrs.get("expected"), role=attrs.get("role", "record"),
        header=header, rows=rows, line=line,
        outputs=_list_attr(attrs.get("outputs")),
        figure=attrs.get("figure") or None,
        comparison=attrs.get("comparison") or None,
    )
    # 교안이 입력과 출력에 같은 글자를 쓰는 실물이 있다(실험3 반감산기
    # `A B D B`). 진리표에서 입력 하나·출력 하나로 갈리면 자리로 가를 수
    # 있다 — `split_indices` 가 뒤의 것을 출력으로 본다. 그 밖의 중복은
    # 어느 열을 읽을지 정할 수 없어 거절한다.
    ins, outs = split_indices(table)
    dup = sorted(c for c, n in Counter(header).items() if n > 1 and not (
        kind == "truth-table" and n == 2
        and sum(header[i] == c for i in ins) == 1
        and sum(header[i] == c for i in outs) == 1))
    if dup:
        raise SpecError(
            f"{path}: {table_id} 의 헤더에 같은 이름의 열이 두 번 있다: {dup}. "
            "진리표에서 입력 하나·출력 하나로 갈릴 때만 자리로 가른다(실험3 "
            "반감산기 `A B D B` — 앞의 B 가 입력, 뒤의 B 가 출력이다). 같은 쪽에 "
            "두 번이거나 진리표가 아니면 어느 열을 읽을지 정할 수 없다"
        )
    return table


def _list_attr(value):
    """`[S, C]` → `["S", "C"]`. 속성이 없으면 None.

    헤더에 있는 이름인지는 보지 않는다 — 의미 결함이라 validate 가 잡는다.
    """
    if value is None:
        return None
    return [c.strip() for c in value.strip().strip("[]").split(",") if c.strip()]


def parse_spec(path) -> LabSpec:
    path = Path(path)
    front, body = md.split_frontmatter(path.read_text(encoding="utf-8"))
    if front.get("schema") != "lab-spec/v2":
        raise SpecError(
            f"{path}: schema 가 lab-spec/v2 가 아닙니다 ({front.get('schema')!r}). "
            "v1 은 `week:` 를 요구했다 — 일정은 이제 config.EXPERIMENT_DATES 한 곳에만 산다"
        )
    for required in ("experiment", "title", "source_manual", "power", "items"):
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
        pages = raw.get("pages")
        if pages is not None and (
                not isinstance(pages, list) or not pages
                or not all(isinstance(p, int) and not isinstance(p, bool) and p > 0
                           for p in pages)):
            raise SpecError(
                f"{path}: 항목 {raw['id']} 의 pages 는 쪽 번호(양의 정수) 리스트여야 한다 — "
                f"받은 값: {pages!r}"
            )
        schematic = raw.get("schematic")
        if schematic is not None and (
                not isinstance(schematic, list) or not schematic
                or not all(isinstance(s, str) and s.strip() for s in schematic)):
            raise SpecError(
                f"{path}: 항목 {raw['id']} 의 schematic 은 회로도 PNG 경로(문자열) 리스트여야 한다 — "
                f"받은 값: {schematic!r}"
            )
        items.append(SpecItem(id=raw["id"], title=raw["title"],
                              device=raw["device"], ics=raw["ics"], tables=raw["tables"],
                              pages=pages, schematic=schematic))

    return LabSpec(experiment=front["experiment"],
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


def split_indices(table):
    """표의 (입력 열 번호, 출력 열 번호). 둘 다 헤더 순서다.

    `derived` 식이 있으면 식이 참조하는 열이 입력, 대입 대상이 출력이다.
    없으면 `outputs` 선언을 따른다 — 교안 원문을 옮겨 `manual:pN` 으로 남아야
    하는 표가 출력이 둘일 때 쓴다(실험3 p4~p7). 둘 다 없으면 마지막 열 하나를
    출력으로 본다 — 확인 칸을 어디에 둘지 정하는 데 쓴다.

    **출력 이름이 헤더에 두 번 나오면 뒤의 것이 출력이다.** 교안이 입력과
    출력에 같은 글자를 쓰는 실물이 있다(실험3 반감산기 `A B D B`). 이름으로는
    두 `B` 를 가를 수 없으므로 셀을 읽는 곳은 이 번호를 쓴다 — `{이름: 번호}`
    로 찾으면 입력 `B` 칸에 출력 값이 찍힌다.
    """
    header = table.header

    def last(name):
        return max(i for i, c in enumerate(header) if c == name)

    pairs = derived_parts(table)
    if pairs:
        targets = [name for name, _ in pairs]
        referenced = set()
        for _, expr in pairs:
            referenced |= set(_NAME.findall(expr))
        outputs = sorted({last(n) for n in targets if n in header})
        inputs = [i for i, c in enumerate(header) if c in referenced and i not in outputs]
        if inputs:
            return inputs, outputs or [i for i in range(len(header)) if i not in inputs]
    declared = sorted({last(n) for n in (table.outputs or []) if n in header})
    if declared:
        return [i for i in range(len(header)) if i not in declared], declared
    if len(header) < 2:
        return list(range(len(header))), []
    return list(range(len(header) - 1)), [len(header) - 1]


def split_columns(table):
    """표의 (입력 컬럼, 출력 컬럼) 이름. 분할 규칙은 `split_indices` 가 정한다.

    같은 글자가 입력과 출력에 한 번씩 나올 수 있다(실험3 반감산기 →
    `(["A", "B"], ["D", "B"])`). 셀을 읽을 때는 이름 말고 `split_indices` 를 쓴다.
    """
    inputs, outputs = split_indices(table)
    return [table.header[i] for i in inputs], [table.header[i] for i in outputs]


def column_label(header, i):
    """열 번호 `i` 를 메시지용 이름으로. 한 표에 같은 이름이 둘 이상이면 자리를 붙인다.

    실험3 반감산기 `A B D B` 에서 넷째 열은 `B(4열)` 이다. 판정은 `split_indices` 로
    자리를 가르지만 메시지가 이름만 쓰면 입력 `B` 인지 출력 `B` 인지 갈리지 않는다.
    """
    name = header[i]
    return f"{name}({i + 1}열)" if header.count(name) > 1 else name
