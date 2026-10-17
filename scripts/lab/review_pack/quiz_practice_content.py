"""Check typed quiz artifacts by DOM and registered roles, not filenames."""
from urllib.parse import unquote, urlsplit
from .html2md import Parser, Node
from .manifest import strip_data


def _tree(html):
    p=Parser();p.feed(html);return p.root


def _text(node):
    return ''.join(c if isinstance(c,str) else _text(c) for c in node.children).strip()


def _has(node,cls):
    return cls in node.attrs.get('class','').split()


def check_quiz_question(problem: dict, html: dict[str,str], problem_figures: list[dict],
                        solution: dict | None, registry: dict[str,dict]) -> list[str]:
    kind=problem.get('question_type')
    if kind is None:return []
    errors=[];ident=problem['id']
    def error(message): errors.append(ident+': '+message)
    def resolve(src):
        path=strip_data(unquote(urlsplit(src).path))
        found=[f for f in registry.values() if path in (f['svg'],f['png'])]
        return found[0] if len(found)==1 else None
    def match(src,role,exposure):
        found=resolve(src)
        return found is not None and found['question_id']==ident and found['role']==role and found['answer_exposure']==exposure
    if solution is not None:
        steps=solution['steps']; required={'true_false':{'판정 근거','문장 확인'},'fill_blank':{'빈칸별 근거'},
            'short_answer':{'채점 핵심','허용 표현'},'breadboard':{'연결 기준','완성 결선도'}}.get(kind,set())
        labels={_text(_tree(s['label'])) for s in steps if _text(_tree(s['html'])) or any(n.tag=='img' for n in _tree(s['html']).walk())}
        if not steps or not required<=labels:error('missing/empty quiz solution steps: '+', '.join(sorted(required-labels)))
        answer=_text(_tree(solution['answer']))
        if not answer:error('empty quiz answer')
        if kind=='true_false' and answer!=problem['derived_answer']:error('T/F answer differs from derived_answer')
    if kind!='breadboard':return errors
    cond=_tree(html['conditions']);all_nodes=list(_tree(''.join(html.values())).walk())
    boards=[n for n in all_nodes if _has(n,'work-board')]
    cond_boards=[n for n in cond.walk() if n.tag=='div' and _has(n,'work-board')]
    imgs=[c for b in cond_boards for c in b.children if isinstance(c,Node) and c.tag=='img']
    if len(boards)!=1 or len(cond_boards)!=1 or len(imgs)!=1:
        error('exactly one conditions div.work-board > img required')
    else:
        src=imgs[0].attrs.get('src','')
        if not match(src,'problem','none'):error('unsafe/unregistered blank board')
        board=resolve(src)
        if board and any((figure:=resolve(f['src'])) is not None and figure['id']==board['id'] for f in problem_figures):
            error('blank board duplicated as schematic')
    tables=[n for n in cond.walk() if n.tag=='table' and _has(n,'chip-spec')]
    if len(tables)!=1:error('one chip-spec table required')
    else:
        table=tables[0];head=[_text(n) for n in table.walk() if n.tag=='th']
        rows=[[n for n in r.children if isinstance(n,Node) and n.tag=='td'] for r in table.walk() if r.tag=='tr']
        rows=[r for r in rows if r]
        if head!=['핀','이름','역할'] or not rows or any(len(r)!=3 or any(not _text(c) for c in r) for r in rows):error('chip-spec needs 핀/이름/역할 and populated rows')
    if not problem_figures or any(not match(f['src'],'problem','none') for f in problem_figures):error('separate registered schematic required')
    if solution is not None:
        complete=[n for s in solution['steps'] if _text(_tree(s['label']))=='완성 결선도' for n in _tree(s['html']).walk() if n.tag=='img']
        if not complete or not any(match(n.attrs.get('src',''),'solution','present') for n in complete):error('registered solution/present completed board required')
    return errors
