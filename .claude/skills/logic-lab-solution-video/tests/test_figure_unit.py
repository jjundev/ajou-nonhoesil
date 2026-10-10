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
        for s in p['shapes']:
            if s['kind']=='unclassified' and inside(s['bbox'],WORK): s['kind']='answer_box'  # 표 칸 선: 저작자가 지정하는 값
        ids=lambda kind:[o['id'] for o in p[kind] if inside(o['bbox'],WORK)]
        return {'work_bbox':WORK,'steps':[{'id':'s','glyph_ids':ids('glyphs'),'shape_ids':ids('shapes')}],'answer_step_id':'s'}
    def test_matching_image_becomes_figure_shape(self):
        p=self.page([PACK/'자료/figures/solutions/q-dec2x4-design-solution-01.png'])
        figs=[s for s in p['shapes'] if s['kind']=='figure']
        self.assertEqual([f['figure_source'] for f in figs],['q-dec2x4-design-solution-01.png'])
        self.assertEqual([round(x) for x in figs[0]['bbox']],[322,188,513,339])
        self.assertFalse(any(inside(i['bbox'],WORK) for i in p['images']))
    def test_unmatched_solution_image_still_stops(self):
        p=self.page([PACK/'자료/figures/solutions/q-enc4x2-design-solution-01.png'])  # 다른 문항 그림은 대응하지 않는다
        self.assertFalse(any(s['kind']=='figure' for s in p['shapes']))
        with self.assertRaisesRegex(ExtractionError,'solution region contains image'):
            extract_layers(p,self.mapping(p))
    def test_gate_zero_with_figure_target(self):
        p=self.page([PACK/'자료/figures/solutions/q-dec2x4-design-solution-01.png'])
        r=compare_completed(extract_layers(p,self.mapping(p)),self.run/'evidence')
        self.assertEqual((r['pixel_diff'],r['non_target_diff'],r['hidden_leaks']),(0,0,0))
    def test_repeated_gate_stays_exact(self):
        # 같은 정적 SVG 를 다시 찍어도 합성 중간 화면을 잡지 않아야 한다(부하 중 721px 차이가 났던 경우).
        p=self.page([PACK/'자료/figures/solutions/q-dec2x4-design-solution-01.png']);l=extract_layers(p,self.mapping(p))
        for attempt in range(8):
            with self.subTest(attempt=attempt):
                r=compare_completed(l,self.run/('evidence-'+str(attempt)))
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
        with self.assertRaisesRegex(InputError,r'figure chunk cannot fit.*chunk1'): build_writing_camera_keys(l,t,compile_writing_units(l))
    def test_oversized_figure_only_chunk_gets_figure_message(self):
        # 글자가 없는 그림 묶음('fig')도 그림 문구를 받는다(다른 줄의 글자 묶음 'txt' 는 들어간다).
        l=self.layers([0,40,1000,740]); l['glyphs'][0]['bbox']=[0,10,9,19]
        l['map']['steps'][0]['writing_units']=[unit('u0',[0,9],['t'],[],line='line1',chunk='txt'),unit('u1',[0,1000],[],['f'],line='line2',chunk='fig')]
        t=self.timeline(l)
        with self.assertRaisesRegex(InputError,r'figure chunk cannot fit even at the full-page view; crop or split the figure: fig$'): build_writing_camera_keys(l,t,compile_writing_units(l))
    def test_oversized_text_chunk_beside_a_figure_chunk_keeps_text_message(self):
        # 그림이 다른 묶음에 있어도 글자만 든 묶음은 글자 문구(작은 묶음으로 나누라)를 받는다.
        gs=[dict(id='a',text='가',bbox=[0,300,10,310],paint_order=0),dict(id='b',text='나',bbox=[1000,300,1010,310],paint_order=1)]
        ss=[dict(id='f',bbox=[320,40,620,200],kind='figure',paint_order=2,svg_ids=['x'],figure_source='a.png')]
        us=[unit('u1',[320,620],[],['f'],line='line1',chunk='fig'),unit('u2',[0,1010],['a','b'],[],line='line2',chunk='wide',camera_break=True)]
        l=dict(glyphs=gs,shapes=ss,metadata=dict(width_pt=1010,height_pt=568),map=dict(steps=[dict(id='step',glyph_ids=['a','b'],shape_ids=['f'],writing_units=us)]))
        t=self.timeline(l)
        with self.assertRaisesRegex(InputError,r'writing chunk cannot fit at 26px; author smaller chunks: wide$'): build_writing_camera_keys(l,t,compile_writing_units(l))
    def mixed_chunk(self,width,height,text_boxes,fig_bbox):
        # 글자와 그림이 한 묶음('mix')에 든 쪽. 그림 혼자는 전체 쪽 배율에서 들어가는 작은 그림이다.
        gs=[dict(id='t%d'%i,text='가',bbox=list(b),paint_order=i) for i,b in enumerate(text_boxes)]
        ss=[dict(id='f',bbox=list(fig_bbox),kind='figure',paint_order=len(gs),svg_ids=['x'],figure_source='a.png')]
        ids=[g['id'] for g in gs]
        l=dict(glyphs=gs,shapes=ss,metadata=dict(width_pt=width,height_pt=height),
               map=dict(steps=[dict(id='step',glyph_ids=ids,shape_ids=['f'],writing_units=[unit('u1',[0,width],ids,['f'],chunk='mix')])]))
        return l,self.timeline(l)
    def test_small_figure_in_oversized_text_chunk_gets_text_message(self):
        # 묶음이 쪽 높이 전체에 걸쳐 안 들어간다. 그림(30x30)은 혼자 들어가므로 원인은 묶음 구성이다.
        l,t=self.mixed_chunk(841.9,595,[[100,10,109,19],[100,570,109,579]],[300,300,330,330])
        with self.assertRaisesRegex(InputError,r'writing chunk cannot fit at 26px; author smaller chunks: mix$'): build_writing_camera_keys(l,t,compile_writing_units(l))
    def test_small_figure_in_page_wide_text_chunk_on_16x9_page_gets_text_message(self):
        l,t=self.mixed_chunk(1440,810,[[0,300,9,309],[1431,300,1440,309]],[600,100,630,130])
        with self.assertRaisesRegex(InputError,r'writing chunk cannot fit at 26px; author smaller chunks: mix$'): build_writing_camera_keys(l,t,compile_writing_units(l))
    def test_big_figure_with_small_text_in_one_chunk_keeps_figure_message(self):
        l,t=self.mixed_chunk(1010,568,[[10,10,19,19]],[0,40,1000,540])
        with self.assertRaisesRegex(InputError,r'figure chunk cannot fit even at the full-page view; crop or split the figure: mix$'): build_writing_camera_keys(l,t,compile_writing_units(l))
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
