from copy import deepcopy
import pytest
from tests._quiz_practice_fixture import quiz_manifest
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.manifest import validate_manifest


def test_policy_and_legacy_validate_without_mutation():
    m=quiz_manifest(); before=deepcopy(m)
    assert validate_manifest(m)==[]
    assert m==before
    assert validate_manifest(fixture())==[]


@pytest.mark.parametrize('change', ['version','bool','missing','modern','explanation','count','mixed','held','kind','scope','answer','given','source','topic','bank','order','tf'])
def test_invalid_quiz_policy_rejected(change):
    m=quiz_manifest(); p=m['problems'][1]
    if change=='version':m['quiz_practice_version']=2
    if change=='bool':m['quiz_practice_version']=True
    if change=='missing':del m['quiz_practice_version']
    if change=='modern':del m['review_presentation_version']
    if change=='explanation':m['problem_explanation_version']=1
    if change=='count':m['problems'].pop()
    if change=='mixed':p['question_type']='fill_blank'
    if change=='held':p.update(status='held',reason='미확인')
    if change=='kind':p['kind']='predicted'
    if change=='scope':p['scope']='supplement'
    if change=='answer':p['answer_status']='unresolved'
    if change=='given':p['given_answer']='T'
    if change=='source':p['sources']=[]
    if change=='topic':p['topics']=[]
    if change=='bank':p['bank_question_id']='bank-1'
    if change=='order':m['problems'].append(m['problems'].pop(0))
    if change=='tf':p['derived_answer']='True'
    assert validate_manifest(m),change


def test_held_and_untyped_practice_do_not_fill_quota():
    m=quiz_manifest(); m['problems'][1].update(status='held',reason='보류')
    p=deepcopy(m['problems'][0]);p['id']='q-other';m['problems'].insert(1,p)
    assert any('true_false' in e for e in validate_manifest(m))
