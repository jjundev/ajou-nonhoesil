(function(root){
 const clamp=n=>Math.max(0,Math.min(1,n));
 function frameState(schedule,frame){
  const spans=schedule.spans||[],active=spans.find(s=>s.start_frame<=frame&&frame<s.end_frame&&frame<s.hide_frame)||null;
  const visible_ids=[...new Set(spans.filter(s=>s.kind==='draw'&&s.start_frame<=frame&&frame<s.hide_frame).map(s=>s.id))];
  return {active,progress:active?(active.end_frame-active.start_frame===1?1:clamp((frame-active.start_frame)/(active.end_frame-active.start_frame-1))):0,visible_ids};
 }
 function createRenderer(svg,compiled){
  const ns='http://www.w3.org/2000/svg',nodes=new Map(),defs=document.createElementNS(ns,'defs');svg.append(defs);
  for(const i of compiled.items){
   const group=svg.querySelector('#annotation-'+i.id);if(!group)throw Error('missing annotation '+i.id);
   const glyphs=[];
   for(const [index,g] of (i.glyphs||[]).entries()){
    const entries=[];
    for(const sid of g.svg_ids){
     const n=svg.querySelector('[id="'+sid+'"]');if(!n)throw Error('missing annotation glyph '+sid);
     const wrapper=document.createElementNS(ns,'g'),clip=document.createElementNS(ns,'clipPath'),rect=document.createElementNS(ns,'rect');clip.id='annotation-clip-'+i.id+'-'+index;clip.setAttribute('clipPathUnits','userSpaceOnUse');clip.append(rect);defs.append(clip);
     const parent=n.parentNode,matrix=parent.getScreenCTM().inverse().multiply(svg.getScreenCTM());rect.setAttribute('transform',`matrix(${matrix.a} ${matrix.b} ${matrix.c} ${matrix.d} ${matrix.e} ${matrix.f})`);parent.insertBefore(wrapper,n);wrapper.append(n);entries.push({n,wrapper,clip,rect});
    }
    glyphs.push(entries);
   }
   nodes.set(i.id,{group,path:i.path_id?svg.querySelector('#'+i.path_id):null,glyphs,item:i});
  }
  let state={visible:false};
  function render(schedule,frame,camera,layout){
   const fs=frameState(schedule,frame),active=fs.active;let tip=null;
   for(const [id,entry] of nodes){
    const itemSpans=schedule.spans.filter(s=>s.id===id),shown=fs.visible_ids.includes(id);entry.group.style.opacity=shown?'1':'0';
    if(entry.path){
     // Screen-constant width without Blink's viewBox-dependent non-scaling-stroke cache.
     entry.path.setAttribute('vector-effect','none');entry.path.style.strokeWidth=String(3/Math.min(1920/camera[2],layout.height/camera[3]));
     const draw=itemSpans.find(s=>s.kind==='draw'),progress=draw&&frame>=draw.start_frame&&frame<draw.hide_frame?(frame>=draw.end_frame?1:clamp((frame-draw.start_frame)/(draw.end_frame-draw.start_frame-1))):0;
     const length=entry.path.getTotalLength();entry.path.style.strokeDasharray=String(length);entry.path.style.strokeDashoffset=String(length*(1-progress));
    }
    for(const [n,glyph] of entry.glyphs.entries()){
     const draw=itemSpans.find(s=>s.kind==='draw'&&s.unit_index===n),current=active?.id===id&&active.kind==='draw'&&active.unit_index===n;
     for(const e of glyph){
      e.n.style.opacity=draw&&frame>=draw.start_frame&&frame<draw.hide_frame?'1':'0';
      if(current){const b=entry.item.glyphs[n].bbox;e.rect.setAttribute('x',b[0]-1);e.rect.setAttribute('y',b[1]-1);e.rect.setAttribute('height',b[3]-b[1]+2);e.rect.setAttribute('width',Math.max(0,(b[2]-b[0])*fs.progress+1+(fs.progress===1?1:0)));e.wrapper.setAttribute('clip-path','url(#'+e.clip.id+')');}else e.wrapper.removeAttribute('clip-path');
     }
    }
   }
   const entry=active&&nodes.get(active.id),show=!!entry&&active.kind!=='space';
   function point(e,unit,progress){if(e.path){const p=e.path.getPointAtLength(e.path.getTotalLength()*progress);return [p.x,p.y];}const b=e.item.glyphs[unit].bbox;return [b[0]+(b[2]-b[0])*progress,b[1]+.8*(b[3]-b[1])];}
   if(show){
    let p=point(entry,active.unit_index,active.kind==='draw'?fs.progress:0);
    if(active.kind==='move'){
     const cue=schedule.cues.find(c=>c.start_frame<=frame&&frame<c.end_frame);
     const prior=schedule.spans.filter(s=>s.kind==='draw'&&s.end_frame<=active.start_frame&&s.start_frame>=(cue?.start_frame||0)).at(-1);
     if(prior){const from=point(nodes.get(prior.id),prior.unit_index,1);p=[from[0]+(p[0]-from[0])*fs.progress,from[1]+(p[1]-from[1])*fs.progress];}
    }
    tip=root.EC2Camera.pageToScreen(p,camera,layout);
   }
   state={...fs,active_id:active?.id||null,kind:active?.kind||null,visible:show,tip_screen:tip,tilt_degrees:active?.kind==='draw'?2*Math.sin(2*Math.PI*fs.progress):0,mirror:false,owner:'annotation'};return state;
  }
  return {render,snapshot:()=>state};
 }
 const api={frameState,createRenderer};if(typeof module!=='undefined')module.exports=api;root.EC2Annotations=api;
})(typeof window==='undefined'?globalThis:window);
