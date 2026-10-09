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
