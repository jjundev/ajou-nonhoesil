"""Optional teaching sidecars; never mutate the frozen PDF or reveal map."""
from pathlib import Path
from typing import TypedDict
import copy,math,re,unicodedata
from .contracts import InputError
from .util import S,read

FONT=S/'assets/fonts/Pretendard-Bold.ttf'
class TeachingPlan(TypedDict):
 schema_version:int; regions:list[dict]; cues:list[dict]; items:list[dict]
class CompiledAnnotations(TypedDict):
 items:list[dict]; svg:str; font_sha256:str|None

def fail(name,why): raise InputError(f'teaching {name}: {why}')
def integer(v,name,minimum=0):
 if type(v) is not int or v<minimum:fail(name,f'integer >= {minimum} required')
 return v

def numbers(v,n,name):
 if not isinstance(v,list) or len(v)!=n or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):fail(name,'finite coordinates required')
 return list(v)

def bbox(v,name):
 b=numbers(v,4,name)
 if b[0]>=b[2] or b[1]>=b[3]:fail(name,'positive area required')
 return b

def overlaps(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def check_box(b,layers,name):
 m=layers['metadata'];w,h=m['width_pt'],m['height_pt']
 if b[0]<0 or b[1]<0 or b[2]>w or b[3]>h:fail(name,'outside page')
 if overlaps(b,layers['map']['work_bbox']):fail(name,'overlaps work_bbox')

def named_list(value,name,key='id'):
 if not isinstance(value,list):fail(name,'list required')
 seen=set()
 for obj in value:
  if not isinstance(obj,dict):fail(name,'object required')
  ident=obj.get(key)
  if not isinstance(ident,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_-]*',ident):fail(name,'safe ASCII ID required')
  if ident in seen:fail(ident,'duplicate ID')
  seen.add(ident)
 return value

def annotation_duration(item):
 return 8+(sum(6 if c.isspace() else 6 for c in item['units']) if item['kind']=='label' else item['duration_frames'])

def _validate(focus,annotations,manifest,layers):
 if focus is None:
  if annotations is not None:fail('annotations.json','focus.json required')
  return None
 for filename,obj in [('focus.json',focus),('annotations.json',annotations)]:
  if obj is None:continue
  if not isinstance(obj,dict) or type(obj.get('schema_version')) is not int or obj['schema_version']!=1:fail(filename,'schema_version must be 1')
  if obj.get('source_sha256')!=layers['metadata']['source_sha256']:fail(filename,'source_sha256 differs from answer')
 regions=named_list(focus.get('regions'),'regions');cues=named_list(focus.get('cues'),'cues','segment_id')
 region_ids={r['id'] for r in regions};segs={s['id']:s for s in manifest['segments']}
 for r in regions:
  # 왼쪽 조건 패널은 중앙 풀이 칸 옆이라 상류(전자회로2)의 "work_bbox 위" 규칙을 두지 않는다. 겹침만 check_box 가 막는다.
  r['bbox']=bbox(r.get('bbox'),r['id']);check_box(r['bbox'],layers,r['id'])
 for c in cues:
  name=c['segment_id']
  if name not in segs or segs[name]['kind'] not in ('reason','check'):fail(name,'cue must target a reason/check segment')
  if c.get('target') not in region_ids:fail(name,'unknown region target')
 items=named_list((annotations or {}).get('items',[]),'annotations')
 if cues and manifest.get('cameras'):fail('focus.json','manual cameras conflict with focus cues')
 bycue={c['segment_id']:c['target'] for c in cues};offsets={};modes={}
 font=None
 for i in items:
  name=i['id'];sid=i.get('segment_id');kind=i.get('kind');g=i.get('geometry')
  if sid not in bycue or bycue[sid]!=i.get('region_id'):fail(name,'matching segment/region cue required')
  chunk=i.get('chunk_id');chunk_mode='chunk_id' in i
  if chunk_mode and (manifest.get('caption_timing')!='pcm-chunks-v1' or not isinstance(chunk,str) or chunk not in {c.get('id') for c in segs[sid].get('chunks',[])}):fail(name,'unknown chunk for segment '+sid)
  if sid in modes and modes[sid]!=chunk_mode:fail(name,'mixed segment/chunk timing for '+sid)
  modes[sid]=chunk_mode;offset_key=(sid,chunk) if chunk_mode else sid;minimum=0 if chunk_mode else 12
  if not isinstance(i.get('source_refs'),list) or not i['source_refs'] or any(not isinstance(s,str) or not s.strip() for s in i['source_refs']):fail(name,'source_refs required')
  if not isinstance(i.get('meaning_notes'),str) or not i['meaning_notes'].strip():fail(name,'meaning_notes required')
  if not isinstance(g,dict):fail(name,'geometry required')
  units=[]
  if kind in ('arrow','underline'):
   a=numbers(g.get('from'),2,name);b=numbers(g.get('to'),2,name)
   if a==b:fail(name,'zero length line')
   bounds=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]
  elif kind=='ellipse':bounds=bbox(g.get('bbox'),name)
  elif kind=='label':
   if 'stroke_width_px' in i:fail(name,'label uses font size, not stroke_width_px')
   if 'duration_frames' in i:fail(name,'label duration is fixed by character rate')
   runs=g.get('runs')
   if not isinstance(runs,list) or not runs:fail(name,'label runs required')
   if font is None:
    if not FONT.is_file():fail(name,'local label font missing')
    import fitz
    font=fitz.Font(fontfile=str(FONT))
   boxes=[]
   for run in runs:
    text=run.get('text');origin=numbers(run.get('origin'),2,name);size=run.get('font_size_pt')
    if type(size) not in (float,int) or not math.isfinite(size) or size<=0:fail(name,'positive font size required')
    if not isinstance(text,str) or not text or any(unicodedata.category(c).startswith('C') or c in '\n\r\\' for c in text):fail(name,'invalid label text')
    if any(not c.isspace() and not font.has_glyph(ord(c)) for c in text):fail(name,'unsupported font glyph')
    units.extend(text);width=font.text_length(text,fontsize=size)
    boxes.append([origin[0],origin[1]-size,origin[0]+width,origin[1]+size*.3])
   if sum(not c.isspace() for c in units)>24 or not any(not c.isspace() for c in units):fail(name,'label must contain 1..24 nonspace characters')
   bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
  else:fail(name,'unsupported kind')
  check_box(bounds,layers,name)
  color=i.get('color','#1565C0')
  if not isinstance(color,str) or not re.fullmatch('#[0-9a-fA-F]{6}',color):fail(name,'color must be #RRGGBB')
  i.update(color=color,units=units,offset_frames=integer(i.get('offset_frames',0 if chunk_mode else offsets.get(sid,12)),name,minimum),hide_at=i.get('hide_at','final'))
  if kind!='label':
   width=i.get('stroke_width_px',3)
   if type(width) not in (int,float) or not math.isfinite(width) or not 2<=width<=12:fail(name,'stroke_width_px must be finite number in 2..12')
   i['stroke_width_px']=width
   i['duration_frames']=integer(i.get('duration_frames',18),name,18)
  # 청크 항목의 오프셋은 그 청크 시작 기준이라 청크마다 따로 쌓는다. 같은 segment 안 hide 비교는 resolve_annotation_windows 가 실측 프레임으로 한다.
  if i['offset_frames']<offsets.get(offset_key,minimum):fail(name,'overlapping or reversed annotation offset')
  offsets[offset_key]=i['offset_frames']+annotation_duration(i)
  hide=i['hide_at']
  if hide!='final':
   if not isinstance(hide,dict) or hide.get('segment_id') not in segs:fail(name,'unknown hide segment')
   offset=integer(hide.get('offset_frames'),name)
   order=[s['id'] for s in manifest['segments']]
   if order.index(hide['segment_id'])<order.index(sid) or (not chunk_mode and hide['segment_id']==sid and offset<offsets[offset_key]):fail(name,'hide must follow annotation completion')
 return dict(schema_version=1,regions=regions,cues=cues,items=items) if cues or items else None

