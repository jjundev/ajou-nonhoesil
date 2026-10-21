import json,re
from pathlib import Path
import pytest
from PIL import Image
from scripts.lab import render
from scripts.lab.fit_pages import tag
from scripts.lab.spec_parser import parse_spec
from tests.test_lab_assembly_parser import parsed

@pytest.fixture
def data(tmp_path):
 n=parsed(tmp_path); s=parse_spec('tests/fixtures/spec_observation_stepped.md')
 for step in n.circuits[0].assembly_steps:
  p=tmp_path/step.diagram; Image.new('RGB',(2,2)).save(p)
  p.with_suffix('.json').write_text(json.dumps({'schema':'breadboard-sidecar/v1','board':'v2','removals':[],'steps':[],'probes':[],'kept':0}))
 return n,s

def test_six_preparation_blocks_before_stage_one(data):
 n,s=data; h=render.circuit_pages(s,n)
 assert h.count('class="stage"')==7
 assert [h.index('준비 '+ch) for ch in '①②③④⑤⑥']==sorted(h.index('준비 '+ch) for ch in '①②③④⑤⑥')
 assert h.index('준비 ⑥')<h.index('<h3>단계 1</h3>')
 assert '조립 순서' not in h

def test_preparation_off_and_no_observation(data):
 n,s=data; h=render._assembly_html(n.circuits[0].assembly_steps[0],n)
 assert '전원과 신호발생기 출력을 꺼요.' in h and '완료 확인' in h
 assert not any(x in h for x in ['observation-procedure','td.check','확인 노드:'])
 assert tag(h).startswith('<div class="stage" data-fit="0">')
 assert 'prep1.png' in h and '레일 연결' in h and '극성 대조' in h

@pytest.mark.parametrize('file',['prep1.png','prep1.json'])
def test_missing_or_unreadable_assets_prevents_render(data,file):
 n,s=data; (n.path.parent/file).write_text('broken')
 with pytest.raises(ValueError): render.render_checklist(s,n,'{{CIRCUITS}}')

def test_no_assembly_preserves_stage_output(data):
 n,s=data; n.circuits[0].assembly_steps=[]
 h=render.render_checklist(s,n,'{{CIRCUITS}}')
 assert h.count('class="stage"')==1 and '완료 확인' not in h

def test_documented_publication_gate_allows_legacy_without_board(data):
 # Run the actual documented pre-render gate with a legacy, unrendered netlist.
 import textwrap
 n,s=data; n.circuits[0].assembly_steps=[]
 skill=Path('.claude/skills/prep-lab-checklist/SKILL.md').read_text()
 code=skill[skill.index('   from scripts.lab.assembly import'):skill.index('   tmpl = Path(')]
 exec(textwrap.dedent(code),{'netlist':n})

def test_legacy_validation_does_not_require_pillow():
 import subprocess,sys
 p=subprocess.run([sys.executable,'-c',"import sys;sys.modules['PIL']=None;from scripts.lab.assembly import check_assets;from types import SimpleNamespace;assert check_assets(SimpleNamespace(circuits=[]))==[]"],capture_output=True,text=True)
 assert p.returncode==0,p.stderr
