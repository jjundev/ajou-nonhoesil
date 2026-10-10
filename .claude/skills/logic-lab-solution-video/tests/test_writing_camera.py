from fixtures import *
from test_writing_units import unit
import importlib
from solution_video.contracts import InputError
from solution_video.reveal import build_timeline
from solution_video.writing import default_writing
from solution_video.review_adapter import default_config

class WritingCameraTests(Sandbox):
    def fixture(self,width=500,split=False,length=160):
        gs=[dict(id='g'+str(i),text='x',bbox=[100+i*width,300,110+i*width,310],paint_order=i) for i in range(2)]
        us=[unit('u1',[100,110],['g0']),unit('u2',[100+width,110+width],['g1'],chunk='chunk2' if split else 'chunk1',camera_break=split)]
        layers=dict(glyphs=gs,shapes=[],metadata=dict(width_pt=1000,height_pt=562.5),map=dict(steps=[dict(id='step',glyph_ids=['g0','g1'],shape_ids=[],writing_units=us)]))
        manifest=dict(segments=[dict(id='intro',kind='problem'),dict(id='w',kind='write',step_id='step')],shape_anchors={},cameras=[])
        w=default_writing();w['pencil_length_px']=length
        t=build_timeline(manifest,layers,[make_audio('intro',24000,self.run),make_audio('w',800,self.run)],default_config(),w)
        return layers,t
    def keys(self,l,t):
        try: mod=importlib.import_module('solution_video.writing_camera')
        except ModuleNotFoundError:self.fail('whole-line camera compiler missing')
        from solution_video.writing_units import compile_writing_units
        return mod.build_writing_camera_keys(l,t,compile_writing_units(l))
    def test_return_fits_whole_next_line(self):
        l,t=self.fixture();keys=self.keys(l,t);v=keys[1]['viewbox'];scale=1080/v[3]
        for g in l['glyphs']:
            b=g['bbox'];self.assertGreaterEqual((b[0]-v[0])*scale,10);self.assertLessEqual((b[2]-v[0])*scale,1910)
            self.assertGreaterEqual((b[1]-v[1])*scale,10);self.assertLessEqual((b[3]-v[1])*scale,890)
        self.assertGreaterEqual(10*scale,26)
    def test_fitting_line_has_one_view(self):
        l,t=self.fixture();keys=self.keys(l,t)
        self.assertEqual(len(keys),3)
        self.assertEqual(keys[1]['transition_frames'],12)
    def test_long_line_requires_authored_chunks(self):
        l,t=self.fixture(800)
        with self.assertRaisesRegex(InputError,r'writing chunk cannot fit at 26px; author smaller chunks: chunk1'):self.keys(l,t)  # 글자 문구는 그림 문구로 바뀌지 않는다
        l,t=self.fixture(800,True);self.assertEqual(len(self.keys(l,t)),4)
    def test_long_line_with_plain_shape_is_not_a_figure_chunk(self):
        # 밑줄·답 상자 같은 도형이 든 글자 묶음은 그림 문구가 아니라 글자 문구를 받는다.
        l,t=self.fixture(800)
        l['shapes']=[dict(id='bar',bbox=[100,312,110,313],kind='unclassified',paint_order=2,svg_ids=['x'])]
        l['map']['steps'][0]['shape_ids']=['bar'];l['map']['steps'][0]['writing_units'][0]['shape_ids']=['bar']
        self.assertTrue(l['map']['steps'][0]['writing_units'][1]['chunk_id']==l['map']['steps'][0]['writing_units'][0]['chunk_id'])
        with self.assertRaisesRegex(InputError,r'writing chunk cannot fit at 26px; author smaller chunks: chunk1'):self.keys(l,t)
    def test_column_change_and_long_pen(self):
        l,t=self.fixture(500,length=400);self.assertEqual(len(self.keys(l,t)),3)
    def test_transition_has_no_draw(self):
        l,t=self.fixture(800,True);keys=self.keys(l,t)
        for k in keys:
            if 'transition_frames' not in k:continue
            for s in t['writing_spans']:
                if s['kind']=='draw':self.assertFalse(max(k['at_frame'],s['start_frame'])<min(k['at_frame']+12,s['end_frame']))
    def test_manual_camera_preserved_and_outside_timeline_rejected(self):
        l,t=self.fixture();t['cameras']=[dict(at_frame=1,viewbox=[20,20,100,100])]
        self.assertIn(t['cameras'][0],self.keys(l,t))
        t['cameras']=[dict(at_frame=t['total_frames']+1,viewbox=[20,20,100,100])]
        with self.assertRaisesRegex(InputError,'outside timeline'):self.keys(l,t)
    def test_manual_transition_crossing_chunk_boundary_rejected(self):
        l,t=self.fixture();t['cameras']=[dict(at_frame=29,viewbox=[20,20,100,100],transition_frames=12)]
        with self.assertRaisesRegex(InputError,'conflicts'):self.keys(l,t)
    def test_shape_only_chunk_keeps_page_context(self):
        # 글자 없는 답 상자 묶음은 상자 오른쪽으로 확대돼 답안이 사라지지 않게 쪽 전체+연필 여백 구도.
        l,t=self.fixture(50)
        l['shapes']=[dict(id='box',bbox=[900,300,980,340])]
        step=l['map']['steps'][0];step['shape_ids']=['box'];step['writing_units'].append(unit('empty',[900,980],[],['box'],line='shape_line',chunk='shape_chunk',camera_break=True))
        m=dict(segments=[dict(id='w',kind='write',step_id='step')],shape_anchors={},cameras=[])
        t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),default_writing())
        keys=self.keys(l,t);view=keys[-2]['viewbox'];scale=1080/view[3]
        for x,y in ((0,0),(1000,562.5)):
            self.assertGreaterEqual((x-view[0])*scale,0);self.assertLessEqual((x-view[0])*scale,1920)
            self.assertGreaterEqual((y-view[1])*scale,0);self.assertLessEqual((y-view[1])*scale,900)
        # 글자 묶음(첫 키, intro 가 없어 0프레임)은 그대로 26px 이상 확대.
        self.assertGreaterEqual(10*1080/keys[0]['viewbox'][3],26)
    def test_figure_only_chunk_keeps_figure_zoom(self):
        # 풀이 그림만 든 묶음은 도형 전용 구도가 아니라 기존 그림 확대 규칙을 따른다.
        l,t=self.fixture(50)
        l['shapes']=[dict(id='fig',bbox=[600,300,700,400],kind='figure')]
        step=l['map']['steps'][0];step['shape_ids']=['fig'];step['writing_units'].append(unit('fig_u',[600,700],[],['fig'],line='fig_line',chunk='fig_chunk',camera_break=True))
        m=dict(segments=[dict(id='w',kind='write',step_id='step')],shape_anchors={},cameras=[])
        t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),default_writing())
        view=self.keys(l,t)[-2]['viewbox']
        self.assertLess(view[2],1000*0.9)  # 쪽 전체보다 확대돼 있다
