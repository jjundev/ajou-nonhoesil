from fixtures import *
from solution_video.manifest import validate_manifest,content_fingerprint
from solution_video.contracts import ReviewError

def example():
    layers=dict(glyphs=[dict(id='g1',text='가',bbox=[100,100,110,110],svg_ids=['a'],paint_order=1),dict(id='g2',text='2',bbox=[100,150,110,160],svg_ids=['b'],paint_order=2)],shapes=[dict(id='s1',svg_ids=['c'],bbox=[90,140,150,170],kind='answer_box',paint_order=0)],map=dict(work_bbox=[90,90,160,180],steps=[dict(id='s',glyph_ids=['g1'],shape_ids=[]),dict(id='answer',glyph_ids=['g2'],shape_ids=['s1'])],answer_step_id='answer'))
    manifest=dict(schema_version=1,problem_id='E10.11',title='차동 이득',segments=[dict(id='intro',step_id='',text='문제를 읽습니다.',source_refs=['problem:1'],kind='problem'),dict(id='write',step_id='s',text='절반 회로를 씁니다.',source_refs=['answer:1'],kind='write'),dict(id='end',step_id='answer',text='답을 확인합니다.',source_refs=['answer:1'],kind='write')],reveal_order=['g1','g2'],shape_anchors={'s1':'g2'},cameras=[])
    coverage=dict(status='passed',pdf_md_agree=True,rows=[dict(step_id=s['id'],source_refs=['answer:1'],pdf_text=''.join(next(g['text'] for g in layers['glyphs'] if g['id']==gid) for gid in s['glyph_ids']),md_text='원문',meaning_review='PDF와 MD의 부호와 값 확인') for s in layers['map']['steps']])
    review=dict(status='passed',steps=[dict(step_id=s['id'],assumptions='조건 확인',equations='원본 식 대조',units='V/V',evidence='원본 답안 수식 확인') for s in layers['map']['steps']])
    h=content_fingerprint(manifest,layers,coverage); coverage['input_hash']=h; review['input_hash']=h
    return manifest,layers,coverage,review
class ManifestTests(Sandbox):
    def test_spoken_math_caption_blocks_content_before_voice(self):
        from solution_video.contracts import InputError
        m,l,c,r=example();m['segments'][1]['caption_text']='전류는 I₀ 더하기 ΔI입니다.'
        h=content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        with self.assertRaisesRegex(InputError,'segment write'):
            validate_manifest(m,l,c,r)

    def test_empty_caption_rejected(self):
        for value in ['', '  ',None,3]:
            m,l,c,r=example();m['segments'][1]['caption_text']=value
            h=content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
            with self.subTest(value=value),self.assertRaises(ReviewError):validate_manifest(m,l,c,r)
    def test_exact_glyph_coverage_and_current_review(self):
        m,l,c,r=example(); validate_manifest(m,l,c,r)
        for bad in [m['reveal_order'][:-1],['g1','g1'],['g2','g1'],['g1','unknown']]:
            with self.assertRaises(ReviewError): validate_manifest(dict(m,reveal_order=bad),l,c,r)
        with self.assertRaises(ReviewError): validate_manifest(m,l,c,dict(r,input_hash='stale'))
        with self.assertRaises(ReviewError): validate_manifest(dict(m,shape_anchors={}),l,c,r)
    def test_pdf_md_disagreement_blocks_voice(self):
        m,l,c,r=example()
        with self.assertRaises(ReviewError): validate_manifest(m,l,dict(c,pdf_md_agree=False),r)
    def test_two_columns_and_independent_camera(self):
        m,l,c,r=example(); m['cameras']=[dict(at_frame=0,viewbox=[300,150,220,200])]
        h=content_fingerprint(m,l,c); c['input_hash']=r['input_hash']=h
        validate_manifest(m,l,c,r); self.assertEqual(m['reveal_order'],['g1','g2'])

    def test_claimed_pdf_text_must_match_original_glyphs(self):
        m,l,c,r=example();c['rows'][0]['pdf_text']='임의 수정'
        h=content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        with self.assertRaises(ReviewError):validate_manifest(m,l,c,r)
    def test_authored_invalid_units_rejected_without_changing_source_review(self):
        m,l,c,r=example();l['map']['steps'][0]['writing_units']=[]
        h=content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        from solution_video.contracts import InputError
        with self.assertRaises(InputError):validate_manifest(m,l,c,r)
    def test_caption_layout_is_validated_for_legacy(self):
        from solution_video.contracts import InputError
        m,l,c,r=example();m['segments'][0]['text']='r_'+'O'*40
        h=content_fingerprint(m,l,c);c['input_hash']=r['input_hash']=h
        with self.assertRaisesRegex(InputError,'segment intro'):validate_manifest(m,l,c,r)
