from pathlib import Path
import copy,json,re,shutil,unicodedata
from .contracts import InputError
from .util import file_hash,digest,write
from .page_layout import page_layout
from .input_gate import input_defects

DATA_DIR='자료'  # scripts/lab/config.PACK_DATA_DIR: manifest.json·figures/ live here since 2026-10-09
KINDS={'past':'기출','predicted':'예상문제','unknown':'출처 미확인','practice':'연습문제'}
def parse_selector(selector):
    m=re.fullmatch(r'(?:실험)?(\d{1,2})(?:-(?:실험)?(\d{1,2}))?',_norm(selector or '').strip())
    lo,hi=(int(m[1]),int(m[2] or m[1])) if m else (0,0)
    if not (1<=lo<=hi<=10): raise InputError('invalid experiment selector: '+str(selector))
    return ['실험%02d'%n for n in range(lo,hi+1)]
def _norm(s): return unicodedata.normalize('NFC',s)
def display_label(label,experiments,experiment):
    """Label shown to the user and used in the file name. Labels repeat across experiments, so a range prefixes it."""
    return label if len(experiments)==1 else experiment+' '+label
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

def _panel_clip(page):
    """The gray condition panel's actual PDF rectangle (it can widen during fitting); the layout's fixed one when none is drawn."""
    import fitz
    panels=[draw['rect'] for draw in page.get_drawings() if draw.get('fill') and
        max(abs(a-b) for a,b in zip(draw['fill'],(246/255,246/255,243/255)))<.002]
    return max(panels,key=lambda r:r.get_area()) if panels else fitz.Rect(22,60,286,573)
def _conditions(ref,with_work=False):
    """Condition panel text. The workbook moves the problem's own table from the problem page's work area into the
    answer page's panel (with a '조건' heading), so the problem side also counts its work-area text, Hint column excluded."""
    import fitz
    with fitz.open(ref['snapshot']) as d:
        p=d[ref['page_index']]
        clip=_panel_clip(p)
        text=p.get_text(clip=clip)
        if with_work:
            layout=page_layout(p.rect.width,p.rect.height)
            hint=[w[0] for w in p.get_text('words') if w[4]=='Hint' and w[0]>clip.x1]
            text+=p.get_text(clip=fitz.Rect(clip.x1,layout['header_bottom'],min(hint)-2 if hint else p.rect.width,layout['body_bottom']))
    return re.sub(r'\s+','',_norm(text))
def _tables(ref,panel=False):
    """Cell matrices (NFC, whitespace stripped, None -> '') of the tables PyMuPDF finds on the page; panel=True keeps only
    those inside the condition panel. A page whose tables cannot be read counts as having none: this check must never
    block an input the character comparison already accepted."""
    import fitz
    try:
        with fitz.open(ref['snapshot']) as d:
            page=d[ref['page_index']]; area=None
            if panel: c=_panel_clip(page); area=fitz.Rect(c.x0-2,c.y0-2,c.x1+2,c.y1+2)
            return [[[_squash(cell or '') for cell in row] for row in t.extract()]
                for t in page.find_tables().tables if area is None or area.contains(fitz.Rect(t.bbox))]
    except Exception: return []
def _table_mismatch(problem_ref,answer_ref):
    """The character multiset ignores order, so a transposed or row-swapped table slips through it. Each problem table is
    held against the tables of the same shape (same row lengths) inside the answer page's condition panel — the only place
    the problem's table is copied to, so a solution-step table cannot vouch for a damaged copy: one of them must match cell
    for cell. No table of that shape in the panel means nothing to compare, so it is skipped (a pure transpose of a
    non-square table has another shape and is not caught here; only changed characters are, by the multiset). Several
    same-shape panel tables: matching any one passes. Returns 'table <i> row <r>' (1-based, the first row that differs from
    the closest candidate) or None."""
    answers=_tables(answer_ref,panel=True)
    for i,table in enumerate(_tables(problem_ref),1):
        shape=[len(row) for row in table]; same=[a for a in answers if [len(row) for row in a]==shape]
        if not same or table in same: continue
        close=min(same,key=lambda a:sum(x!=y for x,y in zip(a,table)))
        return 'table %d row %d'%(i,next(r for r,(x,y) in enumerate(zip(close,table),1) if x!=y))
    return None
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
        mismatch=_table_mismatch(p['problem'],p['answer'])
        if mismatch: raise InputError('table rows differ: '+p['problem_id']+' '+mismatch)
        key=_answer_hash(p['answer'])
        if p['problem_id'] in seen and seen[p['problem_id']]!=key: raise InputError('different answers for '+p['problem_id'])
        seen[p['problem_id']]=key

