from pathlib import Path
from copy import deepcopy
import pytest
from tests._workbook_fixture import create_workbook_run
from scripts.lab.review_pack.manifest import output_names, validate_manifest
from scripts.lab.review_pack.explanation_content import load_explanations

FRAGMENT = '''<div class="layer eli5" data-explanation="understand"><span class="layer-title">무엇을 할까요</span><p>선택선이 고른 입력을 찾아요.</p></div>
<div class="layer formal" data-explanation="start"><span class="layer-title">첫 줄</span><p>S=0이면 I0를 골라요.</p></div>
<div class="layer formal" data-explanation="solve"><span class="layer-title">함께 풀어요</span><p>Y=I0예요.</p></div>
<div class="layer formal" data-explanation="verify"><span class="layer-title">답과 검산</span><p>선택선 0과 입력 번호 0이 같아요.</p></div>
<div class="layer warn" data-explanation="pitfall"><span class="layer-title">주의</span><p>선택선은 데이터가 아니에요.</p></div>
<div class="layer formal" data-explanation="retry"><span class="layer-title">다시 풀어요</span><ol><li>선택 입력을 찾아요.</li></ol></div>
<div class="sum" hidden><p>S를 읽고 입력을 골라요.</p></div>'''

def setup(tmp_path):
    m, root = create_workbook_run(tmp_path)
    m['problem_explanation_version'] = 1
    m['explanation_checks'] = dict.fromkeys(('source_visual','content','independent','browser'), 'not_run')
    p = m['problems'][0]
    p['explanation_fragment'] = f'problem-explanations/{p["id"]}.html'
    (root/'problem-explanations').mkdir()
    (root/p['explanation_fragment']).write_text(FRAGMENT)
    payload = dict(meta=dict(mode='problems',total=1),problems=[dict(id=p['id'],number='1',title=p['title'],html=dict(original='<p>問題</p>',conditions='',ask='<p>Y?</p>'),figures=[])])
    return m,root,payload

def test_optional_explanation_contract(tmp_path):
    m,root,data=setup(tmp_path)
    assert validate_manifest(m)==[]
    names=output_names(4,review_presentation_version=2,problem_explanation_version=1)
    assert names['explanation_html']=='실험04_문제설명.html'
    assert names['explanation_md']=='실험04_문제설명.md'
    del m['problem_explanation_version'];del m['explanation_checks']
    assert validate_manifest(m)==[]
    assert 'explanation_html' not in output_names(4)

def test_included_only_and_payload_order(tmp_path):
    m,root,data=setup(tmp_path)
    m['problems'].append(dict(m['problems'][0],id='q-held',status='held',reason='읽기 어려움'))
    rows=load_explanations(m,data,root)
    assert [(r.problem['id'],r.problem['number']) for r in rows]==[(data['problems'][0]['id'],'1')]

@pytest.mark.parametrize('change',['missing','duplicate','number','foreign','title'])
def test_missing_duplicate_or_reordered_question_rejected(tmp_path,change):
    m,root,data=setup(tmp_path)
    if change=='missing':(root/m['problems'][0]['explanation_fragment']).unlink()
    if change=='duplicate':data['problems']*=2
    if change=='number':data['problems'][0]['number']='2'
    if change=='foreign':data['problems'][0]['id']='q-other'
    if change=='title':data['problems'][0]['title']='changed'
    with pytest.raises(ValueError):load_explanations(m,data,root)

@pytest.mark.parametrize('value',['../outside.html','/outside.html','<script>x</script>','<img onerror="x">','<a href="javascript:alert(1)">x</a>','<article id="x">x</article>'])
def test_unsafe_fragment_rejected(tmp_path,value):
    m,root,data=setup(tmp_path)
    if value.startswith(('/','..')):m['problems'][0]['explanation_fragment']=value
    else:(root/m['problems'][0]['explanation_fragment']).write_text(FRAGMENT+value)
    with pytest.raises(ValueError):load_explanations(m,data,root)

def test_symlink_rejected(tmp_path):
    m,root,data=setup(tmp_path);path=root/m['problems'][0]['explanation_fragment']
    original=path.read_text();path.unlink();other=tmp_path/'outside.html';other.write_text(original);path.symlink_to(other)
    with pytest.raises(ValueError):load_explanations(m,data,root)

@pytest.mark.parametrize('key',['understand','start','solve','verify','pitfall','retry','sum'])
def test_required_learning_sections(tmp_path,key):
    m,root,data=setup(tmp_path)
    (root/m['problems'][0]['explanation_fragment']).write_text(FRAGMENT.replace(key,'removed'))
    with pytest.raises(ValueError):load_explanations(m,data,root)
