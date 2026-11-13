"""Right panels retain aids/summaries without copying the current main title.

A copied heading, stale summary, removed state key, or broken stage builder is
observable here in a real HTTP browser, using existing authoring fixtures.
"""
from contextlib import contextmanager
from copy import deepcopy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from threading import Thread
from urllib.parse import quote

import pytest
from playwright.sync_api import sync_playwright

from scripts.lab.review_pack.explanation_render import write_explanations
from scripts.lab.review_pack.render import assemble
from tests.test_review_pack_explanation_content import setup
from tests.test_review_pack_manifest import fixture

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')
RUN = Path('tests/fixtures/review_pack')
VIEWPORTS = [(1280, 900), (375, 812)]


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        with p.chromium.launch(channel='chrome') as browser:
            yield browser


@contextmanager
def served(folder):
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass
    root = folder.resolve().parent
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/{quote(folder.name)}/'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def open_right(page):
    if page.locator('.layout').get_attribute('data-right') != 'open':
        page.locator('#toggle-right').click()
    assert page.locator('#panel-right-title').is_visible()


def close_right(page):
    if page.viewport_size['width'] < 1024:
        page.locator('#panel-right [data-panel-close]').click()


def assert_summary(page, current_title, expected_summary):
    open_right(page)
    assert page.locator('main h3', has_text=current_title).is_visible()
    assert page.locator('#panel-right').get_by_text(current_title, exact=True).count() == 0
    assert page.locator('#panel-right .sum:not([hidden])').count() == 1
    assert page.locator('#panel-right .sum:not([hidden])').inner_text() == expected_summary
    assert page.locator('#sum-for').count() == 1
    assert page.locator('#panel-right .sums#sum-for').count() == 1


