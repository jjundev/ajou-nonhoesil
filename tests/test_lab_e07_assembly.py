import hashlib,json
from pathlib import Path
import pytest
from scripts.lab.place_search import load
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab import assembly
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'보고서/실험07/결선도'
TITLES=['보드·U1 전원 준비','U2 입력 고정','U3 입력 고정','U4 입력 고정','위쪽 LED 준비','아래쪽 LED 준비']
def norm(x):
 if isinstance(x,dict): return {repr(k):norm(v) for k,v in x.items()}
 if isinstance(x,(set,frozenset)):return sorted([norm(v) for v in x],key=repr)
 if isinstance(x,(tuple,list)):return [norm(v) for v in x]
 return x

def test_e07_exactly_six_preparations():
 e,w=load(FOLDER/'배치.py');n=parse_netlist(FOLDER/'netlist.md');c=n.circuits[0]
 assert [s.title for s in c.assembly_steps]==TITLES
 assert len(w.ASSEMBLY_BOARDS[c.stages[0]['diagram']])==6
 assert assembly.check_registry(n,w.ASSEMBLY_BOARDS)==[]
 assert len(c.stages)==23 and len(c.procedures)==12
 assert [s['procedure'] for s in c.stages if not s['walk']]==[f'V{i}' for i in range(1,13)]

def test_preparations_add_only_foundation_and_keep_paths(tmp_path):
 e,w=load(FOLDER/'배치.py');base=None;old_paths=set();counts=[]
 for name,fn,stage,prep in e.iter_procedure_boards(w):
  if not prep: break
  b=fn(str(tmp_path/name),baseline=base)
  assert not b.removed() and not b.new_signal
  paths={(k,tuple(pts)) for k,pts,_ in b._segments}
  assert old_paths<=paths
  old_paths=paths;base=b.snapshot();counts.append(len(b.led_chains))
 assert counts==[0,0,0,0,3,6]
 assert len(base['chips'])==4
 assert len(base['wires'])==48  # old foundation 49 wires minus D input


def test_absolute_boards_match_preimplementation_reference(tmp_path):
 ref=Path('/tmp/e07-assembly-baseline/states.json')
 if not ref.exists(): pytest.skip('execution-local preimplementation reference unavailable')
 expected=json.loads(ref.read_text());e,w=load(FOLDER/'배치.py');base=None
 for name,fn,stage,prep in e.iter_procedure_boards(w):
  b=fn(str(tmp_path/name),baseline=base,**({} if prep else {'stage':stage}));base=b.snapshot()
  if prep: continue
  assert norm(base)==expected[repr(name)][repr('snapshot')]
  assert norm(b._segments)==expected[repr(name)][repr('paths')]
  assert norm(b.nets())==expected[repr(name)][repr('nets')]
  # Only stage-one numbering/highlighting changes.
  if stage!=1:
   assert b.stamp()==expected[repr(name)][repr('stamp')]
 for name,fn in w.FINALS:
  b=fn(str(tmp_path/name));assert b.stamp()==expected[repr(name)][repr('stamp')]
