"""Authored rows are data; validation must not invent a state transition."""
from dataclasses import replace
from pathlib import Path
import pytest
from scripts.lab.netlist_parser import parse_netlist
from scripts.lab.spec_parser import parse_spec
from scripts.lab import observations as obs, nodes
from tests.test_lab_observation_parser import parsed, TEXT, FIX
from tests.test_lab_nodes import _circuit, _spec
from scripts.lab.spec_parser import SpecTable

@pytest.fixture
def circuit(tmp_path):
    return parsed(tmp_path).circuits[0]

@pytest.fixture
def spec():
    return parse_spec(FIX / 'spec_observation_stepped.md')

def test_authored_procedure_does_not_require_truth_table(circuit, spec):
    t = obs.stage_observations(circuit,spec,circuit.stages[0],['BIT1'])
    assert t.points == [('BIT1','U2 pin 15')]
    assert len(t.rows) == 5
    assert t.rows[-1].expected == ['1']
    assert t.provenance == 'derived'
    assert obs.procedure_issues(circuit,circuit.procedures[0]) == []

def test_same_inputs_can_have_different_authored_states(circuit,spec):
    p = circuit.procedures[0]
    p.steps = [replace(p.steps[0],expected=['0']),replace(p.steps[0],order=2,expected=['1'])]
    t=obs.stage_observations(circuit,spec,circuit.stages[0],['BIT1'])
    assert len(t.rows)==2
    assert t.rows[0].inputs == t.rows[1].inputs
    assert [r.expected for r in t.rows] == [['0'],['1']]

def test_computed_adapter_matches_existing_nodes():
    table=SpecTable(id='T1',title='x',kind='truth-table',encoding='0/1',source='manual:p1',expected=None,role='record',header=['A','Y'],rows=[['0','1'],['1','0']],line=1)
    c=_circuit(['T1'], [('Y',"A'",'U1 pin 3')]); s=_spec(table)
    old=nodes.stage_nodes_table(c,s,['Y'])
    new=obs.stage_observations(c,s,{},['Y'])
    assert new.inputs == old.inputs == ['A']
    assert [(r.inputs,r.expected) for r in new.rows] == [(['0'],['1']),(['1'],['0'])]
    assert new.provenance == 'computed'

def test_empty_unknown_and_unobserved_are_distinct(circuit,spec):
    p=circuit.procedures[0]
    for token,valid in [('',False),('미정',True),('관측 안 함',True)]:
        p.steps[0].expected=[token]
        assert (not obs.procedure_issues(circuit,p)) == valid
    t=obs.stage_observations(circuit,spec,circuit.stages[0],['BIT1','SERIAL DATA 보수'])
    assert t.rows[0].expected == ['관측 안 함','관측 안 함']

@pytest.mark.parametrize('change',[
    {'inputs':['CLK','CLK']}, {'observe':['MISSING']}, {'observe':['CLK']},
    {'provenance':'guessed'}, {'rationale':''}, {'setup':''},
    {'encoding':'binary'}, {'clocks':['MISSING']}, {'source':'manual:p0'}
])
def test_rejects_missing_duplicate_columns_nodes_and_bad_provenance(circuit,change):
    assert obs.procedure_issues(circuit,replace(circuit.procedures[0],**change))

@pytest.mark.parametrize('row,col,value',[(0,1,'0->1'),(1,1,'1->0'),(1,1,'1'),(1,0,'0->1'),(0,0,''),(0,0,'X')])
def test_clock_trace_rejects_mismatched_edge_and_hidden_transition(circuit,row,col,value):
    p=circuit.procedures[0]; p.steps[row].inputs[col]=value
    assert obs.procedure_issues(circuit,p)

def test_running_clock_allows_input_changes_and_explicit_stop(circuit):
    p = circuit.procedures[0]
    base = p.steps[0]
    p.steps = [replace(base, order=i, inputs=[data, clk, '1', '1'], expected=['0'])
               for i, (data, clk) in enumerate([('0','0'), ('1','RUN'), ('0','RUN'), ('0','1'), ('0','1->0')], 1)]
    assert obs.procedure_issues(circuit, p) == []

@pytest.mark.parametrize('values', [ [('0','RUN')], [('RUN','0')], [('0','0'),('0','RUN'),('0','1->0')] ])
def test_running_clock_rejects_ambiguous_transitions(circuit, values):
    p = circuit.procedures[0]
    base = p.steps[0]
    p.steps = [replace(base, order=i, inputs=[*pair, '1', '1'], expected=['0']) for i, pair in enumerate(values, 1)]
    assert obs.procedure_issues(circuit, p)

def test_rejects_bad_order_and_empty_action(circuit):
    p=circuit.procedures[0]
    p.steps[1].order=7; p.steps[0].action=''
    issues=obs.procedure_issues(circuit,p)
    assert len(issues)>=2

def test_relative_expectation_requires_prior_observation(circuit):
    p=circuit.procedures[0]
    p.steps[0].expected=['유지']
    assert obs.procedure_issues(circuit,p)
    p.steps[0].expected=['관측 안 함']; p.steps[1].expected=['반전']
    assert obs.procedure_issues(circuit,p)
    p.steps[0].expected=['미정']
    assert not obs.procedure_issues(circuit,p)

def test_observed_points_are_not_boolean_expressions(circuit,spec):
    with pytest.raises(ValueError,match='observed'):
        obs.stage_observations(circuit,spec,{},['BIT1'])
    with pytest.raises(ValueError,match='observed'):
        nodes.stage_nodes_table(circuit,spec,['BIT1'])

def test_duplicate_points_and_missing_reference(circuit):
    circuit.nodes.append(dict(circuit.nodes[-1]))
    with pytest.raises(obs.ObservationError): obs.points(circuit)
    with pytest.raises(obs.ObservationError): obs.procedure_for_stage(circuit,{'procedure':'V99'})
