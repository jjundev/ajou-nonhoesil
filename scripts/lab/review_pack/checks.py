"""Mechanical checks do not establish scientific correctness."""
from pathlib import Path
from itertools import product
from collections import Counter
from urllib.parse import unquote,urlsplit
import re
from scripts.lab.boolexpr import variables,eval_boolean
from .manifest import load_manifest,output_names,data_dir,DATA
from .html2md import Parser,check_md
from .bank_provenance import check_bank_import
from .bank_asset_checks import check_bank_problem_assets
from .note_metadata import check_note_metadata
from .navigation import check_navigation

def boolean_equivalent(left,right):
    names=sorted(set(variables(left))|set(variables(right)))
    if len(names)>8:raise ValueError('At most 8 inputs for exhaustive verification')
    return all(eval_boolean(left,dict(zip(names,b)))==eval_boolean(right,dict(zip(names,b))) for b in product((0,1),repeat=len(names)))

def check_pack(folder):
    folder=Path(folder)
    if not (folder/DATA).is_dir():return ['Missing data folder: '+DATA+'/']
    try:m=load_manifest(folder/DATA/'manifest.json')
    except (ValueError,OSError) as e:return [str(e)]
    workbook=m.get('review_presentation_version')==2
    names=output_names(m['experiment'],review_presentation_version=m.get('review_presentation_version'));errors=[];trees={}
    # 저장 규칙: 팩의 자료는 자료/ 안에 둔다. 루트에 남은 옛 위치(assets·evidence·figures·JSON)를 막는다.
    # 사용자가 따로 둔 파일(publish 가 보존한다)은 건드리지 않는다.
    errors+=['Pack data outside '+DATA+'/: '+n for n in ('assets','evidence','figures','manifest.json','authoring-index.json') if (folder/n).exists()]
    bank_errors=check_bank_import(folder,m)
    errors.extend(bank_errors)
    if not bank_errors:
        errors.extend(check_bank_problem_assets(folder,m))
    for key in (('note_html',) if workbook else ('note_html','review_html')):
        path=folder/names[key]
        if not path.exists():errors.append('Missing page: '+str(path));continue
        text=path.read_text(encoding='utf-8')
        if '{{' in text:errors.append('Unreplaced placeholder: '+path.name)
        parser=Parser();parser.feed(text);trees[key]=parser.root
        errors.extend(check_navigation(parser.root,names[key]))
        ids=[n.attrs['id'] for n in parser.root.walk() if n.attrs.get('id')]
        errors += ['duplicate ID: '+i for i,n in Counter(ids).items() if n>1]
        try:errors+=check_md(path,path.with_suffix('.md'))
        except (ValueError,OSError) as e:errors.append(str(e))
    for key,tree in trees.items():
        if key=='note_html' and (folder/names['note_md']).is_file():
            errors+=check_note_metadata(m,(folder/names[key]).read_text(encoding='utf-8'),(folder/names['note_md']).read_text(encoding='utf-8'))
        for node in tree.walk():
            attr='src' if node.tag in {'img','script','source'} else 'href' if node.tag in {'a','link'} else None
            value=node.attrs.get(attr) if attr else None
            if not value:continue
            remote=bool(urlsplit(value).scheme or value.startswith('//'))
            if remote:
                if node.tag!='a':errors.append('remote resource: '+value)
                continue
            part,_,frag=unquote(value).partition('#')
            if part.startswith('../../') and node.tag=='a':continue
            dest=folder/part if part else folder/names[key]
            if not dest.is_file():errors.append('Missing resource: '+value);continue
            if frag and dest.suffix=='.html':
                if workbook and dest.name in (names['review_html'],names['question_html']):
                    from .workbook_render import read_workbook_payload
                    try:
                        if frag not in {p['id'] for p in read_workbook_payload(dest)['problems']}: errors.append('Missing workbook anchor: '+value)
                    except (ValueError,OSError,KeyError,TypeError) as exc: errors.append(str(exc))
                    continue
                other=Parser();other.feed(dest.read_text(encoding='utf-8'))
                if not any(n.attrs.get('id')==frag for n in other.root.walk()):errors.append('Missing anchor: '+value)
    for row in m['topics']+[p for p in m['problems'] if p['status']=='included']:
        kind='note_html' if row in m['topics'] else 'review_html'
        if kind not in trees:continue
        nodes=[n for n in trees[kind].walk() if n.tag=='article' and n.attrs.get('id')==row['id']]
        if not nodes:errors.append('Missing content: '+row['id']);continue
        if kind=='review_html':
            details=[n for n in nodes[0].walk() if n.tag=='details']
            if len(details)<2:errors.append(row['id']+': missing hint/solution')
            for topic in row['topics']:
                if not any(n.tag=='a' and unquote(n.attrs.get('href','')).endswith('#'+topic) for n in nodes[0].walk()):errors.append(row['id']+': missing concept link '+topic)
    for css in (folder/DATA/'assets').rglob('*.css'):
        text=css.read_text(encoding='utf-8')
        for url in re.findall(r'url\([\x22\x27]?([^\)\x22\x27]+)',text):
            if url.startswith('data:'):continue
            if urlsplit(url).scheme or url.startswith('//'):errors.append('remote CSS resource: '+url)
            elif not (css.parent/unquote(url)).is_file():errors.append('Missing CSS resource: '+url)
        if re.search(r'@import\s+[\x22\x27]https?:',text):errors.append('remote CSS import: '+str(css))
    from .explanation_checks import check_explanations
    errors.extend(check_explanations(folder,m))
    return errors
