from pathlib import Path
import json,itertools,hashlib,re,html
from playwright.sync_api import sync_playwright
from PIL import Image,ImageDraw
out=Path('output/validation/problem-recall');stage=Path((out/'stage-02.txt').read_text(encoding='utf-8-sig').strip()).resolve();url=(stage/'실험02_문제설명.html').as_uri()
shots=out/'browser-02';shots.mkdir(exist_ok=True)
results=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome')
 for width,theme in itertools.product([375,1280],['light','dark']):
  ctx=b.new_context(viewport={'width':width,'height':900},color_scheme=theme);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url)
  ids=page.locator('main article.topic').evaluate_all('(a)=>a.map(x=>x.id)')
  for ident in ids:
   page.evaluate('(id)=>location.hash=id',ident);page.wait_for_function('(id)=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ident)
   recall=page.locator('#'+ident+' [data-explanation="recall"]');recall.scroll_into_view_if_needed();assert recall.is_visible()
   recall.screenshot(path=str(shots/f'{width}-{theme}-{ident}-recall.png'))
   assert page.locator('.katex-error').count()==0
   assert page.locator('img').evaluate_all('(a)=>a.every(x=>x.complete&&x.naturalWidth>0)')
   metrics=page.evaluate('''(id)=>{const a=document.getElementById(id),u=a.querySelector('[data-explanation="understand"]'),s=getComputedStyle(u);return {documentWidth:document.documentElement.scrollWidth,viewport:innerWidth,gap:{margin:s.marginTop,padding:s.paddingTop,border:s.borderTopWidth},cards:[...a.querySelectorAll('.equation-card,.table-card')].map(x=>{const c=getComputedStyle(x);return {width:x.clientWidth,scroll:x.scrollWidth,overflow:c.overflowX,padding:c.paddingTop,border:c.borderTopWidth,background:c.backgroundColor}})}}''',ident)
   assert metrics['documentWidth']<=width
   assert all(c['overflow']=='auto' and float(c['padding'][:-2])>=16 and float(c['border'][:-2])>=1 for c in metrics['cards'])
   if page.locator('.layout').get_attribute('data-right')!='open':page.locator('#toggle-right').click()
   summary=page.locator('#panel-right .sum:not([hidden]) [data-summary="recall"]');assert summary.is_visible()
   fragment=(stage/'자료/problem-explanations'/(ident+'.html')).read_text(encoding='utf-8')
   expected=html.unescape(re.sub('<[^>]+>','',re.search(r'<p data-summary="recall">(.*?)</p>',fragment,re.S).group(1)))
   assert summary.inner_text()==expected
   summary.screenshot(path=str(shots/f'{width}-{theme}-{ident}-summary.png'))
   if width<1024:page.locator('#panel-right [data-panel-close]').click()
   results.append({'id':ident,'width':width,'theme':theme,'recall':recall.inner_text(),'summary':summary.inner_text(),'metrics':metrics,'errors':list(errors)})
  assert not errors
  # Drawer/keyboard/navigation and local read-state namespace.
  if width<1024:
   page.locator('#toggle-left').click();page.locator('.toc-list a').first.click();assert page.locator('.layout').get_attribute('data-left')=='closed'
  page.locator('#pager-next').focus();assert page.locator('#pager-next').evaluate('(e)=>e===document.activeElement');page.keyboard.press('Enter')
  assert page.evaluate('!!localStorage.getItem("od-note-read:logic-lab-02-problem-explanation")')
  assert not page.evaluate('!!localStorage.getItem("od-note-read:logic-lab-02")')
  ctx.close()
 ctx=b.new_context(viewport={'width':375,'height':900},java_script_enabled=False);page=ctx.new_page();page.goto(url)
 assert page.locator('article.topic').count()==14
 assert page.locator('[data-explanation="recall"],[data-explanation="solve"],[data-explanation="verify"]').evaluate_all('(a)=>a.every(x=>getComputedStyle(x).display!=="none"&&x.getBoundingClientRect().height>0)')
 assert page.locator('.toc-list a').count()==14
 page.locator('[data-explanation="recall"]').first.screenshot(path=str(shots/'no-js-recall.png'));ctx.close();b.close()
(out/'browser-02.json').write_text(json.dumps({'stage':str(stage),'cases':results,'no_js':{'articles':14,'visible_recall_solve_verify':42}},ensure_ascii=False,indent=2),encoding='utf-8')
# Contact sheets retain actual browser pixels; no visual content is redrawn.
for width,theme in itertools.product([375,1280],['light','dark']):
 for group in range(4):
  subset=ids[group*4:(group+1)*4];images=[]
  for ident in subset:
   r=Image.open(shots/f'{width}-{theme}-{ident}-recall.png').convert('RGB');s=Image.open(shots/f'{width}-{theme}-{ident}-summary.png').convert('RGB')
   canvas=Image.new('RGB',(max(r.width,s.width),r.height+s.height+35),'#999999');canvas.paste(r,(0,25));canvas.paste(s,(0,r.height+35));ImageDraw.Draw(canvas).text((4,4),ident,fill='black');images.append(canvas)
  cw=max(x.width for x in images);ch=max(x.height for x in images);sheet=Image.new('RGB',(cw*2,ch*2),'#bbbbbb')
  for n,img in enumerate(images):sheet.paste(img,((n%2)*cw,(n//2)*ch))
  sheet.save(shots/f'sheet-{width}-{theme}-{group}.png')
print('56 cases, 112 screenshots, 16 contact sheets; errors/KaTeX/broken images/document overflow=0; noJS=14 readable')
