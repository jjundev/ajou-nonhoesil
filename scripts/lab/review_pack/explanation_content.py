"""Authored teaching fragments matched to the existing question projection."""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, unquote
from .html2md import Parser, Node
from .manifest import safe_relative

SECTIONS = ('understand','start','solve','verify','pitfall','retry')
CHECK_KEYS = ('source_visual','content','independent','browser')

@dataclass(frozen=True)
class Explanation:
    problem: dict
    fragment: str

def within(root: Path, relative: str) -> Path:
    if not safe_relative(relative):
        raise ValueError('Unsafe explanation path: '+str(relative))
    root=Path(root).resolve(); path=root
    for part in Path(relative).parts:
        path=path/part
        if path.is_symlink(): raise ValueError('Symlink explanation path: '+relative)
    if not path.resolve().is_relative_to(root): raise ValueError('Explanation outside root')
    return path

def text(node):
    return ''.join(c if isinstance(c,str) else text(c) for c in node.children)

def validate_fragment(fragment: str, ident: str, state: str) -> None:
    parser=Parser();parser.feed(fragment);nodes=list(parser.root.walk())
    for n in nodes:
        if n.tag in {'script','style','iframe','object','embed','base','link','meta','article','h1','details','input','button','select'}:
            raise ValueError(ident+': forbidden explanation markup '+n.tag)
        for key,value in n.attrs.items():
            if key.lower().startswith('on') or key in {'style','srcset'}:
                raise ValueError(ident+': active explanation attribute '+key)
            if key in {'src','href','xlink:href'}:
                parts=urlsplit(unquote(value or ''))
                if parts.scheme or parts.netloc or (parts.path and not safe_relative(parts.path)):
                    raise ValueError(ident+': unsafe explanation resource '+str(value))
    for key in SECTIONS:
        found=[n for n in nodes if n.attrs.get('data-explanation')==key]
        if len(found)!=1 or not text(found[0]).strip(): raise ValueError(ident+': missing/empty explanation '+key)
    for cls in ('eli5','formal','warn'):
        if not any(cls in n.attrs.get('class','').split() for n in nodes): raise ValueError(ident+': missing layer '+cls)
    sums=[n for n in parser.root.children if isinstance(n,Node) and 'sum' in n.attrs.get('class','').split()]
    if len(sums)!=1 or 'hidden' not in sums[0].attrs or not text(sums[0]).strip(): raise ValueError(ident+': missing direct summary')
    retry=next(n for n in nodes if n.attrs.get('data-explanation')=='retry')
    if not 1<=sum(n.tag=='li' for n in retry.walk())<=3: raise ValueError(ident+': retry requires 1-3 items')
    if state!='verified':
        warns=' '.join(text(n) for n in nodes if 'warn' in n.attrs.get('class','').split())
        if ('답안 충돌' if state=='disputed' else '정답 미확정') not in warns: raise ValueError(ident+': missing uncertainty warning')

def load_explanations(manifest: dict, question_data: dict, author_root: Path) -> list[Explanation]:
    selected=[p for p in manifest['problems'] if p['status']=='included']
    rows=question_data.get('problems',[])
    if [p.get('id') for p in rows]!=[p['id'] for p in selected]: raise ValueError('Explanation question identity/order mismatch')
    result=[]
    for number,(p,row) in enumerate(zip(selected,rows),1):
        if row.get('number')!=str(number) or row.get('title')!=p.get('title',p['id']): raise ValueError(p['id']+': explanation number/title mismatch')
        path=within(author_root,p.get('explanation_fragment'))
        try:fragment=path.read_text(encoding='utf-8')
        except OSError as exc:raise ValueError(p['id']+': missing explanation fragment') from exc
        validate_fragment(fragment,p['id'],p['answer_status'])
        result.append(Explanation(row,fragment))
    return result