def validate_teaching(focus,annotations,manifest,layers):
 try:return _validate(copy.deepcopy(focus),copy.deepcopy(annotations),manifest,layers)
 except (KeyError,TypeError,AttributeError) as e:raise InputError('teaching malformed input: '+str(e)) from e

def load_teaching(run,manifest,layers):
 source=Path(run)/'source'
 try:return validate_teaching(read(source/'focus.json') if (source/'focus.json').exists() else None,read(source/'annotations.json') if (source/'annotations.json').exists() else None,manifest,layers)
 except (ValueError,OSError) as e:
  if isinstance(e,InputError):raise
  raise InputError('teaching sidecar: '+str(e)) from e

def compile_annotations(plan,layers,dest):
 """Generate trusted paths and font outlines only; inventory measures their real bounds."""
 import fitz,xml.etree.ElementTree as ET
 from .util import browser,file_hash,write
 from .composition import _prefix
 ns='http://www.w3.org/2000/svg';ET.register_namespace('',ns);ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
 dest=Path(dest);dest.mkdir(parents=True,exist_ok=True);m=layers['metadata']
 root=ET.Element('{'+ns+'}svg',dict(width=str(m['width_pt']),height=str(m['height_pt']),viewBox=f"0 0 {m['width_pt']} {m['height_pt']}"));group=ET.SubElement(root,'{'+ns+'}g',id='teaching-annotations');items=[];font_used=False
 for item in plan['items']:
  i=copy.deepcopy(item);ident=i['id'];g=i['geometry'];node=ET.SubElement(group,'{'+ns+'}g',id='annotation-'+ident);node.set('fill',i['color'])
  if i['kind']=='label':
   font_used=True
   if not FONT.is_file():fail(ident,'label font missing')
   font=fitz.Font(fontfile=str(FONT));doc=fitz.open();pg=doc.new_page(width=m['width_pt'],height=m['height_pt']);pg.insert_font(fontname='teaching',fontfile=str(FONT));units=[]
   for run in g['runs']:
    x,y=run['origin'];size=run['font_size_pt']
    for c in run['text']:
     if not c.isspace():pg.insert_text((x,y),c,fontname='teaching',fontsize=size)
     units.append(dict(text=c,origin=[x,y],font_size_pt=size,svg_ids=[],bbox=[x,y,x,y]));x+=font.text_length(c,fontsize=size)
   svg=_prefix(pg.get_svg_image(text_as_path=True),'annotation-'+ident+'-');doc.close()
   sub=ET.fromstring(svg);filename=dest/(ident+'.svg');filename.write_text(ET.tostring(sub,encoding='unicode'))
   inventory=browser(['--mode','inventory','--svg',str(filename.resolve())]);paint=[n for n in sub.iter() if n.tag.split('}')[-1]=='use' and 'data-text' in n.attrib];inv=[e for e in inventory if e['text'] is not None];chars=[u for u in units if not u['text'].isspace()]
   if len(inv)!=len(chars) or len(paint)!=len(chars):fail(ident,'font outline inventory differs from label')
   for u,n,e in zip(chars,paint,inv):
    if e['text']!=u['text']:fail(ident,'font outline order differs')
    if e['bbox'][0]>=e['bbox'][2] or e['bbox'][1]>=e['bbox'][3]:fail(ident,'font outline has no measurable bounds')
    sid='annotation-'+ident+'-'+e['id'];u.update(svg_ids=[sid],bbox=e['bbox']);n.set('id',sid);check_box(e['bbox'],layers,ident)
   for n in list(sub):node.append(n)
   boxes=[u['bbox'] for u in chars];i['glyphs']=units;i['body_height']=max(b[3]-b[1] for b in boxes)
  else:
   if i['kind']=='ellipse':
    x0,y0,x1,y1=g['bbox'];cx=(x0+x1)/2;cy=(y0+y1)/2;rx=(x1-x0)/2;ry=(y1-y0)/2
    d=f'M {cx} {y0} A {rx} {ry} 0 0 1 {cx} {y1} A {rx} {ry} 0 0 1 {cx} {y0}';start=[cx,y0]
   else:
    a,b=g['from'],g['to'];d=f'M {a[0]} {a[1]} L {b[0]} {b[1]}';start=a
    if i['kind']=='arrow':
     dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);size=min(6,length/3);ux,uy=dx/length,dy/length
     left=[b[0]-size*ux-size*.5*uy,b[1]-size*uy+size*.5*ux];right=[b[0]-size*ux+size*.5*uy,b[1]-size*uy-size*.5*ux]
     d+=f' L {left[0]} {left[1]} L {b[0]} {b[1]} L {right[0]} {right[1]}'
   path=ET.SubElement(node,'{'+ns+'}path',id='annotation-'+ident+'-path',d=d,fill='none',stroke=i['color'],**{'stroke-width':'3','vector-effect':'non-scaling-stroke','stroke-linecap':'round','stroke-linejoin':'round'})
   i.update(path=d,path_id=path.get('id'),start_point=start,body_height=None)
   temp=dest/(ident+'.svg');temp.write_text(ET.tostring(root,encoding='unicode'))
   inv=browser(['--mode','inventory','--svg',str(temp.resolve())]);entry=inv[-1];boxes=[entry['bbox']]
  i['bbox']=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)];check_box(i['bbox'],layers,ident);items.append(i)
 path=dest/'annotations.svg';path.write_text(ET.tostring(root,encoding='unicode'))
 result=dict(items=items,svg=str(path.resolve()),font_sha256=file_hash(FONT) if font_used else None);write(dest/'compiled.json',result);return result
