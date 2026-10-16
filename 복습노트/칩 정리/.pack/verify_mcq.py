"""User-flow checks for local five-choice study pages."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parent
questions=json.loads((P/'mcq.json').read_text(encoding='utf-8'))
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':375,'height':900})
    page.set_default_timeout(5000)
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto((P.parent/'문제풀이.html').as_uri()+'#q14')
    box=page.locator('#q14 .mcq')
    correct=box.get_attribute('data-correct')
    wrong=next(str(i) for i in range(1,6) if str(i)!=correct)
    box.locator(f'[data-choice-id="{wrong}"]').click()
    assert box.get_attribute('data-selected')==wrong
    assert '정답이 아니에요' in box.locator('.mcq-status').inner_text()
    box.locator(f'[data-choice-id="{correct}"]').click()
    assert box.get_attribute('data-selected')==wrong
    page.reload()
    assert box.get_attribute('data-selected')==wrong
    box.locator('.mcq-reset').click()
    assert box.get_attribute('data-selected') is None
    button=box.locator(f'[data-choice-id="{correct}"]')
    button.focus();page.keyboard.press('Enter')
    assert '정답이에요' in box.locator('.mcq-status').inner_text()
    # Every question: unselected, wrong, first-answer lock, reset, correct.
    for q in questions:
        page.goto((P.parent/'문제풀이.html').as_uri()+'#'+q['id'])
        box=page.locator('#'+q['id']+' .mcq')
        if box.get_attribute('data-selected') is not None:box.locator('.mcq-reset').click()
        assert box.locator('.mcq-reason:visible').count()==0
        assert box.locator('.mcq-label:visible').count()==0
        correct=q['correctChoiceId']
        wrong=next(str(i) for i in range(1,6) if str(i)!=correct)
        box.locator(f'[data-choice-id="{wrong}"]').click()
        assert box.locator('.mcq-reason:visible').count()==2
        assert '내 선택' in box.locator(f'[data-option-id="{wrong}"] .mcq-label').inner_text()
        assert box.locator('[data-result="correct"]').get_attribute('data-choice-id')==correct
        box.locator(f'[data-choice-id="{correct}"]').dblclick()
        assert box.get_attribute('data-selected')==wrong
        box.locator('.mcq-reset').click()
        btn=box.locator(f'[data-choice-id="{correct}"]')
        btn.focus();page.keyboard.press('Space')
        assert box.get_attribute('data-selected')==correct
        assert box.locator('.mcq-reason:visible').count()==1
        assert '정답이에요' in box.locator('.mcq-status').inner_text()
        box.locator('.mcq-reset').click()
    # Shared problem/answer schema in actual rendered DOM, not substrings.
    def contents(page):
        return page.locator('.mcq').evaluate_all('''boxes=>boxes.map(b=>({
          id:b.dataset.questionId,correct:b.dataset.correct,
          choices:[...b.querySelectorAll('li')].map(li=>({id:li.dataset.optionId,
            text:li.querySelector('.mcq-choice,.mcq-option').textContent,
            explanation:li.querySelector('.mcq-reason').textContent}))}))''')
    practice=contents(page)
    explain=browser.new_page()
    explain.goto((P.parent/'문제설명.html').as_uri())
    assert practice==contents(explain)
    # Corrupt, invalid, and outdated storage must not restore an answer.
    page.goto((P.parent/'문제풀이.html').as_uri()+'#q14')
    key=page.locator('#q14 .mcq').evaluate("b=>'chip-mcq-v1:'+b.dataset.questionId+':'+b.dataset.signature")
    for bad in ['{broken','"6"','{}']:
        page.evaluate('([key,value])=>sessionStorage.setItem(key,value)',[key,bad])
        page.reload()
        assert page.locator('#q14 .mcq').get_attribute('data-selected') is None
    page.evaluate('key=>{sessionStorage.removeItem(key);sessionStorage.setItem(key+"-old",JSON.stringify("1"))}',key)
    page.reload()
    assert page.locator('#q14 .mcq').get_attribute('data-selected') is None
    blocked=browser.new_page()
    blocked.add_init_script("Object.defineProperty(window,'sessionStorage',{get(){throw new Error('blocked')}})")
    blocked.goto((P.parent/'문제풀이.html').as_uri()+'#q14')
    blocked.locator('#q14 [data-choice-id="1"]').click()
    assert blocked.locator('#q14 .mcq').get_attribute('data-selected')=='1'
    blocked.locator('#q14 .mcq-reset').click()
    assert blocked.locator('#q14 .mcq').get_attribute('data-selected') is None
    # Print unanswered and answered documents; restore exact on-screen state.
    for answered in [False,True]:
        page.goto((P.parent/'문제풀이.html').as_uri()+'#q14')
        box=page.locator('#q14 .mcq')
        if answered:box.locator('[data-choice-id="1"]').click()
        before=box.inner_html()
        page.emulate_media(media='print')
        page.evaluate("dispatchEvent(new Event('beforeprint'))")
        assert page.locator('.mcq-choice:visible').count()==150
        assert page.locator('.mcq-reason:visible').count()==0
        assert page.locator('.mcq-label:visible').count()==0
        page.evaluate("dispatchEvent(new Event('afterprint'))")
        page.emulate_media(media='screen')
        assert box.inner_html()==before
    explain.emulate_media(media='print')
    explain.evaluate("dispatchEvent(new Event('beforeprint'))")
    assert explain.locator('.mcq-option:visible').count()==150
    assert explain.locator('.mcq-reason:visible').count()==150
    # Responsive visual evidence for representative pin-heavy questions.
    for width in [375,1280]:
        page.set_viewport_size({'width':width,'height':900})
        for theme in ['light','dark']:
            page.emulate_media(color_scheme=theme)
            page.evaluate('theme=>document.documentElement.dataset.theme=theme',theme)
            for ident in ['q14','q19','q26']:
                page.goto((P.parent/'문제풀이.html').as_uri()+'#'+ident)
                page.evaluate('theme=>document.documentElement.dataset.theme=theme',theme)
                box=page.locator('#'+ident+' .mcq')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                for b in box.locator('.mcq-choice').all():
                    bounds=b.bounding_box();assert bounds['height']>=44
                page.screenshot(path=str(P/f'mcq-{width}-{theme}-{ident}.png'))
    assert not errors,errors
    browser.close()
print('30 questions / 150 shared choices: PASS')
print('Correct/wrong, first-answer lock, reset, reload, Enter/Space: PASS')
print('Blocked/corrupt/outdated storage, mobile/desktop themes, print restoration: PASS')
