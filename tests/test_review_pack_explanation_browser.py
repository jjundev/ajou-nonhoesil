from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright
from tests.test_review_pack_explanation_content import setup
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack

@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        with p.chromium.launch(channel='chrome') as b:yield b

@pytest.fixture
def pages(tmp_path):
    m,run,data=setup(tmp_path)
    paths=assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    return paths

@pytest.mark.parametrize('width',[375,1280])
@pytest.mark.parametrize('theme',['light','dark'])
def test_explanation_navigation(browser,pages,width,theme):
    ctx=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(pages['explanation_html'].as_uri()+'#q-mux-001')
    page.wait_for_function('document.querySelector("article.topic").getAttribute("aria-hidden") !== "true"')
    if width<1024:page.locator('#toggle-left').click()
    assert page.locator('.toc-list a').count()==1
    page.locator('.toc-list a').click()
    assert page.locator('.toc a[aria-current="true"]').get_attribute('href')=='#q-mux-001'
    if width<1024:assert page.locator('.layout').get_attribute('data-left')=='closed'
    if page.locator('.layout').get_attribute('data-right')!='open':page.locator('#toggle-right').click()
    assert page.locator('#panel-right .sum:not([hidden])').is_visible()
    assert page.locator('.pack-nav,#progress-n,#progress-total,#progress-bar').count()==0
    assert page.locator('.katex-error').count()==0
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
    ctx.close()

def test_read_state_isolated(browser,pages):
    ctx=browser.new_context();page=ctx.new_page()
    page.goto(pages['note_html'].as_uri()+'#t-mux')
    page.locator('#pager-next').click()
    before=page.evaluate('({...localStorage})')
    page.goto(pages['explanation_html'].as_uri()+'#q-mux-001')
    page.locator('#pager-prev').click()
    after=page.evaluate('({...localStorage})')
    assert after.get('od-note-read:logic-lab-04')==before.get('od-note-read:logic-lab-04')
    assert 'od-note-read:logic-lab-04-problem-explanation' in after
    page.reload()
    assert page.evaluate('localStorage.getItem("od-note-read:logic-lab-04-problem-explanation")')
    ctx.close()

@pytest.mark.parametrize('hash_value',['#missing','#%'])
def test_no_js_and_invalid_hash(browser,pages,hash_value):
    page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(pages['explanation_html'].as_uri()+hash_value)
    assert not errors;page.close()
    ctx=browser.new_context(java_script_enabled=False);page=ctx.new_page()
    page.goto(pages['explanation_html'].as_uri())
    assert page.locator('article.topic').is_visible()
    assert page.locator('[data-explanation="solve"]').is_visible()
    assert page.locator('.toc-list a').is_visible();ctx.close()

@pytest.mark.parametrize('number',range(1,6))
@pytest.mark.parametrize('width',[375,1280])
@pytest.mark.parametrize('theme',['light','dark'])
def test_all_published_explanation_articles(browser,number,width,theme):
    root=Path(__file__).resolve().parents[1]
    path=root/'복습노트'/f'실험{number:02d}'/f'실험{number:02d}_문제설명.html'
    ctx=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(path.as_uri())
    ids=page.locator('main article.topic').evaluate_all('(a)=>a.map(x=>x.id)')
    assert len(ids)==[12,14,15,12,19][number-1]
    for ident in ids:
        page.evaluate('(id)=>location.hash=id',ident)
        page.wait_for_function('(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ident)
        assert page.locator('#'+ident).is_visible()
        assert page.locator('#'+ident+' [data-explanation="solve"]').is_visible()
        assert page.locator('#'+ident+' .equation-card').evaluate_all('''cards => cards.every(el => {
            const style = getComputedStyle(el);
            return parseFloat(style.borderTopWidth) >= 1 && parseFloat(style.paddingTop) >= 16
                && style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.overflowX === 'auto';
        })''')
        assert_explanation_section_gap(page, '#'+ident+' [data-explanation="understand"]')
        assert page.locator('.katex-error').count()==0
        assert page.locator('img').evaluate_all('(a)=>a.every(x=>x.complete&&x.naturalWidth>0)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
    ctx.close()

@pytest.mark.parametrize('number',range(1,6))
def test_all_published_explanations_without_js(browser,number):
    root=Path(__file__).resolve().parents[1]
    path=root/'복습노트'/f'실험{number:02d}'/f'실험{number:02d}_문제설명.html'
    ctx=browser.new_context(java_script_enabled=False);page=ctx.new_page();page.goto(path.as_uri())
    assert page.locator('article.topic').count()==[12,14,15,12,19][number-1]
    assert page.locator('[data-explanation="verify"]').evaluate_all('(a)=>a.every(x=>getComputedStyle(x).display!=="none")')
    ctx.close()


def assert_explanation_section_gap(page, selector):
    spacing = page.locator(selector).evaluate('''el => {
        const previous = el.previousElementSibling;
        const heading = el.querySelector('.layer-title');
        const style = getComputedStyle(el);
        return {
            gap: heading.getBoundingClientRect().top - previous.getBoundingClientRect().bottom,
            margin: parseFloat(style.marginTop),
            padding: parseFloat(style.paddingTop),
            border: parseFloat(style.borderTopWidth)
        };
    }''')
    assert spacing['gap'] >= 48, spacing
    assert spacing['margin'] >= 24, spacing
    assert spacing['padding'] >= 24, spacing
    assert spacing['border'] >= 1, spacing


@pytest.mark.parametrize('width', [375, 1280])
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_generated_explanation_separates_problem_from_first_instruction(browser, pages, width, theme):
    ctx = browser.new_context(viewport=dict(width=width, height=900), color_scheme=theme)
    page = ctx.new_page()
    page.goto(pages['explanation_html'].as_uri() + '#q-mux-001')
    assert_explanation_section_gap(page, '#q-mux-001 [data-explanation="understand"]')
    note = Path(__file__).resolve().parents[1] / '복습노트/실험04/실험04_실험설명.html'
    page.goto(note.as_uri())
    assert page.locator('article.topic .layer.eli5').first.evaluate('el => parseFloat(getComputedStyle(el).marginTop)') == 0
    ctx.close()


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_formula_card_scroll_does_not_turn_the_page(browser, theme):
    root = Path(__file__).resolve().parents[1]
    ctx = browser.new_context(viewport=dict(width=375, height=900), color_scheme=theme, has_touch=True)
    page = ctx.new_page()
    page.goto((root/'복습노트/실험03/실험03_문제설명.html').as_uri() + '#q-fa-design')
    card = page.locator('#q-fa-design .equation-card').first
    assert card.is_visible()
    assert card.evaluate('el => el.scrollWidth > el.clientWidth')
    card.evaluate('''el => {
        el.dispatchEvent(new TouchEvent('touchstart', {bubbles:true, touches:[new Touch({identifier:1,target:el,clientX:300,clientY:200})]}));
        el.dispatchEvent(new TouchEvent('touchend', {bubbles:true, changedTouches:[new Touch({identifier:1,target:el,clientX:100,clientY:200})]}));
    }''')
    assert page.evaluate('location.hash') == '#q-fa-design'
    card.evaluate('el => el.scrollLeft = 60')
    assert card.evaluate('el => el.scrollLeft') > 0
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    ctx.close()
