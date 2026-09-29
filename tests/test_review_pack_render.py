from pathlib import Path
import pytest
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.render import assemble

ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')
RUN=Path('tests/fixtures/review_pack')

def test_assemble_keeps_solution_and_links(tmp_path):
    paths=assemble(fixture(),RUN,tmp_path/'stage',ASSETS)
    review=paths['review_html'].read_text(encoding='utf-8')
    assert 'I0입니다.' in review
    assert '실험04_실험설명.html#t-mux' in review
    assert '새 연습' in review
    assert paths['audit'].is_file()
    assert (tmp_path/'stage/assets/vendor/katex/katex.min.js').is_file()

def test_biology_navigation_and_templates(tmp_path):
    paths=assemble(fixture(),RUN,tmp_path/'stage',ASSETS)
    note=paths['note_html'].read_text(encoding='utf-8')
    review=paths['review_html'].read_text(encoding='utf-8')
    assert 'data-screens="article.topic"' in note
    assert 'class="topic"' in note
    assert 'class="card"' in review
    assert 'id="pager-ui"' in note and 'id="panels-ui"' in note
    assert 'href="https://cdn.' not in note

def test_missing_questions_are_explicit(tmp_path):
    m=fixture();m['problems']=[]
    paths=assemble(m,RUN,tmp_path/'stage',ASSETS)
    assert '수록할 문항이 없습니다' in paths['review_html'].read_text(encoding='utf-8')

def test_preserve_existing_stage(tmp_path):
    (tmp_path/'keep.txt').write_text('user')
    with pytest.raises(ValueError):
        assemble(fixture(),RUN,tmp_path,ASSETS)
    assert (tmp_path/'keep.txt').read_text()=='user'

def test_disputed_answer_not_labelled_verified(tmp_path):
    m=fixture();m['problems'][0].update(answer_status='disputed',given_answer='I1')
    paths=assemble(m,RUN,tmp_path/'stage',ASSETS)
    text=paths['review_html'].read_text(encoding='utf-8')
    assert '답안 충돌' in text and 'I1' in text
