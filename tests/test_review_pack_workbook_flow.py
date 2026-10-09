import json
from pathlib import Path
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.workbook_render import read_workbook_payload
from tests._workbook_fixture import create_workbook_run

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')

def test_modern_build_checks_dynamic_ids_and_three_md(tmp_path):
    m, run = create_workbook_run(tmp_path)
    stage = tmp_path/'stage'; paths = assemble(m,run,stage,ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    assert paths['question_html'].is_file()
    for label in ('실험설명','기출문제','기출풀이'):
        assert (stage/f'실험04_{label}.md').is_file()
    a = read_workbook_payload(paths['review_html'])
    q = read_workbook_payload(paths['question_html'])
    assert [p['id'] for p in a['problems']] == [p['id'] for p in q['problems']]
    assert check_pack(stage) == []
    # canonical JSON 본문은 스크립트 내부이므로 정적 article 검사를 적용하지 않는다
    assert '<article class="card"' not in paths['review_html'].read_text(encoding='utf-8')

def test_tampered_question_payload_rejected(tmp_path):
    from scripts.lab.review_pack.workbook_render import render_workbook_html
    m, run = create_workbook_run(tmp_path)
    stage = tmp_path/'stage'; paths = assemble(m,run,stage,ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    data = read_workbook_payload(paths['question_html'])
    data['problems'][0]['solution'] = {'answer':'exposed'}
    paths['question_html'].write_text(render_workbook_html(data,ASSETS),encoding='utf-8')
    assert check_pack(stage)

import copy
import pytest
from scripts.lab.review_pack.workbook_render import render_workbook_html

@pytest.mark.parametrize('change', ['order','duplicate','conditions','encoded_path','solution_image','foreign'])
def test_payload_mutations_rejected(tmp_path,change):
    m, run = create_workbook_run(tmp_path)
    p2 = copy.deepcopy(m['problems'][0]); p2['id'] += '-second'
    p2['workbook_fragment'] = f'workbook/{p2["id"]}.json'
    (run/p2['workbook_fragment']).write_bytes((run/m['problems'][0]['workbook_fragment']).read_bytes())
    m['problems'].append(p2)
    paths = assemble(m,run,tmp_path/'stage',ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    key = 'review_html' if change == 'conditions' else 'question_html'
    data = read_workbook_payload(paths[key])
    if change == 'order': data['problems'].reverse()
    if change == 'duplicate': data['problems'][1]['id'] = data['problems'][0]['id']
    if change == 'conditions': data['problems'][0]['html']['conditions'] = '<p>S=1</p>'
    if change == 'encoded_path':
        data['problems'][0]['figures'] = [dict(src='%2e%2e/outside.png',w_mm=10,h_mm=10)]
    if change == 'solution_image':
        data['problems'][0]['figures'] = [dict(src='figures/solutions/fake.png',w_mm=10,h_mm=10)]
    if change == 'foreign':
        data['problems'].append(dict(data['problems'][0],id='q-held'))
    paths[key].write_text(render_workbook_html(data,ASSETS),encoding='utf-8')
    assert check_pack(tmp_path/'stage')

def test_exposed_bank_asset_cannot_author_problem_diagram(tmp_path):
    from tests.test_review_pack_bank_assets import asset_pack
    from tests._workbook_fixture import add_redrawn_figure
    from scripts.lab.review_pack.workbook_figures import check_redrawn_figures
    run, m = asset_pack(tmp_path,exposure='present')
    m['review_presentation_version'] = 2
    m['figure_manifest'] = 'figures/redraw-manifest.json'
    row = add_redrawn_figure(m,run)
    bank = json.loads((run/m['bank_import']['snapshot_path']).read_text(encoding='utf-8'))
    row['source_asset_ids'] = [bank['assets'][0]['id']]
    (run/m['figure_manifest']).write_text(json.dumps(dict(schema_version=1,figures=[row])),encoding='utf-8')
    assert check_redrawn_figures(run,m)

def test_build_puts_data_under_data_folder_and_links_follow(tmp_path):
    from tests._workbook_fixture import add_redrawn_figure
    m, run = create_workbook_run(tmp_path)
    add_redrawn_figure(m, run)
    fragment = run/m['problems'][0]['workbook_fragment']
    authored = json.loads(fragment.read_text(encoding='utf-8'))
    authored['problem_figures'] = ['f1']
    fragment.write_text(json.dumps(authored, ensure_ascii=False), encoding='utf-8')
    stage = tmp_path/'stage'; paths = assemble(m,run,stage,ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    assert {p.name for p in stage.iterdir() if p.is_dir()} == {'자료'}
    assert not {'assets','figures','evidence','manifest.json'} & {p.name for p in stage.iterdir()}
    for name in ('manifest.json','assets','figures/questions/diagram.png'):
        assert (stage/'자료'/name).exists()
    payload = read_workbook_payload(paths['question_html'])
    assert payload['problems'][0]['figures'][0]['src'] == '자료/figures/questions/diagram.png'
    assert '자료/figures/questions/diagram.png' in paths['question_md'].read_text(encoding='utf-8') or \
        '%EC%9E%90%EB%A3%8C/figures/questions/diagram.png' in paths['question_md'].read_text(encoding='utf-8')
    assert 'href="자료/assets/vendor/' in paths['question_html'].read_text(encoding='utf-8')
    assert check_pack(stage) == []
