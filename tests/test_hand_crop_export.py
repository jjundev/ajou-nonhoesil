import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import fitz
from PIL import Image
from scripts.lab import export_hand_diagrams as ehd

class TestCropExport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.pdf=self.root/'source.pdf'; self.plan=self.root/'plan.json'; self.out=self.root/'out'
        with fitz.open() as doc:
            for _ in range(2):
                p=doc.new_page(width=600,height=800)
                for box,c in [((100,200,500,700),(0,0,0)),((250,80,400,160),(1,0,0)),((40,300,100,340),(0,0,1))]:
                    p.draw_rect(fitz.Rect(box),color=c)
            doc.save(self.pdf)
        self.data=dict(schema='hand-crop/v1',source_sha256=hashlib.sha256(self.pdf.read_bytes()).hexdigest(),pages=[
            dict(page=i,page_rect=[0,0,600,800],board_box=[100,200,500,700],
                 keep=[dict(label='power',box=[250,80,400,160]),dict(label='signal',box=[40,300,100,340])],excluded=[],ambiguous=[]) for i in (1,2)])
        self.save()
    def save(self): self.plan.write_text(json.dumps(self.data))
    def run_cli(self,*extra):
        return ehd.main(['99',str(self.pdf),'--out',str(self.out),'--dpi','72',*extra])
    def test_content_and_dpi(self):
        for dpi in (72,144):
            paths=ehd.export_hand_diagrams(99,self.pdf,self.out,dpi=dpi,crop_board=True,crop_plan=self.plan)
            self.assertEqual(len(paths),2)
            with Image.open(paths[0]) as im:
                self.assertEqual(im.size,(476*dpi//72,636*dpi//72))
                # Bottom black edge survives, rather than merely a tall aspect ratio.
                self.assertLess(min(im.convert('L').crop((60*dpi//72,626*dpi//72,460*dpi//72,630*dpi//72)).getdata()),100)
    def test_missing_plan_and_default(self):
        self.assertEqual(self.run_cli('--crop'),1)
        for flags in [[],['--crop','--no-crop'],['--crop','--full-page']]:
            self.assertEqual(self.run_cli(*flags),0)
            with Image.open(next(self.out.glob('*.png'))) as im: self.assertEqual(im.size,(600,800))
    def test_pending_and_resume(self):
        self.data['pages'][1]['ambiguous']=[dict(label='?',box=[510,300,560,340],reason='unclear')]; self.save()
        self.assertEqual(self.run_cli('--crop','--crop-plan',str(self.plan)),2)
        self.assertEqual(len(list(self.out.glob('*.png'))),1)
        self.assertEqual(len(list((self.out/'candidates').glob('*.png'))),3)
        report=json.loads((self.out/'crop-report.json').read_text())
        self.assertEqual([p['status'] for p in report['pages']],['saved','pending'])
        first_path=next(self.out.glob('*.png'))
        original_first=first_path.read_bytes()
        self.data['pages'][1]['keep']+=self.data['pages'][1]['ambiguous']; self.data['pages'][1]['ambiguous']=[]; self.save()
        self.assertEqual(self.run_cli('--crop','--crop-plan',str(self.plan),'--pages','2'),0)
        report=json.loads((self.out/'crop-report.json').read_text())
        self.assertEqual([p['page'] for p in report['pages']],[2])
        self.assertEqual(first_path.read_bytes(),original_first)
        self.assertEqual(len(list(self.out.glob('*.png'))),2)
        self.assertTrue(report['pages'][0]['output'].endswith('p2.png'))
    def test_invalid_plan_writes_no_png(self):
        self.data['pages'][1]['board_box']=[1,1,900,400];self.save()
        self.assertEqual(self.run_cli('--crop','--crop-plan',str(self.plan)),1)
        self.assertEqual(list(self.out.glob('*.png')),[])
    def test_invalid_page_is_not_silently_dropped(self):
        self.assertEqual(self.run_cli('--crop','--crop-plan',str(self.plan),'--pages','1,3'),1)
    def test_rotation(self):
        with fitz.open(self.pdf) as doc:
            for p in doc: p.set_rotation(90)
            rotated=self.root/'rotated.pdf';doc.save(rotated)
        self.data['source_sha256']=hashlib.sha256(rotated.read_bytes()).hexdigest()
        for entry in self.data['pages']:
            entry['page_rect']=[0,0,800,600]
            entry['board_box']=[100,100,600,500];entry['keep']=[]
        self.save()
        paths=ehd.export_hand_diagrams(99,rotated,self.out,dpi=72,crop_board=True,crop_plan=self.plan)
        with Image.open(paths[0]) as im:self.assertEqual(im.size,(520,420))

    def test_netlist_subset_name_stability(self):
        full=ehd.resolve_circuit_filenames(1,2,pdf_path=self.pdf)
        subset=ehd.resolve_circuit_filenames(1,1,pdf_path=self.pdf,pages=[1])
        self.assertEqual(subset,[full[1]])

    def test_multi_experiment_report_keeps_pending(self):
        with fitz.open(self.pdf) as doc:
            doc.new_page(width=600,height=800); doc.new_page(width=600,height=800)
            pdf4=self.root/'four.pdf';doc.save(pdf4)
        self.data['source_sha256']=hashlib.sha256(pdf4.read_bytes()).hexdigest()
        self.data['pages'] += [dict(self.data['pages'][1],page=n) for n in (3,4)]
        self.data['pages'][0]['ambiguous']=[dict(label='?',box=[510,300,560,340],reason='unclear')]
        self.save()
        result=ehd.main(['3주차',str(pdf4),'--out',str(self.out),'--dpi','72','--crop','--crop-plan',str(self.plan)])
        self.assertEqual(result,2)
        report=json.loads((self.out/'crop-report.json').read_text())
        self.assertEqual([p['page'] for p in report['pages']],[1,2,3,4])
        self.assertEqual(report['pages'][0]['status'],'pending')
