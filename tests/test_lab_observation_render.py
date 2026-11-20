from dataclasses import replace
from pathlib import Path
import re
import pytest
from scripts.lab import render, observations
from scripts.lab.leds import Led
from scripts.lab.spec_parser import parse_spec
from tests.test_lab_observation_parser import parsed, FIX

@pytest.fixture
def data(tmp_path):
    n=parsed(tmp_path); s=parse_spec(FIX/'spec_observation_stepped.md')
    return n,s,n.circuits[0]

def stage_html(data, **kw):
    n,s,c=data
    return render._stage_html(c.stages[0],n,c,spec=s,last=True,**kw)

def test_last_stage_prints_explicit_procedure(data):
    h=stage_html(data)
    assert 'BIT1 초기화 및 입력 확인' in h
    assert 'U2 pin 15' in h
    assert all(action in h for action in ['초기화','CLR 해제','데이터 설정','클럭 상승','클럭 하강'])
    assert h.count('data-observation-order=') == 10 # same five rows in both areas

def test_diagnostic_procedure_is_preserved_but_not_a_required_stage_check(tmp_path):
    from tests.test_lab_observation_parser import TEXT
    n = parsed(tmp_path, TEXT.replace('- setup:', '- checklist: diagnostic\n- setup:', 1))
    s = parse_spec(FIX / 'spec_observation_stepped.md')
    c = n.circuits[0]
    assert c.procedures[0].checklist == 'diagnostic'
    h = stage_html((n, s, c))
    assert 'BIT1 초기화 및 입력 확인' not in h
    assert '확인 노드:' not in h
    assert 'observation-procedure' not in h
    assert len(c.procedures[0].steps) == 5

def test_invalid_checklist_policy_is_rejected(tmp_path):
    from tests.test_lab_observation_parser import TEXT
    from scripts.lab.netlist_parser import NetlistError
    with pytest.raises(NetlistError, match='checklist'):
        parsed(tmp_path, TEXT.replace('- setup:', '- checklist: typo\n- setup:', 1))

def test_v2_diagnostic_stage_keeps_wiring_without_a_measurement_table(tmp_path):
    from scripts.lab import config
    from scripts.lab.netlist_parser import parse_netlist
    source = Path(config.experiment_dir(3)) / '결선도/netlist.md'
    content = source.read_text(encoding='utf-8')
    content = content.replace('LED1 을 A·B 네 조합으로 본다 (01·10 만 켜짐). 74HC86 첫 사용',
                              'LED1 을 A·B 네 조합으로 본다 (01·10 만 켜짐). 74HC86 첫 사용 [진단용]', 1)
    path = tmp_path / 'netlist.md'
    path.write_text(content, encoding='utf-8')
    net = parse_netlist(path)
    circuit = net.circuits[0]
    stage = circuit.stages[0]
    assert stage['diagnostic'] is True
    html = render._stage_html(stage, net, circuit, spec=parse_spec(Path(config.experiment_dir(3)) / '체크리스트/명세.md'))
    assert '확인 노드:' not in html
    assert '<b>확인:</b>' not in html
    assert '01·10 만 켜짐' not in html
    assert '단계 1' in html

def test_running_clock_is_readable_in_both_layouts(data):
    n, s, c = data
    p = c.procedures[0]
    p.steps[1].inputs[1] = 'RUN'
    p.steps[2].inputs[1] = 'RUN'
    p.steps[3].inputs[1] = '0'
    p.steps[4].inputs[1] = '0->1'
    p.steps[4].action = '클럭 상승'
    p.setup = '1 Hz, 0~5 V 사각파'
    for layout in ('split', 'inline'):
        p.layout = layout
        h = stage_html(data)
        assert '1 Hz, 0~5 V 사각파' in h
        assert 'CLK = 반복 클록' in h
        assert 'CLK = RUN' not in h
        assert '클럭 상승' in h

def test_running_clock_start_and_stop_are_highlighted():
    rows = render._input_settings_html(['CLK'], [['0'], ['RUN'], ['RUN'], ['0']])
    assert 'input-change' in rows[1]
    assert 'input-change' not in rows[2]
    assert 'input-change' in rows[3]

def test_running_clock_appears_in_stepped_and_record():
    from scripts.lab.spec_parser import SpecTable
    from scripts.lab.record import _stepped
    t = SpecTable(id='T1', title='x', kind='stepped', encoding='0/1', source='manual:p1', expected=None, role='record', header=['스텝','CLK','기록'], rows=[['1','RUN','']], line=1)
    for output in (render._stepped_html(t), _stepped(t)):
        assert '반복 클록' in output
        assert 'RUN' not in output

def test_running_clock_in_comparison_record():
    from scripts.lab.spec_parser import SpecTable
    from scripts.lab.record import _stepped
    t = SpecTable(id='T1', title='x', kind='stepped', encoding='0/1', source='manual:p1', expected=None, role='record', header=['스텝','CLK','Q'], rows=[['1','RUN','1']], line=1, comparison='led', outputs=['Q'])
    assert 'CLK=반복 클록' in _stepped(t)

