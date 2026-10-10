import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
export async function teachingCheck(page,opt){
 const capture=async options=>{await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));return page.screenshot(options);};
 const dest=opt('dest');if(dest)fs.mkdirSync(dest,{recursive:true});
 const layers=JSON.parse(fs.readFileSync(opt('layers'),'utf8')),original=fs.readFileSync(layers.original_svg,'utf8');
 await page.setViewport({width:1920,height:1080});await page.goto(pathToFileURL(opt('entry')).href);
 await page.waitForFunction(()=>typeof window.renderSolutionFrame==='function');await page.evaluate(async()=>{for(const i of document.images)await i.decode();});
 const actual=await page.evaluate(()=>({timeline:window.solutionTimeline,compiled:window.solutionAnnotationsData||null}));
 const expected=opt('timeline')?JSON.parse(fs.readFileSync(opt('timeline'),'utf8')):actual,t=expected.timeline||expected;
 const compiled=Object.hasOwn(expected,'compiled')?expected.compiled:actual.compiled;
 const annotationSvg=compiled?fs.readFileSync(compiled.svg,'utf8'):null;
 let result={timeline_equal:true,geometry_equal:true,cameras_equal:true,seek_equal:true,gsap_seek_equal:true,bounds_ok:true,inactive_hidden:true,tip_error_px:0,original_pixel_diff:0,annotation_pixel_diff:0,future_leaks:0,final_visible:false,evidence:[],seek_debug:[]};
 const withoutCamera=x=>JSON.stringify({...x,cameras:[]});result.timeline_equal=withoutCamera(actual.timeline)===withoutCamera(t);
 result.cameras_equal=JSON.stringify(actual.timeline.cameras)===JSON.stringify(t.cameras);
 result.geometry_equal=JSON.stringify({...actual.compiled,svg:null})===JSON.stringify({...compiled,svg:null});
 result.lesson_flow=true;
 for(const probe of expected.lesson?.probes||[]){
  await page.evaluate(f=>window.renderSolutionFrame(f),probe.frame);
  result.lesson_flow&&=await page.evaluate(probe=>{
   const svg=document.querySelector('#answer-page>svg'),m=svg.getScreenCTM(),b=probe.region_bbox;
   const corners=[[b[0],b[1]],[b[2],b[3]]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
   const regionOK=corners.every(p=>p.x>=0&&p.x<=1920&&p.y>=0&&p.y<=900);
   const shown=node=>{if(!node)return false;for(let n=node;n&&n instanceof Element;n=n.parentElement)if(getComputedStyle(n).opacity==='0'||getComputedStyle(n).display==='none'||getComputedStyle(n).visibility==='hidden')return false;return true;};
   return regionOK&&probe.annotation_ids.every(id=>{const n=svg.querySelector('#annotation-'+id);if(!shown(n))return false;const r=n.getBoundingClientRect(),path=n.querySelector('path[stroke]');
    // SVG geometric rectangles exclude stroke; a horizontal underline has zero
    // geometric height while its painted stroke is valid teaching evidence.
    const radius=path?parseFloat(getComputedStyle(path).strokeWidth)*Math.hypot(m.a,m.b)/2:0;
    return r.width+2*radius>0&&r.height+2*radius>0&&r.left-radius>=0&&r.right+radius<=1920&&r.top-radius>=0&&r.bottom+radius<=900;});
  },probe);
 }
 const frames=new Set([0,t.total_frames-1]);
 for(const c of t.teaching.cues)for(const f of [c.start_frame,c.start_frame+6,c.start_frame+12,c.end_frame-12,c.end_frame-6,c.end_frame])frames.add(f);
 for(const s of t.teaching.spans)for(const f of [s.start_frame,Math.floor((s.start_frame+s.end_frame-1)/2),s.end_frame-1,s.end_frame,s.hide_frame-1,s.hide_frame])frames.add(f);
 for(const s of (t.writing_spans||[]).filter(s=>s.kind==='draw')){frames.add(s.start_frame);break;}
 const progress=(s,f)=>s.end_frame-s.start_frame===1?1:Math.max(0,Math.min(1,(f-s.start_frame)/(s.end_frame-s.start_frame-1)));
 for(const frame of [...frames].filter(f=>f>=0&&f<t.total_frames).sort((a,b)=>a-b)){
  await page.evaluate(f=>window.renderSolutionFrame(f),frame);
  const stats=await page.evaluate(({t,compiled,frame})=>{
   // Independent camera interpolation and geometry/endpoints, not renderer snapshots.
   const keys=t.cameras;let current=keys[0],prior=keys[0];for(let n=1;n<keys.length&&keys[n].at_frame<=frame;n++){prior=keys[n-1];current=keys[n];}
   const u=current.transition_frames?Math.max(0,Math.min(1,(frame-current.at_frame)/current.transition_frames)):1,e=u*u*(3-2*u),box=current.viewbox.map((v,n)=>prior.viewbox[n]+(v-prior.viewbox[n])*e);
   const svg=document.querySelector('#answer-page>svg'),actualBox=svg.getAttribute('viewBox').split(/\s+/).map(Number),camera_ok=box.every((v,n)=>Math.abs(v-actualBox[n])<1e-6);
   const span=t.teaching.spans.find(s=>s.start_frame<=frame&&frame<s.end_frame&&frame<s.hide_frame),should=span&&span.kind!=='space',im=document.getElementById('pencil'),snapshot=window.solutionPen?.snapshot(),visible=!!im&&getComputedStyle(im).opacity!=='0';
   const originalActive=(t.writing_spans||[]).find(s=>s.start_frame<=frame&&frame<s.end_frame);
   let bounds_ok=true,tip=0,bounds_debug=[];
   if(visible){
    const meta=window.pencilMeta,m=new DOMMatrix(getComputedStyle(im).transform),b=meta.visible_bounds_px,origin=meta.tip_px;
    const cs=[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]].map(([x,y])=>new DOMPoint(x-origin[0],y-origin[1]).matrixTransform(m)).map(p=>[p.x+origin[0],p.y+origin[1]]);
    bounds_ok=cs.every(p=>p[0]>=-1e-3&&p[0]<=1920.001&&p[1]>=-1e-3&&p[1]<=900.001);
    const a=new DOMPoint(0,0).matrixTransform(m),z=new DOMPoint(meta.end_px[0]-origin[0],meta.end_px[1]-origin[1]).matrixTransform(m);bounds_ok&&=Math.abs(Math.hypot(z.x-a.x,z.y-a.y)-(t.writing?.pencil_length_px||160))<=.5;
    if(span?.kind==='draw'){
     const i=compiled.items.find(i=>i.id===span.id),p=(frame-span.start_frame)/(span.end_frame-span.start_frame-1);let xy;
     if(i.path){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',i.path);svg.append(path);const q=path.getPointAtLength(path.getTotalLength()*p);xy=[q.x,q.y];path.remove();}
     else {const b=i.glyphs[span.unit_index].bbox;xy=[b[0]+(b[2]-b[0])*p,b[1]+.8*(b[3]-b[1])];}
     const sc=Math.min(1920/box[2],window.solutionLayout.height/box[3]),want=[(1920-box[2]*sc)/2+(xy[0]-box[0])*sc,(window.solutionLayout.height-box[3]*sc)/2+(xy[1]-box[1])*sc];tip=Math.hypot(origin[0]+a.x-want[0],origin[1]+a.y-want[1]);
    }
   }
   let future=0,final=false;
   for(const i of compiled?.items||[]){const node=svg.querySelector('#annotation-'+i.id),spans=t.teaching.spans.filter(s=>s.id===i.id),show=spans.some(s=>s.kind==='draw'&&s.start_frame<=frame&&frame<s.hide_frame),painted=node&&getComputedStyle(node).opacity!=='0';if(painted&&!show)future++;if(frame===t.total_frames-1&&painted)final=true;if(!node)bounds_ok=false;
    const focused=t.teaching.cues.some(c=>c.target===i.region_id&&c.start_frame+12<=frame&&frame<c.end_frame-12);
    if(painted&&node&&focused){const r=node.getBoundingClientRect(),radius=i.kind==='label'?0:(i.stroke_width_px??3)/2;
     const fits=r.left-radius>=-1e-3&&r.right+radius<=1920.001&&r.top-radius>=-1e-3&&r.bottom+radius<=900.001;bounds_ok&&=fits;if(!fits)bounds_debug.push({id:i.id,rect:[r.left,r.top,r.right,r.bottom],radius});
     if(i.path_id){const path=svg.querySelector('#'+i.path_id),sc=Math.min(1920/box[2],window.solutionLayout.height/box[3]);const width=parseFloat(getComputedStyle(path).strokeWidth)*sc,ok=Math.abs(width-(i.stroke_width_px??3))<1e-3;bounds_ok&&=ok;if(!ok)bounds_debug.push({id:i.id,width,expected:i.stroke_width_px??3});}
    }}
   return {camera_ok,bounds_ok,bounds_debug,tip,future,final,inactive_hidden:should?visible&&snapshot?.owner==='annotation':originalActive?true:!visible};
  },{t,compiled,frame});
  if(stats.bounds_debug.length)(result.bounds_debug??=[]).push({frame,items:stats.bounds_debug});
  result.cameras_equal&&=stats.camera_ok;result.bounds_ok&&=stats.bounds_ok;result.inactive_hidden&&=stats.inactive_hidden;result.tip_error_px=Math.max(result.tip_error_px,stats.tip);result.future_leaks+=stats.future;result.final_visible||=stats.final;
  // Backward and GSAP seeks must reconstruct the same pixels including the pencil.
  const shot=await capture();await page.evaluate(()=>window.renderSolutionFrame(0));await page.evaluate(f=>window.renderSolutionFrame(f),frame);const backward=await capture();const seekOK=Buffer.from(shot).equals(Buffer.from(backward));result.seek_equal&&=seekOK;if(!seekOK&&dest){fs.writeFileSync(dest+'/seek-before-'+frame+'.png',shot);fs.writeFileSync(dest+'/seek-after-'+frame+'.png',backward);result.seek_debug.push(frame);}
  await page.evaluate(f=>{window.__timelines.solution.seek(0,false);window.__timelines.solution.seek(f/30,false);},frame);result.gsap_seek_equal&&=Buffer.from(shot).equals(Buffer.from(await capture()));
  await page.evaluate(f=>{window.renderSolutionFrame(f);const im=document.getElementById('pencil');if(im)im.style.opacity='0';document.getElementById('cursor').style.opacity='0';},frame);
  const combined=await capture(dest?{path:dest+'/teaching-'+frame+'.png'}:{});
  await page.evaluate(()=>{const g=document.getElementById('teaching-annotations');if(g)g.style.opacity='0';});
  const base=await capture();
  await page.evaluate(({original,annotationSvg,t,layers,compiled,frame})=>{
   const ns='http://www.w3.org/2000/svg',host=document.getElementById('answer-page'),actual=host.firstElementChild;
   const parser=new DOMParser(),ref=parser.parseFromString(original,'image/svg+xml').documentElement;
   [...ref.querySelectorAll('use[data-text],path,rect,line,circle,ellipse,polygon,image')].filter(n=>!n.closest('defs')).forEach((n,i)=>n.id='sv-'+i);
   ref.id='teaching-reference';ref.style.position='absolute';ref.style.left='0';ref.style.top='0';ref.setAttribute('viewBox',actual.getAttribute('viewBox'));host.append(ref);actual.style.opacity='0';
   const done=new Set(t.events.filter(e=>e.frame<=frame).map(e=>e.id)),writing=(t.writing_spans||[]).find(s=>s.kind==='draw'&&s.start_frame<=frame&&frame<s.end_frame);
   function clip(node,b,p,name){const parent=node.parentNode,m=parent.getScreenCTM().inverse().multiply(ref.getScreenCTM()),defs=document.createElementNS(ns,'defs'),c=document.createElementNS(ns,'clipPath'),r=document.createElementNS(ns,'rect'),w=document.createElementNS(ns,'g');c.id=name;c.setAttribute('clipPathUnits','userSpaceOnUse');r.setAttribute('transform',`matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e} ${m.f})`);r.setAttribute('x',b[0]-1);r.setAttribute('y',b[1]-1);r.setAttribute('width',1+(b[2]-b[0])*p+(p===1?1:0));r.setAttribute('height',b[3]-b[1]+2);c.append(r);defs.append(c);ref.append(defs);parent.insertBefore(w,node);w.append(node);w.setAttribute('clip-path','url(#'+name+')');}
   for(const obj of [...layers.glyphs,...layers.shapes])for(const sid of obj.svg_ids){
    const node=ref.querySelector('[id="'+sid+'"]');if(!node)throw Error('oracle glyph missing');
    if(t.writing_unit_spans&&!done.has(obj.id)){
     const parts=t.writing_spans.filter(s=>s.kind==='draw'&&s.id===obj.id&&s.start_frame<=frame);
     if(!parts.length){node.remove();continue;}
     const parent=node.parentNode,m=parent.getScreenCTM().inverse().multiply(ref.getScreenCTM()),defs=document.createElementNS(ns,'defs'),c=document.createElementNS(ns,'clipPath'),w=document.createElementNS(ns,'g');
     c.id='oracle-writing-'+sid;c.setAttribute('clipPathUnits','userSpaceOnUse');
     for(const part of parts){const b=part.clip_bbox,p=frame>=part.end_frame?1:(frame-part.start_frame)/(part.end_frame-part.start_frame-1),r=document.createElementNS(ns,'rect');r.setAttribute('transform',`matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e} ${m.f})`);const vertical=part.target_kind==='shape'&&b[2]===b[0];r.setAttribute('x',b[0]-(vertical?1:0));r.setAttribute('y',b[1]-1);r.setAttribute('width',vertical?2:Math.max(0,(b[2]-b[0])*p));r.setAttribute('height',(b[3]-b[1])*(vertical?p:1)+2);c.append(r);}
     defs.append(c);ref.append(defs);parent.insertBefore(w,node);w.append(node);w.setAttribute('clip-path','url(#'+c.id+')');
    }else if(!done.has(obj.id)&&writing?.id!==obj.id)node.remove();else if(writing?.id===obj.id)clip(node,obj.bbox,(frame-writing.start_frame)/(writing.end_frame-writing.start_frame-1),'oracle-writing-'+sid);
   }
   function namespace(root){
    const nodes=[...root.querySelectorAll('[id]')],map=new Map(nodes.map(n=>[n.id,'oracle-'+n.id]));
    for(const node of nodes)node.id=map.get(node.id);
    for(const node of root.querySelectorAll('*'))for(const attr of [...node.attributes]){
     const value=attr.value.replace(/#([A-Za-z0-9_-]+)/g,(match,id)=>map.has(id)?'#'+map.get(id):match);
     if(value!==attr.value){if(attr.namespaceURI)node.setAttributeNS(attr.namespaceURI,attr.name,value);else node.setAttribute(attr.name,value);}
    }
   }
   namespace(ref);
   if(annotationSvg){const g=parser.parseFromString(annotationSvg,'image/svg+xml').documentElement.querySelector('g');g.id='oracle-annotations';g.style.opacity='0';ref.append(g);
    for(const item of compiled.items){const node=g.querySelector('#annotation-'+item.id),spans=t.teaching.spans.filter(s=>s.id===item.id);node.style.opacity=spans.some(s=>s.kind==='draw'&&s.start_frame<=frame&&frame<s.hide_frame)?'1':'0';
     if(item.path){const b=ref.viewBox.baseVal,sc=Math.min(1920/b.width,window.solutionLayout.height/b.height),draw=spans.find(s=>s.kind==='draw'),path=node.querySelector('path'),p=frame>=draw.end_frame?1:Math.max(0,(frame-draw.start_frame)/(draw.end_frame-draw.start_frame-1));if(item.kind==='arrow'){
      const a=item.geometry.from,b=item.geometry.to,dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy),size=Math.min(6,length/3),ux=dx/length,uy=dy/length;
      const left=[b[0]-size*ux-size*.5*uy,b[1]-size*uy+size*.5*ux],right=[b[0]-size*ux+size*.5*uy,b[1]-size*uy-size*.5*ux];
      path.setAttribute('d',`M ${a[0]} ${a[1]} L ${b[0]} ${b[1]} L ${left[0]} ${left[1]} L ${b[0]} ${b[1]} L ${right[0]} ${right[1]}`);
     }
     path.setAttribute('vector-effect','none');path.style.strokeWidth=String((item.stroke_width_px??3)/sc);path.style.strokeDasharray=String(path.getTotalLength());path.style.strokeDashoffset=String(path.getTotalLength()*(1-p));}
     else for(const [u,glyph] of item.glyphs.entries()){const s=spans.find(s=>s.kind==='draw'&&s.unit_index===u),show=s&&s.start_frame<=frame&&frame<s.hide_frame;for(const sid of glyph.svg_ids){const n=node.querySelector('[id="'+sid+'"]');n.style.opacity=show?'1':'0';if(show&&frame<s.end_frame)clip(n,glyph.bbox,(frame-s.start_frame)/(s.end_frame-s.start_frame-1),'oracle-label-'+sid);}}
    }
    namespace(g);
   }
  },{original,annotationSvg,t,layers,compiled,frame});
  const reference=await capture();result.original_pixel_diff+=Buffer.from(base).equals(Buffer.from(reference))?0:1;
  await page.evaluate(()=>{const g=document.getElementById('oracle-annotations');if(g)g.style.opacity='1';});
  const expectedShot=await capture(dest?{path:dest+'/oracle-'+frame+'.png'}:{});result.annotation_pixel_diff+=Buffer.from(combined).equals(Buffer.from(expectedShot))?0:1;
  await page.evaluate(()=>{document.getElementById('teaching-reference').remove();document.querySelector('#answer-page>svg').style.opacity='1';const g=document.getElementById('teaching-annotations');if(g)g.style.opacity='1';});
 }
 result.evidence=dest?fs.readdirSync(dest).filter(n=>n.endsWith('.png')).map(n=>dest+'/'+n):[];return result;
}
