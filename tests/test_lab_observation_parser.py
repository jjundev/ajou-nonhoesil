"""Reject losing authored timeline/type/version boundaries at the parse boundary."""
from pathlib import Path
import pytest
from scripts.lab.netlist_parser import parse_netlist, NetlistError

FIX = Path(__file__).parent / 'fixtures'
TEXT = (FIX / 'netlist_observation_v3.md').read_text()

def parsed(tmp_path, text=TEXT):
    p = tmp_path / 'netlist.md'
    p.write_text(text)
    return parse_netlist(p)

def test_v3_parses_observed_and_expression_nodes(tmp_path):
    n = parsed(tmp_path)
    assert n.schema == 'lab-netlist/v3'
    expression, observed = n.circuits[0].nodes
    assert observed['expr'] is None
    assert observed['kind'] == 'observed'
    assert expression['expr'] == "SERIAL_DATA'"

def test_procedure_keeps_duplicate_input_rows_in_order(tmp_path):
    text = TEXT.replace('| 2 | CLR 해제 | 0 | 0 | 1 | 1 | 0 |',
                        '| 2 | 다른 상태 | 0 | 0 | 0 | 1 | 1 |')
    a, b, *_ = parsed(tmp_path, text).circuits[0].procedures[0].steps
    assert a.inputs == b.inputs
    assert (a.expected, b.expected) == (['0'], ['1'])
    assert (a.order, b.order) == (1, 2)

def test_v3_stage_resolves_procedure_syntax(tmp_path):
    stage = parsed(tmp_path).circuits[0].stages[0]
    assert stage.get('node') == 'BIT1'
    assert stage['procedure'] == 'V1'

def test_v2_parse_shape_is_unchanged(tmp_path):
    text = TEXT[:TEXT.index('## 확인 절차')].replace('lab-netlist/v3','lab-netlist/v2')
    text = text.replace('| 노드 | 유형 | 식 | 핀 |','| 노드 | 식 | 핀 |').replace('|---|---|---|---|\n| SERIAL','|---|---|---|\n| SERIAL')
    text = text.replace('| expression | ', '| ').replace('| observed | - |','| 0 |')
    text = text.replace(' · 절차 `V1`','')
    n = parsed(tmp_path, text)
    assert n.schema == 'lab-netlist/v2'
    assert n.circuits[0].nodes[0] == {'name':'SERIAL DATA 보수','expr':"SERIAL_DATA'",'pin':'U1 pin 11'}
    assert 'procedure' not in n.circuits[0].stages[0]

@pytest.mark.parametrize('old,new', [
    ('lab-netlist/v3','lab-netlist/v2'),
    ('| 노드 | 유형 | 식 | 핀 |','| 노드 | 식 | 유형 | 핀 |'),
    ('| 순서 | 조작 | SERIAL_DATA','| 번호 | 조작 | SERIAL_DATA'),
    ('| 1 | 초기화 | 0 | 0 | 0 | 1 | 0 |','| 1 | 초기화 | 0 |'),
    ('절차 `V1`','절차 `V0`'),
    ('절차 `V1`','절차 V1'),
    ('| observed | - |','| observed | Q |'),
    ('| expression |', '| random |'),
])
def test_rejects_bad_version_headers_rows_and_reference(tmp_path, old, new):
    with pytest.raises(NetlistError):
        parsed(tmp_path, TEXT.replace(old,new))

def test_rejects_duplicate_procedure_ids(tmp_path):
    with pytest.raises(NetlistError):
        parsed(tmp_path, TEXT + '\n' + TEXT[TEXT.index('## 확인 절차'):])

def test_procedure_is_removed_from_circuit_body(tmp_path):
    body = parsed(tmp_path).circuits[0].body
    assert '확인 절차' not in body
    assert '클럭 하강' not in body

def test_procedure_reference_without_description_preserves_closing_backtick(tmp_path):
    n=parsed(tmp_path,TEXT.replace(' · 절차 `V1` — 프로브 확인',' · 절차 `V1`'))
    assert n.circuits[0].stages[0]['procedure']=='V1'

def test_procedure_reference_without_closing_backtick_is_rejected(tmp_path):
    with pytest.raises(NetlistError):
        parsed(tmp_path,TEXT.replace(' · 절차 `V1` — 프로브 확인',' · 절차 `V1'))
