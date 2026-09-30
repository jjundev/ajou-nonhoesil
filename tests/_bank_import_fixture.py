"""Evidence-backed input for bank-import behavior tests."""
import copy
import hashlib
import json
from pathlib import Path
from tests.test_review_pack_question_bank import populated

def save_bank(path, bank):
    path.write_text(json.dumps(bank,ensure_ascii=False,indent=2),encoding='utf-8')

def create_bank(root, *, relative='문제은행/실험04/question-bank.json'):
    bank=populated()
    source=root/'quiz.txt';source.write_bytes(b'original quiz evidence')
    bank['sources'][0]['sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    bank['audit']['status']='complete'
    bank['audit']['checks'].update(structure='pass',source_visual='pass')
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    save_bank(path,bank)
    return path,bank

def add_answer(bank, ident, value, status):
    occurrence=copy.deepcopy(bank['occurrences'][0])
    occurrence.update(id=ident,role='answer',blocks=[dict(id='b-'+ident,type='text',
        text=value,tex=None,cells=None,asset_id=None)])
    bank['occurrences'].append(occurrence)
    bank['audit']['units'][0]['occurrence_ids'].append(ident)
    bank['questions'][0]['answers'].append(dict(occurrence_id=ident,target_id='q1',
        status=status,reason='provided association'))
    return occurrence

def add_asset(path, bank, ident, role, exposure, content):
    file=path.parent/'assets'/(ident+'.png')
    file.parent.mkdir(exist_ok=True);file.write_bytes(content)
    row=dict(id=ident,path='assets/'+ident+'.png',sha256=hashlib.sha256(content).hexdigest(),
        location=copy.deepcopy(bank['occurrences'][0]['location']),role=role,answer_exposure=exposure)
    bank['assets'].append(row)
    return row

def mark_partial(bank):
    occurrence=bank['occurrences'][0]
    occurrence.update(reading='partial',uncertainties=[dict(block_id='b1',symbol='overbar',
        candidates=['present','absent'],reason='blurred',location=copy.deepcopy(occurrence['location']))])
    bank['audit'].update(status='complete_with_holds',unresolved=[dict(target_id='o1',reason='blurred')])
    bank['audit']['checks']['source_visual']='partial'

def add_variant(bank):
    occurrence=copy.deepcopy(bank['occurrences'][0])
    occurrence.update(id='o2',blocks=[dict(id='b2',type='text',text='different condition',
        tex=None,cells=None,asset_id=None)])
    bank['occurrences'].append(occurrence)
    bank['audit']['units'][0]['occurrence_ids'].append('o2')
    q=copy.deepcopy(bank['questions'][0])
    q.update(id='q2',occurrence_ids=['o2'],representative_occurrence_id='o2',answers=[],subparts=[])
    bank['questions'].append(q)
    bank['relations'].append(dict(from_id='q1',to_id='q2',type='variant_of',
        reason='different condition',evidence=[copy.deepcopy(occurrence['location'])]))
