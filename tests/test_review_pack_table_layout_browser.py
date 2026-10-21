from pathlib import Path
import json
import pytest
from tests.test_review_pack_explanation_browser import browser
from tests.test_review_pack_table_layout import table,schema
from scripts.lab.review_pack.table_layout import layout_problem_tables


def assert_managed_tables_match_metadata(page, metadata):
    expected=[entry['key'] for entry in metadata['tables']]
    actual=page.locator('[data-layout-table]').evaluate_all(
        'tables=>tables.map(t=>t.dataset.layoutTable)')
    assert len(expected)==len(set(expected)), '메타데이터에 표 ID가 중복됐다'
    assert len(actual)==len(set(actual)), 'HTML에 표 ID가 중복됐다'
    assert set(actual)==set(expected), {'missing':set(expected)-set(actual),
                                       'unexpected':set(actual)-set(expected)}

@pytest.mark.parametrize('width',[375,768,1280])
@pytest.mark.parametrize('theme',['light','dark'])
@pytest.mark.parametrize('javascript',[True,False])
def test_compact_widths_gaps_and_text(browser,width,theme,javascript):
    template=Path('.agents/skills/logic-lab-review-pack/assets/note-template.html').read_text()
    css=template.split('<style>')[1].split('</style>')[0]
    s=schema();entry=s['tables'][0];entry['columns'][1]['kind']='signal'
    source=layout_problem_tables('q',dict(original=table()),s)['original']
    text_schema=schema();text_schema['tables'][0]['columns']=[dict(role='description',kind='text',group='비교')]*2
    text_schema['tables'][0]['boundaries']=[]
    prose=layout_problem_tables('q',dict(original=table()),text_schema)['original']
    ctx=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme,java_script_enabled=javascript)
    page=ctx.new_page();page.set_content('<style>'+css+'</style><body data-problem-explanation="true"><div class="table-card" id="compact">'+source+'</div><div class="table-card" id="text">'+prose+'</div></body>')
    result=page.locator('#compact table').evaluate('''t=>{
      let c=[...t.querySelectorAll('tbody td')];let p=c.map(x=>getComputedStyle(x));
      return {w:t.getBoundingClientRect().width,card:t.parentElement.clientWidth,
      a:c[0].getBoundingClientRect().width-parseFloat(p[0].paddingLeft)-parseFloat(p[0].paddingRight),
      b:c[1].getBoundingClientRect().width-parseFloat(p[1].paddingLeft)-parseFloat(p[1].paddingRight),
      right:parseFloat(p[0].paddingRight),left:parseFloat(p[1].paddingLeft)}
    }''')
    assert result['w']<result['card']-32
    assert abs(result['a']-result['b'])<1
    assert result['right']==16 and result['left']==16
    assert page.locator('#text table').evaluate('t=>Math.abs(t.getBoundingClientRect().width-(t.parentElement.clientWidth-32))<1 || t.parentElement.scrollWidth>t.parentElement.clientWidth')
    assert page.locator('[data-layout-group-row] th').evaluate_all('cells=>cells.every(c=>c.scope==="colgroup")')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    ctx.close()

