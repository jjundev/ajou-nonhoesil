"""`## 노드` 표 × 기록 진리표 → 회로 안 관측점(게이트 출력 핀)의 기대값.

용의자를 "선"이 아니라 "노드"로 좁히는 표다. 틀린 입력 행에서 입력 쪽 핀부터
프로브로 찍어 기대값과 처음 갈라지는 노드가 고장 자리이고, 용의자는 그 게이트와
그 게이트로 들어오는 두세 가닥뿐이다 (2026-09-20 디버깅 회고,
docs/plans/2026-09-20-중간노드-기대값표-설계.md).

`compute` 는 모든 노드 × 기록표 전 행이다 — `validate` 가 출력 노드를 명세 식과
대조하는 데 쓴다. `stage_table` 은 노드 하나 × 그 노드가 쓰는 입력만이다 — 체크리스트
단계 블록 안의 단계 진리표다 (docs/plans/2026-09-28-단계별-진리표-설계.md).
`stage_nodes_table` 은 그 여러 노드판이다 — 단계 LED 점등 표가 쓴다
(docs/plans/2026-10-11-체크리스트-LED-점등열-설계.md).

이 모듈은 `spec_parser`·`boolexpr`·`notation` 만 import 한다 — `validate` 가
`render` 를 import 하므로 둘이 공유하는 계산은 여기에 있어야 순환이 없다.
"""

from dataclasses import dataclass
from itertools import product

from .boolexpr import eval_boolean, variables
from .notation import DONT_CARE, bit_of, normalize_cell
from .spec_parser import split_indices


@dataclass
class NodeTable:
    inputs: list      # 입력 열 이름 (기록표 헤더 순서)
    nodes: list       # (노드 이름, 핀) — `## 노드` 표 순서
    rows: list        # 행마다 (입력 셀 문자열 리스트, 노드 비트 리스트 | None)
    encoding: str     # 기록표의 encoding — 셀은 이것으로 찍는다 (H/L ↔ 0/1 변환 금지)


@dataclass
class StageTable:
    inputs: list      # 이 노드 식에 나오는 입력 열 이름 (기록표 헤더 순서)
    node: tuple       # (노드 이름, 핀)
    rows: list        # 행마다 (입력 셀 문자열 리스트, 노드 비트 0/1) — 값이 정해진 행만
    encoding: str     # 기록표의 encoding


@dataclass
class StageNodesTable:
    inputs: list      # 노드 식들에 나오는 입력의 합집합 (기록표 헤더 순서)
    nodes: list       # (노드 이름, 핀) — 인자 순서
    rows: list        # 행마다 (입력 셀 문자열 리스트, [비트 0/1 | None, ...]) — 하나라도 정해진 행만
    encoding: str     # 기록표의 encoding


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
    expressions = [n for n in circuit.nodes if n.get("kind", "expression") == "expression"]
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
        for node in expressions:
            try:
                bits.append(eval_boolean(node["expr"], env))
            except ValueError as exc:
                raise ValueError(f"노드 {node['name']} 의 식 {node['expr']!r}: {exc}") from exc
        rows.append((cells, bits))
    return NodeTable(inputs=names,
                     nodes=[(n["name"], n["pin"]) for n in expressions],
                     rows=rows, encoding=table.encoding or "0/1")


def _settled(expr, fixed, free):
    """`free` 변수에 0·1 을 다 넣어도 값이 하나면 그 값, 갈리면 None."""
    values = {eval_boolean(expr, {**fixed, **dict(zip(free, combo))})
              for combo in product((0, 1), repeat=len(free))}
    return values.pop() if len(values) == 1 else None


