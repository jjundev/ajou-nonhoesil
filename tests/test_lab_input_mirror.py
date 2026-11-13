"""위치 미러 칸 — '입력 설정' 칸이 표 위 위치도와 같은 묶음·위→아래 순서로 쌓이는지.

2026-11-14 실험09 실측: 위치도는 `IN0, WR1, OE0 │ WR0` 인데 칸은 명세 순서 `OE0, IN0, WR0, WR1`
이라 학생이 점퍼를 찾느라 위치도와 표를 오갔다. 순서의 출처를 결선도 JSON 하나로 묶는다.
"""
import json
import re
from pathlib import Path

import pytest

from scripts.lab import config, observations, render
from scripts.lab.io_locations import input_columns
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.spec_parser import parse_spec


def _sidecar(tmp_path, rows):
    png = tmp_path / 'board.png'
    data = {'inputs': [{'name': n, 'at': f'좌 j{r}', 'rail': rail, 'x': x, 'row': r}
                       for n, rail, x, r in rows]}
    png.with_suffix('.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return png


@pytest.fixture
def board(tmp_path):
    # 왼쪽 레일(x=10): IN0 5행, WR1 6행, OE0 25행 · 가운데 레일(x=50): WR0 7행 · 표에 없는 IN1
    return _sidecar(tmp_path, [('OE0', '좌 GND레일25행', 10, 25), ('IN0', '좌 GND레일5행', 10, 5),
                               ('WR0', '중앙GND레일7행', 50, 7), ('WR1', '좌 GND레일6행', 10, 6),
                               ('IN1', '좌 GND레일15행', 10, 15), ('X', '중앙GND레일30행', 60, 30)])


def test_columns_follow_board_not_table_order(board):
    assert input_columns(board, ['OE0', 'IN0', 'WR0', 'WR1']) == [
        ('왼쪽', ['IN0', 'WR1', 'OE0']), ('가운데', ['WR0'])]


def test_unused_jumpers_and_empty_groups_are_dropped(board):
    assert input_columns(board, ['WR1', 'IN1']) == [('왼쪽', ['WR1', 'IN1'])]


def test_any_unlocated_input_falls_back_to_none(board):
    assert input_columns(board, ['OE0', 'NOPE']) is None
    assert input_columns(None, ['OE0']) is None
    assert input_columns(board.with_name('missing.png'), ['OE0']) is None


def test_alias_sorts_by_board_name_but_keeps_table_name(tmp_path):
    png = _sidecar(tmp_path, [('CLK', '좌 GND레일3행', 10, 3), ('D', '좌 GND레일9행', 10, 9)])
    assert input_columns(png, ['SERIAL DATA', 'CLK']) == [('왼쪽', ['CLK', 'SERIAL DATA'])]


def test_mirror_cell_keeps_change_highlight_per_input(board):
    columns = input_columns(board, ['OE0', 'IN0', 'WR0', 'WR1'])
    rows = render._input_settings_html(['OE0', 'IN0', 'WR0', 'WR1'],
                                       [['0', '0', '0', '1'], ['0', '1', '0', '1']], columns=columns)
    cols = re.findall(r'<div class="col">(.*?)</div>', rows[1])
    assert [re.findall(r'(\w+) = ', c) for c in cols] == [['IN0', 'WR1', 'OE0'], ['WR0']]
    assert re.findall(r'<span class="input-change">(.*?)</span>', rows[1]) == ['IN0 = 1']
    assert 'style="--g:2"' in rows[1]


def _table(layout):
    t = observations.ObservationTable(
        ['OE0', 'IN0', 'WR0', 'WR1'], [('OUT0', 'U3 pin 11')],
        [observations.ObservationRow(1, '전원 직후', ['0', '0', '0', '1'], ['0']),
         observations.ObservationRow(2, 'IN0 을 올린다', ['0', '1', '0', '1'], ['0'])],
        '0/1', 'derived', 'manual:p1', '준비', '유도')
    t.layout = layout
    return t


@pytest.mark.parametrize('layout', ['inline', 'split'])
def test_both_procedure_layouts_mirror_with_group_header(board, layout):
    h = render._observation_procedure_html(_table(layout), (), {}, png=board)
    assert h.count('class="mirror"') == 2
    head = re.search(r'<th>입력 설정(.*?)</th>', h, re.S)[1]
    assert re.findall(r'<span>(.*?)</span>', head) == ['왼쪽', '가운데']


@pytest.mark.parametrize('layout', ['inline', 'split'])
def test_without_board_cells_stay_a_plain_list(layout):
    h = render._observation_procedure_html(_table(layout), (), {})
    assert 'mirror' not in h
    assert 'OE0 = 0<br>IN0 = 0<br>WR0 = 0<br>WR1 = 1' in h


def test_seven_column_table_gets_explicit_widths():
    h = render._comparison_table_html(list('abcdefg'), [['1'] * 7])
    assert '14.28' not in h and '<col style="width:27%;">' in h


@pytest.fixture(scope='module')
def lab09():
    root = Path(config.experiment_dir(9))
    spec = parse_spec(root / '체크리스트/명세.md')
    netlist = parse_netlist(root / '결선도/netlist.md')
    template = Path('.claude/skills/prep-lab-checklist/template.html').read_text(encoding='utf-8')
    return render.render_checklist(spec, netlist, template)


def _first_cell_after(html, marker):
    start = html.index(marker)
    table = html[html.index('<table class="comparison-table">', start):]
    row = re.search(r'<tbody>\s*<tr[^>]*>(.*?)</tr>', table, re.S)[1]
    cell = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)[2]
    return [re.findall(r'([A-Z][A-Z0-9]*) ?=', c) for c in re.findall(r'<div class="col">(.*?)</div>', cell)]


def test_lab09_cells_match_location_map(lab09):
    assert _first_cell_after(lab09, 'V5 · A 한 비트') == [['IN0', 'WR1', 'OE0'], ['WR0']]
    assert _first_cell_after(lab09, 'V1 · 첫 데이터 비트') == [['RB', 'RA'], ['D1', 'WA', 'WB', 'WE', 'RE']]


def test_lab09_every_comparison_table_is_mirrored(lab09):
    tables = lab09.count('class="comparison-table"')
    assert tables and lab09.count('class="mirror-head"') == tables
