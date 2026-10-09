"""Inert authored content and explicit question/answer projections."""
from copy import deepcopy
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
from .question_bank import _unique_json_object
from .bank_index import canonical_relative
from .manifest import strip_data, link_data, data_url
from .html2md import Parser
from .work_table import check_work_tables

AUTHOR_KEYS = {'original','conditions','ask','problem_figures','hints','solution','notes'}
KINDS = {'past':'기출','predicted':'예상문제','unknown':'출처 미확인','practice':'연습문제'}
STATES = {'verified':'풀이 검토됨','disputed':'답안 충돌','unresolved':'정답 미확정'}

def _strict_json(path):
    def bad(value):
        raise ValueError('Nonfinite JSON value: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=_unique_json_object, parse_constant=bad)

def _within(folder, relative):
    if not canonical_relative(relative):
        raise ValueError('Unsafe workbook path: '+str(relative))
    base=Path(folder).resolve(); path=base
    for part in relative.split('/'):
        path=path/part
        if path.is_symlink(): raise ValueError('Symlink workbook path: '+relative)
    if not path.resolve().is_relative_to(base): raise ValueError('Path outside workbook')
    return path

def _text(value, location):
    if not isinstance(value,str): raise ValueError(location+': expected text')

def _shape(value, keys, location, optional=()):
    if not isinstance(value,dict) or not set(keys)<=value.keys() or value.keys()-set(keys)-set(optional):
        raise ValueError(location+': unexpected or missing fields')

def check_authored_html(text, folder, question_id, figures, *, problem=False):
    """Check every resource, including images disguised as backgrounds."""
    _text(text,question_id)
    parser=Parser(); parser.feed(text)
    forbidden={'script','style','iframe','object','embed','svg','link','meta','base','video','audio','source'}
    for node in parser.root.walk():
        if node.tag in forbidden: raise ValueError(question_id+': forbidden markup '+node.tag)
        if problem and node.tag=='a' and 'href' in node.attrs:
            raise ValueError(question_id+': question hyperlink may expose an answer; put review links in the solution')
        for key,value in node.attrs.items():
            if key.lower().startswith('on'): raise ValueError(question_id+': active attribute')
            if key=='style':
                style=re.sub(r'\s','',value or '').rstrip(';')
                if node.tag!='img' or style not in {'max-width:100%;height:auto','height:auto;max-width:100%'}:
                    raise ValueError(question_id+': forbidden inline style')
        for attr in ('src','href','xlink:href','srcset','data','poster'):
            if attr not in node.attrs: continue
            value=node.attrs[attr] or ''
            parts=urlsplit(value)
            if parts.scheme or parts.netloc or attr not in {'src','href'}:
                raise ValueError(question_id+': unsupported resource '+value)
            if attr=='src':
                path=strip_data(unquote(parts.path))   # 발행본은 문서 기준 `자료/..`, 저작 RUN 은 `figures/..`
                _within(folder,path)
                matching=[f for f in figures.values() if path in (f['svg'],f['png'])]
                if not matching or not any(f['question_id']==question_id for f in matching):
                    raise ValueError(question_id+': unregistered/foreign diagram '+path)
                if problem and any(f['role']!='problem' or f['answer_exposure']!='none' for f in matching):
                    raise ValueError(question_id+': solution diagram in question')
            elif parts.path:
                _within(folder,unquote(parts.path))
                if parts.query: raise ValueError(question_id+': unsupported link query')
            elif not parts.fragment:
                raise ValueError(question_id+': empty link')

def load_workbook_content(manifest, run):
    from .workbook_figures import check_redrawn_figures
    errors=check_redrawn_figures(run,manifest)
    if errors: raise ValueError('\n'.join(errors))
    registry=_strict_json(_within(run,manifest['figure_manifest']))
    figures={f['id']:f for f in registry['figures']}
    result=[]
    for p in manifest['problems']:
        if p['status']!='included': continue
        obj=_strict_json(_within(run,p['workbook_fragment']))
        _shape(obj,AUTHOR_KEYS,p['id'])
        for field in ('original','conditions','ask'):
            check_authored_html(obj[field],run,p['id'],figures,problem=True)
            check_work_tables(obj[field],p['id'])
        if not isinstance(obj['problem_figures'],list) or any(not isinstance(f,str) for f in obj['problem_figures']):
            raise ValueError(p['id']+': invalid problem figures')
        if len(set(obj['problem_figures']))!=len(obj['problem_figures']):
            raise ValueError(p['id']+': duplicate problem figure')
        projected=[]
        for ident in obj['problem_figures']:
            f=figures.get(ident)
            if not f or f['question_id']!=p['id'] or f['role']!='problem' or f['answer_exposure']!='none':
                raise ValueError(p['id']+': unsafe/foreign problem figure '+ident)
            projected.append(dict(src=f['png'],w_mm=f['w_mm'],h_mm=f['h_mm']))
        if not isinstance(obj['hints'],list): raise ValueError(p['id']+': hints must be a list')
        for hint in obj['hints']:
            _shape(hint,{'label','html'},p['id']+'.hint',optional={'formula'})
            check_authored_html(hint['label'],run,p['id'],figures,problem=True)
            check_authored_html(hint['html'],run,p['id'],figures,problem=True)
            if 'formula' in hint:
                values=hint['formula'] if isinstance(hint['formula'],list) else [hint['formula']]
                if not values or any(not isinstance(v,str) for v in values): raise ValueError(p['id']+': invalid formula')
        _shape(obj['solution'],{'steps','answer'},p['id']+'.solution')
        if not isinstance(obj['solution']['steps'],list): raise ValueError(p['id']+': steps must be a list')
        for step in obj['solution']['steps']:
            _shape(step,{'label','html'},p['id']+'.step')
            check_authored_html(step['label'],run,p['id'],figures)
            check_authored_html(step['html'],run,p['id'],figures)
        check_authored_html(obj['solution']['answer'],run,p['id'],figures)
        if not obj['solution']['steps'] and not obj['solution']['answer'].strip():
            raise ValueError(p['id']+': missing solution')
        if not isinstance(obj['notes'],list) or any(not isinstance(n,str) for n in obj['notes']):
            raise ValueError(p['id']+': notes must be text list')
        row=deepcopy(obj)
        row.update(id=p['id'],title=p.get('title',p['id']),number=str(len(result)+1),
            kind=KINDS[p['kind']],section=f"실험 {manifest['experiment']} · {STATES[p['answer_status']]}",
            figures=projected,topics=deepcopy(p['topics']),sources=deepcopy(p['sources']),
            answer_status=p['answer_status'],given_answer=p.get('given_answer'),derived_answer=p.get('derived_answer'))
        result.append(row)
    return result

def build_workbook_data(manifest, content, mode):
    if mode not in {'problems','answers'}: raise ValueError('Unknown workbook mode: '+str(mode))
    entries=[]
    for row in content:
        entry=dict(id=row['id'],kind=row['kind'],number=row['number'],title=row['title'],
            section=row['section'],book_page=None,difficulty=None,sol=None,original_lang='ko',depends_on=[],
            html={key:link_data(row[key]) for key in ('original','conditions','ask')},
            figures=[dict(f,src=data_url(f['src'])) for f in row['figures']],
            hints=[{k:(link_data(v) if k in ('label','html') else v) for k,v in h.items()} for h in row['hints']])
        if mode=='answers':
            solution=dict(steps=[dict(label=link_data(s['label']),html=link_data(s['html'])) for s in row['solution']['steps']],
                          answer=link_data(row['solution']['answer']))
            entry['solution']=solution
        entries.append(entry)
    label='기출 문제' if mode=='problems' else '기출 풀이'
    return dict(meta=dict(mode=mode,title=f"실험 {manifest['experiment']} · {label}",chapter=0,total=len(entries)),problems=entries)
