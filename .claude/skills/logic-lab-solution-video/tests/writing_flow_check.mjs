/* Independent geometry oracle: authored bands and original target bboxes define order/fit. */
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
export async function writingFlowCheck(page,opt){
 const layers=JSON.parse(fs.readFileSync(opt('layers'),'utf8')),dest=opt('dest');fs.mkdirSync(dest,{recursive:true});
 await page.setViewport({width:1920,height:1080});await page.goto(pathToFileURL(opt('entry')).href);
 await page.waitForFunction(()=>typeof window.renderSolutionFrame==='function');
 await page.evaluate(async()=>{for(const im of document.images)await im.decode();});
 const result=await page.evaluate(layers=>{
  window.renderSolutionFrame(0);
  const t=window.solutionTimeline,units=layers.map.steps.flatMap(s=>s.writing_units.map(u=>({...u,step_id:s.id}))),objects=new Map([...layers.glyphs,...layers.shapes].map(o=>[o.id,o]));
  const draws=t.writing_spans.filter(s=>s.kind==='draw');let order_ok=true,fit_ok=true,transitions_ok=true,stable_camera=true;
  const expected=[];
  for(const u of units){
   const parts=[...u.glyph_ids.map(id=>({id,kind:'glyph'})),...u.shape_ids.map(id=>({id,kind:'shape'}))].map(p=>{
    const o=objects.get(p.id),b=o.bbox;return {...p,b:[Math.max(b[0],u.band[0]),b[1],Math.min(b[2],u.band[1]),b[3]],paint:o.paint_order};
   }).sort((a,b)=>a.b[0]-b.b[0]||a.b[1]-b.b[1]||a.paint-b.paint);
   for(const p of parts)if(p.kind==='shape'||objects.get(p.id).text.trim())expected.push({...p,unit_id:u.id});
  }
  order_ok=draws.length===expected.length&&draws.every((s,i)=>s.id===expected[i].id&&s.unit_id===expected[i].unit_id&&JSON.stringify(s.clip_bbox)===JSON.stringify(expected[i].b));
  for(const k of t.cameras){if(k.transition_frames)for(const s of draws)transitions_ok&&=Math.max(k.at_frame,s.start_frame)>=Math.min(k.at_frame+k.transition_frames,s.end_frame);}
  const m=window.pencilMeta,len=t.writing.pencil_length_px,unit=len/Math.hypot(m.end_px[0]-m.tip_px[0],m.end_px[1]-m.tip_px[1]),envelope=[];
  for(const angle of [-t.writing.tilt_degrees,0,t.writing.tilt_degrees])for(const x of [m.visible_bounds_px[0],m.visible_bounds_px[2]])for(const y of [m.visible_bounds_px[1],m.visible_bounds_px[3]]){
   const a=angle*Math.PI/180,dx=(x-m.tip_px[0])*unit,dy=(y-m.tip_px[1])*unit;envelope.push([dx*Math.cos(a)-dy*Math.sin(a),dx*Math.sin(a)+dy*Math.cos(a)]);
  }
  const groups=new Map();for(const u of units){const k=u.line_id+'|'+u.chunk_id;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(u);}
  for(const group of groups.values()){
   const ids=new Set(group.map(u=>u.id)),ss=draws.filter(s=>ids.has(s.unit_id)),first=ss[0];if(!first){fit_ok=false;continue;}
   window.renderSolutionFrame(first.start_frame);const view=document.querySelector('#answer-page>svg').getAttribute('viewBox');
   for(const s of ss){window.renderSolutionFrame(s.end_frame-1);stable_camera&&=document.querySelector('#answer-page>svg').getAttribute('viewBox')===view;}
   const v=view.split(' ').map(Number),scale=Math.min(1920/v[2],window.solutionLayout.height/v[3]);
   const pageToScreen=(x,y)=>[(1920-v[2]*scale)/2+(x-v[0])*scale,(window.solutionLayout.height-v[3]*scale)/2+(y-v[1])*scale];
   for(const u of group)for(const id of [...u.glyph_ids,...u.shape_ids]){
    const o=objects.get(id),b=o.bbox;if(o.text?.trim()==='')continue;
    const lo=Math.max(b[0],u.band[0]),hi=Math.min(b[2],u.band[1]);
    for(const [x,y] of [[lo,b[1]],[hi,b[3]]]){const p=pageToScreen(x,y);fit_ok&&=p[0]>=-.01&&p[0]<=1920.01&&p[1]>=-.01&&p[1]<=900.01;}
    for(const x of [lo,hi])for(const y of !o.text&&lo===hi?[b[1],b[3]]:[b[1]+.8*(b[3]-b[1])]){const tip=pageToScreen(x,y);for(const e of envelope)fit_ok&&=tip[0]+e[0]>=-.01&&tip[0]+e[0]<=1920.01&&tip[1]+e[1]>=-.01&&tip[1]+e[1]<=900.01;}
   }
   for(const step of new Set(group.map(u=>u.step_id))){
    const heights=layers.map.steps.find(s=>s.id===step).glyph_ids.map(id=>objects.get(id)).filter(g=>g.text.trim()&&g.bbox[3]-g.bbox[1]>=2).map(g=>g.bbox[3]-g.bbox[1]).sort((a,b)=>a-b);
    fit_ok&&=heights[Math.floor((heights.length-1)*.75)]*scale>=25.99;
   }
  }
  return {order_ok,fit_ok,transitions_ok,stable_camera,frames:[...new Set(draws.flatMap(s=>[s.start_frame,s.end_frame-1]))]};
 },layers);
 let seek_equal=true;const evidence=[];
 for(const f of result.frames.filter((_,i,a)=>i===0||i===Math.floor(a.length/2)||i===a.length-1)){
  await page.evaluate(f=>window.renderSolutionFrame(f),f);const p=dest+'/flow-'+f+'.png',direct=await page.screenshot({path:p});evidence.push(p);
  await page.evaluate(f=>{window.renderSolutionFrame(window.solutionTimeline.total_frames-1);window.renderSolutionFrame(f);},f);seek_equal&&=Buffer.from(direct).equals(Buffer.from(await page.screenshot()));
 }
 delete result.frames;return {...result,seek_equal,evidence};
}
