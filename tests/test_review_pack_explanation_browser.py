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

@pytest.mark.parametrize('number',range(1,7))
@pytest.mark.parametrize('width',[375,1280])
@pytest.mark.parametrize('theme',['light','dark'])
def test_all_published_explanation_articles(browser,number,width,theme):
    root=Path(__file__).resolve().parents[1]
    path=root/'복습노트'/f'실험{number:02d}'/f'실험{number:02d}_문제설명.html'
    ctx=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(path.as_uri())
    ids=page.locator('main article.topic').evaluate_all('(a)=>a.map(x=>x.id)')
    assert len(ids)==[12,14,15,12,19,24][number-1]
    for ident in ids:
        page.evaluate('(id)=>location.hash=id',ident)
        page.wait_for_function('(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ident)
        assert page.locator('#'+ident).is_visible()
        if width < 1024:
            page.locator('#'+ident+' .problem-inline > summary').click()
        current_surfaces = f'#{ident}, #panel-prob [data-problem-reading="{ident}"]'
        assert page.locator(current_surfaces).locator('table').evaluate_all('(tables)=>tables.every(el=>el.closest(".table-card"))')
        assert page.locator('#'+ident+' [data-explanation="solve"]').is_visible()
        assert page.locator(current_surfaces).locator('.equation-card, .table-card').evaluate_all('''cards => cards.every(el => {
            const style = getComputedStyle(el);
            return parseFloat(style.borderTopWidth) >= 1 && parseFloat(style.paddingTop) >= 16
                && style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.overflowX === 'auto';
        })''')
        for section in ('recall', 'understand'):
            selector = f'#{ident} .layer + [data-explanation="{section}"]'
            if page.locator(selector).count():
                assert_explanation_section_gap(page, selector)
        assert page.locator('.katex-error').count()==0
        assert page.locator('img').evaluate_all('(a)=>a.every(x=>x.complete&&x.naturalWidth>0)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
    ctx.close()

@pytest.mark.parametrize('number',range(1,7))
def test_all_published_explanations_without_js(browser,number):
    root=Path(__file__).resolve().parents[1]
    path=root/'복습노트'/f'실험{number:02d}'/f'실험{number:02d}_문제설명.html'
    ctx=browser.new_context(java_script_enabled=False);page=ctx.new_page();page.goto(path.as_uri())
    assert page.locator('article.topic').count()==[12,14,15,12,19,24][number-1]
    assert page.locator('[data-explanation="verify"]').evaluate_all('(a)=>a.every(x=>getComputedStyle(x).display!=="none")')
    assert page.locator('[data-explanation="recall"]').count()==[12,14,15,12,19,24][number-1]
    assert page.locator('[data-explanation="recall"]').evaluate_all('(a)=>a.every(x=>getComputedStyle(x).display!=="none")')
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
    page.locator('#q-fa-design .problem-inline > summary').click()
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


@pytest.mark.parametrize('width', [375, 1280])
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_generated_wide_table_scrolls_inside_card(browser, tmp_path, width, theme):
    import json
    m, run, data = setup(tmp_path)
    workbook = run / m['problems'][0]['workbook_fragment']
    authored = json.loads(workbook.read_text())
    table = '<table><tr>' + ''.join(f'<th>Input{i}</th>' for i in range(64)) + '</tr><tr>' + '<td></td>' * 64 + '</tr></table>'
    authored['original'] = '<p>표를 채우세요.</p><div class="table-wrap work-table">' + table + '</div>'
    workbook.write_text(json.dumps(authored))
    paths = assemble(m, run, tmp_path/'stage', Path('.claude/skills/logic-lab-review-pack/assets'))
    ctx = browser.new_context(viewport=dict(width=width, height=900), color_scheme=theme, has_touch=True)
    page = ctx.new_page();page.goto(paths['explanation_html'].as_uri()+'#q-mux-001')
    card = page.locator('#q-mux-001 .table-card')
    assert card.is_visible()
    assert card.locator('th').count() == 64
    assert card.locator('td').evaluate_all('cells=>cells.every(el=>el.textContent==="")')
    assert card.evaluate('el=>el.scrollWidth>el.clientWidth')
    card.evaluate('''el => {
        el.dispatchEvent(new TouchEvent('touchstart', {bubbles:true, touches:[new Touch({identifier:1,target:el,clientX:300,clientY:200})]}));
        el.dispatchEvent(new TouchEvent('touchend', {bubbles:true, changedTouches:[new Touch({identifier:1,target:el,clientX:100,clientY:200})]}));
        el.scrollLeft = 60;
    }''')
    assert page.evaluate('location.hash') == '#q-mux-001'
    assert card.evaluate('el=>el.scrollLeft') > 0
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    ctx.close()


@pytest.mark.parametrize('width', [375,1280])
@pytest.mark.parametrize('theme', ['light','dark'])
def test_generated_v2_recall_and_summary(browser,tmp_path,width,theme):
    from tests._explanation_recall_fixture import setup_v2
    m,run,data=setup_v2(tmp_path)
    paths=assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    ctx=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme)
    page=ctx.new_page(); errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(paths['explanation_html'].as_uri()+'#q-mux-001')
    recall=page.locator('main article.topic [data-explanation="recall"]')
    assert recall.is_visible() and '선택선이라는 단서' in recall.inner_text()
    if page.locator('.layout').get_attribute('data-right')!='open':
        page.locator('#toggle-right').click()
    summary=page.locator('#panel-right .sum:not([hidden]) [data-summary="recall"]')
    assert summary.count()==1 and summary.is_visible()
    assert '입력 하나' in summary.inner_text()
    assert page.locator('.katex-error').count()==0
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
    ctx.close()


@pytest.mark.parametrize('number',range(1,7))
@pytest.mark.parametrize('width',[375,1280])
@pytest.mark.parametrize('theme',['light','dark'])
def test_published_recall_and_summary(browser,number,width,theme):
    import json
    root=Path(__file__).resolve().parents[1]
    folder=root/'복습노트'/f'실험{number:02d}'
    manifest=json.loads((folder/'.pack/manifest.json').read_text(encoding='utf-8'))
    ids=[p['id'] for p in manifest['problems'] if p['status']=='included']
    # Read each authored summary before JS moves all .sum nodes into the panel.
    from scripts.lab.review_pack.html2md import Parser
    from scripts.lab.review_pack.explanation_content import text
    parser=Parser(); parser.feed((folder/f'실험{number:02d}_문제설명.html').read_text(encoding='utf-8'))
    expected={n.attrs['id']:text(next(x for x in n.walk() if x.attrs.get('data-summary')=='recall')).strip()
              for n in parser.root.walk() if n.tag=='article' and 'topic' in n.attrs.get('class','').split()}
    ctx=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme)
    page=ctx.new_page(); errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto((folder/f'실험{number:02d}_문제설명.html').as_uri())
    if page.locator('.layout').get_attribute('data-right')!='open':
        page.locator('#toggle-right').click()
    for ident in ids:
        page.evaluate('(id)=>location.hash=id',ident)
        page.wait_for_function('(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ident)
        assert page.locator('#'+ident+' [data-explanation="recall"]').is_visible()
        summary=page.locator('#panel-right .sum:not([hidden]) [data-summary="recall"]')
        assert summary.count()==1 and summary.is_visible()
        assert ' '.join(summary.inner_text().split())==' '.join(expected[ident].split())
        assert page.locator('.katex-error').count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
    ctx.close()
