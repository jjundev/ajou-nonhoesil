"""Deterministic authoring views; original extraction stays in the snapshot."""
from copy import deepcopy
import re
from pathlib import PurePosixPath

AUTHORING_STATES=('pending','reading_hold','ready','not_selected','held')
BINDING_KEYS={'bank_id','schema_version','source_path','sha256','snapshot_path','index_path'}

def canonical_relative(value):
    return (isinstance(value,str) and bool(value)
        and not any(c in value for c in ('\\',':','\x00'))
        and not PurePosixPath(value).is_absolute()
        and all(p not in ('','.','..') for p in value.split('/')))

def question_sources(bank, question):
    occurrences={o['id']:o for o in bank['occurrences']}
    return [dict(deepcopy(occurrences[i]['location']),question=occurrences[i]['original_number'])
            for i in question['occurrence_ids']]

def build_authoring_index(bank, bank_sha256):
    occurrences={o['id']:o for o in bank['occurrences']}
    assets={a['id']:a for a in bank['assets']}
    rows=[]
    for q in bank['questions']:
        targets={q['id']}|{p['id'] for p in q['subparts']}
        occurrence_ids=list(q['occurrence_ids'])
        answer_ids=[a['occurrence_id'] for a in q['answers']]
        answer_ids += [r['from_id'] for r in bank['relations']
                       if r['type']=='answer_candidate' and r['to_id'] in targets]
        relevant=targets|set(occurrence_ids)|set(answer_ids)
        relations=[r for r in bank['relations'] if r['from_id'] in relevant or r['to_id'] in relevant]
        safe=[];other=[]
        for ident in dict.fromkeys(occurrence_ids+answer_ids):
            occurrence=occurrences[ident]
            relevant.add(occurrence['location']['source_id'])
            for loc in [u['location'] for u in occurrence['uncertainties']]:
                relevant.add(loc['source_id'])
            for b in occurrence['blocks']:
                relevant.add(b['id'])
                if b['type']!='figure':continue
                asset=assets[b['asset_id']]
                relevant.update((asset['id'],asset['location']['source_id']))
                allowed=(ident in occurrence_ids and asset['role']=='problem'
                         and asset['answer_exposure']=='none')
                (safe if allowed else other).append(asset['id'])
        relevant.update(loc['source_id'] for loc in q['evidence'])
        relevant.update(loc['source_id'] for r in relations for loc in r['evidence'])
        reading=occurrences[q['representative_occurrence_id']]['reading']
        unresolved=[u for u in bank['audit']['unresolved'] if u['target_id'] in relevant]
        rows.append(dict(question_id=q['id'],kind=q['kind'],
            representative_occurrence_id=q['representative_occurrence_id'],
            occurrence_ids=deepcopy(q['occurrence_ids']),subparts=deepcopy(q['subparts']),
            provided_answers=deepcopy(q['answers']),relations=deepcopy(relations),
            unresolved=deepcopy(unresolved),representative_reading=reading,
            safe_problem_asset_ids=list(dict.fromkeys(safe)),
            evidence_only_asset_ids=list(dict.fromkeys(other)),
            authoring_status='pending' if reading=='readable' else 'reading_hold',
            selection_reason='설명·개념 연결·독립 풀이 저작 대기'))
    return dict(schema='logic-lab-bank-import',schema_version=1,bank_id=bank['bank_id'],
        bank_sha256=bank_sha256,experiment=bank['experiment'],questions=rows)

def initial_manifest(bank, source_path, bank_sha256):
    index=build_authoring_index(bank,bank_sha256)
    by_id={q['question_id']:q for q in index['questions']}
    problems=[]
    for q in bank['questions']:
        row=by_id[q['id']]
        reasons=[row['selection_reason']]+[u['reason'] for u in row['unresolved']]
        problems.append(dict(id=q['id'],bank_question_id=q['id'],kind=q['kind'],status='held',
            reason=' · '.join(dict.fromkeys(reasons)),topics=[],sources=question_sources(bank,q),
            duplicate_of=None,scope='unknown',given_answer=None,derived_answer=None,
            answer_status='unresolved'))
    return dict(schema_version=1,experiment=bank['experiment'],
        title=f'실험{bank["experiment"]} 문제은행 저작',edition_status='unknown',
        bank_import=dict(bank_id=bank['bank_id'],schema_version=bank['schema_version'],
            source_path=source_path,sha256=bank_sha256,
            snapshot_path='evidence/question-bank.json',index_path='authoring-index.json'),
        sources=[dict(id=s['id'],path=s['path'],sha256=s['sha256'],kind='quiz',edition='unknown')
                 for s in bank['sources']],
        topics=[],problems=problems,
        checks={k:'not_run' for k in ('source_visual','content','independent','browser')})

def validate_bank_import_fields(manifest):
    errors=[]
    present='bank_import' in manifest
    binding=manifest.get('bank_import')
    if present:
        if not isinstance(binding,dict):
            errors.append('$.bank_import: must be an object')
        else:
            if set(binding)!=BINDING_KEYS:errors.append('$.bank_import: unknown or missing fields')
            if not isinstance(binding.get('bank_id'),str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',binding['bank_id']):
                errors.append('$.bank_import.bank_id: invalid id')
            if type(binding.get('schema_version')) is not int or binding['schema_version']!=1:
                errors.append('$.bank_import.schema_version: unsupported version')
            if not isinstance(binding.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',binding['sha256']):
                errors.append('$.bank_import.sha256: invalid hash')
            for k in ('source_path','snapshot_path','index_path'):
                if not canonical_relative(binding.get(k)):errors.append('$.bank_import.'+k+': unsafe path')
            if binding.get('snapshot_path')!='evidence/question-bank.json':errors.append('$.bank_import.snapshot_path: unexpected location')
            if binding.get('index_path')!='authoring-index.json':errors.append('$.bank_import.index_path: unexpected location')
    rows=manifest.get('problems',[])
    if isinstance(rows,list):
        for i,p in enumerate(rows):
            if not isinstance(p,dict) or 'bank_question_id' not in p:continue
            if not present:errors.append(f'$.problems[{i}]: missing bank_import')
            ident=p['bank_question_id']
            if not isinstance(ident,str) or ident!=p.get('id'):
                errors.append(f'$.problems[{i}].bank_question_id: must match id')
    return errors