def discover(repo,selector,problem_ids=None,failures=None):
    repo=Path(repo); experiments=parse_selector(selector)
    # A token is an internal ID, a label, or '실험NN:<label or ID>'; labels repeat across experiments.
    selected={_norm(p).strip() for p in problem_ids} if problem_ids else None
    root=_child(repo,'복습노트')
    if root is None: raise InputError('review folder missing')
    packs={};listed=set();labels={}  # (experiment, id) -> label counted in manifest order; filled as each pack is read
    def fail(pid,experiment,reason):
        if failures is None: raise InputError(reason)
        # label is None only when the pack itself is missing (no manifest, so no problem is known); a missing PDF pair fails per problem and keeps its label.
        failures.append({'problem_id':pid,'experiment':experiment,'label':labels.get((experiment,pid)),'reason':reason})
    for name in experiments:
        folder=_child(root,name); data=_child(folder,DATA_DIR) if folder else None; manifest=_child(data,'manifest.json') if data else None
        if manifest is None: fail(None,name,'experiment pack missing: '+name);continue
        included=[p for p in json.loads(manifest.read_text(encoding='utf-8'))['problems'] if p.get('status')=='included']
        # Labels come from the current manifest order every time; the PDF badge must agree.
        packs[name]=(folder,[(_norm(p['id']),KINDS[p['kind']]+str(n),_norm(p['title'])) for n,p in enumerate(included,1)])
        for pid,label,_ in packs[name][1]: listed.update([pid,label,name+':'+pid,name+':'+label]);labels[(name,pid)]=label
    for token in selected or ():
        owners=[name for name,(_,problems) in packs.items() if any(token==label for _,label,_ in problems)]
        if len(owners)>1: raise InputError('ambiguous label '+token+' in '+', '.join(owners)+'; use '+owners[-1]+':'+token)
    pairs=[]
    for name,(folder,problems) in packs.items():
        problems=[p for p in problems if selected is None or {p[0],p[1],name+':'+p[0],name+':'+p[1]}&selected]
        if not problems: continue
        pdfs=[p for p in folder.iterdir() if p.suffix.lower()=='.pdf']
        ps=[p for p in pdfs if _norm(p.name).endswith('_기출문제.pdf')];ans=[p for p in pdfs if _norm(p.name).endswith('_기출풀이.pdf')]
        if len(ps)!=1 or len(ans)!=1:
            for pid,_,_ in problems: fail(pid,name,'missing or ambiguous PDF pair')
            continue
        md=_child(folder,name+'_기출풀이.md'); figures=_child(_child(folder,DATA_DIR),'figures'); solutions=_child(figures,'solutions') if figures else None
        # Match each selected ID independently; unrelated damaged pages cannot stop it.
        for pid,label,title in problems:
            try:
                pp,aa=_pages(ps[0],[(pid,label,title)]),_pages(ans[0],[(pid,label,title)])
                if pid not in pp or pid not in aa: raise InputError('header/list mismatch: '+pid)
                defects=[d['code']+' p.'+str(ref['page_index']+1) for ref in (pp[pid],aa[pid]) for d in input_defects(ref['snapshot'],ref['page_index'])]
                if defects: raise InputError('input defect: '+';'.join(defects))
                # PNG (pixel comparison) and its SVG (evidence of what the figure means) share one name rule: exactly <id>-solution-NN.
                listing=list(solutions.iterdir()) if solutions else []
                by_ext=lambda ext:sorted(str(x.resolve()) for x in listing if re.fullmatch(re.escape(pid)+r'-solution-\d{2}\.'+ext,_norm(x.name)))
                pngs,svgs=by_ext('png'),by_ext('svg')
                # A PNG without its SVG is a warning, not a failure: the pixels are still frozen and compared.
                svg_stems={_norm(Path(f).stem) for f in svgs}
                svg_missing=[_norm(Path(f).name) for f in pngs if _norm(Path(f).stem) not in svg_stems]
                pair=dict(problem_id=pid,label=label,title=title,problem=pp[pid],answer=aa[pid],md_snapshot=str(md.resolve()) if md and md.is_file() else None,experiments=[name],
                    figure_refs=pngs,figure_svg_refs=svgs,figure_svg_missing=svg_missing)
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
    def freeze(path,keep_name=False):
        # Figures keep their PNG name (figure_source, coverage evidence) under a content-addressed folder.
        src=Path(path); sha=file_hash(src); target=dest/'figures'/sha/_norm(src.name) if keep_name else dest/(sha+src.suffix)
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,target) if not target.exists() else None
        rel=target.relative_to(batch).as_posix(); provenance[rel]={'original':str(src.resolve()),'sha256':sha}; return rel
    for p in result:
        for source in p.get('sources',[]):
            for role in ['problem','answer']: source[role]['snapshot']=freeze(source[role]['snapshot'])
            if source['md_snapshot']: source['md_snapshot']=freeze(source['md_snapshot'])
        for role in ['problem','answer']: p[role]['snapshot']=freeze(p[role]['snapshot'])
        if p['md_snapshot']: p['md_snapshot']=freeze(p['md_snapshot'])
        p['figure_refs']=[freeze(f,True) for f in p.get('figure_refs',[])]
        p['figure_svg_refs']=[freeze(f,True) for f in p.get('figure_svg_refs',[])]  # evidence only; never fed to the pixel comparison
    import fitz,sys
    write(batch/'source/inputs.json',{'files':provenance,'pairs':result,'tools':{'python':sys.version,'pymupdf':fitz.VersionBind}}); return result
