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

def location():
    return dict(source_id='s1', pdf_page=None, printed_page=None, locator='document:1', bbox=None, image_size=None)

def populated():
    data = bank()
    data['sources'] = [dict(id='s1', path='quiz.txt', sha256='0'*64, format='text',
        filename_metadata={'year':None,'term':None}, observed_metadata={'year':None,'term':None},
        conflicts=[], processing='complete', reason='', unit_kind='document', unit_count=1)]
    data['occurrences'] = [dict(id='o1', role='question', location=location(), original_number='1',
        blocks=[dict(id='b1',type='text',text='입력이 0일 때 출력은?',tex=None,cells=None,asset_id=None)], reading='readable', uncertainties=[])]
    data['questions'] = [dict(id='q1',occurrence_ids=['o1'],representative_occurrence_id='o1',kind='unknown',
        classification_reason='실제 시험 여부 미확인',evidence=[location()],subparts=[],answers=[])]
    data['audit']['units'] = [dict(source_id='s1',index=1,outcome='questions',occurrence_ids=['o1'],reason='')]
    return data

@pytest.mark.parametrize('change', [
    lambda d: d['questions'][0].update(representative_occurrence_id='missing'),
    lambda d: d['occurrences'][0].update(reading='partial'),
    lambda d: d['occurrences'][0]['blocks'][0].update(id='q1'),
    lambda d: d['audit'].update(status='complete'),
    lambda d: d['questions'][0]['answers'].append(dict(occurrence_id='o1',target_id='q1',status='confirmed',reason='번호만 같음')),
])
def test_semantic_errors(change):
    data = populated(); change(data)
    assert validate_question_bank(data)

def test_variant_is_not_merged_or_mutated():
    data = populated()
    occ = copy.deepcopy(data['occurrences'][0]); occ['id']='o2'; occ['blocks'][0].update(id='b2',text='입력이 1일 때 출력은?')
    data['occurrences'].append(occ)
    q = copy.deepcopy(data['questions'][0]); q.update(id='q2',occurrence_ids=['o2'],representative_occurrence_id='o2')
    data['questions'].append(q)
    data['audit']['units'][0]['occurrence_ids'].append('o2')
    data['relations'].append(dict(from_id='q1',to_id='q2',type='variant_of',reason='입력값이 다름',evidence=[location()]))
    before=copy.deepcopy(data)
    assert validate_question_bank(data)==[]
    assert len(data['questions'])==2 and data==before

def test_conflicting_provided_answers_remain_candidates():
    data=populated()
    for number, value in [(2,'0'),(3,'1')]:
        occ=copy.deepcopy(data['occurrences'][0]); occ.update(id=f'o{number}',role='answer')
        occ['blocks'][0].update(id=f'b{number}',text=value)
        data['occurrences'].append(occ)
        data['questions'][0]['answers'].append(dict(occurrence_id=occ['id'],target_id='q1',status='candidate',reason='분반 미확인'))
        data['audit']['units'][0]['occurrence_ids'].append(occ['id'])
    before=copy.deepcopy(data)
    assert validate_question_bank(data)==[]
    assert data==before
def test_exposed_image_cannot_be_problem_asset():
    data=populated()
    data['assets']=[dict(id='a1',path='assets/a.png',sha256='0'*64,location=location(),role='problem',answer_exposure='present')]
    assert validate_question_bank(data)

def test_complete_with_holds_is_valid_but_not_complete():
    data=populated(); data['occurrences'][0]['reading']='partial'
    data['occurrences'][0]['uncertainties']=[dict(block_id='b1',symbol='오버바',candidates=[],reason='흐림',location=location())]
    data['audit'].update(status='complete_with_holds',unresolved=[dict(target_id='o1',reason='오버바 판독 보류')])
    data['audit']['checks']['source_visual']='partial'
    assert validate_question_bank(data)==[]
    data['audit']['status']='complete'
    assert validate_question_bank(data)

@pytest.mark.parametrize('page', [0, 3, True])
def test_invalid_pdf_page(page):
    data=populated(); data['sources'][0].update(format='pdf',path='quiz.pdf',unit_kind='page',unit_count=2)
    data['occurrences'][0]['location']['pdf_page']=page
    data['questions'][0]['evidence'][0]['pdf_page']=1
    assert validate_question_bank(data)

def test_order_does_not_reissue_ids():
    data=populated()
    occurrence=copy.deepcopy(data['occurrences'][0]); occurrence['id']='o2'; occurrence['blocks'][0].update(id='b2',text='다른 조건')
    data['occurrences'].append(occurrence)
    question=copy.deepcopy(data['questions'][0]); question.update(id='q2',occurrence_ids=['o2'],representative_occurrence_id='o2')
    data['questions'].append(question)
    data['audit']['units'][0]['occurrence_ids'].append('o2')
    before=copy.deepcopy(data)
    for key in ('sources','assets','occurrences','questions','relations'): data[key].reverse()
    assert validate_question_bank(data)==[]
    assert {q['id'] for q in data['questions']}=={q['id'] for q in before['questions']}

