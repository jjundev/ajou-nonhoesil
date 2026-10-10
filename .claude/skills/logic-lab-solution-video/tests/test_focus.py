from fixtures import *
from test_annotations import make_teaching_plan,teaching_fixture
from solution_video.teaching import build_teaching_timeline
from solution_video.review_adapter import default_config
try:
 from solution_video.focus import compile_focus_keys
except ImportError:compile_focus_keys=None
class FocusTests(Sandbox):
 def test_return_before_first_writing_and_final_full(self):
  self.assertIsNotNone(compile_focus_keys,'focus camera compiler missing')
  _,_,m,l=teaching_fixture();p=make_teaching_plan();t=build_teaching_timeline(m,l,[make_audio(s['id'],800,self.run) for s in m['segments']],default_config(),None,p)
  base=[dict(at_frame=0,viewbox=[0,0,400,300]),dict(at_frame=86,viewbox=[80,90,250,117.1875]),dict(at_frame=109,viewbox=[0,0,400,300])]
  keys=compile_focus_keys(m,l,t,p,None,base)
  self.assertEqual([k['at_frame'] for k in keys],[0,1,69,86,109])
  self.assertEqual(keys[2]['viewbox'],base[1]['viewbox']);self.assertEqual(keys[1]['transition_frames'],12)
  self.assertEqual(keys[-1]['viewbox'],[0,0,400,300])
 def test_label_and_accumulated_bounds(self):
  self.assertIsNotNone(compile_focus_keys,'focus camera compiler missing')
  _,_,m,l=teaching_fixture();p=make_teaching_plan();t=build_teaching_timeline(m,l,[make_audio(s['id'],800,self.run) for s in m['segments']],default_config(),None,p)
  compiled={'items':[dict(id='a',bbox=[5,30,190,90],body_height=8)],'svg':'','font_sha256':None}
  keys=compile_focus_keys(m,l,t,p,compiled,[dict(at_frame=0,viewbox=[0,0,400,300])]);b=keys[1]['viewbox'];scale=900/b[3]
  self.assertGreaterEqual(8*scale,26);self.assertLess(b[0],5);self.assertGreater(b[0]+b[2],190)
  compiled['items'][0]['bbox']=[0,0,4000,4000]
  from solution_video.contracts import InputError
  with self.assertRaisesRegex(InputError,'circuit'):compile_focus_keys(m,l,t,p,compiled,keys)
 def test_table_edges_and_infeasible_readability(self):
  from solution_video.page_layout import page_layout
  from solution_video.contracts import InputError
  _,_,m,l=teaching_fixture();p=make_teaching_plan();t=build_teaching_timeline(m,l,[make_audio(s['id'],800,self.run) for s in m['segments']],default_config(),None,p)
  for width,height,b in [(1440,810,[0,0,1440,40]),(400,300,[0,0,400,40]),(400,300,[0,0,1,99])]:
   l['metadata'].update(width_pt=width,height_pt=height);p['regions'][0]['bbox']=b
   keys=compile_focus_keys(m,l,t,p,None,[dict(at_frame=0,viewbox=[0,0,width,height])]);v=keys[1]['viewbox'];scale=min(1920/v[2],page_layout(width,height)['height']/v[3])
   self.assertGreaterEqual((b[0]-v[0])*scale,179);self.assertLessEqual((b[2]-v[0])*scale,1741)
   self.assertGreaterEqual((b[1]-v[1])*scale,199);self.assertLessEqual((b[3]-v[1])*scale,871)
 def test_configured_long_pen_fits_top_edge_annotation(self):
  from solution_video.writing import load_pencil_asset
  import math
  _,_,m,l=teaching_fixture();p=make_teaching_plan();t=build_teaching_timeline(m,l,[make_audio(s['id'],800,self.run) for s in m['segments']],default_config(),None,p);t['writing']={'pencil_length_px':400}
  compiled={'items':[dict(id='a',bbox=[20,40,20,55],body_height=None)],'svg':'','font_sha256':None}
  v=compile_focus_keys(m,l,t,p,compiled,[dict(at_frame=0,viewbox=[0,0,400,300])])[1]['viewbox'];sc=min(1920/v[2],900/v[3]);tip=[(20-v[0])*sc,(40-v[1])*sc]
  meta=load_pencil_asset(S/'assets/pencil');unit=400/math.dist(meta['tip_px'],meta['end_px']);b=meta['visible_bounds_px']
  for angle in [-2,0,2]:
   r=math.radians(angle)
   for x,y in [(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])]:
    dx=(x-meta['tip_px'][0])*unit;dy=(y-meta['tip_px'][1])*unit;sx=tip[0]+dx*math.cos(r)-dy*math.sin(r);sy=tip[1]+dx*math.sin(r)+dy*math.cos(r)
    self.assertGreaterEqual(sx,0);self.assertLessEqual(sx,1920);self.assertGreaterEqual(sy,0);self.assertLessEqual(sy,900)
