"""Authored links from circuit evidence to writing; never infer circuit meaning."""
from pathlib import Path
from .contracts import InputError
from .util import read
from .subtitles import caption_text,split_caption


def _require(ok, name, message):
    if not ok:raise InputError(f'lesson {name}: {message}')


def validate_lesson(lesson:dict,manifest:dict,layers:dict,teaching:dict|None)->dict:
    _require(isinstance(lesson,dict) and lesson.get('schema_version')==1,'schema','expected version 1')
    rows=lesson.get('steps');expected=[s['id'] for s in layers['map']['steps']]
    _require(isinstance(rows,list) and all(isinstance(s,dict) for s in rows),'steps','expected list of objects')
    _require([s.get('step_id') for s in rows]==expected,'steps','must cover PageMap exactly in order')
    segments={s['id']:s for s in manifest['segments']};order=list(segments)
    for seg in segments.values():
        _require('caption_text' in seg,seg['id'],'guided caption_text required');split_caption(caption_text(seg))
    cues={c['segment_id']:c['target'] for c in (teaching or {}).get('cues',[])}
    regions={r['id'] for r in (teaching or {}).get('regions',[])}
    items={i['id']:i for i in (teaching or {}).get('items',[])}
    for row in rows:
        name=row['step_id'];mode=row.get('mode')
        writes=[s['id'] for s in segments.values() if s['kind']=='write' and s.get('step_id')==name]
        _require(len(writes)==1,name,'one writing segment required');write=writes[0]
        _require(mode in ('circuit','calculation'),name,'unknown mode')
        _require(isinstance(row.get('meaning_notes'),str) and row['meaning_notes'].strip(),name,'meaning_notes required')
        _require(isinstance(row.get('source_refs'),list) and row['source_refs'] and all(isinstance(x,str) and x.strip() for x in row['source_refs']),name,'source_refs required')
        for key in ['reason_segment_ids','check_segment_ids','region_ids','annotation_ids']:
            values=row.get(key)
            _require(isinstance(values,list) and all(isinstance(v,str) for v in values) and len(set(values))==len(values),name,f'invalid {key}')
        for key,kind in [('reason_segment_ids','reason'),('check_segment_ids','check')]:
            for ident in row[key]:
                _require(ident in segments and segments[ident]['kind']==kind and segments[ident].get('step_id')==name,name,f'unknown or mismatched {kind} {ident}')
                _require(order.index(ident)<order.index(write) if kind=='reason' else order.index(ident)>order.index(write),name,f'{kind} out of order')
        if mode=='calculation':
            _require(not any(row[k] for k in ['reason_segment_ids','region_ids','annotation_ids']),name,'calculation has circuit links')
            _require(isinstance(row.get('exemption_reason'),str) and row['exemption_reason'].strip(),name,'exemption_reason required')
            continue
        _require(all(row[k] for k in ['reason_segment_ids','region_ids','annotation_ids']),name,'circuit evidence required')
        _require(set(row['region_ids'])<=regions,name,'unknown region')
        _require(all(cues.get(s) in row['region_ids'] for s in row['reason_segment_ids']),name,'reason focus missing')
        _require(set(row['region_ids'])=={cues[s] for s in row['reason_segment_ids']},name,'unused region')
        for ident in row['annotation_ids']:
            i=items.get(ident)
            _require(i and i['segment_id'] in row['reason_segment_ids'] and i['region_id'] in row['region_ids'],name,f'annotation mismatch {ident}')
        _require(all(any(items[i]['segment_id']==s for i in row['annotation_ids']) for s in row['reason_segment_ids']),name,'reason has no referenced mark')
    return lesson


def load_lesson(run:Path,manifest:dict,layers:dict,teaching:dict|None)->dict|None:
    p=Path(run)/'source/lesson.json'
    return validate_lesson(read(p),manifest,layers,teaching) if p.is_file() else None


def lesson_screen_passed(expected:dict,screen:dict|None)->bool:
    return not expected['probes'] or bool(screen and screen.get('lesson_flow') is True)


def lesson_expectations(lesson:dict,manifest:dict,timeline:dict,teaching:dict)->dict:
    segs={s['id']:s for s in timeline['segments']};regions={r['id']:r['bbox'] for r in teaching['regions']};items={i['id']:i for i in teaching['items']}
    result={'steps':[],'probes':[]}
    for row in lesson['steps']:
        name=row['step_id'];write=next(s for s in manifest['segments'] if s['kind']=='write' and s['step_id']==name);w=segs[write['id']]
        result['steps'].append(dict(row,write_segment_id=write['id']))
        for sid in row['check_segment_ids']:_require(segs[sid]['start_sample']>=w['end_sample'],name,'check precedes writing completion')
        for sid in row['reason_segment_ids']:
            r=segs[sid];_require(r['end_sample']<=w['start_sample'],name,'reason overlaps writing')
            cue=next((c for c in timeline['teaching']['cues'] if c['segment_id']==sid),None)
            _require(cue and cue['target'] in row['region_ids'],name,'timeline focus missing')
            ids=[i for i in row['annotation_ids'] if items[i]['segment_id']==sid]
            spans=[s for s in timeline['teaching']['spans'] if s['id'] in ids and s['kind']=='draw']
            _require(set(s['id'] for s in spans)==set(ids),name,'timeline marks missing')
            frame=max(cue['start_frame']+12,max(s['end_frame'] for s in spans))
            _require(frame<cue['end_frame']-12 and all(frame<s['hide_frame'] for s in spans),name,'no stable completed evidence frame')
            result['probes'].append(dict(step_id=name,segment_id=sid,frame=frame,region_bbox=regions[cue['target']],annotation_ids=ids))
    return result
