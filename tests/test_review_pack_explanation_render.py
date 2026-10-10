from pathlib import Path
from copy import deepcopy
import pytest
from tests.test_review_pack_explanation_content import setup, FRAGMENT
from scripts.lab.review_pack.explanation_render import write_explanations
from scripts.lab.review_pack.html2md import Parser
ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')

def test_shared_note_shell_and_complete_content(tmp_path):
    m,root,data=setup(tmp_path);folder=tmp_path/'stage';folder.mkdir()
    paths=write_explanations(m,data,root,folder,ASSETS)
    html=paths['explanation_html'].read_text();md=paths['explanation_md'].read_text()
    assert 'data-screens="article.topic"' in html
    assert 'data-range="logic-lab-04-problem-explanation"' in html
    assert 'class="topic"' in html and 'data-explanation="solve"' in html
    assert '<details' not in html and 'pack-nav' not in html
    assert '문제 1 · 문항 제목' in html
    assert 'S=0이면 I0' in md and 'q-mux-001' in md
    template=ASSETS.joinpath('note-template.html').read_text()
    assert html.partition('<style>')[2].partition('</style>')[0]==template.partition('<style>')[2].partition('</style>')[0]

def test_original_prefilled_table_preserved(tmp_path):
    m,root,data=setup(tmp_path);folder=tmp_path/'stage';folder.mkdir()
    original='<table><tr><th>D7</th><th>D0</th></tr><tr><td>0</td><td>1</td></tr></table>'
    data['problems'][0]['html']['original']=original
    paths=write_explanations(m,data,root,folder,ASSETS)
    assert original in paths['explanation_html'].read_text()

def test_md_keeps_math_figures_anchors_and_sources(tmp_path):
    m,root,data=setup(tmp_path);folder=tmp_path/'stage';folder.mkdir()
    m['problems'][0]['sources']=m['topics'][0]['sources']
    path=root/m['problems'][0]['explanation_fragment']
    path.write_text(FRAGMENT.replace('Y=I0예요.','$Y=I_0$예요.'))
    paths=write_explanations(m,data,root,folder,ASSETS)
    md=paths['explanation_md'].read_text()
    assert '$Y=I_0$' in md and '<a id="q-mux-001"></a>' in md
    assert '출처:' in md and '출처:' not in paths['explanation_html'].read_text()

@pytest.mark.parametrize('state,label',[('disputed','답안 충돌'),('unresolved','정답 미확정')])
def test_answer_status_warning_is_not_lost(tmp_path,state,label):
    m,root,data=setup(tmp_path);m['problems'][0]['answer_status']=state
    (root/m['problems'][0]['explanation_fragment']).write_text(FRAGMENT.replace('선택선은 데이터가 아니에요.',label+' 조건을 확인해요.'))
    before=deepcopy(m);folder=tmp_path/'stage';folder.mkdir()
    paths=write_explanations(m,data,root,folder,ASSETS)
    assert label in paths['explanation_html'].read_text() and label in paths['explanation_md'].read_text()
    assert m==before

def test_future_workbook_build_includes_explanations(tmp_path):
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    m,root,data=setup(tmp_path)
    paths=assemble(m,root,tmp_path/'stage',ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    for label in ('실험설명','기출문제','기출풀이','문제설명'):
        for ext in ('html','md'):assert (tmp_path/'stage'/f'실험04_{label}.{ext}').is_file()
