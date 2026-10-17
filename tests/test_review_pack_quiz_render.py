import hashlib,json
from pathlib import Path
import pytest
from tests._workbook_fixture import create_workbook_run
from scripts.lab.review_pack.workbook_content import load_workbook_content,build_workbook_data
from scripts.lab.review_pack.workbook_render import render_workbook_html,apply_local_patches

ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')


def test_unversioned_render_matches_baseline(tmp_path):
    m,run=create_workbook_run(tmp_path);rows=load_workbook_content(m,run)
    hashes=json.loads(Path('tests/fixtures/review_pack/quiz-legacy-render-sha256.json').read_text())
    for mode in ('problems','answers'):
        assert hashlib.sha256(render_workbook_html(build_workbook_data(m,rows,mode),ASSETS).encode()).hexdigest()==hashes[mode]


@pytest.mark.parametrize('version',[True,0,2,'1',None])
def test_renderer_rejects_unsupported_explicit_quiz_version(tmp_path,version):
    m,run=create_workbook_run(tmp_path);data=build_workbook_data(m,load_workbook_content(m,run),'problems')
    data['meta']['quiz_practice_version']=version
    with pytest.raises(ValueError,match='quiz_practice_version'):render_workbook_html(data,ASSETS)


@pytest.mark.parametrize('name',['problem.html','answer.html'])
def test_quiz_patch_anchor_fail_closed(name):
    from scripts.lab.review_pack.quiz_practice_patches import apply_quiz_patches
    text=apply_local_patches((ASSETS/'workbook'/name).read_text(encoding='utf-8'),name)
    apply_quiz_patches(text,name)
    with pytest.raises(ValueError):apply_quiz_patches('',name)
    with pytest.raises(ValueError):apply_quiz_patches(text+text,name)
