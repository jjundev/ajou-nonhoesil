from pathlib import Path

import pytest

from scripts.lab.review_pack.explanation_stage import prepare_explanation_stage
from tests.test_review_pack_explanation_browser import browser


@pytest.fixture(scope='module')
def pilot(tmp_path_factory):
    original = Path('복습노트/실험09').resolve()
    stage = tmp_path_factory.mktemp('problem-panel') / '실험09'
    prepare_explanation_stage(
        original, original / '.pack/problem-explanations', stage, problem_panel=True,
    )
    return original, stage


@pytest.mark.parametrize('entry_point', ['build', 'explain-stage'])
def test_experiment_10_gets_problem_panel_by_default(browser, tmp_path, entry_point):
    from scripts.lab.review_pack.__main__ import main
    from scripts.lab.review_pack.render import assemble
    from tests._explanation_recall_fixture import FRAGMENT_V2, setup_v2
    from tests.test_review_pack_explanation_stage import ASSETS, pack

    stage = tmp_path / 'stage'
    if entry_point == 'build':
        manifest, run, _ = setup_v2(tmp_path)
        manifest['experiment'] = 10
        assemble(manifest, run, stage, ASSETS)
    else:
        original, author = pack(tmp_path, experiment=10)
        (author / 'q-mux-001.html').write_text(FRAGMENT_V2, encoding='utf-8')
        assert main(['explain-stage', '--folder', str(original), '--author-root', str(author), '--stage', str(stage)]) == 0

    for name in ('explanation-panel.css', 'explanation-panel.js'):
        reference = Path('복습노트/실험09/.pack/assets') / name
        assert (stage / '.pack/assets' / name).read_bytes() == reference.read_bytes()
    page = browser.new_page(viewport={'width': 1280, 'height': 650})
    try:
        page.goto((stage / '실험10_문제설명.html').as_uri() + '#q-mux-001')
        panel = page.locator('#panel-prob')
        assert panel.locator('[data-problem-reading="q-mux-001"]').is_visible()
        panel.get_by_role('button', name='띄우기').click()
        assert panel.get_by_role('button', name='문제 창 크기 조절').is_visible()
        page.set_viewport_size({'width': 375, 'height': 812})
        page.get_by_text('문제 보기', exact=True).click()
        assert page.locator('main [data-problem-reading="q-mux-001"]').is_visible()
    finally:
        page.close()


@pytest.mark.parametrize('width', [375, 1280])
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_problem_follows_current_question(browser, pilot, width, theme):
    _, stage = pilot
    with browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme) as context:
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((stage / '실험09_문제설명.html').as_uri())
        ids = page.locator('main article.topic').evaluate_all('nodes => nodes.map(node => node.id)')
        assert len(ids) == 19
        for ident in ids:
            page.evaluate('id => { location.hash = id; }', ident)
            article = page.locator(f'article[id="{ident}"].is-current')
            article.wait_for()
            if width < 1024:
                article.get_by_text('문제 보기', exact=True).click()
                problem = article.locator('[data-problem-reading]')
            else:
                problem = page.locator('#panel-prob [data-problem-reading]')
            assert problem.is_visible()
            assert problem.get_attribute('data-problem-reading') == ident
            assert article.locator('[data-explanation="solve"]').is_visible()
            assert page.locator('#panel-right .sum:not([hidden])').count() == 1
            assert page.locator('.katex-error').count() == 0
            assert page.locator('img').evaluate_all('images => images.every(image => image.complete && image.naturalWidth > 0)')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors


