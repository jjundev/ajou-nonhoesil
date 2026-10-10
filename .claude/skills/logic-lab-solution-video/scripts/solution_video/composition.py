from pathlib import Path
import copy,html,json,re,shutil,math,xml.etree.ElementTree as ET
from .util import digest,S,read,write,file_hash,local
from .contracts import InputError
from .page_layout import page_layout
from .annotations import load_teaching,compile_annotations
from .teaching import teaching_timing_settings
from .focus import compile_focus_keys
from .writing import load_pencil_asset,representative_height,load_writing,timing_settings

def pencil_camera_keys(manifest,layers,timeline):
    if timeline.get('writing_unit_spans'):
        from .writing_units import compile_writing_units
        from .writing_camera import build_writing_camera_keys
        return build_writing_camera_keys(layers,timeline,compile_writing_units(layers))
    meta=layers['metadata'];full=[0,0,meta['width_pt'],meta['height_pt']];layout=page_layout(full[2],full[3]);height=layout['height']
    glyphs={g['id']:g for g in layers['glyphs']};bases={s['id']:representative_height([glyphs[g] for g in s['glyph_ids']]) for s in layers['map']['steps']}
    asset=load_pencil_asset(S/'assets/pencil');length=timeline['writing']['pencil_length_px'];unit=length/math.dist(asset['tip_px'],asset['end_px'])
    x0,y0,x1,y1=asset['visible_bounds_px'];points=[]
    for angle in [-timeline['writing']['tilt_degrees'],0,timeline['writing']['tilt_degrees']]:
        rad=math.radians(angle)
        for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:
            dx,dy=(x-asset['tip_px'][0])*unit,(y-asset['tip_px'][1])*unit
            points.append((dx*math.cos(rad)-dy*math.sin(rad),dx*math.sin(rad)+dy*math.cos(rad)))
    envelope=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
    manual=manifest.get('cameras',[])
    if any(k['at_frame']>=timeline['total_frames'] for k in manual):raise InputError('camera outside timeline')
    keys=[dict(at_frame=0,viewbox=full)];current=None;active_manual=None;current_mirror=False
    for span in timeline['writing_spans']:
        if span['kind']!='move':continue
        g=glyphs[span['id']];b=g['bbox']
        if g['text'].isspace():continue
        y=b[1]+.8*(b[3]-b[1])
        def needed(scale,mirror=False):
            e=[-envelope[2],envelope[1],-envelope[0],envelope[3]] if mirror else envelope
            return [min(b[0]*scale,b[0]*scale+e[0]),min(b[1]*scale,y*scale+e[1]),max(b[2]*scale,b[2]*scale+e[2]),max(b[3]*scale,y*scale+e[3])]
        def fits(view,mirror=False):
            sc=height/view[3];a=needed(sc,mirror)
            return bases[span['step_id']]*sc>=26 and a[0]-view[0]*sc>=9.999 and a[2]-view[0]*sc<=1910.001 and a[1]-view[1]*sc>=9.999 and a[3]-view[1]*sc<=890.001
        requested=next((k for k in reversed(manual) if k['at_frame']<=span['start_frame']),None)
        changed=requested is not None and requested!=active_manual
        if current is not None and not changed and not fits(current,current_mirror) and fits(current,not current_mirror):
            current_mirror=not current_mirror;keys.append(dict(at_frame=span['start_frame'],viewbox=current,mirror=current_mirror))
        if current is None or changed or not fits(current,current_mirror):
            scale=min(1920/requested['viewbox'][2],height/requested['viewbox'][3]) if requested else 28/bases[span['step_id']]
            if bases[span['step_id']]*scale<25.99:raise InputError('camera makes writing body too small: '+g['id'])
            w=1920/scale;h=height/scale;safe=900/scale
            cx=(b[0]+b[2])/2;preferred_x=max(0,min(max(0,full[2]-w),cx-w/2));preferred_y=max(0,min(max(0,full[3]-safe),y-safe/2))
            if requested:
                v=requested['viewbox'];preferred_x=v[0]+v[2]/2-w/2;preferred_y=v[1]+v[3]/2-h/2
            candidates=[]
            for mirror in [False,True]:
                a=needed(scale,mirror)
                if a[2]-a[0]>1900 or a[3]-a[1]>880:continue
                left=max((a[2]-1910)/scale,min((a[0]-10)/scale,preferred_x));top=max((a[3]-890)/scale,min((a[1]-10)/scale,preferred_y))
                view=[left,top,w,h]
                if fits(view,mirror):candidates.append((abs(left-preferred_x)+abs(top-preferred_y),mirror,view))
            if not candidates:raise InputError('pencil cannot fit content area')
            _,current_mirror,current=min(candidates,key=lambda item:(item[0],item[1]))
            keys.append(dict(at_frame=span['start_frame'],viewbox=current,mirror=current_mirror));active_manual=requested
    final=timeline['segments'][-1]['end_sample']//800
    keys.append(dict(at_frame=final,viewbox=full));return keys

