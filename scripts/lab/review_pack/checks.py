"""Mechanical checks do not establish scientific correctness."""
from pathlib import Path
from itertools import product
from collections import Counter
from urllib.parse import unquote,urlsplit
import re
from scripts.lab.boolexpr import variables,eval_boolean
from .manifest import load_manifest,output_names
from .html2md import Parser,check_md

def boolean_equivalent(left,right):
    names=sorted(set(variables(left))|set(variables(right)))
    if len(names)>8:raise ValueError('At most 8 inputs for exhaustive verification')
    return all(eval_boolean(left,dict(zip(names,b)))==eval_boolean(right,dict(zip(names,b))) for b in product((0,1),repeat=len(names)))

def check_pack(folder):
    folder=Path(folder)
    try:m=load_manifest(folder/'manifest.json')
    except (ValueError,OSError) as e:return [str(e)]
    names=output_names(m['experiment']);errors=[];trees={}
    for key in ('note_html','review_html'):
        path=folder/names[key]
        if not path.exists():errors.append('Missing page: '+str(path));continue
        text=path.read_text(encoding='utf-8')
        if '{{' in text:errors.append('Unreplaced placeholder: '+path.name)
        parser=Parser();parser.feed(text);trees[key]=parser.root
        ids=[n.attrs['id'] for n in parser.root.walk() if n.attrs.get('id')]
        errors += ['duplicate ID: '+i for i,n in Counter(ids).items() if n>1]
        try:errors+=check_md(path,path.with_suffix('.md'))
        except (ValueError,OSError) as e:errors.append(str(e))
    for key,tree in trees.items():
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
    for css in (folder/'assets').rglob('*.css'):
        text=css.read_text(encoding='utf-8')
        for url in re.findall(r'url\([\x22\x27]?([^\)\x22\x27]+)',text):
            if url.startswith('data:'):continue
            if urlsplit(url).scheme or url.startswith('//'):errors.append('remote CSS resource: '+url)
            elif not (css.parent/unquote(url)).is_file():errors.append('Missing CSS resource: '+url)
        if re.search(r'@import\s+[\x22\x27]https?:',text):errors.append('remote CSS import: '+str(css))
    return errors
