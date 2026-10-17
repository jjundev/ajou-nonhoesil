from pathlib import Path
import pytest
from tests._quiz_practice_fixture import create_quiz_run
from scripts.lab.review_pack.render import assemble
from tests.test_review_pack_workbook_browser import assert_offline_reload,assert_workbook_bounds_and_links

ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')


@pytest.mark.parametrize('viewport',[dict(width=1280,height=900),dict(width=375,height=812)])
def test_quiz_board_print_geometry(tmp_path,viewport):
    from playwright.sync_api import sync_playwright
    m,run=create_quiz_run(tmp_path);paths=assemble(m,run,tmp_path/'stage',ASSETS)
    with sync_playwright() as pw, pw.chromium.launch(channel='chrome') as browser:
        page=browser.new_page(viewport=viewport);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        for media in ('screen','print'):
            page.emulate_media(media=media)
            for key in ('question_html','review_html'):
                page.goto(paths[key].resolve().as_uri());page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
                assert page.locator('html').get_attribute('data-ready')=='true'
                assert page.locator('body').get_attribute('data-overflow')==''
                assert page.locator('.page--problem').evaluate_all('xs=>xs.map(x=>x.id)')==[p['id'] for p in m['problems']]
                assert page.locator('.katex-error').count()==0
                assert page.locator('img').evaluate_all('xs=>xs.every(x=>x.complete && x.naturalWidth>0)')
                assert page.locator('#q-qp-e04-board-01 .panel .fig-band').count()==1
                assert page.locator('#q-qp-e04-board-01 .page-center .fig-band').count()==0
                if key=='question_html':
                    assert page.locator('.page-center .work-board').count()==1
                    assert page.locator('.panel .work-board').count()==0
                    assert page.locator('.work-board img').evaluate('x=>x.offsetWidth*25.4/96')>=90
                    assert page.locator('.work-board img').evaluate('x=>{let a=x.getBoundingClientRect(),b=x.closest(".page-center").getBoundingClientRect();return a.left>=b.left-1 && a.right<=b.right+1 && a.bottom<=b.bottom+1}')
                else:
                    assert page.locator('.work-board').count()==0
                    assert page.locator('table.chip-spec').count()==1
                    assert page.locator('img[src*="complete.png"]').count()==1
                assert_workbook_bounds_and_links(page);assert_offline_reload(page)
        assert errors==[]


@pytest.mark.parametrize('change',['tall_board','long_spec'])
def test_oversized_board_or_pin_spec_reports_overflow(tmp_path,change):
    import json
    from playwright.sync_api import sync_playwright
    from scripts.lab.review_pack.workbook_render import render_workbook_html,read_workbook_payload
    m,run=create_quiz_run(tmp_path);paths=assemble(m,run,tmp_path/'stage',ASSETS)
    data=read_workbook_payload(paths['question_html']);p=next(p for p in data['problems'] if 'board' in p['id'])
    if change=='long_spec':p['html']['conditions']=p['html']['conditions'].replace('</tbody>','<tr><td>2</td><td>X</td><td>입력</td></tr>'*120+'</tbody>')
    path=paths['question_html'];path.write_text(render_workbook_html(data,ASSETS),encoding='utf-8')
    with sync_playwright() as pw,pw.chromium.launch(channel='chrome') as browser:
        page=browser.new_page()
        if change=='tall_board':page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{let s=document.createElement('style');s.textContent='#book .work-board img {height:250mm}';document.head.append(s)})")
        page.goto(path.resolve().as_uri());page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
        assert p['id'] in page.locator('body').get_attribute('data-overflow').split(',')
