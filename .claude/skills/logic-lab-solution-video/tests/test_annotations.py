from fixtures import *
import copy
from solution_video.contracts import InputError
try:
 from solution_video.annotations import validate_teaching,load_teaching
except ImportError:
 validate_teaching=load_teaching=None

def teaching_fixture():
 h='a'*64
 f=dict(schema_version=1,source_sha256=h,regions=[dict(id='circuit',bbox=[20,40,180,90])],cues=[dict(segment_id='r',target='circuit')])
 a=dict(schema_version=1,source_sha256=h,items=[dict(id='a',region_id='circuit',segment_id='r',kind='arrow',geometry={'from':[60,50],'to':[60,80]},source_refs=['answer:1'],meaning_notes='Current direction')])
 m=dict(segments=[dict(id='intro',kind='problem',step_id='',text='problem'),dict(id='r',kind='reason',step_id='',text='reason'),dict(id='w',kind='write',step_id='s',text='write')],cameras=[],shape_anchors={},reveal_order=['g'])
 l=dict(metadata=dict(source_sha256=h,width_pt=400,height_pt=300),map=dict(work_bbox=[100,100,300,240],steps=[dict(id='s',glyph_ids=['g'],shape_ids=[])],answer_step_id='s'),glyphs=[dict(id='g',text='x',bbox=[110,110,120,120],svg_ids=['g'],paint_order=0)],shapes=[])
 return f,a,m,l

def make_teaching_plan(): return validate_teaching(*teaching_fixture())

class AnnotationContractTests(Sandbox):
 def test_optional_legacy_and_focus_only(self):
  self.assertIsNotNone(validate_teaching,'teaching validation is missing')
  f,a,m,l=teaching_fixture();self.assertIsNone(validate_teaching(None,None,m,l))
  self.assertEqual(validate_teaching(f,None,m,l)['items'],[])
  f['cues']=[];self.assertIsNone(validate_teaching(f,None,m,l))
  self.assertIsNone(load_teaching(self.run,m,l))
 def test_normalized_defaults_and_label_runs(self):
  self.assertIsNotNone(validate_teaching,'teaching validation is missing')
  p=make_teaching_plan();i=p['items'][0]
  self.assertEqual((i['color'],i['offset_frames'],i['duration_frames'],i['hide_at']),('#1565C0',12,18,'final'))
  f,a,m,l=teaching_fixture();a['items'][0].update(kind='label',geometry={'runs':[dict(text='v',origin=[40,60],font_size_pt=12),dict(text='x',origin=[47,64],font_size_pt=8)]})
  self.assertEqual(validate_teaching(f,a,m,l)['items'][0]['units'],['v','x'])
 def test_invalid_authored_inputs(self):
  self.assertIsNotNone(validate_teaching,'teaching validation is missing')
  mutations=[lambda f,a,m,l:a.update(source_sha256='bad'),lambda f,a,m,l:f['regions'].append(copy.deepcopy(f['regions'][0])),lambda f,a,m,l:f['cues'][0].update(target='unknown'),lambda f,a,m,l:f['cues'][0].update(segment_id='w'),lambda f,a,m,l:m.update(cameras=[{}]),lambda f,a,m,l:f['regions'][0].update(bbox=[20,40,float('nan'),90]),lambda f,a,m,l:f['regions'][0].update(bbox=[20,40,True,90]),lambda f,a,m,l:f['regions'][0].update(bbox=[20,40,180,110]),lambda f,a,m,l:a['items'][0]['geometry'].update(to=[60,50]),lambda f,a,m,l:a['items'][0].update(kind='ellipse',geometry={'bbox':[40,40,40,80]}),lambda f,a,m,l:a['items'][0].update(duration_frames=17),lambda f,a,m,l:a['items'][0].update(offset_frames=True),lambda f,a,m,l:a['items'][0].update(offset_frames=11),lambda f,a,m,l:a['items'][0].update(color='red'),lambda f,a,m,l:a['items'][0].update(source_refs=[]),lambda f,a,m,l:a['items'][0].update(hide_at={'segment_id':'bad','offset_frames':0})]
  for mutate in mutations:
   f,a,m,l=teaching_fixture();mutate(f,a,m,l)
   with self.subTest(mutate=mutate),self.assertRaises(InputError):validate_teaching(f,a,m,l)
  for txt in ['x'*25,'x\ny','\\alpha','\x00','\U0010ffff']:
   f,a,m,l=teaching_fixture();a['items'][0].update(kind='label',geometry={'runs':[dict(text=txt,origin=[40,60],font_size_pt=12)]})
   with self.subTest(txt=txt),self.assertRaises(InputError):validate_teaching(f,a,m,l)
  f,a,m,l=teaching_fixture()
  with self.assertRaises(InputError):validate_teaching(None,a,m,l)
  a['items'].append(dict(a['items'][0],id='b',offset_frames=20))
  with self.assertRaises(InputError):validate_teaching(f,a,m,l)

class AnnotationGeometryTests(Sandbox):
 def test_arrow_ellipse_and_label_outlines(self):
  import solution_video.annotations as module
  self.assertTrue(hasattr(module,'compile_annotations'),'annotation geometry compiler missing')
  f,a,m,l=teaching_fixture();a['items'] += [dict(a['items'][0],id='circle',kind='ellipse',geometry={'bbox':[40,45,80,85]}),dict(a['items'][0],id='label',kind='label',geometry={'runs':[dict(text='v x',origin=[40,60],font_size_pt=12)]})]
  p=validate_teaching(f,a,m,l);c=module.compile_annotations(p,l,self.run/'geometry')
  self.assertIn('L',c['items'][0]['path']);self.assertIn('A',c['items'][1]['path'])
  self.assertEqual(c['items'][1]['start_point'],[60,45]);self.assertEqual(len(c['items'][2]['glyphs']),3)
  self.assertEqual(c['items'][2]['glyphs'][1]['svg_ids'],[]);self.assertEqual(len(c['font_sha256']),64)
  self.assertTrue(Path(c['svg']).is_file());self.assertNotIn('data-reveal',Path(c['svg']).read_text())

class AnnotationEarlyHideTests(Sandbox):
 def test_hide_before_completion_rejected_before_voice(self):
  f,a,m,l=teaching_fixture();a['items'][0]['hide_at']={'segment_id':'r','offset_frames':20}
  with self.assertRaisesRegex(InputError,'a'):validate_teaching(f,a,m,l)

class StandaloneAnnotationTests(Sandbox):
 def test_font_outline_compilation_does_not_depend_on_pdf_export_import(self):
  import subprocess
  code=f"""import sys,json
from pathlib import Path
sys.path[:0]=[{str(S/'scripts')!r},{str(S/'tests')!r}]
from test_annotations import teaching_fixture
from solution_video.annotations import validate_teaching,compile_annotations
f,a,m,l=teaching_fixture()
a['items'][0].update(kind='label',geometry={{'runs':[dict(text='v',origin=[40,60],font_size_pt=12)]}})
c=compile_annotations(validate_teaching(f,a,m,l),l,Path({str(self.run/'standalone')!r}))
print(json.dumps(c['items'][0]['body_height']))
"""
  result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True)
  self.assertGreater(json.loads(result.stdout.strip()),2)
