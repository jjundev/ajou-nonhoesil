from pathlib import Path
import copy,json,re,shutil,unicodedata
from .contracts import InputError
from .util import file_hash,digest,write
from .page_layout import page_layout

KINDS={'past':'기출','predicted':'예상문제','unknown':'출처 미확인','practice':'연습문제'}
def parse_selector(selector):
    m=re.fullmatch(r'(?:실험)?(\d{1,2})(?:-(?:실험)?(\d{1,2}))?',_norm(selector or '').strip())
    lo,hi=(int(m[1]),int(m[2] or m[1])) if m else (0,0)
    if not (1<=lo<=hi<=10): raise InputError('invalid experiment selector: '+str(selector))
    return ['실험%02d'%n for n in range(lo,hi+1)]
def _norm(s): return unicodedata.normalize('NFC',s)
def _child(folder,name):
    return next((x for x in folder.iterdir() if _norm(x.name)==name),None) if folder.is_dir() else None
def _squash(s): return re.sub(r'\s+','',_norm(s))
def _pages(pdf,problems):
    """problems: [(id,label,title)]. A page belongs to an ID when its badge equals the label and the header carries the title."""
    import fitz
    found={}
    with fitz.open(pdf) as doc:
        for idx,pg in enumerate(doc):
            bottom=page_layout(pg.rect.width,pg.rect.height)['header_bottom']-1
            header=_norm(pg.get_text(clip=fitz.Rect(0,0,pg.rect.width,bottom)))
            lines=_norm(pg.get_text(clip=fitz.Rect(0,0,140,bottom))).splitlines() if header else []
            badge=lines[0].strip() if lines else ''
            for pid,label,title in problems:
                if badge==label and _squash(title) in _squash(header):
                    if pid in found: raise InputError('duplicate page for '+pid)
                    found[pid]=dict(snapshot=str(pdf.resolve()),page_index=idx,width_pt=pg.rect.width,height_pt=pg.rect.height)
    return found

def _conditions(ref,with_work=False):
    """Condition panel text. The workbook moves the problem's own table from the problem page's work area into the
    answer page's panel (with a '조건' heading), so the problem side also counts its work-area text, Hint column excluded."""
    import fitz
    with fitz.open(ref['snapshot']) as d:
        p=d[ref['page_index']]
        # The gray condition panel can widen during fitting; use its actual PDF rectangle.
        panels=[draw['rect'] for draw in p.get_drawings() if draw.get('fill') and
            max(abs(a-b) for a,b in zip(draw['fill'],(246/255,246/255,243/255)))<.002]
        clip=max(panels,key=lambda r:r.get_area()) if panels else fitz.Rect(22,60,286,573)
        text=p.get_text(clip=clip)
        if with_work:
            layout=page_layout(p.rect.width,p.rect.height)
            hint=[w[0] for w in p.get_text('words') if w[4]=='Hint' and w[0]>clip.x1]
            text+=p.get_text(clip=fitz.Rect(clip.x1,layout['header_bottom'],min(hint)-2 if hint else p.rect.width,layout['body_bottom']))
    return re.sub(r'\s+','',_norm(text))
def _answer_hash(ref):
    import fitz
    with fitz.open(ref['snapshot']) as d:
        # Workbook content band excludes the fixed heading/pagination/footer only.
        pg=d[ref['page_index']];layout=page_layout(pg.rect.width,pg.rect.height)
        clip=fitz.Rect(0,layout['header_bottom'],pg.rect.width,layout['body_bottom'])
        pix=pg.get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,alpha=False)
        import hashlib
        return hashlib.sha256(pix.samples).hexdigest()
def validate_pairs(pairs):
    seen={}
    for p in pairs:
        same=lambda s:sorted(s.replace('조건',''))
        if same(_conditions(p['problem'],True))!=same(_conditions(p['answer'])): raise InputError('problem/answer conditions differ: '+p['problem_id'])
        key=_answer_hash(p['answer'])
        if p['problem_id'] in seen and seen[p['problem_id']]!=key: raise InputError('different answers for '+p['problem_id'])
        seen[p['problem_id']]=key

