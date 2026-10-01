import json
from pathlib import Path
import pytest
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack

@pytest.mark.parametrize('viewport',[{'width':1280,'height':900},{'width':375,'height':812}])
def test_real_workbook_decode_ready_and_no_overflow(tmp_path,viewport):
    pw = pytest.importorskip('playwright.sync_api')
    run = Path('docs/learning-pack-source/실험04')
    m = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    paths = assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    expected = [p['id'] for p in m['problems'] if p['status']=='included']
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport=viewport)
            errors = []; page.on('pageerror',lambda e:errors.append(str(e)))
            for key in ('question_html','review_html'):
                page.goto(paths[key].resolve().as_uri())
                page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
                assert page.locator('html').get_attribute('data-ready') == 'true'
                assert page.locator('body').get_attribute('data-overflow') == ''
                assert page.locator('.page--problem').evaluate_all('(nodes)=>nodes.map(n=>n.id)') == expected
                assert page.locator('.katex-error').count() == 0
                assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)')
                assert_workbook_bounds_and_links(page)
                if key == 'question_html':
                    assert page.locator('#q-mux4 tbody tr td:last-child').all_text_contents() == ['','','','']
                assert_offline_reload(page)
            assert errors == []

def assert_workbook_bounds_and_links(page):
    assert page.locator('.sol-step img').evaluate_all('''imgs => imgs.every(img => {
      const p=img.closest('.sol-step-body').getBoundingClientRect(),r=img.getBoundingClientRect();
      return r.left>=p.left-1 && r.right<=p.right+1;
    })''')
    assert page.locator('.sol-answer').evaluate_all('''nodes => nodes.every(node => {
      const p=node.closest('.work').getBoundingClientRect(),r=node.getBoundingClientRect();
      return r.bottom<=p.bottom+1;
    })''')
    assert page.locator('table').evaluate_all('''tables => tables.every(table => {
      const p=table.parentElement.getBoundingClientRect(),r=table.getBoundingClientRect();
      return r.left>=p.left-1 && r.right<=p.right+1;
    })''')
    assert page.locator('a.hint-strip').evaluate_all('''links => links.every(a =>
      document.getElementById(decodeURIComponent(a.hash.slice(1))))''')

def assert_offline_reload(page):
    page.context.set_offline(True)
    try:
        page.reload()
        page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
        assert page.locator('html').get_attribute('data-ready') == 'true'
        assert page.locator('.katex-error').count() == 0
        assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)')
    finally:
        page.context.set_offline(False)