def test_docking_navigation_and_fallback(browser, pilot):
    original, stage = pilot
    assert (stage / '.pack/실험09_문제설명.md').read_bytes() == (original / '.pack/실험09_문제설명.md').read_bytes()
    url = (stage / '실험09_문제설명.html').as_uri()
    with browser.new_context(viewport={'width': 1280, 'height': 900}) as context:
        page = context.new_page()
        page.goto(url)
        page.locator('#pager-next').click()
        panel = page.locator('#panel-prob')
        assert panel.is_visible()
        for name in ('왼쪽에 붙이기', '오른쪽에 붙이기', '띄우기'):
            button = panel.get_by_role('button', name=name)
            assert button.get_attribute('title') == name
            assert button.locator('svg[aria-hidden="true"]').is_visible()
            assert button.inner_text() == ''
        content = page.locator('.content')
        summary = page.locator('#panel-right')
        toggle = page.locator('#toggle-prob')
        assert panel.bounding_box()['x'] + panel.bounding_box()['width'] == pytest.approx(content.bounding_box()['x'], abs=1)
        assert toggle.evaluate('node => node.previousElementSibling.id') == 'toggle-left'
        panel.get_by_role('button', name='오른쪽에 붙이기').click()
        assert summary.is_visible()
        assert content.bounding_box()['x'] + content.bounding_box()['width'] == pytest.approx(panel.bounding_box()['x'], abs=1)
        assert panel.bounding_box()['x'] + panel.bounding_box()['width'] == pytest.approx(summary.bounding_box()['x'], abs=1)
        assert toggle.evaluate('node => node.nextElementSibling.id') == 'toggle-right'
        panel.get_by_role('button', name='띄우기').click()
        assert panel.evaluate('node => getComputedStyle(node).position') == 'fixed'
        move = panel.get_by_role('button', name='문제 창 이동')
        assert move.locator('svg[aria-hidden="true"]').is_visible()
        move.focus()
        old_x = panel.bounding_box()['x']
        move.press('ArrowLeft')
        assert panel.bounding_box()['x'] < old_x
        assert panel.get_by_role('link', name='문제지 PDF').get_attribute('href').endswith('.pdf')
        page.locator('.toc-list a').last.click()
        last_id = page.locator('article.is-current').get_attribute('id')
        assert panel.locator('[data-problem-reading]').get_attribute('data-problem-reading') == last_id
        page.locator('#pager-prev').click()
        assert panel.locator('[data-problem-reading]').get_attribute('data-problem-reading') != last_id
        panel.get_by_role('button', name='왼쪽에 붙이기').click()
        page.set_viewport_size({'width': 1024, 'height': 768})
        page.locator('#toggle-right').click()
        assert page.locator('#panel-right').is_visible()
        assert content.bounding_box()['width'] >= 320
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.emulate_media(media='print')
        page.wait_for_function('document.querySelectorAll("main details.problem-inline[open]").length === 19')
        assert page.locator('main [data-problem-reading]').count() == 19
        page.emulate_media(media='screen')
        panel.locator('[data-problem-reading]').wait_for(state='visible')
        page.set_viewport_size({'width': 375, 'height': 900})
        assert panel.is_hidden()
        assert page.locator('article.is-current').get_by_text('문제 보기', exact=True).is_visible()
    with browser.new_context(java_script_enabled=False) as context:
        page = context.new_page()
        page.goto(url)
        assert page.locator('main [data-problem-reading]').count() == 19
        assert page.locator('main [data-problem-reading]').first.is_visible()


def test_floating_window_stays_between_bars_and_docks_at_edges(browser, pilot):
    _, stage = pilot
    url = (stage / '실험09_문제설명.html').as_uri() + '#q-ram-role'
    with browser.new_context(viewport={'width': 1280, 'height': 650}) as context:
        page = context.new_page()
        page.goto(url)
        panel = page.locator('#panel-prob')
        panel.get_by_role('button', name='띄우기').click()
        header = page.locator('.topbar').bounding_box()
        pager = page.locator('.pager').bounding_box()
        initial = panel.bounding_box()
        assert initial['x'] + initial['width'] == pytest.approx(1256, abs=1)
        assert initial['y'] >= header['y'] + header['height']
        assert initial['y'] + initial['height'] <= pager['y'] + 1

        title = panel.get_by_role('heading', name='문제', level=2, exact=True).bounding_box()
        page.mouse.move(title['x'] + 4, title['y'] + 4)
        page.mouse.down()
        page.mouse.move(title['x'] - 120, 2, steps=8)
        page.mouse.up()
        moved = panel.bounding_box()
        assert moved['x'] < initial['x']
        assert moved['y'] == pytest.approx(header['y'] + header['height'], abs=1)

        resize = panel.get_by_role('button', name='문제 창 크기 조절')
        resize.press('ArrowLeft')
        assert panel.bounding_box()['width'] < moved['width']
        corner = resize.bounding_box()
        page.mouse.move(corner['x'] + 8, corner['y'] + 8)
        page.mouse.down()
        page.mouse.move(corner['x'] - 32, corner['y'] - 40, steps=6)
        page.mouse.up()
        assert panel.bounding_box()['height'] < moved['height']

        grip = panel.get_by_role('button', name='문제 창 이동').bounding_box()
        page.mouse.move(grip['x'] + 8, grip['y'] + 8)
        page.mouse.down()
        page.mouse.move(5, grip['y'] + 8, steps=10)
        page.mouse.up()
        assert page.locator('.layout').get_attribute('data-problem-dock') == 'left'

        title = panel.get_by_role('heading', name='문제', level=2, exact=True).bounding_box()
        page.mouse.move(title['x'] + 4, title['y'] + 4)
        page.mouse.down()
        page.mouse.move(760, 300, steps=8)
        assert page.locator('.layout').get_attribute('data-problem-dock') == 'float'
        page.mouse.move(1275, 620, steps=8)
        assert page.locator('.layout').get_attribute('data-problem-snap') == 'right'
        window = panel.bounding_box()
        assert window['y'] + window['height'] <= pager['y'] + 1
        page.mouse.up()
        assert page.locator('.layout').get_attribute('data-problem-dock') == 'right'