@pytest.mark.parametrize('number',range(1,7))
@pytest.mark.parametrize('width',[375,768,1280])
@pytest.mark.parametrize('theme',['light','dark'])
def test_all_managed_tables(browser,request,number,width,theme):
    root=Path(request.config.getoption('--explanation-pack-root')).resolve()
    folder=root/f'실험{number:02d}'
    metadata=json.loads((folder/'.pack/problem-explanations/table-layout.json').read_text())
    context=browser.new_context(viewport=dict(width=width,height=900),color_scheme=theme,has_touch=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((folder/f'실험{number:02d}_문제설명.html').as_uri())
    assert_managed_tables_match_metadata(page,metadata)
    profiles={}
    for ident in page.locator('main article.topic').evaluate_all('els=>els.map(e=>e.id)'):
        page.evaluate('id=>location.hash=id',ident)
        page.wait_for_function('id=>document.querySelector(".toc a[aria-current=true]").getAttribute("href")==="#"+id',arg=ident)
        for t in page.locator('#'+ident+' [data-layout-table]').all():
            key=t.get_attribute('data-layout-table')
            entry=next(e for e in metadata['tables'] if e['key']==key)
            result=t.evaluate('''t=>{
                let rows=[...t.rows].filter(r=>!r.hasAttribute('data-layout-group-row'));
                let all=[...t.querySelectorAll('td,th[data-layout-kind]')];
                let first=[...rows[rows.length-1].cells];
                let cells=first.map(c=>{let s=getComputedStyle(c);return {kind:c.dataset.layoutKind,
                content:c.getBoundingClientRect().width-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight),
                l:parseFloat(s.paddingLeft),r:parseFloat(s.paddingRight),boundary:c.dataset.layoutBoundary||''}});
                let clipped=all.filter(c=>{let s=getComputedStyle(c);if(s.whiteSpace!=='nowrap')return false;
                    let range=document.createRange();range.selectNodeContents(c);
                    return range.getBoundingClientRect().width>c.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)+1;
                }).map(c=>c.textContent);
                let card=t.closest('.table-card');
                return {cells,clipped,width:t.getBoundingClientRect().width,card:!!card,
                    inners:[...card.querySelectorAll('.table-wrap')].map(e=>getComputedStyle(e).overflowX),
                    cols:[...t.querySelectorAll('col')].map(c=>c.getBoundingClientRect().width)};
            }''')
            assert result['card'] and all(x=='visible' for x in result['inners']),key
            assert not result['clipped'],(key,width,result['clipped'])
            signals=[c['content'] for c in result['cells'] if c['kind']=='signal']
            assert not signals or max(signals)-min(signals)<=1,(key,signals)
            for cell in result['cells']:
                for side in ['left','right']:
                    if 'major-'+side in cell['boundary']:assert cell[side[0]]==16,(key,cell)
                    if 'minor-'+side in cell['boundary']:assert cell[side[0]]==12,(key,cell)
            if pair:=entry.get('pair'):
                if pair in profiles:assert all(abs(a-b)<=1 for a,b in zip(profiles[pair],result['cols'])),key
                profiles[pair]=result['cols']
            card=t.locator('xpath=ancestor::div[contains(@class,"table-card")]').first
            card.evaluate('e=>e.scrollLeft=e.scrollWidth')
            assert card.evaluate('e=>e.scrollLeft+e.clientWidth>=e.scrollWidth-1')
            card.evaluate('''el=>{
                el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[new Touch({identifier:1,target:el,clientX:300,clientY:200})]}));
                el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,changedTouches:[new Touch({identifier:1,target:el,clientX:100,clientY:200})]}));
            }''')
            assert page.evaluate('location.hash')=='#'+ident
        assert page.locator('.katex-error').count()==0
        assert page.locator('img').evaluate_all('els=>els.every(e=>e.complete&&e.naturalWidth>0)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),ident
    assert not errors
    context.close()

@pytest.mark.parametrize('number',range(1,7))
def test_published_managed_without_javascript(browser,request,number):
    root=Path(request.config.getoption('--explanation-pack-root')).resolve()
    metadata=json.loads((root/f'실험{number:02d}/.pack/problem-explanations/table-layout.json').read_text())
    context=browser.new_context(java_script_enabled=False,viewport=dict(width=375,height=900))
    page=context.new_page();page.goto((root/f'실험{number:02d}/실험{number:02d}_문제설명.html').as_uri())
    assert_managed_tables_match_metadata(page,metadata)
    assert page.locator('article.topic').evaluate_all('els=>els.every(e=>getComputedStyle(e).display!=="none")')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    context.close()

def test_text_minima_and_equal_remaining_space(browser):
    template=Path('.agents/skills/logic-lab-review-pack/assets/note-template.html').read_text()
    css=template.split('<style>')[1].split('</style>')[0]
    s=schema();s['tables'][0]['columns']=[dict(role='description',kind='text',group='설명',min_rem=20),dict(role='description',kind='text',group='설명')];s['tables'][0]['boundaries']=[]
    source=layout_problem_tables('q',dict(original=table()),s)['original']
    page=browser.new_page(viewport=dict(width=375,height=900))
    page.set_content('<style>'+css+'</style><body data-problem-explanation="true"><div class="table-card">'+source+'</div></body>')
    widths=page.locator('col').evaluate_all('cols=>cols.map(c=>c.getBoundingClientRect().width/16)')
    assert widths[0]>=20 and widths[1]>=7.8-0.01,widths
    page.set_viewport_size(dict(width=1280,height=900))
    widths=page.locator('col').evaluate_all('cols=>cols.map(c=>c.getBoundingClientRect().width/16)')
    assert abs((widths[0]-20)-(widths[1]-7.8))<0.01,widths
    page.close()
