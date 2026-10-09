from fixtures import *
from solution_video.input_gate import input_defects
from solution_video.sources import discover
class InputGateTests(Sandbox):
    def pdf(self,text=None,image_bottom=None):
        import fitz,io; from PIL import Image
        d=fitz.open(); p=d.new_page(width=841.9,height=595)
        p.draw_rect((22,59,286,572),fill=(246/255,246/255,243/255),color=None)
        if text: p.insert_text((330,120),text)
        p.insert_text((330,500),'답',fontname='korea')
        if image_bottom:
            buf=io.BytesIO(); Image.new('RGB',(40,40),'black').save(buf,'PNG'); p.insert_image((330,380,500,image_bottom),stream=buf.getvalue(),keep_proportion=False)
        out=self.run/'g.pdf'; d.save(out); return out
    def codes(self,pdf): return [d['code'] for d in input_defects(pdf,0)]
    def test_raw_latex(self):
        self.assertEqual(self.codes(self.pdf(text=r'$V_{CC}=5\,\mathrm{V}$')),['raw_latex'])
        self.assertEqual(self.codes(self.pdf(text='V_CC = 5 V, 가격 $5')),[])
    def test_clipped_figure(self):
        self.assertEqual(self.codes(self.pdf(image_bottom=540)),['clipped_figure'])
        self.assertEqual(self.codes(self.pdf(image_bottom=470)),[])
    def test_real_packs(self):
        failures=[]; ok=discover(REPO,'실험05',None,failures)
        bad={f['problem_id']:f['reason'] for f in failures}
        self.assertIn('clipped_figure',bad['q-demux-from-dec']); self.assertIn('q-prio-exam',[p['problem_id'] for p in ok])
        failures=[]; self.assertEqual(discover(REPO,'실험02',None,failures),[])
        self.assertTrue(failures and all('raw_latex' in f['reason'] for f in failures))
