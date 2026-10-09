import math
from .contracts import InputError
from .review_adapter import validate_config
from .writing import validate_writing,representative_height

def build_timeline(manifest,layers,audio,config,writing=None,*,minimum_frames=None):
    validate_config(config); fps,rate=30,24000; per_frame=800
    voices={a['id']:a for a in audio}
    if len(voices)!=len(audio) or set(voices)!={s['id'] for s in manifest['segments']}: raise InputError('audio/segment mismatch')
    if any(a['rate']!=rate or type(a['samples']) is not int or a['samples']<=0 for a in audio): raise InputError('invalid measured PCM')
    if writing is not None: validate_writing(writing)
    settings=writing or config; pencil=writing is not None and writing['mode']=='pencil'
    interval=math.ceil(fps/float(settings['chars_per_second'])); hold=math.ceil(float(settings['read_hold_seconds'])*fps)
    glyphs={g['id']:g for g in layers['glyphs']}; spans=[]; previous=None; previous_step=None
    spatial=pencil and any('writing_units' in s for s in layers['map']['steps'])
    units=[]; unit_spans=[]; previous_piece=None; previous_unit=None
    if spatial:
        from .writing_units import compile_writing_units
        units=compile_writing_units(layers)
    last_piece={(p['kind'],p['id']):(u['id'],i) for u in units for i,p in enumerate(u['pieces'])}
    steps={s['id']:s for s in layers['map']['steps']}; segs=[]; events=[]; frame=0
    for seg in manifest['segments']:
        n=math.ceil(voices[seg['id']]['samples']/per_frame)
        if seg['kind']=='write':
            step=steps[seg['step_id']]; count=len(step['glyph_ids']); offset=0
            if pencil and not count:raise InputError('empty writing step')
            height=representative_height([glyphs[g] for g in step['glyph_ids']]) if pencil else None
            if spatial:
                for u in [u for u in units if u['step_id']==seg['step_id']]:
                    transition=previous_unit is None or (u['line_id'],u['chunk_id'])!=(previous_unit['line_id'],previous_unit['chunk_id'])
                    if transition: offset+=12
                    start=frame+offset
                    for i,piece in enumerate(u['pieces']):
                        b=piece['clip_bbox']; gid=piece['id'];kind=piece['kind']
                        space=kind=='glyph' and glyphs[gid]['text'].isspace()
                        lifted=previous_unit is not None and previous_unit['line_id']!=u['line_id']
                        move=interval if space else max(8,writing['lifted_move_frames']) if lifted else writing['adjacent_move_frames']
                        draw=0 if space else max(18 if kind=='shape' else 2,interval-writing['adjacent_move_frames'])
                        base=dict(id=gid,from_id=previous_piece['id'] if previous_piece else None,from_bbox=previous_piece['clip_bbox'] if previous_piece else None,
                                  target_kind=kind,step_id=seg['step_id'],unit_id=u['id'],piece_index=i,clip_bbox=b)
                        spans.append(dict(base,kind='move',start_frame=frame+offset,end_frame=frame+offset+move,lifted=lifted));offset+=move
                        if draw:
                            spans.append(dict(base,kind='draw',start_frame=frame+offset,end_frame=frame+offset+draw));offset+=draw;previous_piece=piece
                        if last_piece[(kind,gid)]==(u['id'],i):events.append(dict(id=gid,frame=frame+offset,kind=kind))
                    unit_spans.append(dict(unit_id=u['id'],step_id=u['step_id'],line_id=u['line_id'],chunk_id=u['chunk_id'],start_frame=start,end_frame=frame+offset,transition_start_frame=start-12 if transition else None))
                    previous_unit=u
            for i,gid in enumerate([] if spatial else step['glyph_ids']):
                if pencil:
                    g=glyphs[gid];b=g['bbox'];space=g['text'].isspace()
                    if not space and (b[2]<=b[0] or b[3]<=b[1]):raise InputError('empty writing glyph bbox')
                    lifted=False
                    if previous and not space:
                        a=glyphs[previous]['bbox'];cx,cy=(b[0]+b[2])/2,(b[1]+b[3])/2;px,py=(a[0]+a[2])/2,(a[1]+a[3])/2
                        lifted=previous_step!=seg['step_id'] or math.hypot(cx-px,cy-py)>height*3 or (abs(cy-py)>height*.6 and cx<px)
                    move=interval if space else max(8,writing['lifted_move_frames']) if lifted else writing['adjacent_move_frames']
                    draw=0 if space else max(2,interval-writing['adjacent_move_frames'])
                    base=dict(id=gid,from_id=previous,step_id=seg['step_id'])
                    spans.append(dict(base,kind='move',start_frame=frame+offset,end_frame=frame+offset+move,lifted=lifted))
                    offset+=move
                    if draw:spans.append(dict(base,kind='draw',start_frame=frame+offset,end_frame=frame+offset+draw));offset+=draw;previous=gid;previous_step=seg['step_id']
                    at=frame+offset
                else: at=frame+(i+1)*interval
                events.append(dict(id=gid,frame=at,kind='glyph'))
                events.extend(dict(id=sid,frame=at,kind='shape') for sid,anchor in manifest['shape_anchors'].items() if anchor==gid)
            n=max(n,offset if pencil else count*interval)+hold
        n=max(n,(minimum_frames or {}).get(seg['id'],0))
        segs.append(dict(seg,start_sample=frame*per_frame,end_sample=(frame+n)*per_frame,voice_samples=voices[seg['id']]['samples']))
        frame+=n
    # Dedicated finished full-page hold; all glyphs remain visible without swapping SVG.
    frame+=max(hold,30)
    result=dict(fps=fps,rate=rate,total_samples=frame*per_frame,total_frames=frame,segments=segs,events=sorted(events,key=lambda e:e['frame']),cameras=manifest.get('cameras',[]))
    if writing is not None:result['writing']=writing
    if pencil:result['writing_spans']=spans
    if spatial:result['writing_unit_spans']=unit_spans
    return result
def visible_ids(timeline,frame): return [e['id'] for e in timeline['events'] if e['kind']=='glyph' and e['frame']<=frame]