def discover(repo,selector,problem_ids=None,failures=None):
    repo=Path(repo); experiments=parse_selector(selector)
    selected={_norm(p).strip() for p in problem_ids} if problem_ids else None
    root=_child(repo,'복습노트')
    if root is None: raise InputError('review folder missing')
    def fail(pid,experiment,reason):
        if failures is None: raise InputError(reason)
        failures.append({'problem_id':pid,'experiment':experiment,'reason':reason})
    pairs=[];listed=set()
    for name in experiments:
        folder=_child(root,name); manifest=_child(folder,'manifest.json') if folder else None
        if manifest is None: fail(None,name,'experiment pack missing: '+name);continue
        included=[p for p in json.loads(manifest.read_text(encoding='utf-8'))['problems'] if p.get('status')=='included']
        # Labels come from the current manifest order every time; the PDF badge must agree.
        problems=[(_norm(p['id']),KINDS[p['kind']]+str(n),_norm(p['title'])) for n,p in enumerate(included,1)]
        for pid,label,_ in problems: listed.update([pid,label])
        problems=[p for p in problems if selected is None or p[0] in selected or p[1] in selected]
        if not problems: continue
        pdfs=[p for p in folder.iterdir() if p.suffix.lower()=='.pdf']
        ps=[p for p in pdfs if _norm(p.name).endswith('_기출문제.pdf')];ans=[p for p in pdfs if _norm(p.name).endswith('_기출풀이.pdf')]
        if len(ps)!=1 or len(ans)!=1:
            for pid,_,_ in problems: fail(pid,name,'missing or ambiguous PDF pair')
            continue
        md=_child(folder,name+'_기출풀이.md'); solutions=_child(_child(folder,'figures') or folder,'solutions')
        # Match each selected ID independently; unrelated damaged pages cannot stop it.
        for pid,label,title in problems:
            try:
                pp,aa=_pages(ps[0],[(pid,label,title)]),_pages(ans[0],[(pid,label,title)])
                if pid not in pp or pid not in aa: raise InputError('header/list mismatch: '+pid)
                figures=sorted(str(x.resolve()) for x in (solutions.iterdir() if solutions else []) if re.fullmatch(re.escape(pid)+r'-solution-\d{2}\.png',_norm(x.name)))
                pair=dict(problem_id=pid,label=label,title=title,problem=pp[pid],answer=aa[pid],md_snapshot=str(md.resolve()) if md and md.is_file() else None,experiments=[name],figure_refs=figures)
                validate_pairs([pair]);pairs.append(pair)
            except (InputError,OSError,ValueError,RuntimeError) as ex: fail(pid,name,str(ex))
    if selected and selected-listed: raise InputError('problem IDs outside range: '+str(sorted(selected-listed)))
    unique={}; invalid=set()
    for p in pairs:
        pid=p['problem_id']; correspondence={k:copy.deepcopy(p[k]) for k in ['problem','answer','md_snapshot']};correspondence['experiment']=p['experiments'][0]
        if pid in invalid: continue
        if pid in unique:
            if _answer_hash(unique[pid]['answer'])!=_answer_hash(p['answer']):
                fail(pid,p['experiments'][0],'different answers for '+pid);invalid.add(pid);unique.pop(pid);continue
            unique[pid]['experiments']+=p['experiments'];unique[pid]['sources'].append(correspondence)
        else: p['sources']=[correspondence];unique[pid]=p
    failed_ids={f['problem_id'] for f in failures} if failures is not None else set()
    return [p for pid,p in unique.items() if pid not in failed_ids]

def freeze_sources(pairs,batch):
    batch=Path(batch); dest=batch/'source/snapshots'; dest.mkdir(parents=True,exist_ok=True); result=copy.deepcopy(pairs); provenance={}
    def freeze(path):
        src=Path(path); sha=file_hash(src); target=dest/(sha+src.suffix); shutil.copyfile(src,target) if not target.exists() else None
        rel=target.relative_to(batch).as_posix(); provenance[rel]={'original':str(src.resolve()),'sha256':sha}; return rel
    for p in result:
        for source in p.get('sources',[]):
            for role in ['problem','answer']: source[role]['snapshot']=freeze(source[role]['snapshot'])
            if source['md_snapshot']: source['md_snapshot']=freeze(source['md_snapshot'])
        for role in ['problem','answer']: p[role]['snapshot']=freeze(p[role]['snapshot'])
        if p['md_snapshot']: p['md_snapshot']=freeze(p['md_snapshot'])
        p['figure_refs']=[freeze(f) for f in p.get('figure_refs',[])]
    import fitz,sys
    write(batch/'source/inputs.json',{'files':provenance,'pairs':result,'tools':{'python':sys.version,'pymupdf':fitz.VersionBind}}); return result
