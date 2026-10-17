import json,hashlib
from pathlib import Path
import pytest
from tests._quiz_practice_fixture import create_quiz_run
from tests._workbook_fixture import create_workbook_run
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.workbook_render import read_workbook_payload,render_workbook_html
from scripts.lab.review_pack.workbook_md import write_workbook_md
from scripts.lab.review_pack.publish import publish

ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')


def hashes(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}


def build(m,run,stage):
    paths=assemble(m,run,stage,ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    return paths


def test_workbook_check_runs_without_explanation(tmp_path):
    m,run=create_workbook_run(tmp_path);stage=tmp_path/'stage';paths=build(m,run,stage)
    for key in ('question','review'):
        d=read_workbook_payload(paths[key+'_html']);d['problems'][0]['html']['conditions']='<a href="answer.html">정답</a>'
        paths[key+'_html'].write_text(render_workbook_html(d,ASSETS),encoding='utf-8')
        write_workbook_md(d,m,paths[key+'_md'])
    assert any('question hyperlink' in e for e in check_pack(stage))


def test_policy_pack_build_has_all_eleven_ids(tmp_path):
    m,run=create_quiz_run(tmp_path);stage=tmp_path/'stage';paths=build(m,run,stage)
    expected=[p['id'] for p in m['problems']]
    for key in ('question','review'):
        assert [p['id'] for p in read_workbook_payload(paths[key+'_html'])['problems']]==expected
    for key in ('question_md','review_md','explanation_md'):
        text=paths[key].read_text(encoding='utf-8');positions=[text.index(f'id="{ident}"') for ident in expected]
        assert positions==sorted(positions)
    text=paths['explanation_html'].read_text(encoding='utf-8');assert all(ident in text for ident in expected)
    assert sum(p.suffix=='.html' for p in stage.iterdir())==4
    assert (stage/'.pack/실험04_실험설명.md').is_file()
    assert all(paths[k].is_file() for k in ('question_md','review_md','explanation_md'))
    assert check_pack(stage)==[]


def test_quota_failure_blocks_build_and_publish(tmp_path):
    m,run=create_quiz_run(tmp_path);stage=tmp_path/'stage';build(m,run,stage)
    dest=tmp_path/'복습노트/실험04';dest.mkdir(parents=True);(dest/'memo').write_bytes(b'keep');before=hashes(dest)
    m['problems'][1].update(status='held',reason='자료 미확인')
    with pytest.raises(ValueError,match='true_false'):build(m,run,tmp_path/'bad')
    (stage/'.pack/manifest.json').write_text(json.dumps(m),encoding='utf-8')
    with pytest.raises(ValueError,match='true_false'):publish(stage,dest,tmp_path)
    assert hashes(dest)==before


def test_repeated_build_and_rerender_do_not_accumulate(tmp_path):
    from scripts.lab.review_pack.workbook_rerender import rerender_workbook
    m,run=create_quiz_run(tmp_path);a=tmp_path/'a';b=tmp_path/'b';build(m,run,a);build(m,run,b)
    assert hashes(a)==hashes(b)
    rerender_workbook(a);first=hashes(a);rerender_workbook(a)
    assert hashes(a)==first
    assert len(read_workbook_payload(a/'실험04_기출문제.html')['problems'])==11


@pytest.mark.parametrize('quiz',[False,True])
def test_explanation_only_keeps_workbook_and_pdf_bytes(tmp_path,quiz):
    from scripts.lab.review_pack.explanation_stage import prepare_explanation_stage
    from tests._explanation_recall_fixture import setup_v2
    if quiz:m,run=create_quiz_run(tmp_path)
    else:m,run,_=setup_v2(tmp_path)
    stage=tmp_path/'stage';build(m,run,stage)
    (stage/'실험04_기출문제.pdf').write_bytes(b'preserve question PDF')
    (stage/'실험04_기출풀이.pdf').write_bytes(b'preserve answer PDF')
    m['generated_files']=sorted(hashes(stage))
    (stage/'.pack/manifest.json').write_text(json.dumps(m),encoding='utf-8');before=hashes(stage)
    out=prepare_explanation_stage(stage,run/'problem-explanations',tmp_path/'new')
    assert hashes(stage)==before
    for name,value in before.items():
        if any(label in name for label in ('기출문제','기출풀이')):assert hashes(out)[name]==value


def publish_quiz_fixture(tmp_path):
    """Test-only review flags to exercise the publisher, not evidence of actual review."""
    m,run=create_quiz_run(tmp_path)
    for s in m['sources']:
        p=tmp_path/s['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'test source')
        s['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    for checks in (m['checks'],m['explanation_checks']):checks.update(source_visual='pass',content='self_review',browser='pass')
    reg=run/m['figure_manifest'];obj=json.loads(reg.read_text(encoding='utf-8'))
    for row in obj['figures']:row.update(review_status='pass',review_notes='Test fixture only')
    reg.write_text(json.dumps(obj),encoding='utf-8')
    stage=tmp_path/'stage';build(m,run,stage);m['generated_files']=sorted(hashes(stage))
    (stage/'.pack/manifest.json').write_text(json.dumps(m),encoding='utf-8')
    dest=tmp_path/'복습노트/실험04';publish(stage,dest,tmp_path)
    return dest
