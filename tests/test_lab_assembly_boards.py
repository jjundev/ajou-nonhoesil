from types import SimpleNamespace
from functools import partial
import pytest
from tests.test_breadboard_boards import _load,FIXTURE
from tests.test_lab_assembly_parser import parsed
from scripts.lab import assembly

def test_insert_preparation_before_parent_and_propagate_snapshot(tmp_path):
 e=_load(); seen=[]
 def build(path,template=None,stage=None,baseline=None,*,n):
  seen.append((n,baseline,stage))
  b=e.BreadboardRenderer(template,baseline=baseline,board='v1'); b.enable_steps()
  if n>=1: b.connect_jacks()
  if n>=2: b.bridge_rails(b.cols['left']['gnd'],b.cols['left']['mid_gnd'],40,kind='gnd')
  b.export(path); return b
 board=SimpleNamespace(BOARD='v1',BOARDS=[('one.png',partial(build,n=3),1),('walk.png',partial(build,n=3),None),('two.png',partial(build,n=3),2)],FINALS=[('final.png',partial(build,n=3))],ASSEMBLY_BOARDS={'one.png':[('a.png',partial(build,n=1)),('b.png',partial(build,n=2))]})
 assert [(x[0],x[2],x[3]) for x in e.iter_procedure_boards(board)]==[('a.png',None,True),('b.png',None,True),('one.png',1,False),('walk.png',None,False),('two.png',2,False)]
 assert list(e.build_all(board,tmp_path))==['a.png','b.png','one.png','walk.png','two.png','final.png']
 assert seen[0][1] is None and seen[1][1]['wires'] and seen[2][1]['wires']
 assert seen[-1][1] is None

def test_empty_registry_preserves_existing_chain():
 e=_load(); b=e.load_board_file(FIXTURE)
 assert list(e.iter_procedure_boards(b))==[(name,fn,stage,False) for name,fn,stage in b.BOARDS]

@pytest.mark.parametrize('registry',[
 {'missing.png':[('a.png',None)]},{'walk.png':[('a.png',None)]},
 {'one.png':[('a.png',None),('a.png',None)]},{'one.png':[('two.png',None)]},
])
def test_registry_rejects_orphan_walk_and_duplicate_names(registry):
 e=_load(); b=SimpleNamespace(BOARDS=[('one.png',None,1),('walk.png',None,None),('two.png',None,2)],FINALS=[],ASSEMBLY_BOARDS=registry)
 with pytest.raises(ValueError): list(e.iter_procedure_boards(b))

def test_registry_authored_order_must_match(tmp_path):
 n=parsed(tmp_path); entries=[(f'prep{i}.png',None) for i in range(1,7)]
 assert assembly.check_registry(n,{'stage.png':entries})==[]
 assert assembly.check_registry(n,{'stage.png':entries[::-1]})
 assert assembly.check_registry(n,{'walk.png':entries})

@pytest.mark.parametrize('mode',['signal','removal'])
def test_preparation_rejects_removal_and_new_signal(tmp_path,mode):
 e=_load()
 def build(path,template=None,baseline=None):
  b=e.BreadboardRenderer(template,baseline=baseline,board='v1'); b.enable_steps()
  if mode=='signal':
   c=b.cols['left']; b.step_wire([(c['b'],b.r_y(7)),(c['b'],b.r_y(9))],'sig','signal')
  elif baseline is None: b.connect_jacks()
  return b
 b=SimpleNamespace(BOARD='v1',BOARDS=[('one.png',None,1)],FINALS=[],ASSEMBLY_BOARDS={'one.png':[('a.png',build),('b.png',build)]})
 with pytest.raises(ValueError): e.build_all(b,tmp_path)
