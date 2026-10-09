from fixtures import *
from test_writing_units import unit
from solution_video.pdf_pages import export_page,extract_layers,compare_completed,figure_pixel_hash,inside
from solution_video.contracts import ExtractionError,InputError
from solution_video.reveal import build_timeline,FIGURE_DRAW_FRAMES
from solution_video.writing import default_writing
from solution_video.writing_units import compile_writing_units
from solution_video.writing_camera import build_writing_camera_keys
from solution_video.review_adapter import default_config
PACK=REPO/'복습노트/실험05'
WORK=[300,59,760,560]  # 쪽 폭 841.9pt, Hint 단(x≈760) 왼쪽, '답' 상자 위까지
class FigureUnitTests(Sandbox):
    def page(self,refs):
        return export_page(PACK/'실험05_기출풀이.pdf',3,self.run/'layers',refs)  # 기출4 q-dec2x4-design (쪽 인덱스 3, 실측)
    def mapping(self,p):
        ids=lambda kind:[o['id'] for o in p[kind] if inside(o['bbox'],WORK)]
        return {'work_bbox':WORK,'steps':[{'id':'s','glyph_ids':ids('glyphs'),'shape_ids':ids('shapes')}],'answer_step_id':'s'}
    def test_matching_image_becomes_figure_shape(self):
        p=self.page([PACK/'figures/solutions/q-dec2x4-design-solution-01.png'])
        figs=[s for s in p['shapes'] if s['kind']=='figure']
        self.assertEqual([f['figure_source'] for f in figs],['q-dec2x4-design-solution-01.png'])
        self.assertEqual([round(x) for x in figs[0]['bbox']],[322,170,622,407])
        self.assertFalse(any(inside(i['bbox'],WORK) for i in p['images']))
    def test_unmatched_solution_image_still_stops(self):
        p=self.page([PACK/'figures/solutions/q-enc4x2-design-solution-01.png'])  # 다른 문항 그림은 대응하지 않는다
        self.assertFalse(any(s['kind']=='figure' for s in p['shapes']))
        with self.assertRaisesRegex(ExtractionError,'solution region contains image'):
            extract_layers(p,self.mapping(p))
    def test_gate_zero_with_figure_target(self):
        p=self.page([PACK/'figures/solutions/q-dec2x4-design-solution-01.png'])
        r=compare_completed(extract_layers(p,self.mapping(p)),self.run/'evidence')
        self.assertEqual((r['pixel_diff'],r['non_target_diff'],r['hidden_leaks']),(0,0,0))
    def layers(self,fig_bbox,glyph_h=9):
        x0,y0,x1,y1=fig_bbox
        gs=[dict(id='t',text='완',bbox=[x0,y0-glyph_h-4,x0+glyph_h,y0-4],paint_order=0)]
        ss=[dict(id='f',bbox=list(fig_bbox),kind='figure',paint_order=1,svg_ids=['x'],figure_source='a.png')]
        us=[unit('u1',[x0,x1],['t'],['f'])]
        return dict(glyphs=gs,shapes=ss,metadata=dict(width_pt=841.9,height_pt=595),map=dict(steps=[dict(id='step',glyph_ids=['t'],shape_ids=['f'],writing_units=us)]))
    def timeline(self,l):
        manifest=dict(segments=[dict(id='intro',kind='problem'),dict(id='w',kind='write',step_id='step')],shape_anchors={},cameras=[])
        return build_timeline(manifest,l,[make_audio('intro',24000,self.run),make_audio('w',800,self.run)],default_config(),default_writing())
    def test_figure_draw_frames(self):
        t=self.timeline(self.layers([320,170,620,407]))
        draws=[s for s in t['writing_spans'] if s['kind']=='draw' and s['id']=='f']
        self.assertEqual(FIGURE_DRAW_FRAMES,60)
        self.assertEqual([s['end_frame']-s['start_frame'] for s in draws],[60])
    def test_figure_camera_fallback(self):
        l=self.layers([320,100,620,500]); t=self.timeline(l)  # 26px(9pt 기준) 배율로는 세로 1156px 이라 안 들어간다
        keys=build_writing_camera_keys(l,t,compile_writing_units(l)); v=keys[1]['viewbox']
        self.assertTrue(inside([320,100,620,500],[v[0],v[1],v[0]+v[2],v[1]+v[3]]))
    def test_oversized_figure_rejected(self):
        l=self.layers([0,40,1000,740]); t=self.timeline(l)
        with self.assertRaisesRegex(InputError,'chunk1'): build_writing_camera_keys(l,t,compile_writing_units(l))
    def test_pixel_hash_ignores_encoding(self):
        import io; from PIL import Image
        im=Image.new('RGB',(3,2),(1,2,3)); a=io.BytesIO(); b=io.BytesIO(); im.save(a,'PNG'); im.save(b,'PNG',compress_level=0)
        self.assertEqual(figure_pixel_hash(a.getvalue()),figure_pixel_hash(b.getvalue()))
        c=io.BytesIO(); Image.new('RGB',(2,3),(1,2,3)).save(c,'PNG'); self.assertNotEqual(figure_pixel_hash(a.getvalue()),figure_pixel_hash(c.getvalue()))

class GateNoiseTests(Sandbox):
    def test_non_target_ignores_one_level_raster_noise(self):
        from PIL import Image
        from solution_video.pdf_pages import changed_pixels
        a=Image.new('RGB',(4,1),(54,54,54)); b=a.copy(); b.putpixel((0,0),(55,55,55)); b.putpixel((1,0),(56,54,54))
        self.assertEqual(changed_pixels(a,b,tolerance=2),0)
        b.putpixel((2,0),(57,54,54)); b.putpixel((3,0),(255,255,255))
        self.assertEqual(changed_pixels(a,b,tolerance=2),2)
        self.assertEqual(changed_pixels(a,b),4)
