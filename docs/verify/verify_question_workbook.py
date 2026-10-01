"""Chrome visual/print QA; optional validation dependencies, no runtime role."""
from pathlib import Path
import argparse
import hashlib
import json
from playwright.sync_api import sync_playwright
import pymupdf as fitz

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((args.stage/'manifest.json').read_text(encoding='utf-8'))
    expected=[p['id'] for p in manifest['problems'] if p['status']=='included']
    result={'stage':str(args.stage),'viewports':[],'prints':[],'artifacts':{}}
    with sync_playwright() as pw:
        with pw.chromium.launch(channel='chrome') as browser:
            page=browser.new_page();errors=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            for width,height in [(1280,900),(375,812)]:
                page.set_viewport_size({'width':width,'height':height})
                for label,stem in [('기출문제','problems'),('기출풀이','answers')]:
                    html=args.stage/f'실험04_{label}.html'
                    page.goto(html.resolve().as_uri());page.wait_for_function('document.documentElement.dataset.ready')
                    assert page.locator('html').get_attribute('data-ready')=='true'
                    assert page.locator('body').get_attribute('data-overflow')==''
                    assert page.locator('.page--problem').evaluate_all('(ns)=>ns.map(n=>n.id)')==expected
                    assert page.locator('.katex-error').count()==0
                    assert page.locator('img').evaluate_all('(ns)=>ns.every(n=>n.complete && n.naturalWidth>0)')
                    assert page.locator('table').evaluate_all('''ns=>ns.every(n=>{
                        const p=n.parentElement.getBoundingClientRect(),r=n.getBoundingClientRect();
                        return r.right<=p.right+1 && r.left>=p.left-1;})''')
                    assert page.locator('.sol-answer').evaluate_all('''ns=>ns.every(n=>
                        n.getBoundingClientRect().bottom<=n.closest('.work').getBoundingClientRect().bottom+1)''')
                    for ident in expected:
                        page.locator('#'+ident).screenshot(path=str(args.out/f'{stem}-{width}-{ident}.png'))
                    page.context.set_offline(True)
                    page.reload();page.wait_for_function('document.documentElement.dataset.ready')
                    assert page.locator('html').get_attribute('data-ready')=='true'
                    assert page.locator('img').evaluate_all('(ns)=>ns.every(n=>n.complete && n.naturalWidth>0)')
                    assert page.locator('.katex-error').count()==0
                    page.context.set_offline(False)
                    if stem=='answers':
                        page.locator('#q-tri a.hint-strip').click()
                        assert page.evaluate('location.hash')=='#hint-q-tri'
                    result['viewports'].append(dict(sheet=stem,width=width,height=height,ready=True,overflow='',offline=True))
                    result['artifacts'][html.name]=hashlib.sha256(html.read_bytes()).hexdigest()
                    if width==1280:
                        pdf=args.out/(stem+'.pdf')
                        page.pdf(path=str(pdf),prefer_css_page_size=True,print_background=True)
                        pages=[]
                        with fitz.open(pdf) as document:
                            for i,printed in enumerate(document):
                                assert abs(printed.rect.width*25.4/72-297)<0.5
                                assert abs(printed.rect.height*25.4/72-210)<0.5
                                printed.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(args.out/f'{stem}-print-{i+1:02}.png')
                                pages.append(i+1)
                        result['prints'].append(dict(sheet=stem,pages=len(pages),size_mm=[297,210]))
            assert errors==[],errors
    result['console_errors']=errors
    (args.out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
