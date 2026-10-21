"""Optional assembly work: authored order, structural and publication gates."""
import json
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING
from PIL import Image
if TYPE_CHECKING:
    from .netlist_parser import AssemblyStep, LabNetlist, NetlistSection
    from .validate import Finding


def steps_for_stage(section: 'NetlistSection', stage_no: int) -> list['AssemblyStep']:
    return [s for s in section.assembly_steps if s.stage_no == stage_no]


def check_structure(netlist: 'LabNetlist') -> list['Finding']:
    from .validate import Finding
    out = []
    diagrams = set()
    for section in netlist.circuits:
        parents = [s['stage_no'] for s in section.stages if not s.get('walk')]
        counts = Counter(parents)
        last_parent, orders = -1, Counter()
        for step in section.assembly_steps:
            where = f'{netlist.path.name}:{step.line}'
            errors = []
            if counts[step.stage_no] != 1:
                errors.append('소속 일반 단계가 정확히 하나 있어야 한다')
            else:
                index = parents.index(step.stage_no)
                if index < last_parent:
                    errors.append('소속 단계는 원문 단계 순서를 따라야 한다')
                last_parent = index
            orders[step.stage_no] += 1
            if step.order != orders[step.stage_no]:
                errors.append('조립 순서는 부모별 1부터 연속이어야 한다')
            if step.diagram in diagrams or any(step.diagram == s['diagram'] for c in netlist.circuits for s in c.stages) or any(step.diagram == c.diagram for c in netlist.circuits):
                errors.append('준비 그림 파일명이 중복된다')
            diagrams.add(step.diagram)
            if Path(step.diagram).suffix.lower() != '.png':
                errors.append('준비 그림은 PNG여야 한다')
            out.extend(Finding('error', where, e) for e in errors)
    return out


def check_assets(netlist: 'LabNetlist') -> list['Finding']:
    from .validate import Finding
    out = []
    for section in netlist.circuits:
        for step in section.assembly_steps:
            png = netlist.path.parent / step.diagram
            try:
                with Image.open(png) as im:
                    if im.format != 'PNG':
                        raise ValueError('PNG 형식이 아니다')
                    im.verify()
                data = json.loads(png.with_suffix('.json').read_text(encoding='utf-8'))
                if not isinstance(data, dict) or data.get('schema') != 'breadboard-sidecar/v1':
                    raise ValueError('사이드카 스키마가 다르다')
            except (OSError, ValueError) as exc:
                out.append(Finding('error', str(png), f'준비 그림/JSON을 읽을 수 없다: {exc}'))
    return out
