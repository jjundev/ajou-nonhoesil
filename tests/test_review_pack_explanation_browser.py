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
    page.locator('#toggle-right').click()
    assert page.locator('#panel-right .sum:not([hidden])').count()==1
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
