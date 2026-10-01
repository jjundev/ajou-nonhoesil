"""Real print regression: moved sidebar solutions must reach printed content."""
from pathlib import Path
import shutil
import subprocess
import pytest
from scripts.lab.html2pdf import html_to_pdf, resolve_chrome, PdfError
from scripts.lab.review_pack.render import assemble
from tests.test_review_pack_manifest import fixture


def test_print_includes_solutions_moved_to_biology_sidebar(tmp_path):
    try:
        chrome = resolve_chrome()
    except PdfError:
        pytest.skip('Local Chrome renderer unavailable')
    pypdf = pytest.importorskip('pypdf')
    paths = assemble(fixture(), Path('tests/fixtures/review_pack'), tmp_path/'stage',
                     Path('.claude/skills/logic-lab-review-pack/assets'))
    pdf = html_to_pdf(paths['review_html'], tmp_path/'printed.pdf', chrome=chrome, timeout=50)
    text = ''.join(page.extract_text() for page in pypdf.PdfReader(pdf).pages)
    assert 'I0입니다.' in ''.join(text.split())


def test_print_restores_sidebar_order_and_open_state():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node JavaScript test runtime unavailable')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const events={};
class Element {
  constructor(tag){this.tagName=tag;this.children=[];this.parentNode=null;this.open=false;this.dataset={};}
  get nextSibling(){if(!this.parentNode)return null;const a=this.parentNode.children;return a[a.indexOf(this)+1]||null;}
  appendChild(d){this.insertBefore(d,null);}
  insertBefore(d,next){
    if(d.parentNode){const a=d.parentNode.children;a.splice(a.indexOf(d),1);}
    const i=next===null?this.children.length:this.children.indexOf(next);
    assert(i>=0);this.children.splice(i,0,d);d.parentNode=this;
  }
}
const card=new Element('ARTICLE'),group=new Element('DIV');group.dataset.cardId='q1';
const first=new Element('DETAILS'),second=new Element('DETAILS'),nested=new Element('DETAILS');
second.open=true;group.appendChild(first);group.appendChild(second);second.appendChild(nested);
const document={
  getElementById:id=>id==='q1'?card:null,
  querySelectorAll:selector=>selector==='.aid[data-card-id]'?[group]:selector==='details'?[first,second,nested]:[]
};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window:{addEventListener:(name,fn)=>events[name]=fn},document});
events.beforeprint();events.beforeprint();
assert.deepStrictEqual(card.children,[first,second]);
assert(first.open&&second.open&&nested.open);
events.afterprint();
assert.deepStrictEqual(group.children,[first,second]);assert.strictEqual(card.children.length,0);
assert.strictEqual(first.open,false);assert.strictEqual(second.open,true);assert.strictEqual(nested.open,false);
events.beforeprint();events.afterprint();assert.deepStrictEqual(group.children,[first,second]);
'''
    result = subprocess.run([node, '-e', script, str(Path('.claude/skills/logic-lab-review-pack/assets/widgets.js'))],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr

