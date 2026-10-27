from pathlib import Path
import shutil
import pytest
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.render import assemble

ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')
RUN=Path('tests/fixtures/review_pack')
CARD_SNIPPET='<div class="table-wrap"><table><thead><tr><th>S</th><th>Y</th></tr></thead><tbody><tr><td>0</td><td>I0</td></tr></tbody></table></div><p>$$Y=\\overline{S}I_0+SI_1$$</p><p>선택선 $S$가 0이면 $Y=I_0$예요.</p>'

def run_with_cards(tmp_path):
    run=tmp_path/'run'
    shutil.copytree(RUN,run)
    for name in ('sections/t-mux.html','problems/q-mux-001.html'):
        path=run/name
        path.write_text(path.read_text(encoding='utf-8')+CARD_SNIPPET,encoding='utf-8')
    return run

def test_note_wraps_tables_and_equations(tmp_path):
    paths=assemble(fixture(),run_with_cards(tmp_path),tmp_path/'stage',ASSETS)
    note=paths['note_html'].read_text(encoding='utf-8')
    assert '<div class="table-wrap"><div class="table-card" role="group" aria-label="표"><table>' in note
    assert '<div class="equation-card" role="group" aria-label="수식"><p>$$Y=\\overline{S}I_0+SI_1$$</p></div>' in note
    assert 'aria-label="표"' not in paths['review_html'].read_text(encoding='utf-8')

def test_note_cards_skip_prose_with_inline_math(tmp_path):
    paths=assemble(fixture(),run_with_cards(tmp_path),tmp_path/'stage',ASSETS)
    note=paths['note_html'].read_text(encoding='utf-8')
    assert '<p>선택선 $S$가 0이면 $Y=I_0$예요.</p>' in note
    assert note.count('aria-label="수식"')==1

def test_assemble_keeps_solution_and_links(tmp_path):
    paths=assemble(fixture(),RUN,tmp_path/'stage',ASSETS)
    review=paths['review_html'].read_text(encoding='utf-8')
    assert 'I0입니다.' in review
    assert '실험04_실험설명.html#t-mux' in review
    assert '새 연습' in review
    assert paths['audit'].is_file()
    assert (tmp_path/'stage/.pack/assets/vendor/katex/katex.min.js').is_file()

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
def test_toc_supplies_flat_article_links(tmp_path):
    from scripts.lab.review_pack.html2md import Parser, Node
    paths = assemble(fixture(), RUN, tmp_path/'stage', ASSETS)
    for kind in ('note_html', 'review_html'):
        parser = Parser()
        parser.feed(paths[kind].read_text(encoding='utf-8'))
        nav = next(n for n in parser.root.walk() if n.tag == 'nav' and n.attrs.get('class') == 'toc')
        hashes = [n.attrs['href'] for n in nav.walk() if n.tag == 'a']
        ids = [n.attrs['id'] for n in parser.root.walk() if n.tag == 'article' and n.attrs.get('class') in ('topic','card')]
        assert hashes == ['#'+id for id in ids]
