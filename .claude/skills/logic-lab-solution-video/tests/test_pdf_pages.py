from fixtures import *
from solution_video.pdf_pages import export_page,extract_layers,compare_completed
from solution_video.contracts import ExtractionError
class PDFTests(Sandbox):
    def test_completed_svg_matches_original(self):
        page=export_page(math_pdf(self.run/'a.pdf'),0,self.run/'page')
        layers=extract_layers(page,mapping(page))
        r=compare_completed(layers,self.run/'evidence')
        self.assertEqual([r[k] for k in ('pixel_diff','non_target_diff','hidden_leaks')],[0,0,0])
    def test_glyph_clip_and_math_primitives(self):
        page=export_page(math_pdf(self.run/'a.pdf'),0,self.run/'page')
        m=mapping(page); layers=extract_layers(page,m)
        self.assertTrue(any(s['kind']=='fraction_bar' for s in layers['shapes']))
        self.assertEqual(layers['map'],m)
        m['steps'][0]['glyph_ids'].append(page['glyphs'][0]['id'])
        with self.assertRaises(ExtractionError): extract_layers(page,m)
    def test_scan_rejected(self):
        import fitz
        d=fitz.open(); d.new_page(); d.save(self.run/'scan.pdf')
        with self.assertRaises(ExtractionError): export_page(self.run/'scan.pdf',0,self.run/'p')
    def test_shared_defs_clipped_overlapping_subscript(self):
        import fitz
        pdf=self.run/'clip.pdf';d=fitz.open();p=d.new_page(width=400,height=300)
        p.insert_text((110,120),'xx',fontsize=18);p.insert_text((115,124),'1',fontsize=8)
        for xref in p.get_contents():
            stream=d.xref_stream(xref);d.update_stream(xref,b'q\n100 170 60 35 re W n\n'+stream+b'\nQ\n')
        p.draw_line((115,133),(140,133));d.save(pdf)
        page=export_page(pdf,0,self.run/'page');self.assertIn('clipPath',Path(page['original_svg']).read_text())
        self.assertEqual(sum(g['text']=='x' for g in page['glyphs']),2)
        result=compare_completed(extract_layers(page,mapping(page)),self.run/'evidence')
        self.assertEqual(result['pixel_diff'],0);self.assertEqual(result['hidden_leaks'],0)
