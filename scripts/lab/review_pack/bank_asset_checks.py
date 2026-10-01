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
    if manifest.get('review_presentation_version')==2:
        from .workbook_checks import check_workbook_pack
        return check_workbook_pack(folder,manifest)
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
                if not parts.path and parts.fragment:return
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
        def css_resources(text,ident,evidence_section):
            if re.search(r'@import\b|(?:-webkit-)?image-set\s*\(',text,re.I):
                errors.append(ident+': CSS imports/image-set unsupported in bank question content')
            for url in re.findall(r'url\(\s*[\x22\x27]?([^\)\x22\x27]+)',text,re.I):
                resource(url.strip(),ident,evidence_section)
        def srcset_urls(value):
            # Candidate URLs end at whitespace; descriptor lists end at a comma.
            remaining=value.strip()
            while remaining:
                remaining=remaining.lstrip(' ,\t\n\r')
                if not remaining:break
                pieces=remaining.split(None,1)
                url=pieces[0];remaining=pieces[1] if len(pieces)>1 else ''
                if url.endswith(','):
                    yield url.rstrip(',')
                else:
                    yield url
                    remaining=remaining.partition(',')[2]
        def visit(node,ident,in_problem=False,in_evidence=False):
            if not isinstance(node,Node):return
            classes=node.attrs.get('class','').split()
            in_problem=in_problem or 'problem' in classes
            if node.tag=='details':
                in_evidence=bool({'original','solution'}&set(classes)) and 'open' not in node.attrs
            # Summaries and a details container's own background are visible when closed.
            if node.tag=='summary':in_evidence=False
            safe_section=in_evidence and not in_problem
            resource_section=safe_section and node.tag!='details'
            attrs=[]
            if node.tag in {'img','source','embed'}:attrs=['src']
            elif node.tag=='image':attrs=['href','xlink:href']
            elif node.tag=='object':attrs=['data']
            for attr in attrs:
                if node.attrs.get(attr):resource(node.attrs[attr],ident,resource_section)
            if node.tag in {'img','source'} and node.attrs.get('srcset'):
                for url in srcset_urls(node.attrs['srcset']):resource(url,ident,resource_section)
            css_resources(node.attrs.get('style',''),ident,resource_section)
            for c in node.children:visit(c,ident,in_problem,in_evidence)
        # A style block applies outside its DOM parent, even under closed details.
        for n in parser.root.walk():
            if n.tag=='style':
                text=''.join(c for c in n.children if isinstance(c,str))
                css_resources(text,'$.bank_styles',False)
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
