"""Versioned learning-content contract. Validation never changes authored data."""
import json
import re
from pathlib import Path, PurePosixPath
from scripts.lab import config
from .bank_index import validate_bank_import_fields
from .question_bank import _unique_json_object

def safe_relative(value):
    return isinstance(value,str) and bool(value) and not PurePosixPath(value).is_absolute() and not any(x in value for x in ('\\',':')) and '..' not in PurePosixPath(value).parts

DATA=config.PACK_DATA_DIR

def data_dir(folder):
    """발행 폴더의 자료 폴더. 저작 RUN 에는 자료/ 가 없으므로 RUN 그대로 돌려준다."""
    folder=Path(folder)
    return folder/DATA if (folder/DATA).is_dir() else folder

def data_url(relative):
    """자료 폴더 기준 경로를 문서(루트) 기준 링크로."""
    return DATA+'/'+relative

def strip_data(path):
    """문서 기준 링크의 자료/ 접두를 떼어 낸다. 접두가 없으면 그대로."""
    return path[len(DATA)+1:] if path.startswith(DATA+'/') else path

_AUTHORED_RESOURCE=re.compile(r"(\b(?:src|href)=[\"'])(figures|assets|evidence)/")

def link_data(text):
    """저작 조각 속 `figures/..` 링크를 문서 기준 `자료/figures/..` 로."""
    return _AUTHORED_RESOURCE.sub(lambda m:m.group(1)+DATA+'/'+m.group(2)+'/',text)

def output_names(experiment, *, review_presentation_version=None, problem_explanation_version=None):
    base=config.experiment_folder_name(experiment)
    names={f'{kind}_{ext}':f'{base}_{label}.{ext}' for kind,label in [('note','실험설명'),('review','기출풀이')] for ext in ('html','md')}
    if review_presentation_version == 2:
        names.update({f'question_{ext}':f'{base}_기출문제.{ext}' for ext in ('html','md')})
    if problem_explanation_version == 1:
        names.update({f'explanation_{ext}':f'{base}_문제설명.{ext}' for ext in ('html','md')})
    return names

