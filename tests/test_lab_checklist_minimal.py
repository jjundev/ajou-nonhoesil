"""현장판에서 설명을 덜어도 실제 작업과 기록을 잃지 않는다."""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.lab import config, render
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.spec_parser import parse_spec


@pytest.fixture(scope='module')
def checklist():
    root = Path(config.experiment_dir(7))
    spec = parse_spec(root / '체크리스트/명세.md')
    netlist = parse_netlist(root / '결선도/netlist.md')
    template = Path('.claude/skills/prep-lab-checklist/template.html').read_text()
    return render.render_checklist(spec, netlist, template), spec, netlist


def test_no_explanatory_pages_or_duplicate_pin_wiring(checklist):
    html, _, _ = checklist
    # These are whole obsolete blocks, not words hidden with CSS.
    assert not re.search(r'<section class="(?:common|closing)"', html)
    assert '<div class="chip">' not in html
    assert html.count('class="circuit-notes"') == 1
    for text in ['칩 자리표', '손으로 할 때 주의', '손그림은 이 그림',
                 '교안 원문이 아니다', '유도 이유:', '출처:', 'LED 사슬과 계측',
                 '실제 결과 —', '스텝마다 1장', '불일치 시 실제 BIT',
                 '간격은 줄였어요', '회색 = 앞 단계에서 그대로 둔 것']:
        assert text not in html


def test_every_stage_image_and_observation_row_survives(checklist):
    html, _, netlist = checklist
    circuit = netlist.circuits[0]
    assert html.count('class="stage"') == 29  # 6 preparation + 11 walks + 12 measurements
    for stage in circuit.stages:
        assert f'src="../결선도/{stage["diagram"]}"' in html
    for procedure in circuit.procedures:
        assert f'{procedure.id} · {procedure.title}' in html
        for row in procedure.steps:
            assert render._esc(row.action).replace('; ', '<br>') in html
    assert html.count('class="observation-procedure"') == len(circuit.procedures)


def test_record_tables_keep_all_steps_clock_actions_and_actual_blanks(checklist):
    html, spec, netlist = checklist
    stage_rows = sum(len(p.steps) for p in netlist.circuits[0].procedures)
    assert html.count('class="actual"') == stage_rows + sum(len(t.rows) for t in spec.tables)
    assert html.count('class="comparison-table"') == 15
    for table in spec.tables:
        if table.role == 'reference':
            continue
        assert f'{table.id} · {table.title}' in html
        for row in table.rows:
            assert render._esc(row[1]).replace('; ', '<br>') in html
    assert '0→1→0' in html and '하강 직후 관측' in html
    assert '먼저 CLR=1, 그다음 PR1=0' in html
    assert '먼저 CLR=1, 그다음 PR2=0' in html
    assert 'class="io-locations"' in html and 'class="steps"' in html
    assert 'class="removals"' in html
    from scripts.lab.review_pack.html2md import Parser
    from scripts.lab.review_pack.explanation_content import text
    tree=Parser(); tree.feed(html)
    pinout_rows=[[text(cell).strip() for cell in row.children
                  if hasattr(cell, 'tag') and cell.tag in {'td','th'}]
                 for row in tree.root.walk() if row.tag=='tr']
    assert ['74HC00','NAND 3 (이번에 사용)','9, 10','8','14','7'] in pinout_rows


def test_sidecar_does_not_hide_non_wiring_operations():
    root = Path(config.experiment_dir(2))
    netlist = parse_netlist(root / '결선도/netlist.md')
    section = netlist.circuits[1]
    stage = section.stages[0]
    html = render._stage_html(stage, netlist, section)
    assert '전원을 끄고' in html and '전원을 켠다' in html


def test_staged_final_still_validates_sidecar(tmp_path):
    png = tmp_path / 'final.png'
    png.touch()
    section = SimpleNamespace(diagram=png.name, stages=[{}])
    netlist = SimpleNamespace(experiment=7, path=tmp_path / 'netlist.md')
    with pytest.raises(FileNotFoundError, match='JSON|json'):
        render._diagram_html(section, netlist)


def test_unique_e07_operating_conditions_survive(checklist):
    html, _, _ = checklist
    assert 'D=CLK=CLR=0' in html and 'PR1=PR2=1' in html
    assert '프로브 GND=회로 GND' in html
    assert '발생기 정지·분리' in html
    assert '0~+5V' in html and '주기≥5s' in html


def test_chip_port_roles_precede_separate_first_preparation_page(checklist):
    html, spec, netlist = checklist
    opening = html.split('<div class="stage">', 1)[0]
    assert '<div class="fit">' in opening and '</div>' in opening
    for section in netlist.of_kind('lookup'):
        assert render._blocks(section.body) in opening
    assert 'J4, K16, CLK1, PR2, CLR3' in opening
    assert 'Q15, Q' in opening and 'NAND 1' in opening
    assert '회로 1/1' in opening
    stage = html.split('<div class="stage">', 1)[1]
    assert '단계 1 준비 ①' in stage
    assert '<h1>' not in stage
