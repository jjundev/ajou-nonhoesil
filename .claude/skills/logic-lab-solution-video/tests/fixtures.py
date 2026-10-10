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