def validate_manifest(data):
    errors=[]
    if not isinstance(data,dict):
        return ['manifest must be an object']
    if data.get('schema_version')!=1:
        errors.append('schema_version must be 1')
    if 'note_presentation_version' in data and (type(data['note_presentation_version']) is not int or data['note_presentation_version'] != 2):
        errors.append('note_presentation_version must be 2 or absent')
    modern=data.get('review_presentation_version') == 2
    if 'review_presentation_version' in data and (type(data['review_presentation_version']) is not int or not modern):
        errors.append('review_presentation_version must be 2 or absent')
    explanation='problem_explanation_version' in data
    if explanation:
        if type(data['problem_explanation_version']) is not int or data['problem_explanation_version']!=1 or not modern:
            errors.append('problem_explanation_version requires version 1 and workbook version 2')
        checks=data.get('explanation_checks',{})
        for key in ('source_visual','content','independent','browser'):
            if not isinstance(checks,dict) or checks.get(key) not in {'pass','fail','not_run','self_review'}:
                errors.append('invalid explanation check: '+key)
    if modern and not safe_relative(data.get('figure_manifest')):
        errors.append('unsafe/missing figure_manifest')
    try: config.experiment_folder_name(data.get('experiment'))
    except (ValueError,TypeError): errors.append('invalid experiment')
    if not isinstance(data.get('title'),str) or not data['title'].strip():
        errors.append('missing title')
    if data.get('edition_status') not in {'current','archive','unknown','general'}:
        errors.append('invalid edition_status')
    collections={}
    seen=set()
    for key in ('sources','topics','problems'):
        rows=data.get(key)
        if not isinstance(rows,list):
            errors.append(key+' must be a list');rows=[]
        collections[key]={}
        for row in rows:
            if not isinstance(row,dict):
                errors.append(key+' row must be an object');continue
            ident=row.get('id')
            if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',ident) or ident in seen:
                errors.append('invalid or duplicate id: '+str(ident));continue
            seen.add(ident);collections[key][ident]=row
    sources,topics,problems=(collections[k] for k in ('sources','topics','problems'))
    for ident,s in sources.items():
        if not safe_relative(s.get('path')): errors.append(ident+': unsafe source path')
        if not isinstance(s.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',s['sha256']): errors.append(ident+': invalid sha256')
        if s.get('kind') not in {'manual','quiz','theory','report','record','datasheet','stt','notice'}: errors.append(ident+': invalid source kind')
        if s.get('edition') not in {'current','archive','unknown'}: errors.append(ident+': invalid edition')
    def refs(ident,row,required=False):
        refs=row.get('sources')
        if not isinstance(refs,list) or (required and not refs):
            errors.append(ident+': missing source location');return
        for ref in refs:
            if not isinstance(ref,dict) or ref.get('source_id') not in sources:
                errors.append(ident+': unknown source');continue
            page=ref.get('pdf_page')
            path=sources[ref['source_id']].get('path','')
            if path.lower().endswith('.pdf') or page is not None:
                if type(page) is not int or page<1: errors.append(ident+': invalid pdf_page')
            if ref.get('printed_page') is not None and not isinstance(ref['printed_page'],str): errors.append(ident+': invalid printed_page')
    for ident,t in topics.items():
        if 'md_notes' in t and not isinstance(t['md_notes'],str):
            errors.append(ident+': md_notes must be text')
        refs(ident,t)
        if not safe_relative(t.get('fragment')): errors.append(ident+': unsafe fragment')
        if not isinstance(t.get('title'),str): errors.append(ident+': missing topic title')
        if not isinstance(t.get('requires'),list) or any(r not in topics for r in t.get('requires',[])): errors.append(ident+': unknown prerequisite')
    for ident,p in problems.items():
        if p.get('kind') not in {'past','unknown','predicted','practice'}: errors.append(ident+': invalid kind')
        if p.get('status') not in {'included','duplicate','held','other_experiment'}: errors.append(ident+': invalid status')
        if p.get('scope') not in {'current','supplement','unknown'}: errors.append(ident+': invalid scope')
        if p.get('answer_status') not in {'verified','disputed','unresolved'}: errors.append(ident+': invalid answer_status')
        refs(ident,p,p.get('kind')!='practice')
        links=p.get('topics')
        if not isinstance(links,list) or any(t not in topics for t in links) or (p.get('status')=='included' and not links): errors.append(ident+': unknown/missing topics')
        if p.get('status')=='included':
            if explanation and p.get('explanation_fragment')!=f'problem-explanations/{ident}.html':
                errors.append(ident+': missing/canonical explanation_fragment required')
            field='workbook_fragment' if modern else 'fragment'
            if not safe_relative(p.get(field)): errors.append(ident+': unsafe/missing '+field)
            if p.get('answer_status')=='verified' and not p.get('derived_answer'): errors.append(ident+': missing derived_answer')
        elif not p.get('reason'): errors.append(ident+': missing reason')
        if p.get('status')=='duplicate' and p.get('duplicate_of') not in problems: errors.append(ident+': missing duplicate target')
    def cycle(rows,edges):
        done=set();active=set()
        def visit(ident):
            if ident in active: return True
            if ident in done or ident not in rows: return False
            active.add(ident)
            values=edges(rows[ident])
            if isinstance(values,list):
                for nxt in values:
                    if isinstance(nxt,str) and visit(nxt): return True
            active.remove(ident);done.add(ident)
            return False
        return any(visit(i) for i in rows)
    if cycle(topics,lambda r:r.get('requires',[])): errors.append('prerequisite cycle')
    if cycle(problems,lambda r:[r.get('duplicate_of')] if r.get('status')=='duplicate' else []): errors.append('duplicate cycle')
    checks=data.get('checks',{})
    if not isinstance(checks,dict): checks={}
    for key in ('source_visual','content','independent','browser'):
        if checks.get(key) not in {'pass','fail','not_run','self_review'}: errors.append('invalid check: '+key)
    files=data.get('generated_files',[])
    if not isinstance(files,list) or any(not safe_relative(p) for p in files): errors.append('unsafe generated_files')
    return errors + validate_bank_import_fields(data)

def load_manifest(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=_unique_json_object)
    errors=validate_manifest(data)
    if errors: raise ValueError('\n'.join(errors))
    return data
