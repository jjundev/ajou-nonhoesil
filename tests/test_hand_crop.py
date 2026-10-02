import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import fitz
from scripts.lab.hand_crop import crop_box, pixel_box, load_crop_plan

class TestCropGeometry(unittest.TestCase):
    def test_content_and_margin(self):
        self.assertEqual(crop_box((0,0,600,800),(100,200,500,700),
                         [(250,80,400,160),(40,300,100,340)]),(32,72,508,708))
    def test_clamp_margin(self):
        self.assertEqual(crop_box((0,0,600,800),(5,5,505,795),[]),(0,0,515,800))
    def test_round_outwards(self):
        self.assertEqual(pixel_box((1.1,2.1,9.1,10.1),(0,0,100,100),(200,200)),(2,4,19,21))
    def test_invalid(self):
        for box in [(10,10,5,50),(-1,10,50,50),(10,10,float('nan'),50),(10,10,610,50),[True,1,4,5]]:
            with self.subTest(box=box), self.assertRaises(ValueError):
                crop_box((0,0,600,800),box,[])

class TestPlan(unittest.TestCase):
    def test_identity_structure_and_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf=Path(tmp)/'source.pdf'; plan_path=Path(tmp)/'plan.json'
            with fitz.open() as doc:
                p=doc.new_page(width=600,height=800); p.set_rotation(90); doc.save(pdf)
            entry=dict(page=1,page_rect=[0,0,800,600],board_box=[100,100,500,500],keep=[],excluded=[],ambiguous=[])
            plan=dict(schema='hand-crop/v1',source_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),pages=[entry])
            plan_path.write_text(json.dumps(plan))
            self.assertEqual(load_crop_plan(plan_path,pdf,[0])[0],entry)
            for update in [dict(source_sha256='0'*64),dict(pages=[]),dict(pages=[entry,entry]),
                           dict(pages=[dict(entry,page_rect=[0,0,600,800])]),dict(pages=[dict(entry,page=True)]),
                           dict(pages=[dict(entry,keep=[dict(label='x',box=[0,0,900,2])])])]:
                plan_path.write_text(json.dumps(dict(plan,**update)))
                with self.subTest(update=update),self.assertRaises(ValueError): load_crop_plan(plan_path,pdf,[0])
