"""Authored observation protocols, independent of circuit-state simulation.

The parser owns structure. This module validates meaning and adapts the existing
combinational calculator without evaluating observed nodes or merging time rows.
"""
import re
from dataclasses import dataclass
from . import nodes


class ObservationError(ValueError):
    pass


def point_kind(node: dict) -> str:
    return node.get('kind', 'expression')


def points(section) -> dict[str, dict]:
    result, pins = {}, set()
    for node in section.nodes:
        pin = ' '.join(node['pin'].split())
        if node['name'] in result or pin in pins:
            raise ObservationError(f"관측점 이름 또는 핀 중복: {node['name']} ({pin})")
        result[node['name']] = node
        pins.add(pin)
    return result


def procedure_for_stage(section, stage: dict):
    ident = stage.get('procedure')
    if not ident:
        return None
    found = [p for p in section.procedures if p.id == ident]
    if len(found) != 1:
        raise ObservationError(f"{section.id} 에 확인 절차 {ident} 가 없거나 중복됐다")
    return found[0]


def procedure_issues(section, procedure) -> list[tuple[int, str]]:
    p = procedure
    issues = []
    def issue(message, line=None):
        issues.append((line or p.line, f'{p.id}: {message}'))
    try:
        known = points(section)
    except ObservationError as exc:
        issue(str(exc)); known = {n['name']: n for n in section.nodes}
    if p.layout not in ("split", "inline"):
        issue("layout 은 split 또는 inline 이어야 한다")
    if p.provenance not in ('manual', 'derived'):
        issue('provenance 는 manual 또는 derived 여야 한다')
    if p.provenance == 'derived' and not p.rationale.strip():
        issue('derived 확인 절차의 rationale 이 없다')
    if not p.setup.strip():
        issue('준비·초기화 setup 이 없다')
    if not re.fullmatch(r'manual:p[1-9][0-9]*', p.source):
        issue('source 는 manual:p<양의 정수> 여야 한다')
    if p.encoding not in ('0/1', 'H/L'):
        issue('encoding 은 0/1 또는 H/L 이어야 한다')
    if (not p.observe or len(set(p.inputs + p.observe)) != len(p.inputs + p.observe)
            or len(set(p.clocks)) != len(p.clocks)):
        issue('inputs/observe/clocks 이름 누락 또는 중복')
    for name in p.observe:
        if name not in known:
            issue(f'관측점 {name!r} 이 노드 표에 없다')
    if not set(p.clocks) <= set(p.inputs):
        issue('clocks 는 inputs 의 부분집합이어야 한다')
    bits = ('H', 'L') if p.encoding == 'H/L' else ('0', '1')
    observed, levels = set(), {}
    if not p.steps:
        issue('확인 절차가 비었다')
    for number, row in enumerate(p.steps, 1):
        if row.order != number:
            issue(f'순서는 1부터 연속이어야 한다 (행 {row.order})', row.line)
        if not row.action.strip():
            issue('조작이 비었다', row.line)
        if len(row.inputs) != len(p.inputs) or len(row.expected) != len(p.observe):
            issue('입력/기대 열 수 불일치', row.line)
        for name, cell in zip(p.inputs, row.inputs):
            if cell in ('0->1', '1->0'):
                start, end = cell.split('->')
                if name not in p.clocks or levels.get(name) != start:
                    issue(f'{name} 에지 {cell}: 선언한 clock 의 직전 레벨과 불일치', row.line)
                levels[name] = end
            elif cell not in bits:
                issue(f'{name} 입력 {cell!r}: 명시적 비트 또는 clock 에지가 필요하다', row.line)
            elif name in p.clocks:
                level = '1' if cell in ('1', 'H') else '0'
                if name in levels and levels[name] != level:
                    issue(f'{name}: 레벨 변경은 에지로 명시한다', row.line)
                levels[name] = level
        for name, cell in zip(p.observe, row.expected):
            if cell not in (*bits, '유지', '반전', '미정', '관측 안 함'):
                issue(f'{name} 기대값 {cell!r}: 빈칸/미지원 토큰', row.line)
            elif cell in ('유지', '반전') and name not in observed:
                issue(f'{name} {cell}: 앞선 관측 행이 필요하다', row.line)
            if cell in (*bits, '미정'):
                observed.add(name)
    return issues


@dataclass
class ObservationRow:
    order: int | None
    action: str
    inputs: list[str]
    expected: list[str]


@dataclass
class ObservationTable:
    inputs: list[str]
    points: list[tuple[str, str]]
    rows: list[ObservationRow]
    encoding: str
    provenance: str
    source: str
    setup: str
    rationale: str
    layout: str = "split"
    purpose: str = ""


def stage_observations(section, spec, stage: dict, node_names: list[str]) -> ObservationTable:
    known = points(section)
    for name in node_names:
        if name not in known:
            raise ObservationError(f'관측점 {name!r} 이 {section.id} 에 없다')
    p = procedure_for_stage(section, stage)
    if p is not None:
        issues = procedure_issues(section, p)
        if issues:
            raise ObservationError('; '.join(message for _, message in issues))
        columns = {name: i for i, name in enumerate(p.observe)}
        rows = [ObservationRow(r.order, r.action, list(r.inputs),
                    [r.expected[columns[n]] if n in columns else '관측 안 함' for n in node_names])
                for r in p.steps]
        return ObservationTable(list(p.inputs), [(n, known[n]['pin']) for n in node_names],
                                rows, p.encoding, p.provenance, p.source, p.setup, p.rationale, p.layout, p.purpose)
    for name in node_names:
        if point_kind(known[name]) == 'observed':
            raise ObservationError(f'observed 노드 {name} 에 확인 절차가 필요하다')
    old = nodes.stage_nodes_table(section, spec, node_names)
    return ObservationTable(old.inputs, old.nodes,
            [ObservationRow(None, '', list(cells),
                [nodes.format_bit(b, old.encoding) if b is not None else '미정' for b in bits])
             for cells, bits in old.rows], old.encoding, 'computed', '', '', '')
