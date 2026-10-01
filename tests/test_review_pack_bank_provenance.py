import copy,json
import pytest
from scripts.lab.review_pack.bank_import import import_bank
from scripts.lab.review_pack.bank_provenance import check_bank_import
from tests._bank_import_fixture import create_bank,add_answer,add_asset,save_bank,mark_partial

def imported(tmp_path):
    path,bank=create_bank(tmp_path);run=tmp_path/'run';import_bank(tmp_path,path,run)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    return path,run,m

def test_origin_change_is_not_local_failure(tmp_path):
    path,run,m=imported(tmp_path);path.write_bytes(path.read_bytes()+b'\n')
    assert check_bank_import(run,m)==[]
    assert check_bank_import(run,m,root=tmp_path)

def test_fixed_index_cannot_change(tmp_path):
    _,run,m=imported(tmp_path);p=run/'authoring-index.json'
    data=json.loads(p.read_text(encoding='utf-8'));data['questions'][0]['kind']='past'
    p.write_text(json.dumps(data),encoding='utf-8')
    assert check_bank_import(run,m)

def test_questions_cannot_disappear(tmp_path):
    _,run,m=imported(tmp_path);m['problems']=[]
    assert check_bank_import(run,m)

def test_partial_cannot_be_included(tmp_path):
    path,bank=create_bank(tmp_path);mark_partial(bank);save_bank(path,bank)
    run=tmp_path/'run';import_bank(tmp_path,path,run)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'));m['problems'][0]['status']='included'
    assert any('q1' in e for e in check_bank_import(run,m))

def test_selection_reason_editable(tmp_path):
    _,run,m=imported(tmp_path);p=run/'authoring-index.json'
    data=json.loads(p.read_text(encoding='utf-8'))
    data['questions'][0].update(authoring_status='not_selected',selection_reason='concept covered')
    p.write_text(json.dumps(data),encoding='utf-8')
    assert check_bank_import(run,m)==[]

@pytest.mark.parametrize('change',[
    lambda m:m['problems'][0].update(kind='past'),
    lambda m:m['problems'][0].update(bank_question_id='other'),
    lambda m:m['problems'][0].pop('bank_question_id'),
    lambda m:m['problems'][0]['sources'][0].update(locator='changed location'),
    lambda m:m['sources'][0].update(sha256='1'*64),
    lambda m:m['bank_import'].update(schema_version=[]),
    lambda m:m['bank_import'].update(extra=True),
    lambda m:m.update(experiment=3),
])
def test_changed_binding(tmp_path,change):
    _,run,m=imported(tmp_path);change(m)
    assert check_bank_import(run,m)

def test_new_practice_allowed(tmp_path):
    _,run,m=imported(tmp_path)
    m['problems'].append(dict(id='new-practice',kind='practice',status='held',reason='not authored',
        topics=[],sources=[],duplicate_of=None,scope='unknown',given_answer=None,
        derived_answer=None,answer_status='unresolved'))
    assert check_bank_import(run,m)==[]

def test_snapshot_changed(tmp_path):
    _,run,m=imported(tmp_path);p=run/'evidence/question-bank.json';p.write_bytes(p.read_bytes()+b'\n')
    assert check_bank_import(run,m)

@pytest.mark.parametrize('where',['original','snapshot','missing'])
def test_asset_change(tmp_path,where):
    path,bank=create_bank(tmp_path);a=add_asset(path,bank,'asset','mixed','unknown',b'image');save_bank(path,bank)
    run=tmp_path/'run';import_bank(tmp_path,path,run)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    p=path.parent/a['path'] if where=='original' else run/'evidence'/a['path']
    if where=='missing':p.unlink()
    else:p.write_bytes(b'changed')
    assert check_bank_import(run,m,root=tmp_path)
    if where=='original':assert check_bank_import(run,m)==[]

def test_source_change(tmp_path):
    _,run,m=imported(tmp_path);(tmp_path/'quiz.txt').write_bytes(b'changed')
    assert check_bank_import(run,m,root=tmp_path)
    assert check_bank_import(run,m)==[]

def test_candidate_answers_not_removable(tmp_path):
    path,bank=create_bank(tmp_path);add_answer(bank,'answer','value','candidate');save_bank(path,bank)
    run=tmp_path/'run';import_bank(tmp_path,path,run)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    p=run/'authoring-index.json';index=json.loads(p.read_text(encoding='utf-8'))
    index['questions'][0]['provided_answers']=[]
    p.write_text(json.dumps(index),encoding='utf-8')
    assert check_bank_import(run,m)

def test_duplicate_json_key_rejected(tmp_path):
    _,run,m=imported(tmp_path);p=run/'authoring-index.json';raw=p.read_text(encoding='utf-8')
    p.write_text(raw.replace('"kind":', '"kind": "past", "kind":',1),encoding='utf-8')
    assert check_bank_import(run,m)

def test_legacy_noop():
    assert check_bank_import(__import__('pathlib').Path('missing'),dict(problems=[]))==[]
