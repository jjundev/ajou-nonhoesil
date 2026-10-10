from pathlib import Path

import pytest

from scripts.lab.review_pack.html2md import Parser
from scripts.lab.review_pack.render import assemble
from tests.test_review_pack_manifest import fixture

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')


def parse(text):
    parser = Parser()
    parser.feed(text)
    return parser.root


def nav(root, cls):
    return next(n for n in root.walk() if n.tag == 'nav' and cls in n.attrs.get('class', '').split())


def test_navigation_only_contains_current_page_sections(tmp_path):
    pages = assemble(fixture(), Path('tests/fixtures/review_pack'), tmp_path/'stage', ASSETS)
    for kind in ('note_html', 'review_html'):
        root = parse(pages[kind].read_text())
        assert not any(n.tag == 'nav' and 'pack-nav' in n.attrs.get('class', '').split() for n in root.walk())
        assert not any(n.attrs.get('id') in {'progress-n', 'progress-total', 'progress-bar'} for n in root.walk())
        assert not any('nav-label' in n.attrs.get('class', '').split() for n in root.walk())
        ids = [n.attrs['id'] for n in root.walk() if n.tag == 'article' and n.attrs.get('class') in ('topic','card')]
        assert [n.attrs['href'] for n in nav(root, 'toc').walk() if n.tag == 'a'] == ['#'+id for id in ids]
        assert not any(n.tag == 'a' for n in nav(root, 'toc').children if hasattr(n, 'tag'))


def test_navigation_checks_boundaries():
    from scripts.lab.review_pack.navigation import check_navigation, render_navigation
    names = {'note_html': 'note.html', 'review_html': 'review.html', 'question_html': 'question.html'}
    slots = render_navigation(names, 'note', [{'id':'t-one','title':'첫 토픽'}])
    assert 'PACK_NAV' not in slots
    page = f'<nav class="toc" aria-label="이 페이지 목차">{slots["TOC"]}</nav><section id="learning"><article class="topic" id="t-one"><h3>첫 토픽</h3></article></section>'
    assert check_navigation(parse(page), 'note.html') == []
    for broken in (
        page.replace(slots['TOC'], slots['TOC'] + '<a href="review.html">풀이</a>'),
        '<nav class="pack-nav">資料</nav>' + page,
        page.replace('#t-one', '#missing'),
        page.replace('aria-label="이 페이지 목차"', 'aria-label="자료 이동"'),
    ):
        assert check_navigation(parse(broken), 'note.html')


def test_pack_check_rejects_mixed_navigation(tmp_path):
    from scripts.lab.review_pack.checks import check_pack
    from scripts.lab.review_pack.html2md import convert_pack
    pages = assemble(fixture(), Path('tests/fixtures/review_pack'), tmp_path/'stage', ASSETS)
    convert_pack(pages['note_html'], pages['review_html'])
    path = pages['note_html']
    text = path.read_text().replace('href="#t-mux"', 'href="실험04_기출풀이.html"')
    path.write_text(text)
    assert any('navigation' in e for e in check_pack(tmp_path/'stage'))


def test_navigation_invalid_kind():
    from scripts.lab.review_pack.navigation import render_navigation
    with pytest.raises(ValueError):
        render_navigation({'note_html': 'note.html'}, 'other')
