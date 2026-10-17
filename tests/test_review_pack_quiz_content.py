import json
from copy import deepcopy
import pytest
from tests._quiz_practice_fixture import create_quiz_run
from tests._workbook_fixture import create_workbook_run
from scripts.lab.review_pack.workbook_content import load_workbook_content,build_workbook_data


def test_projection_contains_ten_typed_practice_without_answers(tmp_path):
    m,run=create_quiz_run(tmp_path); rows=load_workbook_content(m,run)
    q=build_workbook_data(m,rows,'problems');a=build_workbook_data(m,rows,'answers')
    assert q['meta']==dict(mode='problems',title='실험 4 · 기출문제와 퀴즈 유형 연습',chapter=0,total=11,quiz_practice_version=1)
    assert a['meta']['title']=='실험 4 · 기출풀이와 퀴즈 유형 연습'
    assert [p['id'] for p in q['problems']]==[p['id'] for p in a['problems']]
    assert sum('자체 출제' in p['section'] for p in q['problems'])==10
    assert all('solution' not in p and 'notes' not in p for p in q['problems'])
    assert all('solution' in p for p in a['problems'])


def test_legacy_projection_unchanged(tmp_path):
    m,run=create_workbook_run(tmp_path);q=build_workbook_data(m,load_workbook_content(m,run),'problems')
    assert q['meta']==dict(mode='problems',title='실험 4 · 기출 문제',chapter=0,total=1)
    assert q['problems'][0]['section']=='실험 4 · 풀이 검토됨'


@pytest.mark.parametrize('kind,label',[('true_false','판정 근거'),('true_false','문장 확인'),('fill_blank','빈칸별 근거'),('short_answer','채점 핵심'),('short_answer','허용 표현'),('breadboard','연결 기준'),('breadboard','완성 결선도')])
def test_quiz_fragment_contract(tmp_path,kind,label):
    m,run=create_quiz_run(tmp_path);p=next(p for p in m['problems'] if p.get('question_type')==kind)
    path=run/p['workbook_fragment'];obj=json.loads(path.read_text(encoding='utf-8'))
    obj['solution']['steps']=[s for s in obj['solution']['steps'] if s['label']!=label]
    path.write_text(json.dumps(obj),encoding='utf-8')
    with pytest.raises(ValueError,match=p['id']):load_workbook_content(m,run)


@pytest.mark.parametrize('change',['solution','foreign','missing','encoded_solution','duplicate','empty_spec','no_schematic','same_schematic','no_complete','wrong_answer','empty_answer','empty_step'])
def test_board_asset_mutations_rejected(tmp_path,change):
    m,run=create_quiz_run(tmp_path);p=next(p for p in m['problems'] if p.get('question_type')=='breadboard')
    if change in ('wrong_answer','empty_answer','empty_step'):p=m['problems'][1]
    path=run/p['workbook_fragment'];o=json.loads(path.read_text(encoding='utf-8'))
    if change in ('solution','encoded_solution'):o['conditions']=o['conditions'].replace('figures/questions/blank.png','figures/solutions/complete.png' if change=='solution' else 'figures/%73olutions/complete.png')
    if change=='missing':o['conditions']=o['conditions'].replace('blank.png','absent.png')
    if change=='foreign':
        reg=run/m['figure_manifest'];r=json.loads(reg.read_text(encoding='utf-8'));r['figures'][1]['question_id']=m['problems'][0]['id'];reg.write_text(json.dumps(r),encoding='utf-8')
    if change=='duplicate':o['conditions']+='<div class="work-board"><img src="figures/questions/blank.png"></div>'
    if change=='empty_spec':o['conditions']=o['conditions'].replace('<td>A</td>','<td> </td>')
    if change=='no_schematic':o['problem_figures']=[]
    if change=='same_schematic':o['problem_figures']=['f-blank']
    if change=='no_complete':o['solution']['steps'][-1]['html']='<p>그림 없음</p>'
    if change=='wrong_answer':o['solution']['answer']='<p>F</p>'
    if change=='empty_answer':o['solution']['answer']='<p> </p>'
    if change=='empty_step':o['solution']['steps'][0]['html']='<p> </p>'
    path.write_text(json.dumps(o),encoding='utf-8')
    with pytest.raises(ValueError,match=p['id']):load_workbook_content(m,run)


def test_published_check_uses_same_contract(tmp_path):
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    from scripts.lab.review_pack.workbook_render import read_workbook_payload,render_workbook_html
    from scripts.lab.review_pack.workbook_md import write_workbook_md
    from scripts.lab.review_pack.checks import check_pack
    from pathlib import Path
    m,run=create_quiz_run(tmp_path);assets=Path('.claude/skills/logic-lab-review-pack/assets')
    paths=assemble(m,run,tmp_path/'stage',assets);convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    assert check_pack(tmp_path/'stage')==[]
    for key in ('question','review'):
        data=read_workbook_payload(paths[key+'_html'])
        board=next(p for p in data['problems'] if p['id']=='q-qp-e04-board-01')
        board['html']['conditions']=board['html']['conditions'].replace('<td>A</td>','<td> </td>')
        paths[key+'_html'].write_text(render_workbook_html(data,assets),encoding='utf-8')
        write_workbook_md(data,m,paths[key+'_md'])
    assert any('q-qp-e04-board-01' in e for e in check_pack(tmp_path/'stage'))
