"""Do not show bank images with exposed/unknown answers as question material."""
from pathlib import Path
import re
from urllib.parse import unquote,urlsplit
from .bank_index import build_authoring_index
from .manifest import output_names
from .question_bank import load_question_bank
from .question_bank_sources import _evidence_path
from .sources import file_sha256
from .html2md import Parser,Node

def check_bank_problem_assets(folder,manifest):
    if 'bank_import' not in manifest:return []
    folder=Path(folder);errors=[]
    try:
        binding=manifest['bank_import']
        bank=load_question_bank(_evidence_path(folder,binding['snapshot_path']))
        index=build_authoring_index(bank,binding['sha256'])
        allowed={q['question_id']:set(q['safe_problem_asset_ids']) for q in index['questions']}
        by_hash={}
        for asset in bank['assets']:by_hash.setdefault(asset['sha256'],[]).append(asset)
        parser=Parser()
        parser.feed((folder/output_names(manifest['experiment'])['review_html']).read_text(encoding='utf-8'))
        cache={}
        def resource(url,ident,evidence_section):
            try:
                parts=urlsplit(url)
                if parts.scheme or parts.netloc:raise ValueError('Nonlocal bank question resource')
                target=_evidence_path(folder,unquote(parts.path))
                if not target.is_file():raise ValueError('Missing resource')
                digest=cache.get(target)
                if digest is None:digest=cache[target]=file_sha256(target)
                matching=by_hash.get(digest,[])
                if evidence_section or not matching:return
                if any(a['role']!='problem' or a['answer_exposure']!='none' for a in matching):
                    raise ValueError('Source image exposes or may expose answers')
                if not any(a['id'] in allowed.get(ident,set()) for a in matching):
                    raise ValueError('Source image belongs to another bank question')
            except (ValueError,OSError) as exc:errors.append(ident+': '+str(exc)+' — '+url)
        def visit(node,ident,in_problem=False,in_evidence=False):
            if not isinstance(node,Node):return
            classes=node.attrs.get('class','').split()
            in_problem=in_problem or 'problem' in classes
            in_evidence=in_evidence or (node.tag=='details' and bool({'original','solution'}&set(classes)))
            safe_section=in_evidence and not in_problem
            attrs=[]
            if node.tag in {'img','source','embed'}:attrs=['src']
            elif node.tag=='image':attrs=['href','xlink:href']
            elif node.tag=='object':attrs=['data']
            for attr in attrs:
                if node.attrs.get(attr):resource(node.attrs[attr],ident,safe_section)
            style=node.attrs.get('style','')
            for url in re.findall(r'url\(\s*[\x22\x27]?([^\)\x22\x27]+)',style,re.I):
                resource(url.strip(),ident,safe_section)
            for c in node.children:visit(c,ident,in_problem,in_evidence)
        for p in manifest['problems']:
            if 'bank_question_id' not in p or p['status']!='included':continue
            cards=[n for n in parser.root.walk() if n.tag=='article' and n.attrs.get('id')==p['id']]
            if len(cards)!=1:errors.append(p['id']+': missing/duplicate bank card');continue
            problems=[n for n in cards[0].walk() if n.tag=='div' and 'problem' in n.attrs.get('class','').split()]
            if len(problems)!=1:errors.append(p['id']+': bank card needs exactly one div.problem')
            visit(cards[0],p['id'])
    except (ValueError,OSError,KeyError,TypeError) as exc:
        errors.append('Bank asset inspection: '+str(exc))
    return errors