def camera_keys(manifest,layers,timeline):
    if timeline.get('writing',{}).get('mode')=='pencil':return pencil_camera_keys(manifest,layers,timeline)
    meta=layers['metadata']; full=[0,0,meta['width_pt'],meta['height_pt']]; glyphs={g['id']:g for g in layers['glyphs']}
    layout=page_layout(full[2],full[3]); screen_h=layout['height']; safe_fraction=900/screen_h
    final=timeline['segments'][-1]['end_sample']//800
    step_of={gid:step['id'] for step in layers['map']['steps'] for gid in step['glyph_ids']}
    base_heights={}; bounds={}
    for step in layers['map']['steps']:
        gs=[glyphs[g] for g in step['glyph_ids'] if not glyphs[g]['text'].isspace()]
        heights=sorted(g['bbox'][3]-g['bbox'][1] for g in gs if g['bbox'][3]-g['bbox'][1]>=2)
        if not heights: raise InputError('writing step has no measurable letter')
        # Thin operators, punctuation and proportional subscripts do not define text size.
        base_heights[step['id']]=representative_height(gs)
        bounds[step['id']]=[min(g['bbox'][0] for g in gs),min(g['bbox'][1] for g in gs),max(g['bbox'][2] for g in gs),max(g['bbox'][3] for g in gs)]
    if manifest.get('cameras'):
        keys=[copy.deepcopy(k) for k in manifest['cameras'] if k['at_frame']<final]
        if not keys or keys[0]['at_frame']!=0: keys.insert(0,dict(at_frame=0,viewbox=full))
        if any(k['at_frame']>=timeline['total_frames'] for k in manifest['cameras']): raise InputError('camera outside timeline')
    else:
        keys=[dict(at_frame=0,viewbox=full)]; current=None; active=None
        for event in timeline['events']:
            if event['kind']!='glyph': continue
            g=glyphs[event['id']]; b=g['bbox']; sid=step_of[g['id']]
            if g['text'].isspace(): continue
            height=base_heights[sid]; h=min(full[3],height*screen_h/28); w=h*1920/screen_h; safe_h=h*safe_fraction
            cx,cy=(b[0]+b[2])/2,(b[1]+b[3])/2
            if active!=sid:
                bound=bounds[sid]; cx=(bound[0]+bound[2])/2; cy=min((bound[1]+bound[3])/2,b[1]+safe_h/3)
            view=[max(0,min(max(0,full[2]-w),cx-w/2)),max(0,min(max(0,full[3]-safe_h),cy-safe_h/2)),w,h]
            if active!=sid or not(current[0]+8<=b[0] and b[2]<=current[0]+current[2]-8 and current[1]+8<=b[1] and b[3]<=current[1]+current[3]*safe_fraction-8):
                keys.append(dict(at_frame=event['frame'],viewbox=view)); current=view; active=sid
    if keys[-1]['at_frame']<final: keys.append(dict(at_frame=final,viewbox=full))
    for event in timeline['events']:
        if event['kind']!='glyph': continue
        g=glyphs[event['id']]; b=g['bbox']
        if g['text'].isspace(): continue
        view=next(k['viewbox'] for k in reversed(keys) if k['at_frame']<=event['frame'])
        scale=min(1920/view[2],screen_h/view[3])
        if base_heights[step_of[g['id']]]*scale<25.99: raise InputError('camera makes writing body too small: '+g['id'])
        left=(1920-view[2]*scale)/2;top=(screen_h-view[3]*scale)/2
        screen=[left+(b[0]-view[0])*scale,top+(b[1]-view[1])*scale,
                left+(b[2]-view[0])*scale,top+(b[3]-view[1])*scale]
        if not(0<=screen[0] and 0<=screen[1] and screen[2]<=1920 and screen[3]<=900): raise InputError('camera clips current writing glyph: '+g['id'])
    return keys

def _prefix(svg,prefix):
    # Separate document IDs, preserving all geometry and shared references.
    ids=re.findall(r'\bid="([^"]+)"',svg)
    for old in sorted(ids,key=len,reverse=True):
        svg=svg.replace('id="'+old+'"','id="'+prefix+old+'"').replace('href="#'+old+'"','href="#'+prefix+old+'"').replace('url(#'+old+')','url(#'+prefix+old+')')
    return svg

