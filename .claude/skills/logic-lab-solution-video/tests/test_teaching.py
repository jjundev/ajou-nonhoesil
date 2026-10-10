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

class ChunkWindowTests(Sandbox):
 def fixture(self):
  import copy
  p=make_teaching_plan();p['items'][0].update(chunk_id='c1',offset_frames=0)
  p['items'].append(dict(copy.deepcopy(p['items'][0]),id='b',chunk_id='c2'))
  t=dict(segments=[dict(id='r',start_sample=80000,end_sample=200000)],caption_cues=[dict(segment_id='r',chunk_id='c1',start_sample=80000,end_sample=104000),dict(segment_id='r',chunk_id='c2',start_sample=104001,end_sample=180001)])
  # 첫 청크는 처음 12f 카메라 + 26f 표시를 담아야 한다.
  t['caption_cues'][0]['end_sample']=104000+8000
  t['caption_cues'][1]['start_sample']=104001+8000
  return p,t
 def resolve(self,p,t):
  import solution_video.teaching as module
  self.assertTrue(hasattr(module,'resolve_annotation_windows'),'chunk resolver missing')
  return module.resolve_annotation_windows(p,t)
 def test_chunk_absolute_windows(self):
  p,t=self.fixture();t['caption_cues'][0]['end_sample']=112000;t['caption_cues'][1]['start_sample']=104001
  # 첫 표시가 138 에 끝나므로 둘째를 오프셋 7 에 둔다: ceil(130.001)+7=138.
  p['items'][1]['offset_frames']=7
  windows=self.resolve(p,t);self.assertEqual([(w['start_frame'],w['end_frame']) for w in windows],[(112,138),(138,164)])
  p['items']=p['items'][1:];p['items'][0]['offset_frames']=0
  self.assertEqual(self.resolve(p,t)[0]['start_frame'],131)
 def test_overlap_deadline_hide_and_long_label(self):
  p,t=self.fixture();self.assertEqual([w['start_frame'] for w in self.resolve(p,t)],[112,141])
  t['caption_cues'][1]['start_sample']=104001
  with self.assertRaisesRegex(InputError,'b.*r.*c2'):self.resolve(p,t)
  p,t=self.fixture();t['caption_cues'][0]['end_sample']=138*800-1
  with self.assertRaisesRegex(InputError,'a.*r.*c1'):self.resolve(p,t)
  p,t=self.fixture();p['items'][0].update(kind='label',units=list('x'*24))
  with self.assertRaisesRegex(InputError,'a.*r.*c1'):self.resolve(p,t)
  p,t=self.fixture();t['segments'][0]['end_sample']=163*800
  with self.assertRaisesRegex(InputError,'b'):self.resolve(p,t)
 def test_same_segment_early_hide(self):
  # 청크 모드는 검증 단계에서 같은 segment hide 비교를 건너뛰므로 window 단계가 막아야 한다.
  p,t=self.fixture();p['items'][0]['hide_at']=dict(segment_id='r',offset_frames=20)
  with self.assertRaisesRegex(InputError,'a segment r chunk c1'):self.resolve(p,t)
 def test_chunk_marks_do_not_extend_segment_and_projection(self):
  import copy
  p,_=self.fixture();p['items'][0]['duration_frames']=300
  self.assertEqual(minimum_segment_frames(p),{'r':54})
  q=copy.deepcopy(p);q['items'][0]['chunk_id']='c2'
  self.assertNotEqual(teaching_timing_settings(p),teaching_timing_settings(q))
  q=copy.deepcopy(p);q['items'][0]['stroke_width_px']=8;q['items'][0]['color']='#C45100'
  self.assertEqual(teaching_timing_settings(p),teaching_timing_settings(q))
 def test_legacy_plan_spans_and_projection_unchanged(self):
  # 청크 없는 계획은 span 과 timing 해시 입력이 이전과 같아야 기존 run 의 timeline 이 그대로 통한다.
  _,_,m,l=teaching_fixture();a=[make_audio(s['id'],800,self.run) for s in m['segments']]
  t=build_teaching_timeline(m,l,a,default_config(),None,make_teaching_plan())
  self.assertEqual([(s['kind'],s['start_frame'],s['end_frame']) for s in t['teaching']['spans']],[('move',13,21),('draw',21,39)])
  self.assertNotIn('chunk_id',teaching_timing_settings(make_teaching_plan())['items'][0])
