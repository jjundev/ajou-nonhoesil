"""Export original glyph outlines. Bboxes are measured from the same SVG DOM."""
from pathlib import Path
import copy,xml.etree.ElementTree as ET,unicodedata
from .util import browser,write,read,file_hash
from .contracts import ExtractionError
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS); ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
ALLOWED={'fraction_bar','radical_bar','step_badge','answer_box','bullet'}
def _painted(root):
    out=[]
    def walk(node,in_defs=False):
        in_defs=in_defs or node.tag==f'{{{NS}}}defs'
        if not in_defs and (node.tag.split('}')[-1] in {'path','rect','line','circle','ellipse','polygon','image'} or node.tag.split('}')[-1]=='use' and 'data-text' in node.attrib): out.append(node)
        for child in node: walk(child,in_defs)
    walk(root); return out

def export_page(pdf,page_index,dest):
    try: import fitz
    except ImportError: raise ExtractionError('PyMuPDF missing in this Python; use a configured interpreter') from None
    dest=Path(dest); dest.mkdir(parents=True,exist_ok=True)
    with fitz.open(pdf) as doc:
        pg=doc[page_index]; svg=pg.get_svg_image(text_as_path=True)
        if 'data-text=' not in svg: raise ExtractionError('scan-only or no extractable glyphs')
        pg.get_pixmap(matrix=fitz.Matrix(2,2)).save(dest/'native.png')
        metadata={'source_sha256':file_hash(pdf),'page_index':page_index,'width_pt':pg.rect.width,'height_pt':pg.rect.height,'pymupdf':fitz.VersionBind}
    original=dest/'original.svg'; original.write_text(svg,encoding='utf-8')
    items=browser(['--mode','inventory','--svg',str(original.resolve())]); root=ET.fromstring(svg); nodes=_painted(root)
    if len(items)!=len(nodes): raise ExtractionError('SVG paint inventory differs')
    glyphs=[]; shapes=[]; images=[]
    for i,(item,node) in enumerate(zip(items,nodes)):
        node.set('id',item['id']); b=item['bbox']
        if item['text'] is not None:
            g=dict(id=f'g{i:05d}',text=item['text'],bbox=b,svg_ids=[item['id']],paint_order=i)
            # PDF decomposed Hangul/combining marks remain original paths, grouped once.
            if glyphs and (unicodedata.combining(g['text']) or '\u1160'<=g['text'][:1]<='\u11ff'):
                prev=glyphs[-1]; prev['text']+=g['text']; prev['svg_ids']+=g['svg_ids']; prev['bbox']=[min(prev['bbox'][0],b[0]),min(prev['bbox'][1],b[1]),max(prev['bbox'][2],b[2]),max(prev['bbox'][3],b[3])]
            else: glyphs.append(g)
        elif item['tag']=='image': images.append(item)
        else:
            w,h=b[2]-b[0],b[3]-b[1]
            kind='answer_box' if w<=3 and h>=15 else 'fraction_bar' if h<=2 and w>3 else 'radical_bar' if w<=2 and h>3 else 'step_badge' if 6<=w<=20 and 6<=h<=20 else 'bullet' if w<=5 and h<=5 else 'answer_box' if w>50 and 15<=h<=180 else 'unclassified'
            shapes.append(dict(id=f's{i:05d}',bbox=b,svg_ids=[item['id']],kind=kind,paint_order=i))
    candidate=dest/'candidate.svg'; candidate.write_text(ET.tostring(root,encoding='unicode'),encoding='utf-8')
    result=dict(original_svg=str(original.resolve()),animated_svg=str(candidate.resolve()),reference_png=str((dest/'native.png').resolve()),glyphs=glyphs,shapes=shapes,map=None,images=images,metadata=metadata)
    write(dest/'candidates.json',result); return result

def inside(b,region,tol=0.01): return b[0]>=region[0]-tol and b[1]>=region[1]-tol and b[2]<=region[2]+tol and b[3]<=region[3]+tol

def extract_layers(page,mapping):
    if not mapping.get('steps') or mapping['steps'][-1]['id']!=mapping['answer_step_id']: raise ExtractionError('answer must be last mapped step')
    region=mapping['work_bbox']
    if len(region)!=4 or region[0]>=region[2] or region[1]>=region[3]: raise ExtractionError('invalid work bbox')
    selected=[]
    for step in mapping['steps']: selected+=step['glyph_ids']+step['shape_ids']
    if len(selected)!=len(set(selected)): raise ExtractionError('duplicate reveal ID')
    all_items={i['id']:i for i in page['glyphs']+page['shapes']}
    if not set(selected)<=all_items.keys(): raise ExtractionError('unknown reveal ID')
    if any(not inside(all_items[i]['bbox'],region) for i in selected): raise ExtractionError('writing outside work bbox')
    # All text/paint wholly inside the authored writing region must be accounted for.
    expected={i['id'] for i in page['glyphs']+page['shapes'] if inside(i['bbox'],region)}
    if set(selected)!=expected: raise ExtractionError('unmapped work glyph/shape: '+str(sorted(expected-set(selected))[:8]))
    if any(inside(i['bbox'],region) for i in page.get('images',[])): raise ExtractionError('solution region contains image; cannot reveal raster glyphs')
    if any(all_items[i].get('kind')=='unclassified' for i in selected): raise ExtractionError('unclassified work shape; inspect and assign its supported kind in candidates.json')
    result=copy.deepcopy(page); result['glyphs']=[g for g in page['glyphs'] if g['id'] in selected]; result['shapes']=[s for s in page['shapes'] if s['id'] in selected]; result['map']=copy.deepcopy(mapping)
    root=ET.parse(page['animated_svg']).getroot(); dom={n.get('id'):n for n in root.iter()}
    for i in selected:
        for sid in all_items[i]['svg_ids']:
            n=dom[sid]; n.set('data-reveal',i); n.set('style',n.get('style','')+';opacity:0')
    dest=Path(page['original_svg']).parent/'animated.svg'; dest.write_text(ET.tostring(root,encoding='unicode'),encoding='utf-8'); result['animated_svg']=str(dest.resolve()); return result

def compare_completed(page,evidence):
    from PIL import Image,ImageChops
    evidence=Path(evidence).resolve(); evidence.mkdir(parents=True,exist_ok=True); write(evidence/'layers.json',page)
    r=browser(['--mode','gate','--layers',str(evidence/'layers.json'),'--dest',str(evidence)])
    load=lambda n:Image.open(evidence/(n+'.png')).convert('RGB')
    a,b,empty,removed=map(load,['original','complete','empty','removed'])
    diff=lambda x,y:sum(p!=(0,0,0) for p in ImageChops.difference(x,y).getdata())
    # Outside exact painted-target bboxes pixels must remain identical.
    outside=ImageChops.difference(a,empty)
    from PIL import ImageDraw
    draw=ImageDraw.Draw(outside); meta=page['metadata']; sx=r['width']/meta['width_pt']; sy=r['height']/meta['height_pt']
    for obj in page['glyphs']+page['shapes']:
        x0,y0,x1,y1=obj['bbox']; draw.rectangle((x0*sx-3,y0*sy-3,x1*sx+3,y1*sy+3),fill=(0,0,0))
    result=dict(pixel_diff=diff(a,b),non_target_diff=sum(p!=(0,0,0) for p in outside.getdata()),hidden_leaks=diff(empty,removed),evidence=[str(evidence/n) for n in r['evidence']])
    write(evidence/'gate.json',result); return result
