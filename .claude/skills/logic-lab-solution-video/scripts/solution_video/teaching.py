"""Pad explanation tails with silence, binding everything to measured PCM frames."""
from .annotations import annotation_duration,fail
from .reveal import build_timeline
from .util import digest

def teaching_timing_settings(plan):
 if not plan:return {}
 # chunk_id 는 있을 때만 넣는다(상류는 늘 넣음). legacy 계획의 timing_hash 가 예전과 같아야 기존 timeline 이 그대로 통한다.
 return dict(cues=plan['cues'],items=[dict(id=i['id'],segment_id=i['segment_id'],region_id=i['region_id'],kind=i['kind'],**({'chunk_id':i['chunk_id']} if 'chunk_id' in i else {}),offset_frames=i['offset_frames'],duration_frames=i.get('duration_frames'),units=[c.isspace() for c in i['units']],hide_at=i['hide_at']) for i in plan['items']])

def minimum_segment_frames(plan):
 if not plan:return {}
 result={c['segment_id']:54 for c in plan['cues']}
 for i in plan['items']:
  if 'chunk_id' not in i:result[i['segment_id']]=max(result[i['segment_id']],i['offset_frames']+annotation_duration(i)+42)
 return result

def resolve_annotation_windows(plan:dict,timeline:dict)->list[dict]:
 """Resolve authored timing against measured speech; never pad chunk marks."""
 segs={s['id']:s for s in timeline['segments']};final=timeline['segments'][-1]['end_sample']//800
 chunks={(c['segment_id'],c['chunk_id']):c for c in timeline.get('caption_cues',[])};windows=[]
 for i in plan['items']:
  sid=i['segment_id'];seg=segs[sid];name=i['id'];chunk=i.get('chunk_id');label=f'{name} segment {sid} chunk {chunk}'
  if chunk is not None:
   cue=chunks.get((sid,chunk))
   if cue is None:fail(label,'measured caption chunk missing')
   start=max((cue['start_sample']+799)//800+i['offset_frames'],seg['start_sample']//800+12)
   deadline=min(cue['end_sample']//800,seg['end_sample']//800-13)
  else:
   start=seg['start_sample']//800+i['offset_frames'];deadline=final
  end=start+annotation_duration(i)
  if end>deadline:fail(label,f'annotation completes at {end}, beyond speech/camera deadline {deadline}')
  hide=i['hide_at'];hide_frame=final if hide=='final' else segs[hide['segment_id']]['start_sample']//800+hide['offset_frames']
  if hide_frame<end or hide_frame>final:fail(label,'hide must follow completion and precede final hold')
  windows.append(dict(id=name,start_frame=start,end_frame=end,hide_frame=hide_frame))
 ordered=sorted(windows,key=lambda w:w['start_frame'])
 for a,b in zip(ordered,ordered[1:]):
  if a['end_frame']>b['start_frame']:
   i=next(i for i in plan['items'] if i['id']==b['id'])
   fail(f"{i['id']} segment {i['segment_id']} chunk {i.get('chunk_id')}",'annotation windows overlap')
 return windows

def build_teaching_timeline(manifest,layers,audio,config,writing,plan):
 t=build_timeline(manifest,layers,audio,config,writing,minimum_frames=minimum_segment_frames(plan))
 if not plan:return t
 segs={s['id']:s for s in t['segments']};spans=[]
 windows={w['id']:w for w in resolve_annotation_windows(plan,t)}
 for i in plan['items']:
  window=windows[i['id']];start=window['start_frame'];hide_frame=window['hide_frame']
  def add(kind,unit,n):
   nonlocal start
   spans.append(dict(id=i['id'],unit_index=unit,kind=kind,start_frame=start,end_frame=start+n,hide_frame=hide_frame));start+=n
  add('move',0,8)
  if i['kind']=='label':
   for n,c in enumerate(i['units']):
    add('space' if c.isspace() else 'move',n,6 if c.isspace() else 1)
    if not c.isspace():add('draw',n,5)
  else:add('draw',0,i['duration_frames'])
 spans.sort(key=lambda s:s['start_frame'])
 t['teaching']=dict(schema_version=1,timing_hash=digest(teaching_timing_settings(plan)),cues=[dict(c,start_frame=segs[c['segment_id']]['start_sample']//800,end_frame=segs[c['segment_id']]['end_sample']//800) for c in plan['cues']],spans=spans)
 return t
