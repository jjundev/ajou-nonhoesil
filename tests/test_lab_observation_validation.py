from dataclasses import replace
from pathlib import Path
import pytest
from scripts.lab import validate, leds
from scripts.lab.spec_parser import parse_spec
from tests.test_lab_observation_parser import parsed, TEXT, FIX

@pytest.fixture
def pair(tmp_path):
    return parsed(tmp_path),parse_spec(FIX/'spec_observation_stepped.md')

def errors(pair):
    return [f.message for f in validate.check_netlist_circuits(*pair) if f.level=='error']

def test_observed_stage_with_procedure_has_no_truth_table_error(pair):
    assert errors(pair)==[]

def test_observed_stage_without_procedure_is_error(pair):
    pair[0].circuits[0].stages[0]['procedure']=None
    assert any('observed' in e for e in errors(pair))

def test_expression_stage_without_record_table_is_still_error(pair):
    s=pair[0].circuits[0].stages[0]; s.update(node='SERIAL DATA 보수',procedure=None)
    assert any('truth-table' in e for e in errors(pair))

@pytest.mark.parametrize('node',[
    {'name':'BIT1','kind':'observed','expr':None,'pin':'U2 pin 11'},
    {'name':'OTHER','kind':'observed','expr':None,'pin':'U2 pin 15'}])
def test_duplicate_point_name_or_pin_is_error_v3(pair,node):
    pair[0].circuits[0].nodes.append(node)
    assert any('중복' in e or '두 번' in e for e in errors(pair))

def test_walk_cannot_reference_procedure(pair):
    pair[0].circuits[0].stages[0].update(walk=True,walk_of=1)
    assert any('절차' in e and '걷기' in e for e in errors(pair))

def test_primary_node_requires_checkable_expectation(pair):
    for row in pair[0].circuits[0].procedures[0].steps: row.expected=['미정']
    assert any('확인 가능' in e for e in errors(pair))

def test_procedure_reference_cannot_cross_circuits(pair):
    pair[0].circuits[0].stages[0]['procedure']='V99'
    assert any('V99' in e for e in errors(pair))

def test_manual_source_page_out_of_range_is_error(pair):
    pair[0].circuits[0].procedures[0].source='manual:p9999'
    assert any('쪽 범위' in e for e in errors(pair))

def test_observed_pin_resolves_led_feed(pair):
    c=pair[0].circuits[0]; c.stages[0]['todo']='U2 pin 15→LED Q 급전'
    assert leds.feeds_by_stage(c)==[{'Q':'BIT1'}]

def test_scenario_inputs_are_checked_against_stage_sidecar(pair):
    fs=validate.check_io_locations(*pair)
    assert fs and all(f.level=='warn' for f in fs)
    assert any('SERIAL_DATA' in f.message for f in fs)

def test_probe_observation_does_not_require_led(pair):
    assert not errors(pair)

def test_walk_contract_is_not_relaxed(pair):
    s=pair[0].circuits[0].stages[0]
    s.update(walk=True,walk_of=2,procedure=None,walk_addresses=[])
    assert any('주소쌍' in e for e in errors(pair))

def test_unused_procedure_warns(pair):
    c=pair[0].circuits[0]
    c.procedures.append(replace(c.procedures[0],id='V2'))
    assert any(f.level=='warn' and 'V2' in f.message for f in validate.check_netlist_circuits(*pair))

def test_corrupt_source_pdf_is_warning_and_does_not_abort(pair,tmp_path):
    broken=tmp_path/'broken.pdf'; broken.write_bytes(b'%PDF-1.7\ntruncated')
    pair[1].source_manual=str(broken)
    findings=validate.check_netlist_circuits(*pair)
    assert any(f.level=='warn' and '쪽 범위' in f.message for f in findings)
    assert not [f for f in findings if f.level=='error']

@pytest.mark.parametrize('expr',['SERIAL_DATA +','(SERIAL_DATA'])
def test_expression_syntax_checked_without_truth_table(pair,expr):
    pair[0].circuits[0].nodes[0]['expr']=expr
    assert any('식' in message for message in errors(pair))
