from pathlib import Path
from playwright.sync_api import sync_playwright
import json,sys
sys.path.insert(0,str(Path("docs/learning-pack-source/실험06").resolve()))
from recall import RECALL
s=Path(Path('output/validation/problem-recall/stage-06.txt').read_text(encoding='utf-8-sig').strip()).resolve();f=s/'실험06_문제설명.html';out=Path('output/validation/problem-recall/browser-06');out.mkdir(exist_ok=True)
result=[]
with sync_playwright() as pw:
 with pw.chromium.launch(channel='chrome') as b:
  for w in [375,1280]:
   for theme in ['light','dark']:
    ctx=b.new_context(viewport={'width':w,'height':900},color_scheme=theme);p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(f.as_uri())
    ids=p.locator('main article.topic').evaluate_all('(a)=>a.map(x=>x.id)');assert len(ids)==14
    for ident in ids:
     p.evaluate('(id)=>location.hash=id',ident);p.wait_for_function('(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ident)
     assert p.locator('#'+ident+' [data-explanation=recall]').is_visible()
     if p.locator('.layout').get_attribute('data-right')!='open':p.locator('#toggle-right').click()
     assert p.locator('#panel-right .sum:not([hidden]) [data-summary=recall]').is_visible()
     assert p.locator('#panel-right .sum:not([hidden]) [data-summary=recall]').inner_text()==RECALL[ident][1]
     assert p.locator('#'+ident+' table').evaluate_all('(a)=>a.every(x=>x.closest(".table-card"))')
     assert p.locator('#'+ident+' .equation-card, #'+ident+' .table-card').evaluate_all('cards=>cards.every(x=>{let s=getComputedStyle(x);return parseFloat(s.borderTopWidth)>=1&&parseFloat(s.paddingTop)>=16&&s.overflowX==="auto"})')
     assert p.locator('.katex-error').count()==0
     assert p.locator('img').evaluate_all('(a)=>a.every(x=>x.complete&&x.naturalWidth>0)')
     assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
     if w==375:
      p.screenshot(path=str(out/f"{w}-{theme}-{ident}-summary.png"))
      p.locator("#panel-scrim").click(position={"x":5,"y":5})
      p.locator('#toggle-left').click();p.locator('.toc-list a[href="#'+ident+'"]').click();assert p.locator('.layout').get_attribute('data-left')=='closed'
     p.wait_for_timeout(350)
     p.locator('#'+ident+' [data-explanation=recall]').scroll_into_view_if_needed();p.screenshot(path=str(out/f'{w}-{theme}-{ident}.png'))
    p.locator('#pager-prev').click();p.locator('#pager-next').click();p.keyboard.press('Tab');p.keyboard.press('Tab');assert p.evaluate('document.activeElement!==document.body')
    assert not errors;result.append({'width':w,'theme':theme,'ids':ids,'pageerrors':errors,'katex_errors':0,'broken_images':0,'document_overflow':False,'summaries':'14 actual opened','screenshots':14});ctx.close()
  ctx=b.new_context(java_script_enabled=False,viewport={'width':375,'height':900});p=ctx.new_page();p.goto(f.as_uri());assert p.locator('article.topic').count()==14
  assert p.locator('[data-explanation=solve]').evaluate_all('(a)=>a.every(x=>getComputedStyle(x).display!=="none")')
  assert p.locator('[data-explanation=verify]').evaluate_all('(a)=>a.every(x=>getComputedStyle(x).display!=="none")')
  p.screenshot(path=str(out/'no-js.png'));ctx.close()
(out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('56 article/theme/viewport captures, summaries/cards/navigation, no-JS PASS')
