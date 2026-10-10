"""Pad explanation tails with silence, binding everything to measured PCM frames."""
from .annotations import annotation_duration,fail
from .reveal import build_timeline
from .util import digest

def teaching_timing_settings(plan):
 if not plan:return {}
 return dict(cues=plan['cues'],items=[dict(id=i['id'],segment_id=i['segment_id'],region_id=i['region_id'],kind=i['kind'],offset_frames=i['offset_frames'],duration_frames=i.get('duration_frames'),units=[c.isspace() for c in i['units']],hide_at=i['hide_at']) for i in plan['items']])

def minimum_segment_frames(plan):
 if not plan:return {}
 result={c['segment_id']:54 for c in plan['cues']}
 for i in plan['items']:result[i['segment_id']]=max(result[i['segment_id']],i['offset_frames']+annotation_duration(i)+42)
 return result

def build_teaching_timeline(manifest,layers,audio,config,writing,plan):
 t=build_timeline(manifest,layers,audio,config,writing,minimum_frames=minimum_segment_frames(plan))
 if not plan:return t
 segs={s['id']:s for s in t['segments']};final=t['segments'][-1]['end_sample']//800;spans=[]
 for i in plan['items']:
  start=segs[i['segment_id']]['start_sample']//800+i['offset_frames'];end=start+annotation_duration(i)
  hide=i['hide_at'];hide_frame=final if hide=='final' else segs[hide['segment_id']]['start_sample']//800+hide['offset_frames']
  if hide_frame<end or hide_frame>final:fail(i['id'],'hide must follow completion and precede final hold')
  def add(kind,unit,n):
   nonlocal start
   spans.append(dict(id=i['id'],unit_index=unit,kind=kind,start_frame=start,end_frame=start+n,hide_frame=hide_frame));start+=n
  add('move',0,8)
  if i['kind']=='label':
   for n,c in enumerate(i['units']):
    add('space' if c.isspace() else 'move',n,6 if c.isspace() else 1)
    if not c.isspace():add('draw',n,5)
  else:add('draw',0,i['duration_frames'])
 t['teaching']=dict(schema_version=1,timing_hash=digest(teaching_timing_settings(plan)),cues=[dict(c,start_frame=segs[c['segment_id']]['start_sample']//800,end_frame=segs[c['segment_id']]['end_sample']//800) for c in plan['cues']],spans=spans)
 return t