def test_filename_header_conflict_requires_evidence():
    data=populated(); source=data['sources'][0]
    source['filename_metadata']['year']='2016'; source['observed_metadata']['year']='2017'
    assert validate_question_bank(data)
    source['conflicts']=[dict(field='year',filename_value='2016',observed_value='2017',location=location())]
    assert validate_question_bank(data)==[]

def test_shared_stem_subpart_references_existing_blocks():
    data=populated()
    data['questions'][0]['subparts']=[dict(id='part1',label='가',occurrence_id='o1',block_ids=['b1'])]
    assert validate_question_bank(data)==[]
    data['questions'][0]['subparts'][0]['block_ids']=['missing']
    assert validate_question_bank(data)

def test_duplicate_candidate_does_not_require_merge():
    data=populated()
    occurrence=copy.deepcopy(data['occurrences'][0]); occurrence['id']='o2'; occurrence['blocks'][0]['id']='b2'
    data['occurrences'].append(occurrence)
    question=copy.deepcopy(data['questions'][0]); question.update(id='q2',occurrence_ids=['o2'],representative_occurrence_id='o2')
    data['questions'].append(question); data['audit']['units'][0]['occurrence_ids'].append('o2')
    data['relations']=[dict(from_id='q1',to_id='q2',type='duplicate_candidate',reason='극성 재확인 필요',evidence=[location()])]
    assert validate_question_bank(data)==[]
    assert len(data['questions'])==2

def test_complete_pdf_must_account_for_every_page():
    data=populated(); data['sources'][0].update(format='pdf',path='quiz.pdf',unit_kind='page',unit_count=2)
    data['occurrences'][0]['location']['pdf_page']=1; data['questions'][0]['evidence'][0]['pdf_page']=1
    data['audit']['status']='complete'; data['audit']['checks']['source_visual']='pass'
    assert validate_question_bank(data)
    data['audit']['units'].append(dict(source_id='s1',index=2,outcome='blank',occurrence_ids=[],reason='빈 뒷면'))
    assert validate_question_bank(data)==[]


@pytest.mark.parametrize('change', [
    lambda d: d['sources'][0].update(unit_count=2),
    lambda d: d['sources'][0].update(processing='held'),
    lambda d: d['occurrences'][0]['location'].update(source_id='missing'),
    lambda d: d['occurrences'][0]['location'].update(pdf_page=1),
    lambda d: d['occurrences'][0]['location'].update(locator=' '),
    lambda d: d['occurrences'][0]['location'].update(bbox=[.7,0,.2,1],image_size=[100,100]),
    lambda d: d['occurrences'][0]['location'].update(bbox=[0,0,1,1]),
    lambda d: d['occurrences'][0].update(blocks=[]),
    lambda d: d['occurrences'][0]['blocks'][0].update(type='math'),
    lambda d: d['occurrences'][0]['blocks'][0].update(type='table',cells=[['a'],['b','c']]),
    lambda d: d['occurrences'][0]['blocks'][0].update(type='figure',asset_id='missing'),
    lambda d: d['occurrences'][0]['blocks'][0].update(tex='unexpected'),
    lambda d: d['questions'][0].update(occurrence_ids=['o1','o1']),
    lambda d: d['questions'][0].update(classification_reason=' '),
    lambda d: d['audit']['units'].append(copy.deepcopy(d['audit']['units'][0])),
    lambda d: d['audit']['units'][0].update(occurrence_ids=['missing']),
    lambda d: d['audit']['units'][0].update(outcome='blank'),
    lambda d: d['audit']['unresolved'].append(dict(target_id='missing',reason='test')),
    lambda d: d['relations'].append(dict(from_id='q1',to_id='q1',type='variant_of',reason='test',evidence=[location()])),
])
def test_invalid_evidence_is_rejected(change):
    data=populated(); change(data)
    assert validate_question_bank(data)


def test_orphan_answer_needs_audit_reason():
    data=populated(); occurrence=copy.deepcopy(data['occurrences'][0])
    occurrence.update(id='o2',role='answer'); occurrence['blocks'][0]['id']='b2'
    data['occurrences'].append(occurrence); data['audit']['units'][0]['occurrence_ids'].append('o2')
    assert validate_question_bank(data)
    data['audit']['unresolved']=[dict(target_id='o2',reason='Matching exam unknown')]
    assert validate_question_bank(data)==[]


def test_summary_reports_kinds_and_holds_without_changing_data():
    from scripts.lab.review_pack.question_bank import summarize_question_bank
    data=populated(); before=copy.deepcopy(data)
    assert summarize_question_bank(data)==dict(sources=1,occurrences=1,unique_questions=1,past=0,predicted=0,unknown=1,unreadable=0,partial=0,candidate_relations=0,unresolved=0)
    assert data==before

from hashlib import sha256
from scripts.lab.review_pack.question_bank import check_question_bank_files

