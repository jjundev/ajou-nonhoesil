from fixtures import *
import copy
from test_annotations import teaching_fixture
from solution_video.annotations import validate_teaching
from solution_video.contracts import InputError
from solution_video.util import write
try:
 from solution_video.lesson import validate_lesson,load_lesson,lesson_expectations
except ImportError:
 validate_lesson=load_lesson=lesson_expectations=None

def lesson_fixture():
 f,a,m,l=teaching_fixture()
 for s in m['segments']:s['caption_text']=s['text'];s['source_refs']=['answer:1']
 m['segments'][1]['step_id']='s'
 p=validate_teaching(f,a,m,l)
 lesson=dict(schema_version=1,steps=[dict(step_id='s',mode='circuit',reason_segment_ids=['r'],check_segment_ids=[],region_ids=['circuit'],annotation_ids=['a'],meaning_notes='original connection',source_refs=['answer:1'])])
 t=dict(segments=[dict(s,start_sample=n*80000,end_sample=(n+1)*80000) for n,s in enumerate(m['segments'])],teaching=dict(cues=[dict(segment_id='r',target='circuit',start_frame=100,end_frame=200)],spans=[dict(id='a',kind='draw',start_frame=120,end_frame=138,hide_frame=300)]))
 return lesson,m,l,p,t

class LessonTests(Sandbox):
 def test_guided_core_steps_have_prior_reason(self):
  self.assertIsNotNone(validate_lesson)
  d,m,l,p,t=lesson_fixture();self.assertEqual(validate_lesson(d,m,l,p),d)
  e=lesson_expectations(d,m,t,p)
  self.assertEqual(e['steps'][0]['write_segment_id'],'w');self.assertTrue(e['probes'])
 def test_missing_late_reason_rejected(self):
  for name in ['load','parallel','gain']:
   d,m,l,p,_=lesson_fixture();d['steps'][0]['step_id']=name;l['map']['steps'][0]['id']=name
   for s in m['segments'][1:]:s['step_id']=name
   d['steps'][0]['reason_segment_ids']=[]
   with self.subTest(name=name),self.assertRaisesRegex(InputError,name):validate_lesson(d,m,l,p)
 def test_unknown_or_duplicate_link(self):
  for key,bad in [('reason_segment_ids',['unknown']),('reason_segment_ids',['w']),('region_ids',['unknown']),('annotation_ids',['unknown']),('annotation_ids',['a','a'])]:
   d,m,l,p,_=lesson_fixture();d['steps'][0][key]=bad
   with self.subTest(key=key,bad=bad),self.assertRaises(InputError):validate_lesson(d,m,l,p)
  d,m,l,p,_=lesson_fixture();d['steps']*=2
  with self.assertRaises(InputError):validate_lesson(d,m,l,p)
  d,m,l,p,_=lesson_fixture();m['segments'][1]['step_id']='other'
  with self.assertRaises(InputError):validate_lesson(d,m,l,p)
 def test_calculation_exemption(self):
  d,m,l,p,_=lesson_fixture();row=d['steps'][0];row.update(mode='calculation',reason_segment_ids=[],region_ids=[],annotation_ids=[])
  with self.assertRaises(InputError):validate_lesson(d,m,l,p)
  row['exemption_reason']='same established equation';self.assertEqual(validate_lesson(d,m,l,p),d)
 def test_missing_guided_caption(self):
  d,m,l,p,_=lesson_fixture();del m['segments'][0]['caption_text']
  with self.assertRaises(InputError):validate_lesson(d,m,l,p)
 def test_legacy_no_lesson(self):
  _,m,l,p,_=lesson_fixture();self.assertIsNone(load_lesson(self.run,m,l,p))
 def test_reversed_actual_timing(self):
  d,m,l,p,t=lesson_fixture();t['segments'][1]['end_sample']=t['segments'][2]['start_sample']+800
  with self.assertRaises(InputError):lesson_expectations(d,m,t,p)
 def test_hidden_or_unfinished_annotation_rejected(self):
  for field,value in [('hide_frame',130),('end_frame',190)]:
   d,m,l,p,t=lesson_fixture();t['teaching']['spans'][0][field]=value
   with self.assertRaises(InputError):lesson_expectations(d,m,t,p)
 def test_check_before_write_rejected(self):
  d,m,l,p,_=lesson_fixture();m['segments'].insert(2,dict(id='c',kind='check',step_id='s',text='check',caption_text='check'));d['steps'][0]['check_segment_ids']=['c']
  with self.assertRaises(InputError):validate_lesson(d,m,l,p)

 def test_missing_guided_gate_blocks_complete(self):
  from solution_video.lesson import lesson_screen_passed
  expected={'probes':[{'frame':138}]}
  self.assertFalse(lesson_screen_passed(expected,None))
  self.assertFalse(lesson_screen_passed(expected,{}))
  self.assertFalse(lesson_screen_passed(expected,{'lesson_flow':False}))
  self.assertTrue(lesson_screen_passed(expected,{'lesson_flow':True}))
  self.assertTrue(lesson_screen_passed({'probes':[]},None))

 def test_chunk_evidence_probes(self):
  d,m,l,p,t=lesson_fixture();p['items'][0]['chunk_id']='c1';p['items'].append(dict(p['items'][0],id='b',chunk_id='c2'));d['steps'][0]['annotation_ids'].append('b')
  t['caption_cues']=[dict(segment_id='r',chunk_id='c1',start_sample=80000,end_sample=120000),dict(segment_id='r',chunk_id='c2',start_sample=120000,end_sample=150000)]
  t['teaching']['spans'].append(dict(id='b',kind='draw',start_frame=156,end_frame=174,hide_frame=300))
  e=lesson_expectations(d,m,t,p);chunk_probes=[v for v in e['probes'] if 'chunk_id' in v]
  self.assertEqual([(v['chunk_id'],v['frame'],v['annotation_ids']) for v in chunk_probes],[('c1',138,['a']),('c2',174,['b'])])
  t['caption_cues'][0]['end_sample']=138*800-1
  with self.assertRaisesRegex(InputError,'c1'):lesson_expectations(d,m,t,p)
