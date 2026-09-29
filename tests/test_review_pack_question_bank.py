import copy
import json
from pathlib import Path
import pytest
from scripts.lab.review_pack.question_bank import validate_question_bank, load_question_bank

def bank():
    return json.loads(Path('tests/fixtures/review_pack/question_bank/minimal.json').read_text(encoding='utf-8'))

def test_minimal_draft_is_valid_and_unchanged():
    data = bank(); before = copy.deepcopy(data)
    assert validate_question_bank(data) == []
    assert data == before

@pytest.mark.parametrize('key,value', [('schema_version', 2), ('schema_version', True), ('experiment', True), ('experiment', 11), ('questions', {}), ('schema', 'learning-pack')])
def test_wrong_shape(key, value):
    data = bank(); data[key] = value
    assert validate_question_bank(data)

def test_unknown_authoring_field_rejected():
    data = bank(); data['derived_answer'] = '1'
    assert any('derived_answer' in e for e in validate_question_bank(data))

def test_loader_reports_invalid_json(tmp_path):
    path = tmp_path / 'bank.json'; path.write_text('{', encoding='utf-8')
    with pytest.raises(ValueError): load_question_bank(path)
