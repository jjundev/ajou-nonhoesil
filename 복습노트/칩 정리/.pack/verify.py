from pathlib import Path
import importlib.util,json,re
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parent;O=P.parent
chips=json.loads((P/'chips.json').read_text(encoding='utf-8'))
questions=json.loads((P/'questions.json').read_text(encoding='utf-8'))
class Doc(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[];self.resources=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag in ['script','img','link']:
            u=a.get('src',a.get('href',''))
            if u:self.resources.append(u)
docs={}
for f in O.glob('*.html'):
    d=Doc();d.feed(f.read_text(encoding='utf-8'));docs[f.name]=d
    assert len(d.ids)==len(set(d.ids)),f'duplicate ID {f}'
    assert not any(u.startswith(('http:','https:','//')) for u in d.resources),'external dependency'
    for u in d.resources:assert (O/unquote(u)).exists(),u
for name,d in docs.items():
    for u in d.links:
        parts=urlsplit(u)
        if parts.scheme:continue
        target=unquote(parts.path) or name
        assert target in docs,(name,u)
        if parts.fragment:assert unquote(parts.fragment) in docs[target].ids,(name,u)
assert len(chips)==13 and sum(not c['extra'] for c in chips)==10
assert len(questions)==30
by={c['num']:c for c in chips}
# Independent expectations transcribed from manufacturer pin descriptions.
assert by['74HC02']['pins']==['1Y','1A','1B','2Y','2A','2B','GND','3A','3B','3Y','4A','4B','4Y','VCC']
assert by['74HC20']['pins'][2]==by['74HC20']['pins'][10]=='NC'
assert by['74HC20']['gates']==[[[1,2,4,5],6],[[9,10,12,13],8]]
assert by['74HC11']['gates']==[[[1,2,13],12],[[3,4,5],6],[[9,10,11],8]]
assert by['74HC42']['pins']==['/Y0','/Y1','/Y2','/Y3','/Y4','/Y5','/Y6','GND','/Y7','/Y8','/Y9','D','C','B','A','VCC']
for c in chips:
    n=len(c['pins']);assert n in [14,16]
    assert c['pins'][n-1]=='VCC' and c['pins'][n//2-1]=='GND'
    for inputs,y in c['gates']:
        assert 'Y' in c['pins'][y-1]
        assert all(c['pins'][i-1] not in ['NC','VCC','GND'] and 'Y' not in c['pins'][i-1] for i in inputs)
for x in questions:
    assert x['id'] in docs['문제풀이.html'].ids and x['id'] in docs['문제설명.html'].ids
    assert x['answer'] in (O/'문제풀이.html').read_text(encoding='utf-8')
    assert x['answer'] in (O/'문제설명.html').read_text(encoding='utf-8')
# Exercise composite circuit answers independently over all Boolean input rows.
for a in [0,1]:
 for b in [0,1]:
  for c in [0,1]:
   assert ((a&b)&c)==int(a+b+c==3)
   assert (((a^b)^c)+2*((a&b)|((a^b)&c)))==a+b+c
assert (1-(1&1&0&1))==1
assert [int(x) for x in f'{5:04b}']==[0,1,0,1]
print('Static content, pin maps, links and calculations: PASS')
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in [1280,375]:
        page=browser.new_page(viewport={'width':width,'height':900})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        for name in docs:
            page.goto((O/name).as_uri());page.wait_for_timeout(180)
            anchors=docs[name].ids
            for ident in (['hc02','hc20','hc42'] if name=='정리노트.html' else ['q14','q26','q30']):
                page.goto((O/name).as_uri()+'#'+ident);page.wait_for_timeout(80)
                assert page.locator('#'+ident).is_visible(),(width,name,ident)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(width,name,ident,'overflow')
            if name=='문제풀이.html':
                page.goto((O/name).as_uri()+'#q14');page.locator('#q14 .practice-answer summary').click()
                assert page.locator('#q14 .practice-answer').get_attribute('open') is not None
                page.evaluate("dispatchEvent(new Event('beforeprint'))")
                assert page.locator('details:not([open])').count()==0
                page.evaluate("dispatchEvent(new Event('afterprint'))")
                assert page.locator('details:not([open])').count()>0
            before=page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg')")
            page.locator('#theme-toggle').click()
            after=page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg')")
            assert before!=after,'theme colors did not change'
            page.screenshot(path=str(P/f'{width}-{name[:-5]}.png'),full_page=False)
            results.append({'width':width,'document':name,'overflow':False,'script_errors':errors.copy()})
            assert not errors,errors
        page.close()
    # Verify all answers are visible when printing, even if user never opened them.
    page=browser.new_page();page.goto((O/'문제풀이.html').as_uri())
    page.emulate_media(media='print');page.evaluate("dispatchEvent(new Event('beforeprint'))")
    assert page.locator('article.topic').count()==30
    assert page.locator('article.topic:visible').count()==30
    assert page.locator('.practice-answer:visible').count()==30
    browser.close()
(P/'browser-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('Chromium desktop/mobile, navigation, theme, answers and print: PASS')
