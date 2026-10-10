"""Frame a complete authored chunk; never chase individual glyphs."""
import math
from .contracts import InputError
from .writing import representative_height,load_pencil_asset
from .page_layout import page_layout
from .util import S


def pencil_envelope(settings):
    asset=load_pencil_asset(S/'assets/pencil');unit=settings['pencil_length_px']/math.dist(asset['tip_px'],asset['end_px'])
    x0,y0,x1,y1=asset['visible_bounds_px'];points=[]
    for angle in (-settings['tilt_degrees'],0,settings['tilt_degrees']):
        rad=math.radians(angle)
        for x,y in ((x0,y0),(x0,y1),(x1,y0),(x1,y1)):
            dx,dy=(x-asset['tip_px'][0])*unit,(y-asset['tip_px'][1])*unit
            points.append((dx*math.cos(rad)-dy*math.sin(rad),dx*math.sin(rad)+dy*math.cos(rad)))
    return [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]


def build_writing_camera_keys(layers:dict,timeline:dict,units:list)->list[dict]:
    meta=layers['metadata'];full=[0,0,meta['width_pt'],meta['height_pt']];height=page_layout(full[2],full[3])['height']
    spans=timeline['writing_unit_spans'];envelope=pencil_envelope(timeline['writing']);groups={}
    glyphs={g['id']:g for g in layers['glyphs']};figures={x['id'] for x in layers.get('shapes',[]) if x.get('kind')=='figure'}
    floor=min(1920/full[2],height/full[3])
    bases={s['id']:representative_height([glyphs[g] for g in s['glyph_ids']]) for s in layers['map']['steps']}
    manual=timeline.get('cameras',[])
    if any(k['at_frame']>=timeline['total_frames'] or k['at_frame']<0 for k in manual):raise InputError('camera outside timeline')
    final=timeline['segments'][-1]['end_sample']//800
    if any(k['at_frame']>=final and k['viewbox']!=full for k in manual):raise InputError('manual camera conflicts with final full-page hold')
    keys=[dict(at_frame=0,viewbox=full)]+[dict(k) for k in manual if k['at_frame']<final]
    for u in units:groups.setdefault((u['line_id'],u['chunk_id']),[]).append(u)
    for group in groups.values():
        ids={u['id'] for u in group};times=[s for s in spans if s['unit_id'] in ids];start=min(s['start_frame'] for s in times);end=max(s['end_frame'] for s in times)
        if any(start-12<=k['at_frame']<end or k['at_frame']<start-12<k['at_frame']+k.get('transition_frames',0) for k in manual):raise InputError('manual camera conflicts with writing chunk')
        base=min(bases[u['step_id']] for u in group)
        pieces=[p for u in group for p in u['pieces'] if p['kind']=='shape' or not glyphs[p['id']]['text'].isspace()]
        def fit(scale,only=None):
            bounds=[]
            for p in only or pieces:
                b=p['clip_bbox'];vertical=p['kind']=='shape' and b[2]==b[0];lo=b[1] if vertical else b[1]+.8*(b[3]-b[1]);hi=b[3] if vertical else lo
                bounds.append([min(b[0]*scale,b[0]*scale+envelope[0]),min(b[1]*scale,lo*scale+envelope[1]),max(b[2]*scale,b[2]*scale+envelope[2]),max(b[3]*scale,hi*scale+envelope[3])])
            a=[min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)]
            if a[2]-a[0]>1900 or a[3]-a[1]>880:return None
            box=[min(u['bbox'][0] for u in group),min(u['bbox'][1] for u in group),max(u['bbox'][2] for u in group),max(u['bbox'][3] for u in group)]
            preferred_x=(box[0]+box[2])*scale/2-960;preferred_y=(box[1]+box[3])*scale/2-450
            left=max(a[2]-1910,min(a[0]-10,preferred_x));top=max(a[3]-890,min(a[1]-10,preferred_y))
            return [left/scale,top/scale,1920/scale,height/scale]
        candidates=[c for c in (fit(body/base) for body in (28,27,26)) if c][:1]
        figure_pieces=[p for p in pieces if p['kind']=='shape' and p['id'] in figures]
        def descend(only=None):
            # A solution figure may be shown smaller than 26px text, but never smaller than the full-page view.
            found=[];scale=26/base
            while not found and scale>=floor:
                found=[c for c in [fit(scale,only)] if c]; scale*=.98
            return found
        if not candidates and figure_pieces:candidates=descend()
        if not candidates:
            # 그림 혼자도 전체 쪽 배율에서 안 들어갈 때만 그림 탓이다. 혼자 들어가면 원인은 묶음 구성(글자·범위)이다.
            if figure_pieces and not descend(figure_pieces):raise InputError('figure chunk cannot fit even at the full-page view; crop or split the figure: '+group[0]['chunk_id'])
            raise InputError('writing chunk cannot fit at 26px; author smaller chunks: '+group[0]['chunk_id'])
        transition=min(s['transition_start_frame'] for s in times if s.get('transition_start_frame') is not None)
        keys.append(dict(at_frame=transition,viewbox=candidates[0],mirror=False,transition_frames=12))
    final=timeline['segments'][-1]['end_sample']//800;keys.append(dict(at_frame=final,viewbox=full))
    unique={k['at_frame']:k for k in keys};return [unique[f] for f in sorted(unique)]
