from fixtures import *
from test_manifest import example
from solution_video.reveal import build_timeline,visible_ids
from solution_video.review_adapter import default_config
class RevealTests(Sandbox):
    def setUp(self):
        super().setUp(); self.m,self.l,_,_=example()
        self.l['glyphs']=[dict(id='g'+str(i),text='가',bbox=[100,100,110,110],svg_ids=['sv'+str(i)],paint_order=i) for i in range(70)]
        self.l['map']['steps'][0]['glyph_ids']=[g['id'] for g in self.l['glyphs'][:-1]]; self.l['map']['steps'][1]['glyph_ids']=['g69']; self.m['reveal_order']=[g['id'] for g in self.l['glyphs']]; self.m['shape_anchors']={'s1':'g69'}
        self.audio=[make_audio(s['id'],24000,self.run) for s in self.m['segments']]
    def test_short_pcm_extends_writing(self):
        t=build_timeline(self.m,self.l,self.audio,default_config())
        self.assertGreaterEqual(t['total_samples'],258000); self.assertEqual(t['total_frames']*800,t['total_samples'])
        self.assertEqual(visible_ids(t,t['total_frames']-1),self.m['reveal_order'])
        events=[e for e in t['events'] if e['kind']=='glyph']
        self.assertTrue(all(b['frame']-a['frame']>=5 for a,b in zip(events,events[1:])))
    def test_seek_is_pure(self):
        t=build_timeline(self.m,self.l,self.audio,default_config()); frames=[0,t['total_frames']-1,100,0]
        results=[visible_ids(t,f) for f in frames]; self.assertEqual(results[0],results[-1]); self.assertEqual(results[2],visible_ids(t,100))

class PencilTimingTests(Sandbox):
    def fixture(self,texts=('x','y'),boxes=None):
        m,l,_,_=example();m['segments']=[dict(id='w',kind='write',step_id='s')]
        boxes=boxes or [[100+i*12,100,110+i*12,110] for i in range(len(texts))]
        l['glyphs']=[dict(id='g'+str(i),text=t,bbox=b,svg_ids=[],paint_order=i) for i,(t,b) in enumerate(zip(texts,boxes))]
        l['map']['steps']=[dict(id='s',glyph_ids=[g['id'] for g in l['glyphs']])];m['shape_anchors']={'line':'g1'}
        return m,l,[make_audio('w',800,self.run)]
    def timeline(self,*args):
        from solution_video.writing import default_writing
        m,l,a=self.fixture(*args);w=default_writing();w['chars_per_second']=5;return build_timeline(m,l,a,default_config(),w)
    def test_requested_default_is_one_and_half_faster(self):
        from solution_video.writing import default_writing
        m,l,a=self.fixture();t=build_timeline(m,l,a,default_config(),default_writing())
        self.assertEqual([(s['start_frame'],s['end_frame']) for s in t['writing_spans'] if s['kind']=='draw'],[(1,4),(5,8)])
        self.assertEqual([e['frame'] for e in t['events'] if e['kind']=='glyph'],[4,8])
    def test_pencil_six_frame_slots(self):
        t=self.timeline()
        self.assertEqual([(s['kind'],s['start_frame'],s['end_frame']) for s in t['writing_spans']],[('move',0,1),('draw',1,6),('move',6,7),('draw',7,12)])
        self.assertEqual([e['frame'] for e in t['events'] if e['kind']=='glyph'],[6,12])
        self.assertEqual(t['segments'][0]['end_sample'],35*800)
        self.assertEqual(t['total_samples'],t['total_frames']*800)
    def test_lifted_moves_and_subscripts(self):
        t=self.timeline(('x','1','y'),[[100,100,110,110],[110,109,115,115],[100,130,110,140]])
        self.assertEqual([s['end_frame']-s['start_frame'] for s in t['writing_spans'] if s['kind']=='move'],[1,1,8])
        self.assertEqual([s['end_frame']-s['start_frame'] for s in t['writing_spans'] if s['kind']=='draw'],[5,5,5])
    def test_whitespace_has_no_draw(self):
        t=self.timeline(('x',' ','y'));self.assertEqual([s['id'] for s in t['writing_spans'] if s['kind']=='draw'],['g0','g2'])
        self.assertEqual([e['frame'] for e in t['events'] if e['kind']=='glyph'],[6,12,18])
    def test_legacy_timeline_unchanged(self):
        m,l,a=self.fixture();t=build_timeline(m,l,a,default_config())
        self.assertNotIn('writing_spans',t);self.assertEqual([e['frame'] for e in t['events'] if e['kind']=='glyph'],[5,10])
    def test_invalid_pcm_blocks_retime_data(self):
        from solution_video.writing import default_writing
        from solution_video.contracts import InputError
        m,l,a=self.fixture();a[0]['samples']=True
        with self.assertRaises(InputError):build_timeline(m,l,a,default_config(),default_writing())

