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
        with self.assertRaisesRegex(InputError,'chunk'):self.keys(l,t)
        l,t=self.fixture(800,True);self.assertEqual(len(self.keys(l,t)),4)
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