@pytest.mark.parametrize('viewport', VIEWPORTS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_generated_note_and_legacy_review_panel_copy(browser, tmp_path, viewport, theme):
    m = fixture()
    run = tmp_path/'run'
    shutil.copytree(RUN, run)
    first = run/m['topics'][0]['fragment']
    first.write_text(first.read_text()+'<div class="sum" hidden>선택선 0은 I0를 골라요.</div>')
    m['topics'].append(dict(deepcopy(m['topics'][0]), id='t-other', title='입력 번호를 골라요', fragment='sections/t-other.html'))
    (run/'sections/t-other.html').write_text('<p>선택선 1은 I1을 골라요.</p><div class="sum" hidden>선택선 1은 I1을 골라요.</div>')
    paths = assemble(m, run, tmp_path/'stage', ASSETS)
    with served(tmp_path/'stage') as base:
        ctx = browser.new_context(viewport=dict(zip(('width', 'height'), viewport)), color_scheme=theme)
        try:
            page = ctx.new_page(); page_errors = []
            page.on('pageerror', lambda e: page_errors.append(str(e)))
            page.goto(base+quote(paths['note_html'].name))
            open_right(page)
            assert page.locator('#sum-empty').is_visible()
            assert page.locator('#panel-right .sum:not([hidden])').count() == 0
            close_right(page)
            page.locator('#pager-next').click()
            assert_summary(page, '선택 신호', '선택선 0은 I0를 골라요.')
            close_right(page)
            page.locator('#pager-next').click()
            assert_summary(page, '입력 번호를 골라요', '선택선 1은 I1을 골라요.')
            assert page.locator('#panel-right .sum', has_text='선택선 0은 I0를 골라요.').is_hidden()
            key = 'od-note-read:logic-lab-04'
            assert json.loads(page.evaluate('(k)=>localStorage.getItem(k)', key)) == ['t-mux', 't-other']
            page.reload(); assert_summary(page, '입력 번호를 골라요', '선택선 1은 I1을 골라요.')
            page.goto(base+quote(paths['review_html'].name)+'#q-mux-001')
            title = page.locator('main article.card h3').inner_text()
            open_right(page)
            assert page.locator('main h3', has_text=title).is_visible()
            assert page.locator('#panel-right').get_by_text(title, exact=True).count() == 0
            for label, content in [('힌트', '선택선과 입력 번호를 연결하세요.'), ('풀이', 'I0입니다.')]:
                page.locator('#panel-right summary', has_text=label).click()
                assert page.locator('#panel-right').get_by_text(content, exact=True).is_visible()
            page.locator('#solved-btn').click()
            assert page.locator('#solved-btn').get_attribute('aria-pressed') == 'true'
            solved = 'od-review-solved:logic-lab-04'
            assert json.loads(page.evaluate('(k)=>sessionStorage.getItem(k)', solved)) == ['q-mux-001']
            page.reload(); open_right(page)
            assert page.locator('#solved-btn').get_attribute('aria-pressed') == 'true'
            page.locator('#solved-btn').click()
            assert json.loads(page.evaluate('(k)=>sessionStorage.getItem(k)', solved)) == []
            assert json.loads(page.evaluate('(k)=>localStorage.getItem(k)', key)) == ['t-mux', 't-other']
            assert page_errors == []
        finally:
            ctx.close()


@pytest.mark.parametrize('viewport', VIEWPORTS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_explanation_panel_copy(browser, tmp_path, viewport, theme):
    m, run, data = setup(tmp_path)
    m['problems'][0]['title'] = data['problems'][0]['title'] = '수식 $Y=I_0$ 선택'
    stage = tmp_path/'stage'
    paths = assemble(m, run, stage, ASSETS)
    # Exercise the direct explanation API with the same shell and preserved raw problem.
    paths.update(write_explanations(m, data, run, stage, ASSETS))
    with served(stage) as base:
        ctx = browser.new_context(viewport=dict(zip(('width', 'height'), viewport)), color_scheme=theme)
        try:
            page = ctx.new_page(); page_errors = []
            page.on('pageerror', lambda e: page_errors.append(str(e)))
            page.goto(base+quote(paths['explanation_html'].name)+'#q-mux-001')
            page.wait_for_selector('main h3 .katex')
            title = ' '.join(page.locator('main h3').text_content().split())
            assert_summary(page, title, '떠올릴 것: 선택선 값 = 고를 입력 번호\n\nS를 읽고 입력을 골라요.')
            assert page.locator('main h3 .katex').is_visible()
            assert page.locator('main').get_by_text('問題', exact=True).is_visible()
            assert page.locator('[data-explanation="solve"]').is_visible()
            close_right(page)
            page.locator('#pager-prev').click()
            open_right(page); assert page.locator('#sum-empty').is_visible()
            close_right(page)
            page.locator('#pager-next').click()
            assert_summary(page, title, '떠올릴 것: 선택선 값 = 고를 입력 번호\n\nS를 읽고 입력을 골라요.')
            assert json.loads(page.evaluate('localStorage.getItem("od-note-read:logic-lab-04-problem-explanation")')) == ['q-mux-001']
            assert page.locator('.katex-error').count() == 0
            assert page_errors == []
        finally:
            ctx.close()


@pytest.fixture(scope='module')
def chip_stage(tmp_path_factory):
    stage = tmp_path_factory.mktemp('chip-panel-stage')
    pack = stage/'.pack'; pack.mkdir()
    source = Path('복습노트/칩 정리/.pack').resolve()
    # build imports a sibling module. Add only this read-only source directory.
    sys.path.insert(0, str(source))
    try:
        spec = importlib.util.spec_from_file_location('task7_chip_builder', source/'build.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for name in ('mcq.json', 'mcq.css', 'mcq.js'):
            shutil.copy2(source/name, pack/name)
        module.OUT, module.PACK = stage, pack
        module.build()
    finally:
        sys.path.remove(str(source))
    assert json.loads((pack/'questions.json').read_text()) == json.loads((source/'questions.json').read_text())
    assert json.loads((pack/'chips.json').read_text()) == json.loads((source/'chips.json').read_text())
    return stage


@pytest.mark.parametrize('viewport', VIEWPORTS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_chip_pages_use_current_panel_contract(browser, chip_stage, viewport, theme):
    with served(chip_stage) as base:
        ctx = browser.new_context(viewport=dict(zip(('width', 'height'), viewport)), color_scheme=theme)
        try:
            page = ctx.new_page(); page_errors = []
            page.on('pageerror', lambda e: page_errors.append(str(e)))
            for filename, anchor, expected in [
                ('정리노트.html', 'common', '노치 기준 위에서 보기. /는 Active Low. 실제 입력 고정·출력 미연결·NC 미연결을 구분해요.'),
                ('문제설명.html', 'q01', 'NAND · 2입력 4개'),
            ]:
                page.goto(base+quote(filename)+'#'+anchor)
                title = page.locator('main article.is-current h3').inner_text()
                assert_summary(page, title, expected)
            page.goto(base+quote('문제풀이.html')+'#q01')
            title = page.locator('main article.is-current h3').inner_text()
            open_right(page)
            assert page.locator('#panel-right').get_by_text(title, exact=True).count() == 0
            assert page.locator('#sum-empty').is_visible()
            close_right(page)
            page.locator('article.is-current .practice-hint summary').click()
            assert page.locator('article.is-current .practice-hint p').is_visible()
            assert page.locator('article.is-current .mcq-choice').count() > 0
            assert page_errors == []
        finally:
            ctx.close()
