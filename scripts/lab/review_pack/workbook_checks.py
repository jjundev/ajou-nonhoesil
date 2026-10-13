"""Validate dynamic workbook data without mistaking scripts for empty content."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
from .manifest import output_names,data_dir,strip_data,DATA
from .workbook_content import KINDS,STATES,_strict_json,_within,check_authored_html
from .workbook_figures import check_redrawn_figures
from .workbook_render import read_workbook_payload,render_workbook_html
from .workbook_md import check_workbook_md,_html_fields
from .html2md import Parser

ENTRY_KEYS={'id','kind','number','title','section','book_page','difficulty','sol','original_lang','depends_on','html','figures','hints'}

def check_workbook_pack(folder,manifest):
    folder=Path(folder);data_folder=data_dir(folder);errors=check_redrawn_figures(folder,manifest)
    if errors: return errors
    try:
        names=output_names(manifest['experiment'],review_presentation_version=2)
        figures={f['id']:f for f in _strict_json(_within(data_folder,manifest['figure_manifest']))['figures']}
        selected=[p for p in manifest['problems'] if p['status']=='included']
        expected=[p['id'] for p in selected];sheets={}
        for key,mode in [('question','problems'),('review','answers')]:
            path=folder/names[key+'_html'];data=read_workbook_payload(path);sheets[key]=data
            if not isinstance(data,dict) or set(data)!={'meta','problems'}: raise ValueError('Invalid workbook payload fields')
            meta=data['meta']
            if not isinstance(meta,dict) or set(meta)!={'mode','title','chapter','total'} or meta['mode']!=mode or type(meta['total']) is not int or meta['total']!=len(expected):
                raise ValueError(key+': invalid workbook metadata')
            if not isinstance(data['problems'],list) or [p['id'] for p in data['problems']]!=expected:
                raise ValueError(key+': workbook question order/identity mismatch')
            if path.read_text(encoding='utf-8')!=render_workbook_html(data,data_folder/'assets'):
                raise ValueError(key+': content outside original template/data slot')
            for n,(p,original) in enumerate(zip(data['problems'],selected),1):
                if set(p)!=(ENTRY_KEYS|({'solution'} if mode=='answers' else set())):
                    raise ValueError(p['id']+': unexpected workbook entry fields')
                if p['number']!=str(n) or p['kind']!=KINDS[original['kind']] or p['title']!=original.get('title',original['id']) or STATES[original['answer_status']] not in p['section']:
                    raise ValueError(p['id']+': classification/number/status mismatch')
                if not isinstance(p['html'],dict) or set(p['html'])!={'original','conditions','ask'}:
                    raise ValueError(p['id']+': invalid question HTML fields')
                for fragment in p['html'].values(): check_authored_html(fragment,data_folder,p['id'],figures,problem=True)
                for f in p['figures']:
                    if not isinstance(f,dict) or set(f)!={'src','w_mm','h_mm'}: raise ValueError(p['id']+': invalid question figure')
                    match=[r for r in figures.values() if f['src'].startswith(DATA+'/') and r['png']==strip_data(f['src']) and r['question_id']==p['id'] and r['role']=='problem' and r['answer_exposure']=='none']
                    if len(match)!=1 or f['w_mm']!=match[0]['w_mm'] or f['h_mm']!=match[0]['h_mm']: raise ValueError(p['id']+': unsafe/unregistered question figure')
                for hint in p['hints']:
                    if not isinstance(hint,dict) or not {'label','html'}<=hint.keys() or hint.keys()-{'label','html','formula'}: raise ValueError(p['id']+': invalid hint')
                    for field in ('label','html'): check_authored_html(hint[field],data_folder,p['id'],figures,problem=True)
                if mode=='answers':
                    sol=p['solution']
                    if not isinstance(sol,dict) or set(sol)!={'steps','answer'} or not isinstance(sol['steps'],list) or not isinstance(sol['answer'],str) or (not sol['steps'] and not sol['answer'].strip()): raise ValueError(p['id']+': missing/invalid solution')
                    for step in sol['steps']:
                        if not isinstance(step,dict) or set(step)!={'label','html'}: raise ValueError(p['id']+': invalid solution step')
                        for field in ('label','html'): check_authored_html(step[field],data_folder,p['id'],figures)
                    check_authored_html(sol['answer'],data_folder,p['id'],figures)
                for fragment in _html_fields(p):
                    parser=Parser();parser.feed(fragment)
                    for node in parser.root.walk():
                        if node.tag not in {'img','a'}: continue
                        url=node.attrs.get('src' if node.tag=='img' else 'href','');parts=urlsplit(url)
                        target=_within(folder,unquote(parts.path)) if parts.path else path
                        if not target.is_file(): errors.append(p['id']+': missing workbook resource '+url)
                        elif parts.fragment and target.suffix in {'.md','.html'}:
                            if target.suffix=='.md':
                                valid='<a id="'+unquote(parts.fragment)+'"></a>' in target.read_text(encoding='utf-8')
                            else:
                                tree=Parser();tree.feed(target.read_text(encoding='utf-8'))
                                valid=any(n.attrs.get('id')==unquote(parts.fragment) for n in tree.root.walk())
                            if not valid: errors.append(p['id']+': missing workbook resource anchor '+url)
            errors.extend(check_workbook_md(data,manifest,folder/DATA/names[key+'_md']))
        for q,a in zip(sheets['question']['problems'],sheets['review']['problems']):
            for field in ENTRY_KEYS:
                if q[field]!=a[field]: errors.append(q['id']+': question/answer '+field+' mismatch')
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:
        errors.append('Workbook inspection: '+str(exc))
    return errors
