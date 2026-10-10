from fixtures import *
import test_composition
from solution_video.util import read,write
from solution_video.pdf_pages import browser
from solution_video.lesson import lesson_expectations
from solution_video.annotations import load_teaching

class LessonRuntimeTests(Sandbox):
 pencil_fixture=test_composition.CompositionTests.pencil_fixture
 teaching_fixture=test_composition.CompositionTests.teaching_fixture
 def test_lesson_focus_mutant(self):
  self.teaching_fixture('typing');m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json');t=read(self.run/'source/timeline.json');p=load_teaching(self.run,m,l)
  row=dict(step_id='solution',mode='circuit',reason_segment_ids=['r'],check_segment_ids=[],region_ids=['circuit'],annotation_ids=['arrow'])
  from solution_video.focus import compile_focus_keys
  from solution_video.composition import camera_keys
  t['cameras']=compile_focus_keys(m,l,t,p,read(self.run/'composition/annotations/compiled.json'),camera_keys(m,l,t))
  expected=dict(timeline=t,compiled=read(self.run/'composition/annotations/compiled.json'),lesson=lesson_expectations(dict(steps=[row]),m,t,p))
  write(self.run/'expect.json',expected);entry=self.run/'composition/index.html';base=entry.read_text()
  args=['--mode','teaching','--entry',str(entry),'--layers',str(self.run/'layers/layers.json'),'--timeline',str(self.run/'expect.json')]
  self.assertTrue(browser(args)['lesson_flow'])
  for change in ["document.querySelector('#answer-page>svg').setAttribute('viewBox','200 100 200 100');","document.getElementById('teaching-annotations').style.display='none';"]:
   entry.write_text(base.replace('</body>',"<script>const old=window.renderSolutionFrame;window.renderSolutionFrame=f=>{old(f);"+change+"};</script></body>"))
   with self.subTest(change=change):self.assertFalse(browser(args)['lesson_flow'])
  entry.write_text(base)

 def test_horizontal_underline_counts_as_painted_lesson_evidence(self):
  # 수평 밑줄은 기하 높이가 0 이지만 칠해진 선은 유효한 근거다.
  self.teaching_fixture('typing');m=read(self.run/'source/manifest.json');l=read(self.run/'layers/layers.json');a=read(self.run/'source/annotations.json')
  a['items'][0].update(kind='underline',stroke_width_px=8,geometry={'from':[60,40],'to':[80,40]});write(self.run/'source/annotations.json',a)
  p=load_teaching(self.run,m,l)
  from solution_video.teaching import build_teaching_timeline
  from solution_video.review_adapter import default_config
  from solution_video.composition import assemble,camera_keys
  from solution_video.focus import compile_focus_keys
  t=build_teaching_timeline(m,l,read(self.run/'source/audio.json')['voices'],default_config(),read(self.run/'source/writing.json'),p);write(self.run/'source/timeline.json',t)
  assemble({'problem':{'snapshot':'pencil.pdf','page_index':0}},l,m,t,self.run,S/'assets/runtime/gsap.min.js')
  row=dict(step_id='solution',mode='circuit',reason_segment_ids=['r'],check_segment_ids=[],region_ids=['circuit'],annotation_ids=['arrow'])
  compiled=read(self.run/'composition/annotations/compiled.json');t['cameras']=compile_focus_keys(m,l,t,p,compiled,camera_keys(m,l,t))
  expected=dict(timeline=t,compiled=compiled,lesson=lesson_expectations(dict(steps=[row]),m,t,p));write(self.run/'expect.json',expected)
  args=['--mode','teaching','--entry',str(self.run/'composition/index.html'),'--layers',str(self.run/'layers/layers.json'),'--timeline',str(self.run/'expect.json')]
  self.assertTrue(browser(args)['lesson_flow'])