class SpatialTimingTests(Sandbox):
    def timeline(self):
        from test_writing_units import spatial_layers
        from solution_video.writing import default_writing
        layers=spatial_layers();manifest=dict(segments=[dict(id='w',kind='write',step_id='step')],shape_anchors={'bar':'right'},cameras=[])
        return build_timeline(manifest,layers,[make_audio('w',800,self.run)],default_config(),default_writing())
    def test_unit_order_is_spatial_not_paint_order(self):
        t=self.timeline()
        self.assertEqual([s['id'] for s in t['writing_spans'] if s['kind']=='draw'],['left','bar','sub','bar','right'])
        self.assertEqual([u['unit_id'] for u in t['writing_unit_spans']],['u1','u2'])
    def test_piece_final_event_once(self):
        t=self.timeline(); events=[e for e in t['events'] if e['id']=='bar']
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['frame'],[s['end_frame'] for s in t['writing_spans'] if s['id']=='bar' and s['kind']=='draw'][-1])
    def test_fraction_shape_has_no_future_leak(self):
        t=self.timeline();bar=[s for s in t['writing_spans'] if s['id']=='bar' and s['kind']=='draw']
        self.assertEqual([s['clip_bbox'] for s in bar],[[0,26,10,27],[10,26,30,27]])
        self.assertTrue(all(s['end_frame']>s['start_frame'] for s in bar))
    def test_shape_total_budget(self):
        # 조각마다 18프레임이 아니라 도형 하나에 예산 18(폭 30, 높이 10, 간격 4)을 폭 10:20 으로 나눈다.
        t=self.timeline();bar=[s for s in t['writing_spans'] if s['id']=='bar' and s['kind']=='draw']
        self.assertEqual([s['end_frame']-s['start_frame'] for s in bar],[6,12])
    def test_split_box_budget_never_slower(self):
        from test_writing_units import unit
        from solution_video.writing import default_writing
        def draw_total(n):
            l=dict(glyphs=[dict(id='a',text='a',bbox=[0,0,10,10],paint_order=0)],shapes=[dict(id='box',bbox=[0,20,240,40],paint_order=1)],
                   map=dict(steps=[dict(id='step',glyph_ids=['a'],shape_ids=['box'],writing_units=[unit('g',[0,10],['a'],line='l0')]+
                       [unit('b'+str(i),[240*i/n,240*(i+1)/n],[],['box'],line='l1') for i in range(n)])]))
            m=dict(segments=[dict(id='w',kind='write',step_id='step')],shape_anchors={},cameras=[])
            t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),default_writing())
            box=[s for s in t['writing_spans'] if s['id']=='box' and s['kind']=='draw']
            self.assertEqual(len(box),n);return sum(s['end_frame']-s['start_frame'] for s in box)
        # 한 조각은 기존 18 그대로, 24조각은 432 가 아니라 폭 공식 상한 90, 5조각 이상이면 같은 예산.
        self.assertEqual(draw_total(1),18);self.assertEqual(draw_total(24),90);self.assertEqual(draw_total(5),90)
    def test_lift_once_per_new_line(self):
        from test_writing_units import spatial_layers,unit
        from solution_video.writing import default_writing
        l=spatial_layers();l['glyphs']+=[dict(id='a',text=' ',bbox=[0,40,1,50],paint_order=4),dict(id='b',text='b',bbox=[2,40,12,50],paint_order=5)]
        l['map']['steps'][0]['glyph_ids']+=['a','b'];l['map']['steps'][0]['writing_units'].append(unit('u3',[0,12],['a','b'],line='line2'))
        m=dict(segments=[dict(id='w',kind='write',step_id='step')],shape_anchors={},cameras=[])
        t=build_timeline(m,l,[make_audio('w',800,self.run)],default_config(),default_writing())
        moves=[s for s in t['writing_spans'] if s['unit_id']=='u3' and s['kind']=='move']
        # 새 줄 첫 대상(공백이어도) 한 번만 들어 옮기고 뒤 대상은 인접 이동.
        self.assertEqual([s['lifted'] for s in moves],[True,False]);self.assertEqual([s['end_frame']-s['start_frame'] for s in moves],[8,1])
