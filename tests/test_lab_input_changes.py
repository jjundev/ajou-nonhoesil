"""Red inputs describe physical work, including repeated clock events."""
import re
from pathlib import Path

import pytest

from scripts.lab import observations, render
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.spec_parser import parse_spec


def highlighted(text):
    return re.findall(r'<span class="input-change">(.*?)</span>', text)


def test_input_changes_follow_end_levels_and_repeat_events():
    rows = [['0', '0'], ['1', '0->1'], ['1', '1->0'],
            ['1', '0'], ['1', '1->0'], ['0', '1->0']]
    result = render._input_settings_html(['D', 'CLK'], rows)
    assert [highlighted(x) for x in result] == [
        [], ['D = 1', 'CLK = 0-&gt;1'], ['CLK = 1-&gt;0'],
        [], ['CLK = 1-&gt;0'], ['D = 0', 'CLK = 1-&gt;0']]
    assert highlighted(render._input_settings_html(['D'], [['1']])[0]) == []


def test_input_markup_escapes_source_and_keeps_unknown_values():
    result = render._input_settings_html(['<D>'], [['0'], ['1'], ['미정'], ['0']])
    assert highlighted(result[1]) == ['&lt;D&gt; = 1']
    assert '<D>' not in ''.join(result)
    assert '미정' in result[2] and highlighted(result[3]) == []


@pytest.mark.parametrize('layout', ['inline', 'split'])
def test_both_observation_layouts_highlight_only_inputs(layout):
    table = observations.ObservationTable(['D', 'CLK'], [('Q', 'U1 pin 3')], [
        observations.ObservationRow(1, '初期 <設定>', ['0', '0'], ['0']),
        observations.ObservationRow(2, '입력과 클록', ['1', '0->1'], ['1']),
        observations.ObservationRow(3, '하강', ['1', '1->0'], ['0']),
        observations.ObservationRow(4, '유지', ['1', '0'], ['0']),
    ], '0/1', 'derived', 'manual:p1', '준비', '이유', layout=layout)
    h = render._observation_procedure_html(table)
    assert highlighted(h) == ['D = 1', 'CLK = 0-&gt;1', 'CLK = 1-&gt;0']
    assert '初期 &lt;設定&gt;' in h
    assert h.count('class="actual"' if layout == 'inline' else 'class="box"') == 4


def test_all_e07_procedures_and_record_tables_use_same_rule():
    spec = parse_spec('보고서/실험07/체크리스트/명세.md')
    netlist = parse_netlist('보고서/실험07/결선도/netlist.md')
    circuit = netlist.circuits[0]
    for stage in circuit.stages:
        if stage.get('procedure'):
            p = observations.procedure_for_stage(circuit, stage)
            table = observations.stage_observations(circuit, spec, stage, p.observe)
            h = render._observation_procedure_html(table)
            assert highlighted(h), p.id
            first = re.search(r'<tbody>\s*<tr[^>]*>(.*?)</tr>', h, re.S)[1]
            assert highlighted(first) == []
    for table in spec.tables:
        h = render._stepped_html(table)
        clock_count = sum(r[table.header.index('CLK')] == '1->0' for r in table.rows)
        assert highlighted(h).count('CLK=1-&gt;0') == clock_count
        assert h.count('class="actual"') == len(table.rows)


def test_checklist_skill_documents_action_based_highlighting():
    skill = Path('.claude/skills/prep-lab-checklist/SKILL.md').read_text()
    assert '### 입력 변경 강조' in skill
    for rule in ['직전 종료 레벨', '매번', '첫 행', '중간', '최종']:
        assert rule in skill.split('### 입력 변경 강조')[1].split('### ')[0]
