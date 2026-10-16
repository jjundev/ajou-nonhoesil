from pathlib import Path
import json
from playwright.sync_api import sync_playwright
out=Path('output/validation/problem-recall');stage=Path((out/'stage-05.txt').read_text(encoding='utf-8-sig').strip()).resolve();results=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome')
 for theme in ['light','dark']:
  c=b.new_context(viewport={'width':375,'height':900},color_scheme=theme,has_touch=True);page=c.new_page();page.goto((stage/'실험05_문제설명.html').as_uri())
  ids=page.locator('main article.topic').evaluate_all('(a)=>a.map(x=>x.id)')
  for ident in ids:
   page.evaluate('(id)=>location.hash=id',ident);page.wait_for_function('(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ident)
   for k,card in enumerate(page.locator('#'+ident+' .equation-card,#'+ident+' .table-card').all()):
    if not card.evaluate('(e)=>e.scrollWidth>e.clientWidth'):continue
    h=page.evaluate('location.hash');card.evaluate('''el=>{el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[new Touch({identifier:1,target:el,clientX:300,clientY:200})]}));el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,changedTouches:[new Touch({identifier:1,target:el,clientX:100,clientY:200})]}));el.scrollLeft=60;}''')
    assert page.evaluate('location.hash')==h;left=card.evaluate('(e)=>e.scrollLeft');assert left>0;results.append({'id':ident,'theme':theme,'card':k,'scrollLeft':left,'hash_unchanged':True})
  page.evaluate('(id)=>location.hash=id',ids[1]);page.wait_for_function('(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ids[1]);page.locator('#pager-prev').click();assert page.evaluate('location.hash')=='#'+ids[0]
  page.reload();assert page.evaluate('!!localStorage.getItem("od-note-read:logic-lab-05-problem-explanation")');assert not page.evaluate('!!localStorage.getItem("od-note-read:logic-lab-05")');c.close()
 b.close()
(out/'touch-05.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print('internal scroll/touch cases',len(results),'previous/reload state passed')
