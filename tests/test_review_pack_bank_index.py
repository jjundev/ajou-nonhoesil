import copy
import pytest
from scripts.lab.review_pack.bank_index import build_authoring_index,initial_manifest,validate_bank_import_fields
from scripts.lab.review_pack.manifest import validate_manifest
from tests._bank_import_fixture import create_bank,add_answer,mark_partial,add_variant,add_asset

def test_answers_not_promoted(tmp_path):
    path,bank=create_bank(tmp_path);before=copy.deepcopy(bank)
    add_answer(bank,'a-confirmed','0','confirmed');add_answer(bank,'a-candidate','1','candidate')
    before=copy.deepcopy(bank)
    index=build_authoring_index(bank,'0'*64)
    assert index['questions'][0]['provided_answers']==bank['questions'][0]['answers']
    m=initial_manifest(bank,path.relative_to(tmp_path).as_posix(),'0'*64)
    assert validate_manifest(m)==[]
    assert set(m['checks'].values())=={'not_run'}
    assert m['problems'][0]['status']=='held'
    assert m['problems'][0]['derived_answer'] is None and m['problems'][0]['given_answer'] is None
    assert bank==before

def test_partial_reading_hold(tmp_path):
    _,bank=create_bank(tmp_path);mark_partial(bank)
    row=build_authoring_index(bank,'0'*64)['questions'][0]
    assert row['authoring_status']=='reading_hold'
    assert row['unresolved']==[dict(target_id='o1',reason='blurred')]

def test_subpart_candidate_source_hold(tmp_path):
    _,bank=create_bank(tmp_path)
    q=bank['questions'][0];q['subparts']=[dict(id='part1',label='가',occurrence_id='o1',block_ids=['b1'])]
    answer=add_answer(bank,'a-part','provided value','candidate')
    q['answers'][0]['target_id']='part1'
    relation=dict(from_id='a-part',to_id='part1',type='answer_candidate',reason='association',evidence=[copy.deepcopy(answer['location'])])
    bank['relations']=[relation];hold=dict(target_id='s1',reason='edition uncertain')
    bank['audit'].update(status='complete_with_holds',unresolved=[hold])
    row=build_authoring_index(bank,'0'*64)['questions'][0]
    assert row['subparts']==q['subparts'] and row['provided_answers']==q['answers']
    assert row['relations']==[relation] and hold in row['unresolved']

def test_variant_order_preserves_ids(tmp_path):
    _,bank=create_bank(tmp_path);add_variant(bank)
    a=initial_manifest(bank,'bank.json','0'*64);bank['questions'].reverse()
    b=initial_manifest(bank,'bank.json','0'*64)
    assert {q['id'] for q in a['problems']}=={q['id'] for q in b['problems']}=={'q1','q2'}

def test_asset_categories(tmp_path):
    path,bank=create_bank(tmp_path)
    for ident,role,exposure in [('safe','problem','none'),('mixed','mixed','present'),('maybe','mixed','unknown')]:
        add_asset(path,bank,ident,role,exposure,ident.encode())
        bank['occurrences'][0]['blocks'].append(dict(id='b-'+ident,type='figure',text=ident,tex=None,cells=None,asset_id=ident))
    row=build_authoring_index(bank,'0'*64)['questions'][0]
    assert row['safe_problem_asset_ids']==['safe']
    assert row['evidence_only_asset_ids']==['mixed','maybe']

@pytest.mark.parametrize('key,value',[('source_path','../bank.json'),('schema_version',[]),('schema_version',True),
    ('sha256','wrong'),('extra',1),('snapshot_path','../file')])
def test_malformed_binding_returns_findings(tmp_path,key,value):
    _,bank=create_bank(tmp_path);m=initial_manifest(bank,'bank.json','0'*64)
    m['bank_import'][key]=value
    assert validate_bank_import_fields(m)
    assert validate_manifest(m)

def test_imported_question_without_metadata_rejected(tmp_path):
    _,bank=create_bank(tmp_path);m=initial_manifest(bank,'bank.json','0'*64)
    del m['bank_import']
    assert validate_manifest(m)

def test_bank_question_id_cannot_change(tmp_path):
    _,bank=create_bank(tmp_path);m=initial_manifest(bank,'bank.json','0'*64)
    m['problems'][0]['bank_question_id']='other'
    assert validate_manifest(m)
