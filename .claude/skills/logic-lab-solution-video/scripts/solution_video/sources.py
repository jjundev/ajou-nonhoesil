from pathlib import Path
import calendar,copy,re,shutil,unicodedata
from .contracts import InputError
from .util import file_hash,digest,write
from .page_layout import page_layout

def _dates(selector):
    dates=selector.split('-')
    def valid(s):
        return len(s)==4 and s.isdigit() and 1<=int(s[:2])<=12 and 1<=int(s[2:])<=calendar.monthrange(2024,int(s[:2]))[1]
    if len(dates)>2 or not all(valid(d) for d in dates) or len(dates)==2 and dates[0]>dates[1]: raise InputError('invalid date selector: '+selector)
    return dates[0],dates[-1]
def _norm(s): return unicodedata.normalize('NFC',s)
def _pages(pdf,ids):
    import fitz
    found={}
    with fitz.open(pdf) as doc:
        for idx,pg in enumerate(doc):
            bottom=page_layout(pg.rect.width,pg.rect.height)['header_bottom']-1
            header=_norm(pg.get_text(clip=fitz.Rect(0,0,pg.rect.width,bottom)))
            badge=_norm(pg.get_text(clip=fitz.Rect(0,0,140,bottom))).splitlines()[0] if header else ''
            # Workbook header shows kind and number separately, not its compact ID.
            candidates=[]
            for pid in ids:
                n=_norm(pid)
                if n==badge: candidates.append(pid); continue
                if re.fullmatch(r'[EPX]\d+\.\d+',pid):
                    kind={'E':'예제','P':'장말문제','X':'연습문제'}[pid[0]]
                    number=re.search(r'(\d+)\.(\d+)',badge)
                    chapter,problem=map(int,pid[1:].split('.'))
                    if badge.startswith(kind) and number and tuple(map(int,number.groups()))==(chapter,problem): candidates.append(pid)
                elif re.fullmatch(r'\d{4}-\d_.*-Q\d+',n):
                    year,term=n[:4],n[5]; q=n.rsplit('Q',1)[1]
                    exam_badge=re.match(r'^기출\s*(\d+)',badge)
                    if exam_badge and int(exam_badge[1])==int(q) and year+'-'+term in header and n.split('_',1)[1].split('-Q',1)[0] in header:
                        matches=[x for x in ids if not re.fullmatch(r'[EPX]\d+\.\d+',x) and x.rsplit('Q',1)[-1]==q]
                        if len([x for x in matches if x.rsplit('-Q',1)[0].replace('_',' ') in header.replace('고사','')])>1: raise InputError('ambiguous exam year/term badge; author explicit pair')
                        candidates.append(pid)
            if len(candidates)>1: raise InputError('ambiguous header: '+str(candidates))
            if candidates:
                pid=candidates[0]
                if pid in found: raise InputError('duplicate page for '+pid)
                found[pid]=dict(snapshot=str(pdf.resolve()),page_index=idx,width_pt=pg.rect.width,height_pt=pg.rect.height)
    return found

def _conditions(ref):
    import fitz
    with fitz.open(ref['snapshot']) as d:
        p=d[ref['page_index']]
        # The gray condition panel can widen during fitting; use its actual PDF rectangle.
        panels=[draw['rect'] for draw in p.get_drawings() if draw.get('fill') and
            max(abs(a-b) for a,b in zip(draw['fill'],(246/255,246/255,243/255)))<.002]
        clip=max(panels,key=lambda r:r.get_area()) if panels else fitz.Rect(22,60,286,573)
        text=p.get_text(clip=clip)
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
        if _conditions(p['problem'])!=_conditions(p['answer']): raise InputError('problem/answer conditions differ: '+p['problem_id'])
        key=_answer_hash(p['answer'])
        if p['problem_id'] in seen and seen[p['problem_id']]!=key: raise InputError('different answers for '+p['problem_id'])
        seen[p['problem_id']]=key

def discover(repo,selector,problem_ids=None,failures=None):
    repo=Path(repo); lo,hi=_dates(selector)
    selected={_norm(p) for p in problem_ids} if problem_ids else None
    root=next((p for p in repo.iterdir() if _norm(p.name)=='복습노트'),None)
    if root is None: raise InputError('review folder missing')
    dates=sorted(p for p in root.iterdir() if p.is_dir() and p.name.isdigit() and len(p.name)==4 and lo<=p.name<=hi)
    if not dates or len(selector)==4 and not any(p.name==selector for p in dates): raise InputError('selected date missing')
    def fail(pid,date,reason):
        if failures is None: raise InputError(reason)
        failures.append({'problem_id':pid,'date':date,'reason':reason})
    pairs=[];listed=set()
    for folder in dates:
        listing=folder/'problems.txt'
        if not listing.is_file(): fail(None,folder.name,'problems.txt missing');continue
        ids=[_norm(line.split('|',1)[0].strip()) for line in listing.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        listed.update(ids); ids=[pid for pid in ids if selected is None or pid in selected]
        if not ids: continue
        pdfs=list(folder.glob('*.pdf'))
        ps=[p for p in pdfs if _norm(p.stem).endswith('-문제')];ans=[p for p in pdfs if _norm(p.stem).endswith('-답안')]
        if len(ps)!=1 or len(ans)!=1:
            for pid in ids: fail(pid,folder.name,'missing or ambiguous PDF pair')
            continue
        # Match each selected complete ID independently; unrelated damaged pages cannot stop it.
        for pid in ids:
            try:
                pp,aa=_pages(ps[0],[pid]),_pages(ans[0],[pid])
                if pid not in pp or pid not in aa: raise InputError('header/list mismatch: '+pid)
                m=re.fullmatch(r'([EPX])(\d+)\.(\d+)',pid)
                if m: relative=Path('교과서/마이크로전자회로')/('ch'+m[2].zfill(2))/{'E':'예제','P':'장말문제','X':'연습문제'}[m[1]]/(pid+'.md')
                else:
                    exam,q=pid.rsplit('-Q',1);relative=Path('from_the_past/md')/exam/('Q'+q+'.md')
                target=repo
                for component in relative.parts:
                    target=next((x for x in target.iterdir() if _norm(x.name)==_norm(component)),target/component) if target.is_dir() else target/component
                pair=dict(problem_id=pid,problem=pp[pid],answer=aa[pid],md_snapshot=str(target.resolve()) if target.is_file() else None,dates=[folder.name])
                validate_pairs([pair]);pairs.append(pair)
            except (InputError,OSError,ValueError,RuntimeError) as ex: fail(pid,folder.name,str(ex))
    if selected and selected-listed: raise InputError('problem IDs outside range: '+str(selected-listed))
    unique={}; invalid=set()
    for p in pairs:
        pid=p['problem_id']; correspondence={k:copy.deepcopy(p[k]) for k in ['problem','answer','md_snapshot']};correspondence['date']=p['dates'][0]
        if pid in invalid: continue
        if pid in unique:
            if _answer_hash(unique[pid]['answer'])!=_answer_hash(p['answer']):
                fail(pid,p['dates'][0],'different answers for '+pid);invalid.add(pid);unique.pop(pid);continue
            unique[pid]['dates']+=p['dates'];unique[pid]['sources'].append(correspondence)
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
    import fitz,sys
    write(batch/'source/inputs.json',{'files':provenance,'pairs':result,'tools':{'python':sys.version,'pymupdf':fitz.VersionBind}}); return result
