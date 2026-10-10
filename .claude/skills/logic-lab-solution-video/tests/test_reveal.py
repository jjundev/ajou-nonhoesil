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
        self.assertTrue(all(s['end_frame']-s['start_frame']>=18 for s in bar))
