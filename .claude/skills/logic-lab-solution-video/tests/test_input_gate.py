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
    def test_real_packs_have_no_false_defects(self):
        # 2026-10-09 re-render fixed every raw_latex/clipped_figure page; the gate must stay quiet on clean packs.
        for n in ['실험01','실험02','실험03','실험04','실험05']:
            failures=[]; discover(REPO,n,None,failures)
            self.assertEqual([f['reason'] for f in failures if 'input defect' in f['reason']],[],n)
    def test_stamped_raw_latex_fails_only_that_problem(self):
        failures=[]; ok=discover(defective_pack(self.run/'repo','실험05',[10]).parents[1],'실험05',None,failures)
        self.assertEqual([(f['problem_id'],f['reason']) for f in failures],[('q-demux-from-dec','input defect: raw_latex p.11')])
        self.assertEqual(len(ok),18)