def stage_nodes_table(circuit, spec, node_names) -> StageNodesTable:
    """단계 하나에서 볼 노드 여럿의 진리표 — 입력은 그 노드 식들에 나오는 것의 합집합.

    행은 기록표 행을 그 입력으로 줄여 겹치는 것을 합친 것이다(처음 나온 순서). 2^k 로
    전개하지 않는다 — 실험04 MUX 는 입력이 7개이고, 기록표가 저작자가 고른 시험 행이다.
    줄인 입력에 X 가 남으면 0·1 을 다 넣어 보고 값이 하나로 정해지는 노드만 비트를, 갈리는
    노드는 None 을 싣는다(MUX `E=1` 행은 NAND 출력이 1 로 정해진다). 정해지는 노드가 하나도
    없는 행과 0/1(H/L)도 X 도 아닌 셀의 행은 뺀다.

    입력 열은 이름이 아니라 `split_indices` 의 **자리**로 고른다 — 입력과 출력이 같은
    글자인 표가 있다(실험3 반감산기 `A B D B`).
    """
    for name in node_names:
        if any(n["name"] == name and n.get("kind") == "observed" for n in circuit.nodes):
            raise ValueError(f"observed 노드 {name} 는 부울식 계산 대신 확인 절차가 필요하다")
    table = record_table(circuit, spec)
    if table is None:
        raise ValueError(
            f"{circuit.id} 에 truth-table 기록표가 없다 — 단계 진리표는 입력 행이 있는 회로에만 둔다")
    picked = []
    for node_name in node_names:
        node = next((n for n in circuit.nodes if n["name"] == node_name), None)
        if node is None:
            raise ValueError(f"노드 {node_name!r} 가 {circuit.id} 의 `## 노드` 표에 없다")
        picked.append(node)
    inputs, _ = split_indices(table)
    names = [table.header[i] for i in inputs]
    used = set()
    for node in picked:
        try:
            node_vars = variables(node["expr"])
        except ValueError as exc:
            raise ValueError(f"노드 {node['name']} 의 식 {node['expr']!r}: {exc}") from exc
        missing = [v for v in node_vars if v not in names]
        if missing:
            raise ValueError(f"노드 {node['name']} 의 식 {node['expr']!r}: "
                             f"입력 변수 {missing} 이(가) 기록표 {table.id} 에 없다")
        used.update(node_vars)
    cols = [(name, i) for name, i in zip(names, inputs) if name in used]
    rows, seen = [], set()
    for row in table.rows:
        if len(row) != len(table.header):
            continue              # 셀 수 불일치는 check_table_integrity 몫이다
        cells = [str(normalize_cell(row[i])) for _, i in cols]
        if tuple(cells) in seen:
            continue
        seen.add(tuple(cells))
        fixed, free, settable = {}, [], True
        for (name, i), cell in zip(cols, cells):
            bit = bit_of(row[i], table.encoding)
            if bit is not None:
                fixed[name] = bit
            elif cell == DONT_CARE:
                free.append(name)
            else:
                settable = False
        if not settable:
            continue
        bits = []
        for node in picked:
            node_vars = set(variables(node["expr"]))
            try:
                bits.append(_settled(node["expr"], {k: v for k, v in fixed.items() if k in node_vars},
                                     [f for f in free if f in node_vars]))
            except ValueError as exc:
                raise ValueError(f"노드 {node['name']} 의 식 {node['expr']!r}: {exc}") from exc
        if any(b is not None for b in bits):
            rows.append((cells, bits))
    return StageNodesTable(inputs=[name for name, _ in cols],
                           nodes=[(n["name"], n["pin"]) for n in picked],
                           rows=rows, encoding=table.encoding or "0/1")


def stage_table(circuit, spec, node_name) -> StageTable:
    """단계 하나에서 볼 노드 하나의 진리표 — `stage_nodes_table` 의 노드 하나짜리에서 값이
    정해진 행만 남긴다.
    """
    t = stage_nodes_table(circuit, spec, [node_name])
    return StageTable(inputs=t.inputs, node=t.nodes[0],
                      rows=[(cells, bits[0]) for cells, bits in t.rows if bits[0] is not None],
                      encoding=t.encoding)


def format_bit(bit, encoding) -> str:
    """인쇄용. 표의 encoding 을 따른다 — 변환이 아니라 표기다."""
    if bit is None:
        return "—"
    if encoding == "H/L":
        return "H" if bit else "L"
    return "1" if bit else "0"