def test_changed_source_and_missing_asset(tmp_path):
    data=populated(); (tmp_path/'quiz.txt').write_bytes(b'original')
    data['sources'][0]['sha256']=sha256(b'original').hexdigest()
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)==[]
    (tmp_path/'quiz.txt').write_bytes(b'changed')
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)
    data['sources'][0]['sha256']=sha256(b'changed').hexdigest()
    data['assets']=[dict(id='a1',path='assets/missing.png',sha256='0'*64,location=location(),role='mixed',answer_exposure='unknown')]
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)

@pytest.mark.parametrize('path',['../outside.txt','C:/outside.txt','/absolute.txt','a\\b.txt','.'])
def test_unsafe_source_path(tmp_path,path):
    data=populated(); data['sources'][0]['path']=path
    assert check_question_bank_files(data,root=tmp_path,bank_dir=tmp_path)

def test_unknown_page_count_is_explicit_hold():
    data=bank()
    source=populated()['sources'][0]
    source.update(path='locked.pdf',format='pdf',unit_kind='page',unit_count=None,processing='held',reason='암호화')
    data['sources']=[source]
    data['audit'].update(status='complete_with_holds',units=[dict(source_id='s1',index=1,outcome='held',occurrence_ids=[],reason='암호화')],unresolved=[dict(target_id='s1',reason='페이지 수 확인 불가')])
    data['audit']['checks']['source_visual']='partial'
    assert validate_question_bank(data)==[]


@pytest.mark.parametrize('change', [
    lambda d: d.update(schema=['logic-lab-question-bank']),
    lambda d: d['sources'][0].update(processing=['complete']),
    lambda d: d['occurrences'][0].update(role=['question']),
])
def test_array_in_enum_returns_errors_instead_of_raising(change):
    data = populated()
    change(data)
    before = copy.deepcopy(data)
    errors = validate_question_bank(data)
    assert errors and all(error.startswith('$.') for error in errors)
    assert data == before


@pytest.mark.parametrize('status', ['draft', 'complete', 'complete_with_holds'])
def test_readable_cannot_hide_unresolved_symbols(status):
    data = populated()
    data['audit']['status'] = status
    data['audit']['checks']['source_visual'] = 'pass'
    data['occurrences'][0]['uncertainties'] = [dict(
        block_id='b1', symbol='overbar', candidates=['present', 'absent'],
        reason='blurred symbol', location=location())]
    if status == 'complete_with_holds':
        data['audit']['unresolved'] = [dict(target_id='o1', reason='blurred symbol')]
    before = copy.deepcopy(data)
    errors = validate_question_bank(data)
    assert any('$.occurrences[0].reading' in error for error in errors)
    assert data == before
    data['occurrences'][0]['reading'] = 'partial'
    data['audit']['status'] = 'complete_with_holds'
    data['audit']['unresolved'] = [dict(target_id='o1', reason='blurred symbol')]
    assert validate_question_bank(data) == []


@pytest.mark.parametrize('nested', [False, True])
def test_duplicate_json_keys_are_rejected_without_losing_evidence(tmp_path, nested):
    raw = json.dumps(populated())
    if nested:
        raw = raw.replace('"text": ', '"text": "discarded condition", "text": ', 1)
        key = 'text'
    else:
        raw = raw.replace('"experiment": 4', '"experiment": 3, "experiment": 4', 1)
        key = 'experiment'
    path = tmp_path / 'duplicate.json'
    path.write_text(raw, encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicate JSON key.*' + key):
        load_question_bank(path)
    assert path.read_text(encoding='utf-8') == raw


@pytest.mark.parametrize('value', [10**400, -(10**400)], ids=['positive', 'negative'])
def test_huge_bbox_integer_returns_range_error(value):
    data = populated()
    data['occurrences'][0]['location'].update(bbox=[0, 0, value, 1], image_size=[100, 100])
    errors = validate_question_bank(data)
    assert any('$.occurrences[0].location.bbox[2]' in error for error in errors)


@pytest.mark.parametrize('case', ['uncertainty', 'duplicate', 'huge_integer'])
def test_invalid_evidence_cli_reports_error_without_mutating_json(tmp_path, capsys, case):
    from scripts.lab.review_pack.question_bank_cli import main
    data = populated()
    (tmp_path / 'quiz.txt').write_bytes(b'evidence')
    data['sources'][0]['sha256'] = sha256(b'evidence').hexdigest()
    data['audit']['status'] = 'complete'
    data['audit']['checks']['source_visual'] = 'pass'
    if case == 'uncertainty':
        data['occurrences'][0]['uncertainties'] = [dict(
            block_id='b1', symbol='overbar', candidates=[], reason='blurred', location=location())]
    elif case == 'huge_integer':
        data['occurrences'][0]['location'].update(bbox=[0, 0, 10**400, 1], image_size=[100, 100])
    raw = json.dumps(data)
    if case == 'duplicate':
        raw = raw.replace('"text": ', '"text": "lost condition", "text": ', 1)
    path = tmp_path / 'bank.json'
    path.write_text(raw, encoding='utf-8')
    assert main(['check', '--root', str(tmp_path), '--bank', str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == '' and 'FAIL' in output.err
    assert path.read_text(encoding='utf-8') == raw
