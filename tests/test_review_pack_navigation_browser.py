from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            yield browser


@pytest.mark.parametrize('width', [375, 1280])
@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('number', range(1, 6))
def test_published_navigation(browser, width, theme, number):
    context = browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme)
    page = context.new_page()
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    folder = ROOT/'복습노트'/f'실험{number:02d}'
    path = folder/f'실험{number:02d}_실험설명.html'
    page.goto(path.as_uri())
    page.wait_for_function('document.querySelectorAll(".toc-list a").length > 0')
    page.evaluate('(t)=>document.documentElement.dataset.theme=t', theme)
    if width < 1024:
        page.locator('#toggle-left').click()
    assert page.locator('.toc').is_visible()
    assert page.locator('.pack-nav').count() == 0
    assert page.locator('.toc a').evaluate_all('(links)=>links.every(a=>a.getAttribute("href").startsWith("#"))')
    assert page.locator('.toc-list').evaluate('(n)=>getComputedStyle(n).paddingLeft') == '0px'
    link = page.locator('.toc-list a').nth(2)
    target = link.get_attribute('href')
    link.click()
    page.wait_for_function('(hash)=>location.hash===hash', arg=target)
    assert page.locator('.toc-list a[aria-current="true"]').get_attribute('href') == target
    if width < 1024:
        assert page.locator('.layout').get_attribute('data-left') == 'closed'
    page.locator('#pager-next').click()
    page.go_back()
    page.wait_for_function('(hash)=>location.hash===hash', arg=target)
    before = page.locator('.toc-mark.is-done').count()
    page.reload()
    page.wait_for_function('document.querySelectorAll(".toc-list a").length > 0')
    assert page.locator('.toc-mark.is-done').count() == before
    assert page.locator('#progress-n, #progress-total, #progress-bar, .nav-label').count() == 0
    page.locator('#toggle-right').click()
    assert page.locator('#panel-right .sum:not([hidden])').count() == 1
    if width < 1024:
        page.locator('#panel-right [data-panel-close]').click()
    else:
        page.locator('#toggle-right').click()
    if page.locator('.layout').get_attribute('data-left') != 'open':
        page.locator('#toggle-left').click()
    if width < 1024:
        page.wait_for_function('document.querySelector(".panel-left").getBoundingClientRect().left >= 0')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.locator('.panel-left .panel-inner').evaluate('(n)=>n.scrollWidth<=n.clientWidth')
    page.locator('.toc a').first.focus()
    assert page.evaluate('document.activeElement.matches(".toc a")')
    if number == 3 and theme == 'dark':
        output = ROOT/'output/validation/navigation'
        output.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output/f'experiment03-{width}-dark.png'))
    page.goto((folder/f'실험{number:02d}_기출풀이.html').as_uri())
    page.wait_for_function('document.documentElement.dataset.ready === "true"', timeout=60000)
    assert page.locator('.page').count() > 0
    page.go_back()
    page.wait_for_function('document.querySelectorAll(".toc-list a").length > 0')
    assert not errors
    assert page.locator('.katex-error').count() == 0
    assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)')
    if number == 4:
        widget = page.locator('[data-widget="mux2"]')
        topic_id = widget.evaluate('(n)=>n.closest("article").id')
        page.goto(path.as_uri() + '#' + topic_id)
        for selector in range(2):
            for i0 in range(2):
                for i1 in range(2):
                    widget.locator('select[name="S"]').select_option(str(selector))
                    widget.locator('input[name="I0"]').set_checked(bool(i0))
                    widget.locator('input[name="I1"]').set_checked(bool(i1))
                    assert widget.locator('output').text_content() == str(i1 if selector else i0)
    page.emulate_media(media='print')
    assert not page.locator('#panel-left').is_visible()
    context.close()


@pytest.mark.parametrize('width', [375, 1280])
def test_navigation_available_without_javascript(browser, width):
    context = browser.new_context(java_script_enabled=False, viewport={'width': width, 'height': 900})
    page = context.new_page()
    page.goto((ROOT/'복습노트/실험03/실험03_실험설명.html').as_uri())
    assert page.locator('.pack-nav').count() == 0
    assert page.locator('.toc-list a').first.is_visible()
    context.close()


@pytest.mark.parametrize('hash_value', ['#missing', '#%'])
def test_invalid_topic_link_keeps_initial_screen(browser, hash_value):
    page = browser.new_page()
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    # Corrupt one topic link: rendering must still work and keep the flat list.
    text = (ROOT/'복습노트/실험03/실험03_실험설명.html').read_text()
    text = text.replace('href="#t-half-adder"', f'href="{hash_value}"')
    from urllib.parse import unquote, urlsplit
    import mimetypes
    def serve(route):
        relative = unquote(urlsplit(route.request.url).path).lstrip('/')
        if relative == 'note.html':
            route.fulfill(content_type='text/html', body=text)
        else:
            resource = ROOT/'복습노트/실험03'/relative
            if resource.is_file():
                route.fulfill(content_type=mimetypes.guess_type(resource.name)[0] or 'application/octet-stream', body=resource.read_bytes())
            else:
                route.abort()
    page.route('http://navigation.test/**', serve)
    page.goto('http://navigation.test/note.html')
    assert page.locator('.toc-list').count() == 1
    assert page.locator('.toc > a, .toc-group').count() == 0
    assert page.locator('.screen.is-current').count() == 1
    assert errors == []
    page.close()


def test_malformed_location_hash_keeps_initial_screen(browser):
    page = browser.new_page()
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((ROOT/'복습노트/실험03/실험03_실험설명.html').as_uri() + '#%')
    assert page.locator('.screen.is-current').count() == 1
    assert errors == []
    page.close()


def test_legacy_pack_has_only_internal_contents(browser, tmp_path):
    from scripts.lab.review_pack.render import assemble
    from tests.test_review_pack_manifest import fixture
    pages = assemble(fixture(), ROOT/'tests/fixtures/review_pack', tmp_path/'stage',
                     ROOT/'.claude/skills/logic-lab-review-pack/assets')
    page = browser.new_page()
    for kind in ('note_html', 'review_html'):
        page.goto(pages[kind].as_uri())
        assert page.locator('.pack-nav').count() == 0
        assert page.locator('.toc a').evaluate_all('(links)=>links.every(a=>a.getAttribute("href").startsWith("#"))')
        assert page.locator('.toc-list a').count() > 0
    page.close()
