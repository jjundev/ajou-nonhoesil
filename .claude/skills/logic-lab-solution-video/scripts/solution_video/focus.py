"""Compile semantic focus cues around the existing original-writing camera keys."""
import copy,math
from .util import S
from .writing import load_pencil_asset
from .annotations import fail
from .page_layout import page_layout

def compile_focus_keys(manifest,layers,timeline,plan,compiled,base_keys):
 if not plan:return base_keys
 meta=layers['metadata'];full=[0,0,meta['width_pt'],meta['height_pt']];layout=page_layout(full[2],full[3]);keys=copy.deepcopy(base_keys)
 regions={r['id']:r for r in plan['regions']};items={i['id']:i for i in (compiled or {}).get('items',[])};authored={i['id']:i for i in plan['items']}
 final=timeline['segments'][-1]['end_sample']//800
 margin_x,margin_top,margin_bottom=180,200,30
 if plan['items']:
  asset=load_pencil_asset(S/'assets/pencil');length=timeline.get('writing',{}).get('pencil_length_px',160);unit=length/math.dist(asset['tip_px'],asset['end_px']);x0,y0,x1,y1=asset['visible_bounds_px'];points=[]
  for angle in [-2,0,2]:
   rad=math.radians(angle)
   for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:
    dx,dy=(x-asset['tip_px'][0])*unit,(y-asset['tip_px'][1])*unit;points.append((dx*math.cos(rad)-dy*math.sin(rad),dx*math.sin(rad)+dy*math.cos(rad)))
  margin_x=max(margin_x,max(abs(p[0]) for p in points)+10);margin_top=max(margin_top,-min(p[1] for p in points)+10);margin_bottom=max(margin_bottom,max(p[1] for p in points)+10)

 for cue in timeline['teaching']['cues']:
  start,end=cue['start_frame'],cue['end_frame'];name=cue['target'];bounds=[regions[name]['bbox']];heights=[]
  visible={s['id'] for s in timeline['teaching']['spans'] if s['start_frame']<end and s['hide_frame']>start}
  for ident in visible:
   if authored[ident]['region_id']==name and ident in items:
    bounds.append(items[ident]['bbox'])
    if items[ident].get('body_height'):heights.append(items[ident]['body_height'])
  b=[min(x[0] for x in bounds),min(x[1] for x in bounds),max(x[2] for x in bounds),max(x[3] for x in bounds)]
  # Geometric SVG bounds include arrowhead vertices; reserve screen-space stroke
  # radius outside them, in addition to the measured pencil clearance.
  radius=max((items[i].get('stroke_width_px',3)/2 for i in visible if i in items and items[i].get('kind')!='label'),default=0)
  mx,mt,mb=margin_x+radius,margin_top+radius,margin_bottom+radius
  scale=min((1920-2*mx)/max(.01,b[2]-b[0]),(900-mt-mb)/max(.01,b[3]-b[1]))
  if scale<=0:fail(name,'pencil bounds cannot fit content area')
  if heights and min(heights)*scale<26:fail(name,'label readability conflicts with region and pencil bounds')
  w,h=1920/scale,layout['height']/scale
  view=[(b[0]+b[2]-w)/2,b[1]-mt/scale,w,h]
  next_write=next((s for s in timeline['segments'] if s['kind']=='write' and s['start_sample']//800>=end),None)
  point=None
  if next_write:
   spans=[s['start_frame'] for s in timeline.get('writing_spans',[]) if s['start_frame']>=next_write['start_sample']//800 and s['start_frame']<next_write['end_sample']//800]
   events=[e['frame'] for e in timeline['events'] if e['kind']=='glyph' and next_write['start_sample']//800<=e['frame']<next_write['end_sample']//800]
   point=min(spans or events) if spans or events else next_write['start_sample']//800
  dest=next((k for k in reversed(base_keys) if point is not None and k['at_frame']<=point),dict(viewbox=full))
  hold_until=point if point is not None else end
  keys=[k for k in keys if not start<=k['at_frame']<hold_until]
  keys.extend([dict(at_frame=start,viewbox=view,transition_frames=12),dict(at_frame=end-12,viewbox=dest['viewbox'],mirror=dest.get('mirror',False),transition_frames=12)])
 keys.append(dict(at_frame=final,viewbox=full))
 unique={k['at_frame']:k for k in keys};keys=[unique[f] for f in sorted(unique)]
 for a,b in zip(keys,keys[1:]):
  if a['at_frame']+a.get('transition_frames',0)>b['at_frame']:fail('camera','overlapping transitions')
 return keys