def test_probe_stage_prints_procedure_without_led(data):
    h=stage_html(data)
    assert '클럭 하강' in h
    assert '관측 예상' in h
    assert '계산할 수 없어요' not in h

def test_provenance_stays_in_source_while_setup_is_printed(data):
    h=stage_html(data)
    assert '교안 원문이 아니다' not in h and 'manual:p9' not in h
    assert 'CLK을 0에 정지' in h
    assert data[2].procedures[0].source == 'manual:p9'
    data[2].procedures[0].provenance='manual'
    assert '교안 원문이 아니다' not in stage_html(data)

def sample(tokens, encoding='0/1'):
    return observations.ObservationTable(['SERIAL_DATA'],[(f'Q{i}',f'U{i+1} pin 3') for i in range(len(tokens))],
        [observations.ObservationRow(1,'입력 <script>', ['1'],tokens)],encoding,'derived','manual:p1','준비','유도')

def test_active_low_and_active_high_known_bits():
    t=sample(['0','1']); ls=[Led('A','좌 a3',True,1),Led('B','좌 a6',False,2)]
    h=render._observation_procedure_html(t,ls,{'A':'Q0','B':'Q1'})
    assert '①A: 켜짐' in h and '②B: 켜짐' in h
    h=render._observation_procedure_html(sample(['1','0']),ls,{'A':'Q0','B':'Q1'})
    assert '①A: 소등' in h and '②B: 소등' in h
    h=render._observation_procedure_html(sample(['L','H'],'H/L'),ls,{'A':'Q0','B':'Q1'})
    assert '①A: 켜짐' in h and '②B: 켜짐' in h

def test_inline_legend_only_explains_different_signals():
    leds = [Led('Q0', '좌 a3', True, 1), Led('B', '좌 a6', False, 2)]
    h = render._inline_observation_html(sample(['0', '1']), leds, {'Q0': 'Q0', 'B': 'Q1'})
    assert '①Q0 = Q0' not in h
    assert '②B = Q1' in h
    assert '<td>①Q0 · ②B</td>' in h  # polarity-aware expected results remain
    h = render._inline_observation_html(sample(['0']), leds[:1], {'Q0': 'Q0'})
    assert '보는 LED:' not in h
    assert '<td>①Q0</td>' in h

def test_mixed_hold_toggle_unknown_and_bits_are_per_led():
    tokens=['1','유지','반전','미정','관측 안 함']
    ls=[Led(f'L{i}','좌 a3',False,i+1) for i in range(5)]
    h=render._observation_procedure_html(sample(tokens),ls,{f'L{i}':f'Q{i}' for i in range(5)})
    for text in ['①L0: 켜짐','②L1: 직전 그대로','③L2: 직전과 반대','④L3: 미정','⑤L4: 이번 절차 관측 안 함']:
        assert text in h
    assert '④L3: 소등' not in h

def test_inherited_led_missing_in_procedure_is_unobserved():
    h=render._observation_procedure_html(sample(['1']),[Led('OLD','좌 a3',False,1)],{'OLD':'PREVIOUS'})
    assert '①OLD: 이번 절차 관측 안 함' in h

def test_scenario_checkboxes_do_not_add_record_cells(data):
    n,s,c=data
    template=Path('.claude/skills/prep-lab-checklist/template.html').read_text()
    authored=render.render_checklist(s,n,template)
    c.stages=[]; c.nodes=[]
    without=render.render_checklist(s,n,template)
    assert authored.count('class="check"') == without.count('class="check"')
    assert authored.count('class="fill"') == without.count('class="fill"')
    assert 'class="box"' in authored

def test_v2_render_html_is_unchanged():
    from scripts.lab import config
    n=parse_spec # real approved corpus, comparing optional CSS inclusion path
    from scripts.lab.netlist_parser import parse_netlist
    s=parse_spec(Path(config.experiment_dir(1))/'체크리스트/명세.md')
    n=parse_netlist(Path(config.experiment_dir(1))/'결선도/netlist.md')
    template=Path('.claude/skills/prep-lab-checklist/template.html').read_text()
    baseline=re.sub(r'<!-- OBSERVATION_STYLE_BEGIN -->.*?<!-- OBSERVATION_STYLE_END -->\n','',template,flags=re.S)
    assert render.render_checklist(s,n,template) == render.render_checklist(s,n,baseline)

def test_all_procedure_text_is_escaped():
    h=render._observation_procedure_html(sample(['미정']))
    assert '<script>' not in h
    assert '&lt;script&gt;' in h

def test_unstaged_observed_nodes_are_not_computed(data):
    n,s,c=data; c.stages=[]
    c.nodes=[c.nodes[-1]]
    assert '계산할 수 없어요' not in render._unstaged_nodes_html(s,c)

