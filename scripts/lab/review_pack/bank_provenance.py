"""Check immutable extraction fields separately from mutable authoring choices."""
import json
from pathlib import Path
from .bank_index import (AUTHORING_STATES,build_authoring_index,initial_manifest,
                         validate_bank_import_fields)
from .question_bank import load_question_bank,check_question_bank_files,_unique_json_object
from .question_bank_sources import _evidence_path
from .manifest import data_dir
from .sources import file_sha256

def strict_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=_unique_json_object)

def same_json(a,b):
    """JSON booleans cannot stand in for integer version numbers."""
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(same_json(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(same_json(x,y) for x,y in zip(a,b))
    return a==b

def _index_errors(actual,expected):
    errors=[]
    if not isinstance(actual,dict) or actual.keys()!=expected.keys():
        return ['$.authoring_index: invalid fields']
    for key in expected:
        if key!='questions' and not same_json(actual[key],expected[key]):
            errors.append('$.authoring_index.'+key+': differs from bank')
    rows=actual.get('questions')
    if not isinstance(rows,list):return errors+['$.authoring_index.questions: must be a list']
    lookup={}
    for i,row in enumerate(rows):
        if not isinstance(row,dict) or not isinstance(row.get('question_id'),str):
            errors.append(f'$.authoring_index.questions[{i}]: invalid row');continue
        if row['question_id'] in lookup:errors.append('Duplicate index question: '+row['question_id'])
        lookup[row['question_id']]=row
    if set(lookup)!={r['question_id'] for r in expected['questions']}:
        errors.append('$.authoring_index.questions: missing/foreign questions')
    for want in expected['questions']:
        ident=want['question_id'];row=lookup.get(ident)
        if row is None:continue
        if row.keys()!=want.keys():errors.append(ident+': invalid index fields');continue
        for key,value in want.items():
            if key not in {'authoring_status','selection_reason'} and not same_json(row[key],value):
                errors.append(ident+': index extraction field changed: '+key)
        if not isinstance(row['authoring_status'],str) or row['authoring_status'] not in AUTHORING_STATES:
            errors.append(ident+': invalid authoring_status')
        if not isinstance(row['selection_reason'],str) or (row['authoring_status'] in ('not_selected','held') and not row['selection_reason'].strip()):
            errors.append(ident+': missing selection reason')
    return errors

def check_bank_import(folder,manifest,*,root=None):
    errors=validate_bank_import_fields(manifest)
    if errors or 'bank_import' not in manifest:return errors
    folder=Path(folder);data=data_dir(folder);binding=manifest['bank_import']
    try:
        snapshot=_evidence_path(data,binding['snapshot_path'])
        if file_sha256(snapshot)!=binding['sha256']:return ['$.bank_import.sha256: snapshot changed']
        bank=load_question_bank(snapshot)
        if bank['audit']['status'] not in ('complete','complete_with_holds'):
            errors.append('$.bank_import: unfinished bank')
        if bank['bank_id']!=binding['bank_id'] or bank['schema_version']!=binding['schema_version'] or bank['experiment']!=manifest.get('experiment'):
            errors.append('$.bank_import: bank id/version/experiment mismatch')
        for asset in bank['assets']:
            path=_evidence_path(snapshot.parent,asset['path'])
            if file_sha256(path)!=asset['sha256']:errors.append('Asset changed: '+asset['id'])
        expected=build_authoring_index(bank,binding['sha256'])
        index=strict_json(_evidence_path(data,binding['index_path']))
        errors.extend(_index_errors(index,expected))
        guide=_evidence_path(folder,'원문과_저작안내.md')
        if not guide.is_file():errors.append('Missing authoring guide')
        initial=initial_manifest(bank,binding['source_path'],binding['sha256'])
        originals={p['id']:p for p in initial['problems']}
        imported={}
        rows=manifest.get('problems',[])
        if not isinstance(rows,list):return errors+['$.problems: must be a list']
        for p in rows:
            if not isinstance(p,dict):errors.append('$.problems: invalid row');continue
            if 'bank_question_id' not in p:continue
            ident=p['bank_question_id']
            if ident in imported:errors.append('Duplicate imported question: '+ident)
            imported[ident]=p
        if imported.keys()!=originals.keys():errors.append('$.problems: bank questions missing or foreign')
        readings={q['question_id']:q['representative_reading'] for q in expected['questions']}
        for ident,p in imported.items():
            original=originals.get(ident)
            if original is None:continue
            for key in ('id','bank_question_id','kind','sources'):
                if not same_json(p.get(key),original[key]):errors.append(ident+': bank field changed: '+key)
            if p.get('status')=='included' and readings[ident]!='readable':
                errors.append(ident+': representative reading is on hold')
        actual_sources=manifest.get('sources',[])
        if not isinstance(actual_sources,list):return errors+['$.sources: must be a list']
        lookup={s['id']:s for s in actual_sources if isinstance(s,dict) and isinstance(s.get('id'),str)}
        for source in bank['sources']:
            row=lookup.get(source['id'])
            if row is None or any(row.get(k)!=source[k] for k in ('id','path','sha256')):
                errors.append('Bank source changed/missing: '+source['id'])
        if root is not None:
            root=Path(root)
            original_bank=_evidence_path(root,binding['source_path'])
            if file_sha256(original_bank)!=binding['sha256']:errors.append('Original bank changed; re-import required')
            errors.extend(check_question_bank_files(bank,root=root,bank_dir=original_bank.parent))
    except (ValueError,OSError) as exc:
        errors.append('$.bank_import: '+str(exc))
    return errors
