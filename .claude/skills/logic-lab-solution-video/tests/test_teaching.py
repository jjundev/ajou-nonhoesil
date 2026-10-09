from fixtures import *
from test_annotations import teaching_fixture,make_teaching_plan
from solution_video.reveal import build_timeline
from solution_video.review_adapter import default_config
from solution_video.util import digest
from solution_video.contracts import InputError
try:
 from solution_video.teaching import build_teaching_timeline,minimum_segment_frames,teaching_timing_settings
except ImportError:build_teaching_timeline=minimum_segment_frames=teaching_timing_settings=None
class TeachingTimingTests(Sandbox):
 def timeline(self,p):
  _,_,m,l=teaching_fixture();a=[make_audio(s['id'],800,self.run) for s in m['segments']]
  return build_teaching_timeline(m,l,a,default_config(),None,p)
 def test_short_voice_appends_silence(self):
  self.assertIsNotNone(build_teaching_timeline,'teaching timing builder missing')
  p=make_teaching_plan();self.assertEqual(minimum_segment_frames(p)['r'],80)
  t=self.timeline(p);r,w=t['segments'][1:]
  self.assertEqual(r['voice_samples'],800);self.assertEqual(r['end_sample']-r['start_sample'],64000)
  self.assertEqual(w['start_sample'],64800);self.assertEqual(t['events'][0]['frame'],86)
  self.assertEqual([(s['kind'],s['start_frame'],s['end_frame']) for s in t['teaching']['spans']],[('move',13,21),('draw',21,39)])
 def test_focus_only_minimum(self):
  self.assertIsNotNone(build_teaching_timeline,'teaching timing builder missing')
  p=make_teaching_plan();p['items']=[];self.assertEqual(minimum_segment_frames(p),{'r':54})
 def test_no_plan_byte_equivalent(self):
  self.assertIsNotNone(build_teaching_timeline,'teaching timing builder missing')
  _,_,m,l=teaching_fixture();a=[make_audio(s['id'],800,self.run) for s in m['segments']]
  self.assertEqual(build_teaching_timeline(m,l,a,default_config(),None,None),build_timeline(m,l,a,default_config()))
 def test_timing_projection(self):
  self.assertIsNotNone(build_teaching_timeline,'teaching timing builder missing')
  import copy
  p=make_teaching_plan();q=copy.deepcopy(p);q['items'][0]['color']='#FF0000';q['items'][0]['geometry']['to']=[70,70]
  self.assertEqual(digest(teaching_timing_settings(p)),digest(teaching_timing_settings(q)))
  q['items'][0]['duration_frames']=24;self.assertNotEqual(digest(teaching_timing_settings(p)),digest(teaching_timing_settings(q)))
 def test_late_check_offsets_labels_and_hide(self):
  self.assertIsNotNone(build_teaching_timeline,'teaching timing builder missing')
  p=make_teaching_plan();p['items'][0].update(hide_at=dict(segment_id='r',offset_frames=37))
  with self.assertRaises(InputError):self.timeline(p)
  p['items'][0]['hide_at']={'segment_id':'w','offset_frames':0}
  self.assertEqual(self.timeline(p)['teaching']['spans'][0]['hide_frame'],81)
 def test_late_check_24_char_label_shifts_two_column_writing(self):
  from solution_video.annotations import validate_teaching
  from solution_video.writing import default_writing
  f,a,m,l=teaching_fixture()
  m['segments'] += [dict(id='c',kind='check',step_id='s',text='check'),dict(id='w2',kind='write',step_id='s2',text='write')]
  l['glyphs'].append(dict(id='g2',text='y',bbox=[250,180,260,190],svg_ids=['g2'],paint_order=1));l['map']['steps'].append(dict(id='s2',glyph_ids=['g2'],shape_ids=[]));m['reveal_order'].append('g2')
  f['cues'].append(dict(segment_id='c',target='circuit'));a['items'].append(dict(a['items'][0],id='label',segment_id='c',kind='label',geometry={'runs':[dict(text='x'*24,origin=[40,60],font_size_pt=4)]},hide_at={'segment_id':'c','offset_frames':190}))
  p=validate_teaching(f,a,m,l);audio=[make_audio(s['id'],800,self.run) for s in m['segments']]
  w=default_writing();w['chars_per_second']=5
  t=build_teaching_timeline(m,l,audio,default_config(),w,p)
  self.assertEqual(minimum_segment_frames(p),{'r':80,'c':206})
  self.assertEqual([e['frame'] for e in t['events']],[87,329]);self.assertEqual(t['segments'][-1]['start_sample'],316*800)
  self.assertEqual(t['total_frames'],382)
  draws=[s for s in t['teaching']['spans'] if s['id']=='label' and s['kind']=='draw']
  self.assertEqual(len(draws),24);self.assertEqual(draws[-1]['end_frame'],274);self.assertEqual(draws[-1]['hide_frame'],300)
  self.assertEqual([s['end_frame']-s['start_frame'] for s in draws],[5]*24)