def test_inherited_same_name_different_pin_is_unobserved(tmp_path):
    import copy,json,base64
    from scripts.lab.netlist_parser import parse_netlist
    n=parse_netlist(FIX/'netlist_observation_jk_v3.md')
    n.path=tmp_path/'netlist.md'
    s=parse_spec(FIX/'spec_observation_jk.md')
    first=n.circuits[0]
    first.stages[0]['todo']='U1 pin 15→LED OLD 급전'
    second=copy.deepcopy(first)
    second.id='C2'; second.continues='C1'; second.title='새 물리 출력 Q'
    second.body=second.body.replace('U1','U2')
    for point in second.nodes: point['pin']=point['pin'].replace('U1','U2')
    second.stages[0]['todo']='U2 pin 15→LED NEW 급전'
    n.sections.append(second)
    pixel=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=')
    board=render.board_version_of(tmp_path/'배치.py',n.experiment)
    for c,tags in [(first,['OLD']),(second,['OLD','NEW'])]:
        c.diagram=f'{c.id}.png'; c.stages[0]["diagram"]=c.diagram
        png=tmp_path/c.diagram; png.write_bytes(pixel)
        png.with_suffix('.json').write_text(json.dumps({'schema':render.SIDECAR_SCHEMA,'board':board,
            'removals':[],'steps':[],'probes':[],'kept':0,
            'leds':[{'tag':tag,'at':f'좌 a{3+i*3}','active_low':False} for i,tag in enumerate(tags)]}))
    h=render.circuit_pages(s,n).split('새 물리 출력 Q',1)[1]
    assert '①OLD: 이번 절차 관측 안 함' in h
    assert '①OLD: 소등' not in h and '①OLD: 직전과 반대' not in h
    assert '②NEW: 소등' in h and '②NEW: 직전과 반대' in h
    # Reuse of a physical pin under a new local name can still be observed.
    second.body += '\n- U1 = 74HC76\n'
    second.nodes[0].update(name='CURRENT',pin='U1 pin 15')
    second.procedures[0].observe[0]='CURRENT'
    second.stages[0].update(node='CURRENT',todo='U1 pin 15→LED NEW 급전')
    h=render.circuit_pages(s,n).split('새 물리 출력 Q',1)[1]
    assert '①OLD: 소등' in h and '①OLD: 직전과 반대' in h


def test_wide_v3_record_reserves_action_width_without_changing_measurements():
    from types import SimpleNamespace
    table=SimpleNamespace(header=['스텝','조작','SERIAL DATA','CLK','CLR','PR1','PR2',
                                  'BIT1','BIT2','BIT3','BIT4','BIT5','BIT6'],
                          rows=[['S1','다음 데이터 비트를 에지 전에 설정','','1->0','1','1','1',
                                 '','','','','','']])
    legacy=render._stepped_html(table)
    wide=render._stepped_html(table, wide=True)
    widths=[float(w) for w in re.findall(r'<col style="width:([\d.]+)%;">',wide)]
    assert len(widths)==13
    assert widths[1] >= 4*widths[0]
    assert sum(widths)==pytest.approx(100,abs=.01)
    assert re.findall(r'<(?:th|td)[^>]*>(.*?)</(?:th|td)>',wide)==re.findall(r'<(?:th|td)[^>]*>(.*?)</(?:th|td)>',legacy)
    assert wide.count('class="fill"')==7
    assert 'class="check"' not in wide
    assert '<col ' not in legacy

@pytest.mark.parametrize('layout', ['inline', 'split'])
def test_authored_purpose_reaches_stage_before_setup(tmp_path, layout):
    from tests.test_lab_observation_parser import TEXT
    purpose = '입력 <D>가 하강 에지에서 BIT1에 저장되는지 확인한다.'
    text = TEXT.replace('- setup:', f'- purpose: {purpose}\n- layout: {layout}\n- setup:', 1)
    n = parsed(tmp_path, text)
    s = parse_spec(FIX / 'spec_observation_stepped.md')
    c = n.circuits[0]
    assert c.procedures[0].purpose == purpose
    h = stage_html((n, s, c))
    escaped = render._esc(purpose)
    assert h.count(escaped) == 1
    assert purpose not in h  # authored text must be HTML escaped
    assert h.index(escaped) < h.index('준비·초기화:')

@pytest.mark.parametrize('with_led', [False, True])
def test_inline_action_is_separate_column_before_input_settings(with_led):
    t = sample(['1'])
    t.layout = 'inline'
    t.rows[0].action = '먼저 입력을 설정'
    ls = [Led('L', '좌 a3', False, 1)] if with_led else []
    h = render._observation_procedure_html(t, ls, {'L': 'Q0'} if with_led else {})
    assert '<th>조작</th>\n<th>입력 설정</th>' in h
    row = re.search(r'<tbody>\s*<tr[^>]*>(.*?)</tr>', h, re.S)[1]
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
    assert cells[1] == '먼저 입력을 설정'
    # LED 판독 표는 기록표(T1 등)처럼 `=` 를 붙여 쓴다
    assert cells[2] == ('SERIAL_DATA=1' if with_led else 'SERIAL_DATA = 1')
    assert h.count('class="actual"') == 1
