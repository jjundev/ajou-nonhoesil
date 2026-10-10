from pathlib import Path
import sys,tempfile,unittest,json,wave,hashlib
S=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(S/'scripts'))
REPO=S.parents[2]
class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.run=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
def math_pdf(dest):
    import fitz
    doc=fitz.open(); p=doc.new_page(width=400,height=300)
    p.insert_text((10,30),'P10.1'); p.insert_text((110,120),'x + y = 2',fontsize=14)
    p.insert_text((130,128),'1',fontsize=8); p.draw_line((150,140),(180,140)); p.draw_rect((105,180,290,220),color=(0,0,1))
    doc.save(dest); return dest
def mapping(page):
    glyphs=[g['id'] for g in page['glyphs'] if g['bbox'][0]>=100]
    shapes=[s['id'] for s in page['shapes'] if s['bbox'][0]>=100]
    return {'work_bbox':[100,80,300,240],'steps':[{'id':'solution','glyph_ids':glyphs,'shape_ids':shapes}], 'answer_step_id':'solution'}
def make_audio(segment_id,samples,run):
    p=run/(segment_id+'.wav'); p.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(p),'wb') as w: w.setparams((1,2,24000,0,'NONE','')); w.writeframes(b'\0\0'*samples)
    return dict(id=segment_id,path=p.relative_to(run).as_posix(),samples=samples,rate=24000,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def defective_pack(repo,name,pages):
    """Copy a real pack into repo and stamp raw LaTeX on the given answer pages (real packs are clean since 2026-10-09)."""
    import fitz,shutil
    dest=repo/'복습노트'/name; shutil.copytree(REPO/'복습노트'/name,dest)
    pdf=dest/(name+'_기출풀이.pdf'); doc=fitz.open(pdf)
    for i in (range(len(doc)) if pages=='all' else pages): doc[i].insert_text((330,575),'$V_{CC}=5\\,\\mathrm{V}$',fontsize=6)
    doc.save(dest/'tmp.pdf'); doc.close(); (dest/'tmp.pdf').replace(pdf); return dest

def synthetic_pack(repo,name,problems,table=None,answer_table=None):
    """Write a minimal pack discover() accepts: 복습노트/<name>/자료/manifest.json plus the problem and answer PDFs.
    problems: [dict(id,kind,title)] in manifest order. A page per problem carries its label badge (KINDS[kind]+n, n =
    position in the manifest) and title in the header. table goes in the problem page's work area (300,200), answer_table
    in the answer page's condition panel (34,200); both are a grid of 60x24 cells (a cell text with '\n' is drawn as wrapped lines). Calling again with another order
    rewrites the manifest and both PDFs, so labels are recomputed the way a rebuilt pack would."""
    import fitz
    from solution_video.sources import DATA_DIR,KINDS
    pack=Path(repo)/'복습노트'/name; (pack/DATA_DIR).mkdir(parents=True,exist_ok=True)
    included=[dict(id=p['id'],kind=p['kind'],title=p['title'],status='included') for p in problems]
    (pack/DATA_DIR/'manifest.json').write_text(json.dumps({'problems':included},ensure_ascii=False),encoding='utf-8')
    for suffix,rows,x0 in (('기출문제',table,300),('기출풀이',answer_table,34)):
        doc=fitz.open()
        for n,p in enumerate(problems,1):
            page=doc.new_page(width=841.9,height=595.3)
            page.insert_text((30,40),KINDS[p['kind']]+str(n),fontname='korea',fontsize=11)
            page.insert_text((150,40),p['title'],fontname='korea',fontsize=14)
            for r,row in enumerate(rows or []):
                for c,text in enumerate(row):
                    cell=fitz.Rect(x0+60*c,200+24*r,x0+60*(c+1),200+24*(r+1))
                    page.draw_rect(cell,color=(0,0,0),width=.8)
                    lines=text.split('\n')
                    if len(lines)==1: page.insert_text((cell.x0+4,cell.y0+16),text,fontname='korea',fontsize=10)
                    else:  # a wrapped cell: extract() reads it back as 'AND\n출력'
                        for k,line in enumerate(lines): page.insert_text((cell.x0+4,cell.y0+9+10*k),line,fontname='korea',fontsize=8)
        doc.save(pack/(name+'_'+suffix+'.pdf')); doc.close()
    return pack
