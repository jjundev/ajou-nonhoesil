"""`## 노드` 표 × 기록 진리표 → 회로 안 관측점(게이트 출력 핀)의 기대값.

용의자를 "선"이 아니라 "노드"로 좁히는 표다. 틀린 입력 행에서 입력 쪽 핀부터
프로브로 찍어 기대값과 처음 갈라지는 노드가 고장 자리이고, 용의자는 그 게이트와
그 게이트로 들어오는 두세 가닥뿐이다 (2026-09-20 디버깅 회고,
docs/plans/2026-09-20-중간노드-기대값표-설계.md).

이 모듈은 `spec_parser`·`boolexpr`·`notation` 만 import 한다 — `validate` 가
`render` 를 import 하므로 둘이 공유하는 계산은 여기에 있어야 순환이 없다.
"""

from dataclasses import dataclass

from .boolexpr import eval_boolean
from .notation import bit_of, normalize_cell
from .spec_parser import split_indices


@dataclass
class NodeTable:
    inputs: list      # 입력 열 이름 (기록표 헤더 순서)
    nodes: list       # (노드 이름, 핀) — `## 노드` 표 순서
    rows: list        # 행마다 (입력 셀 문자열 리스트, 노드 비트 리스트 | None)
    encoding: str     # 기록표의 encoding — 셀은 이것으로 찍는다 (H/L ↔ 0/1 변환 금지)


def record_table(circuit, spec):
    """회로 `tables` 의 첫 기록 진리표. 없으면 None.

    둘 이상이면 입력 열이 첫 표와 같아야 한다 — 다른 입력 집합을 한 노드 표에 섞을 수
    없다. `role: reference` 는 교안 이론표라 제외하고, `stepped`·`capture` 는 입력 행이
    없어 제외한다.
    """
    tables = [spec.table(t) for t in circuit.tables]
    tables = [t for t in tables
              if t is not None and t.role != "reference" and t.kind == "truth-table"]
    if not tables:
        return None
    first = tables[0]
    inputs = [first.header[i] for i in split_indices(first)[0]]
    for t in tables[1:]:
        other = [t.header[i] for i in split_indices(t)[0]]
        if other != inputs:
            raise ValueError(
                f"{t.id} 의 입력 열 {other} 이 {first.id} 의 {inputs} 와 다르다 — "
                "노드 표는 입력 열이 같은 기록표에만 걸친다")
    return first


def compute(circuit, spec) -> NodeTable:
    """기록표의 입력 행마다 `## 노드` 표의 식을 전부 평가한다.

    입력에 don't-care 가 있는 행은 구체적 식으로 계산할 수 없어 `None` —
    `validate.check_boolean` 이 그런 행을 건너뛰는 것과 같은 이유다.
    """
    table = record_table(circuit, spec)
    if table is None:
        raise ValueError(
            f"{circuit.id} 에 truth-table 기록표가 없다 — 노드 표는 입력 행이 있는 회로에만 둔다")
    inputs, _ = split_indices(table)
    names = [table.header[i] for i in inputs]
    rows = []
    for row in table.rows:
        if len(row) != len(table.header):
            continue              # 셀 수 불일치는 check_table_integrity 몫이다
        cells = [str(normalize_cell(row[i])) for i in inputs]
        env = {}
        for name, i in zip(names, inputs):
            bit = bit_of(row[i], table.encoding)
            if bit is None:
                env = None
                break
            env[name] = bit
        if env is None:
            rows.append((cells, None))
            continue
        bits = []
        for node in circuit.nodes:
            try:
                bits.append(eval_boolean(node["expr"], env))
            except ValueError as exc:
                raise ValueError(f"노드 {node['name']} 의 식 {node['expr']!r}: {exc}") from exc
        rows.append((cells, bits))
    return NodeTable(inputs=names,
                     nodes=[(n["name"], n["pin"]) for n in circuit.nodes],
                     rows=rows, encoding=table.encoding or "0/1")


def format_bit(bit, encoding) -> str:
    """인쇄용. 표의 encoding 을 따른다 — 변환이 아니라 표기다."""
    if bit is None:
        return "—"
    if encoding == "H/L":
        return "H" if bit else "L"
    return "1" if bit else "0"
