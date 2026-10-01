import json
from pathlib import Path
import pytest
from scripts.lab.review_pack.manifest import validate_manifest

def fixture():
    return json.loads(Path('tests/fixtures/review_pack/manifest.json').read_text(encoding='utf-8'))

def test_valid():
    assert validate_manifest(fixture()) == []

def test_past_needs_source():
    m=fixture(); m['problems'][0]['kind']='past'
    assert validate_manifest(m)

def test_answer_conflict_preserved():
    m=fixture(); m['problems'][0].update(given_answer='I1',answer_status='disputed')
    assert validate_manifest(m) == []
    assert m['problems'][0]['given_answer']=='I1'

@pytest.mark.parametrize('change',[
    lambda m:m['topics'][0].update(requires=['t-mux']),
    lambda m:m['problems'][0].update(topics=['missing']),
    lambda m:m['problems'][0].update(id='t-mux'),
    lambda m:m['problems'][0].update(status='held',reason=''),
    lambda m:m['problems'][0].update(status='duplicate',duplicate_of='q-mux-001'),
    lambda m:m['topics'][0].update(fragment='../outside.html'),
    lambda m:m['topics'][0]['sources'][0].update(pdf_page=0),
    lambda m:m.update(experiment=True),
])
def test_invalid_contract(change):
    m=fixture();change(m)
    assert validate_manifest(m)

def test_distinct_conditions_remain_distinct():
    m=fixture()
    m['problems'].append(dict(m['problems'][0],id='q-mux-002',derived_answer='I1'))
    assert validate_manifest(m)==[]
