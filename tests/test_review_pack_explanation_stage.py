from pathlib import Path
import hashlib,json
import pytest
from tests.test_review_pack_explanation_content import setup,FRAGMENT
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack
from scripts.lab.review_pack.explanation_stage import prepare_explanation_stage
from scripts.lab.review_pack.explanation_checks import check_explanations
ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')

def pack(tmp_path):
    m,run,data=setup(tmp_path)
    del m['problem_explanation_version'];del m['explanation_checks']
    folder=tmp_path/'pack';paths=assemble(m,run,folder,ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    (folder/'실험04_기출문제.pdf').write_bytes(b'pdf-preserve')
    m['generated_files']=sorted(str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file())
    (folder/'.pack/manifest.json').write_text(json.dumps(m,ensure_ascii=False))
    (folder/'사용자메모.md').write_text('사용자 기록')
    return folder,run/'problem-explanations'

def hashes(folder):return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}

def test_stage_preserves_existing_bytes(tmp_path):
    folder,author=pack(tmp_path);before=hashes(folder)
    stage=prepare_explanation_stage(folder,author,tmp_path/'stage')
    after=hashes(stage)
    assert hashes(folder)==before
    assert '사용자메모.md' not in after
    for name,value in before.items():
        if name not in {'.pack/manifest.json','사용자메모.md'}:assert after[name]==value
    m=json.loads((stage/'.pack/manifest.json').read_text())
    assert check_explanations(stage,m)==[]
    assert set(m['generated_files'])==set(after)
    assert m['explanation_checks']['browser']=='not_run'

def test_failed_stage_never_mutates_source(tmp_path):
    folder,author=pack(tmp_path);before=hashes(folder)
    (author/'q-mux-001.html').unlink()
    with pytest.raises(ValueError):prepare_explanation_stage(folder,author,tmp_path/'stage')
    assert hashes(folder)==before

def test_explanation_only_rerun_is_deterministic(tmp_path):
    folder,author=pack(tmp_path)
    a=prepare_explanation_stage(folder,author,tmp_path/'a');b=prepare_explanation_stage(folder,author,tmp_path/'b')
    assert hashes(a)==hashes(b)
    with pytest.raises(ValueError):prepare_explanation_stage(folder,author,a)

@pytest.mark.parametrize('mutation',['delete','body','link'])
def test_check_detects_missing_or_modified_explanation(tmp_path,mutation):
    folder,author=pack(tmp_path);stage=prepare_explanation_stage(folder,author,tmp_path/'stage')
    path=stage/'실험04_문제설명.html';m=json.loads((stage/'.pack/manifest.json').read_text())
    if mutation=='delete':path.unlink()
    else:path.write_text(path.read_text().replace('Y=I0예요.','removed' if mutation=='body' else '<a href="missing.html#x">Y</a>'))
    assert check_explanations(stage,m)

def test_unreviewed_explanation_cannot_publish(tmp_path):
    from scripts.lab.review_pack.publish import publish
    folder,author=pack(tmp_path);stage=prepare_explanation_stage(folder,author,tmp_path/'stage')
    with pytest.raises(ValueError,match='문제설명 검토'):publish(stage,tmp_path/'복습노트/실험04',tmp_path)

def test_original_publish_guards_remain(tmp_path):
    folder,author=pack(tmp_path);before=hashes(folder)
    (folder/'.pack/assets/widgets.js').unlink()
    with pytest.raises(ValueError):prepare_explanation_stage(folder,author,tmp_path/'stage')
    assert hashes(folder)=={k:v for k,v in before.items() if k!='.pack/assets/widgets.js'}

def test_duplicate_html_id_cannot_break_question_navigation(tmp_path):
    folder,author=pack(tmp_path)
    path=author/'q-mux-001.html'
    path.write_text(path.read_text().replace('선택선이 고른 입력을 찾아요.','<span id="q-mux-001">선택선이 고른 입력을 찾아요.</span>'))
    with pytest.raises(ValueError,match='duplicate ID'):
        prepare_explanation_stage(folder,author,tmp_path/'stage')

def test_workbook_question_and_review_anchors_are_valid(tmp_path):
    folder,author=pack(tmp_path)
    path=author/'q-mux-001.html'
    path.write_text(path.read_text().replace('Y=I0예요.','Y=I0예요. <a href="{{REVIEW_HREF}}#q-mux-001">기출풀이의 같은 문항</a>'))
    stage=prepare_explanation_stage(folder,author,tmp_path/'stage')
    m=json.loads((stage/'.pack/manifest.json').read_text())
    assert check_explanations(stage,m)==[]
