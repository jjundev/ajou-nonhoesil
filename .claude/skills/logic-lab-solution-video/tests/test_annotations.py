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

class AnnotationRegionPlacementTests(Sandbox):
 # 논회실 풀이는 조건 패널이 중앙 풀이 칸 왼쪽에 있어, 패널의 표·문장·회로도 확대·주석 대상이 된다.
 def region(self,bbox):
  f,a,m,l=teaching_fixture();f['regions'][0]['bbox']=bbox;a['items']=[]
  return validate_teaching(f,a,m,l)
 def test_region_beside_work_area_is_accepted(self):
  self.assertIsNotNone(validate_teaching,'teaching validation is missing')
  self.assertEqual(self.region([10,40,90,200])['regions'][0]['bbox'],[10,40,90,200])  # 아래 끝 200 > 풀이 칸 위 100 이지만 겹치지 않는다
 def test_region_overlapping_work_area_is_still_rejected(self):
  self.assertIsNotNone(validate_teaching,'teaching validation is missing')
  with self.assertRaisesRegex(InputError,'overlaps work_bbox'):self.region([80,40,150,200])
 def test_region_touching_work_area_edge_is_accepted(self):
  # work_bbox=[100,100,300,240]: 한 변만 닿는 것은 겹침이 아니다(overlaps 는 엄격 부등식).
  for b in ([10,40,100,200],[10,240,90,290],[300,10,390,290],[120,10,280,100]):
   with self.subTest(bbox=b):self.assertEqual(self.region(b)['regions'][0]['bbox'],b)
 def test_region_outside_page_is_still_rejected(self):
  for b in ([-1,40,90,200],[10,40,401,200],[10,40,90,301]):
   with self.subTest(bbox=b),self.assertRaisesRegex(InputError,'outside page'):self.region(b)

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

class AnnotationLeftPanelGeometryTests(Sandbox):
 def test_left_panel_annotations_compile_and_work_area_crossing_is_rejected(self):
  import solution_video.annotations as module
  f,a,m,l=teaching_fixture();f['regions'][0]['bbox']=[10,40,90,200]  # 풀이 칸 [100,100,300,240] 왼쪽
  base=a['items'][0]
  a['items']=[dict(base,id='arrow',geometry={'from':[30,60],'to':[30,150]}),dict(base,id='circle',kind='ellipse',geometry={'bbox':[20,160,80,190]}),
              dict(base,id='label',kind='label',geometry={'runs':[dict(text='Q',origin=[20,60],font_size_pt=10)]})]
  c=module.compile_annotations(validate_teaching(f,a,m,l),l,self.run/'left')
  for i in c['items']:self.assertLessEqual(i['bbox'][2],100,i['id'])  # 모두 풀이 칸 왼쪽에 머문다
  a['items']=[dict(base,id='cross',geometry={'from':[30,60],'to':[150,150]})]  # 끝이 풀이 칸 안으로 들어간다
  with self.assertRaisesRegex(InputError,'overlaps work_bbox'):validate_teaching(f,a,m,l)

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

class InkWidthTests(Sandbox):
 def test_stroke_width_contract(self):
  self.assertEqual(make_teaching_plan()['items'][0].get('stroke_width_px'),3)
  for width in [2,4,6,8,12,4.5]:
   f,a,m,l=teaching_fixture();a['items'][0]['stroke_width_px']=width
   self.assertEqual(validate_teaching(f,a,m,l)['items'][0]['stroke_width_px'],width)
  for width in [1.9,12.1,True,'6',float('nan'),float('inf')]:
   f,a,m,l=teaching_fixture();a['items'][0]['stroke_width_px']=width
   with self.subTest(width=width),self.assertRaises(InputError):validate_teaching(f,a,m,l)
 def test_label_rejects_stroke_width(self):
  f,a,m,l=teaching_fixture();a['items'][0].update(kind='label',stroke_width_px=6,geometry={'runs':[dict(text='v',origin=[40,60],font_size_pt=12)]})
  with self.assertRaises(InputError):validate_teaching(f,a,m,l)

