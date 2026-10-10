from pathlib import Path
import re
from .util import digest,file_hash
from .contracts import ReviewError,InputError
from .subtitles import caption_text,split_caption

def content_fingerprint(manifest,layers,coverage):
    data=dict(layers)
    for k in ['original_svg','animated_svg','reference_png']:
        if k in data:
            p=Path(data[k]); data[k]={'path':data[k],'sha256':file_hash(p) if p.is_file() else None}
    return digest({'manifest':manifest,'layers':data,'coverage':{k:v for k,v in coverage.items() if k not in ('status','input_hash')}})

def validate_manifest(manifest,layers,coverage,circuit_review):
    def require(ok,why):
        if not ok: raise ReviewError(why)
    require(manifest.get('schema_version')==1,'manifest schema_version must be 1')
    require(bool(manifest.get('problem_id')) and bool(manifest.get('title','').strip()),'problem ID/title required')
    mapping=layers.get('map'); require(bool(mapping),'PageMap not authored')
    gs={g['id']:g for g in layers['glyphs']}; ss={s['id']:s for s in layers['shapes']}
    order=manifest.get('reveal_order',[])
    require(len(order)==len(gs) and set(order)==gs.keys(),'exact glyph coverage required')
    if any('writing_units' in step for step in mapping['steps']):
        from .writing_units import compile_writing_units
        compile_writing_units(layers)
    steps=mapping['steps']; ids=[s['id'] for s in steps]
    require(len(set(ids))==len(ids) and ids[-1]==mapping['answer_step_id'],'answer must be final step')
    expected=[g for s in steps for g in s['glyph_ids']]
    require(order==expected,'explicit PageMap reading order required; no coordinate sorting')
    glyph_step={g:s['id'] for s in steps for g in s['glyph_ids']}
    shape_step={g:s['id'] for s in steps for g in s['shape_ids']}
    anchors=manifest.get('shape_anchors',{})
    require(set(anchors)==ss.keys(),'exact shape anchors required')
    require(all(g in gs and glyph_step[g]==shape_step[s] for s,g in anchors.items()),'shape anchor must belong to same step')
    segs=manifest.get('segments',[]); require(bool(segs),'narration segments required')
    require(len({s['id'] for s in segs})==len(segs),'duplicate segment ID')
    writing=[]
    for s in segs:
        require(bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',s['id'])),'segment ID must be safe ASCII')
        require(s.get('kind') in ['problem','reason','write','check','summary'],'invalid segment kind')
        require(bool(s.get('text','').strip()) and bool(s.get('source_refs')),'segment text/source_refs required')
        if 'caption_text' in s:
            require(isinstance(s['caption_text'],str) and bool(s['caption_text'].strip()),'nonempty caption_text required')
        try:split_caption(caption_text(s))
        except InputError as ex:raise InputError('segment '+s['id']+': '+str(ex)) from ex
        if s['kind']=='write':
            require(s.get('step_id') in ids,'unknown writing step'); writing.append(s['step_id'])
        elif s.get('step_id'): require(s['step_id'] in ids,'unknown step')
    require(writing==ids,'one ordered write segment per mapped step; split the PageMap for smaller writing units')
    require(segs[0]['kind']=='problem','begin on original problem PDF')
    keys=manifest.get('cameras',[])
    require(all(type(k['at_frame']) is int and k['at_frame']>=0 and len(k['viewbox'])==4 and k['viewbox'][2]>0 and k['viewbox'][3]>0 for k in keys),'invalid camera key')
    require([k['at_frame'] for k in keys]==sorted(set(k['at_frame'] for k in keys)),'camera keys must be unique and ordered')
    h=content_fingerprint(manifest,layers,coverage)
    for r in [coverage,circuit_review]: require(r.get('status')=='passed' and r.get('input_hash')==h,'current authored review required')
    require(coverage.get('pdf_md_agree') is True,'PDF/MD disagreement blocks TTS')
    rows=coverage.get('rows',[])
    require([r.get('step_id') for r in rows]==ids,'coverage rows must follow every mapped step')
    require(all(r.get('source_refs') and r.get('pdf_text') and r.get('meaning_review') for r in rows),'source text and meaning evidence required')
    for row,step in zip(rows,steps):
        source_text=''.join(gs[g]['text'] for g in step['glyph_ids'])
        require(re.sub(r'\s+','',row['pdf_text'])==re.sub(r'\s+','',source_text),'coverage pdf_text differs from original glyph order')
    checks=circuit_review.get('steps',[])
    require([r.get('step_id') for r in checks]==ids,'circuit review must cover every step')
    require(all(all(r.get(k) for k in ['assumptions','equations','units','evidence']) for r in checks),'circuit assumptions/equations/units/evidence required')