def assemble(pair,layers,manifest,timeline,run,runtime):
    import fitz
    run=Path(run).resolve(); runtime=Path(runtime)
    if runtime.is_dir(): runtime=runtime/'gsap.min.js'
    if not runtime.is_file(): raise InputError('local GSAP runtime missing')
    t=copy.deepcopy(timeline)
    if (run/'source/writing.json').is_file():
        current=load_writing(run,{})
        if not t.get('writing') or timing_settings(current)!=timing_settings(t['writing']):raise InputError('writing timing changed; retime before assemble')
        # Refresh visual settings without changing the saved timing output/hash.
        t['writing']=current
    dest=run/'composition'; dest.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(S/'assets/camera.js',dest/'camera.js'); shutil.copyfile(runtime,dest/'gsap.min.js'); shutil.copyfile(S/'assets/player.js',dest/'player.js'); shutil.copyfile(S/'assets/layout.css',dest/'layout.css')
    plan=load_teaching(run,manifest,layers)
    if (t.get('teaching') or {}).get('timing_hash')!=(digest(teaching_timing_settings(plan)) if plan else None):raise InputError('teaching timing changed; retime before assemble')
    compiled=compile_annotations(plan,layers,dest/'annotations') if plan and plan['items'] else None
    t['cameras']=compile_focus_keys(manifest,layers,t,plan,compiled,camera_keys(manifest,layers,t))
    ref=pair['problem']; path=Path(ref['snapshot']); path=path if path.is_absolute() else local(run,path)
    with fitz.open(path) as pdf: problem=pdf[ref['page_index']].get_svg_image(text_as_path=True)
    answer=Path(layers['animated_svg']).read_text(encoding='utf-8')
    if compiled:
        root=ET.fromstring(answer);root.append(ET.parse(compiled['svg']).getroot().find('{http://www.w3.org/2000/svg}g'));answer=ET.tostring(root,encoding='unicode')
    pencil=t.get('writing',{}).get('mode')=='pencil';has_pen=pencil or bool(compiled);asset_meta=None
    if has_pen:
        asset_meta=load_pencil_asset(S/'assets/pencil')
        for name in (asset_meta['file'],'pencil-yellow-v1.json'):shutil.copyfile(S/'assets/pencil'/name,dest/name)
        shutil.copyfile(S/'assets/writing.js',dest/'writing.js');shutil.copyfile(S/'assets/pencil.js',dest/'pencil.js')
    if compiled:shutil.copyfile(S/'assets/annotations.js',dest/'annotations.js')
    write(dest/'timeline.json',t)
    encode=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    contents='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><link rel="stylesheet" href="layout.css"><script src="gsap.min.js"></script></head><body>'''
    contents+=f'<div data-composition-id="solution" data-width="1920" data-height="1080" data-duration="{t["total_frames"]/30}" id="solution">'
    contents+='<div id="pdf-viewport"><div id="problem-page">'+_prefix(problem,'problem-')+'</div><div id="answer-page" data-layout-allow-overflow>'+answer+'</div><div id="cursor"></div>'+('<img id="pencil" src="pencil-yellow-v1.png" data-layout-allow-overflow>' if has_pen else '')+'</div><div id="caption-strip"></div></div>'
    layout=page_layout(layers['metadata']['width_pt'],layers['metadata']['height_pt'])
    contents+='<script src="camera.js"></script>'
    contents+=('<script src="writing.js"></script><script src="pencil.js"></script><script>window.pencilMeta='+encode(asset_meta)+';</script>' if has_pen else '')
    if compiled:contents+='<script src="annotations.js"></script><script>window.solutionAnnotationsData='+encode(compiled)+';</script>'
    contents+='<script>window.solutionLayout='+encode(layout)+';window.solutionTimeline='+encode(t)+';window.solutionGlyphs='+encode({g['id']:g for g in layers['glyphs']+(layers['shapes'] if t.get('writing_unit_spans') else [])})+';</script><script>'+(dest/'player.js').read_text(encoding='utf-8')+'</script></body></html>'
    (dest/'index.html').write_text(contents,encoding='utf-8')
    write(dest/'hyperframes.json',{'width':1920,'height':1080,'fps':30})
    write(dest/'runtime.json',{'gsap_sha256':file_hash(dest/'gsap.min.js'),'player_sha256':file_hash(dest/'player.js'),'layout_sha256':file_hash(dest/'layout.css')})
    if has_pen:
        r=json.loads((dest/'runtime.json').read_text());r['writing_assets']={n:file_hash(dest/n) for n in ['writing.js','pencil.js',asset_meta['file'],'pencil-yellow-v1.json']};write(dest/'runtime.json',r)
    r=read(dest/'runtime.json');r['teaching_assets']={p.relative_to(dest).as_posix():file_hash(p) for p in dest.rglob('*') if p.is_file() and (p.suffix in ('.js','.svg') or p.name=='compiled.json')};write(dest/'runtime.json',r)
    parts=[dict(entry='composition/index.html',first_frame=0,last_frame=t['total_frames'],key='solution')]; write(run/'source/parts.json',parts); return parts
