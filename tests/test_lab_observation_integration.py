from pathlib import Path
import hashlib
import re
import pytest
from scripts.lab import render, validate, observations
from scripts.lab.spec_parser import parse_spec
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.record import derive_record, write_record, RecordExistsError
from tests.test_lab_observation_parser import FIX

TEMPLATE=Path('.claude/skills/prep-lab-checklist/template.html').read_text()

def load(case):
    n=parse_netlist(FIX/f'netlist_observation_{case}_v3.md')
    s=parse_spec(FIX/f'spec_observation_{case}.md')
    return n,s

def test_jk_hold_toggle_sequence_end_to_end():
    n,s=load('jk')
    assert [f for f in validate.check_netlist_circuits(n,s) if f.level=='error']==[]
    h=render.render_checklist(s,n,TEMPLATE)
    assert all(x in h for x in ['CLR 초기화','유지 하강','반전 하강','Qbar (U1 pin 14): 반전'])
    assert 'class="check"' not in h

def test_six_bit_sequence_preserves_serial_timeline():
    n,s=load('sixbit'); c=n.circuits[0]
    assert [f for f in validate.check_netlist_circuits(n,s) if f.level=='error']==[]
    t=observations.stage_observations(c,s,c.stages[0],[f'BIT{i}' for i in range(1,7)])
    assert [''.join(t.rows[i].expected) for i in (0,4,7)]==['000000','100000','010000']
    h=render.render_checklist(s,n,TEMPLATE)
    orders=re.findall(r'data-observation-order="(\d+)"',h)
    assert orders==list(map(str,range(1,9)))*2
    assert '다음 데이터 설정' in h and 'BIT6 (U4 pin 11): 0' in h

def test_scenario_does_not_change_derived_record():
    n,s=load('sixbit'); before=derive_record(s)
    render.render_checklist(s,n,TEMPLATE)
    for c in n.circuits: c.procedures=[]; c.nodes=[]; c.stages=[]
    render.render_checklist(s,n,TEMPLATE)
    assert derive_record(s)==before
    assert '| 1' in before

def test_filled_record_is_not_overwritten(tmp_path):
    _,s=load('sixbit'); blank=derive_record(s)
    filled=blank.replace('filled_by: ~','filled_by: hand')+'\n실측 메모: 초기화 확인\n'
    p=tmp_path/'기록.md'; p.write_text(filled)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(RecordExistsError): write_record(p,blank)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