class ChunkAnnotationTests(Sandbox):
 def fixture(self):
  f,a,m,l=teaching_fixture();m['caption_timing']='pcm-chunks-v1';m['segments'][1]['chunks']=[dict(id='c1'),dict(id='c2')];m['segments'][0]['chunks']=[dict(id='other')]
  a['items'][0].update(chunk_id='c1',offset_frames=0);return f,a,m,l
 def test_chunk_annotation_contract(self):
  f,a,m,l=self.fixture();a['items'].append(dict(a['items'][0],id='b',chunk_id='c2'))
  self.assertEqual([i['offset_frames'] for i in validate_teaching(f,a,m,l)['items']],[0,0])
  mutations=[lambda f,a,m,l:a['items'][0].update(chunk_id='missing'),lambda f,a,m,l:a['items'][0].update(chunk_id='other'),lambda f,a,m,l:m.pop('caption_timing'),lambda f,a,m,l:a['items'][0].update(offset_frames=-1),lambda f,a,m,l:a['items'][0].update(offset_frames=True),lambda f,a,m,l:a['items'].append(dict(a['items'][0],id='b',chunk_id='c1',offset_frames=25)),lambda f,a,m,l:a['items'].append({k:v for k,v in dict(a['items'][0],id='b',offset_frames=40).items() if k!='chunk_id'})]
  for mutate in mutations:
   f,a,m,l=self.fixture();mutate(f,a,m,l)
   with self.subTest(mutate=mutate),self.assertRaises(InputError):validate_teaching(f,a,m,l)
 def test_chunk_and_legacy_in_different_segments(self):
  # 섞임 금지는 같은 segment 안만이다. 다른 segment 의 legacy 항목은 예전 기본값(오프셋 12)을 그대로 받는다.
  f,a,m,l=self.fixture();m['segments'].insert(2,dict(id='r2',kind='reason',step_id='',text='reason two',chunks=[dict(id='k1')]))
  f['cues'].append(dict(segment_id='r2',target='circuit'))
  a['items'].append({k:v for k,v in dict(a['items'][0],id='b',segment_id='r2').items() if k not in ('chunk_id','offset_frames')})
  items=validate_teaching(f,a,m,l)['items']
  self.assertEqual([(i['id'],i.get('chunk_id'),i['offset_frames']) for i in items],[('a','c1',0),('b',None,12)])

class InkCompileTests(Sandbox):
 def test_compiled_stroke_and_color(self):
  from solution_video.annotations import compile_annotations
  import xml.etree.ElementTree as ET
  f,a,m,l=teaching_fixture();a['items'][0].update(stroke_width_px=6,color='#C45100')
  c=compile_annotations(validate_teaching(f,a,m,l),l,self.run/'ink')
  path=ET.parse(c['svg']).find('.//{http://www.w3.org/2000/svg}path')
  self.assertEqual(float(path.get('stroke-width')),6);self.assertEqual(path.get('stroke'),'#C45100')
  self.assertEqual(c['items'][0]['stroke_width_px'],6)

class LogicLabelGlyphTests(Sandbox):
 # 논리식 label 은 프라임(′)을 쓴다. MuPDF 가 공유 글리프를 다른 코드포인트로 내보내도 저작 글자를 남겨야 한다.
 def test_logic_label_keeps_authored_unicode(self):
  from solution_video.annotations import compile_annotations
  f,a,m,l=teaching_fixture();a['items'][0].update(kind='label',geometry={'runs':[dict(text='S1′S0′',origin=[40,60],font_size_pt=12)]})
  c=compile_annotations(validate_teaching(f,a,m,l),l,self.run/'logic-label')
  self.assertEqual([g['text'] for g in c['items'][0]['glyphs']],['S','1','′','S','0','′'])
  self.assertIn('data-text="′"',Path(c['svg']).read_text())
 def test_xor_symbol_rejected(self):
  # Pretendard 에 ⊕ 글리프가 없다. 조용히 빠지지 않고 막혀야 한다(XOR 은 글자로 쓴다).
  f,a,m,l=teaching_fixture();a['items'][0].update(kind='label',geometry={'runs':[dict(text='A⊕B',origin=[40,60],font_size_pt=12)]})
  with self.assertRaisesRegex(InputError,'unsupported font glyph'):validate_teaching(f,a,m,l)
