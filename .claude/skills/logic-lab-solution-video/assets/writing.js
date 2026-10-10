/* The integer frame is the only source of state. SVG outlines and defs stay intact. */
(function(root){
 const clamp=n=>Math.max(0,Math.min(1,n));
 function frameState(t,g,frame){
  const span=(t.writing_spans||[]).find(s=>s.start_frame<=frame&&frame<s.end_frame)||null;
  return {span,progress:span?(span.end_frame-span.start_frame===1?1:clamp((frame-span.start_frame)/(span.end_frame-span.start_frame-1))):0};
 }
 function revealedPieces(t,id,frame){
  return (t.writing_spans||[]).filter(s=>s.id===id&&s.kind==='draw'&&s.clip_bbox&&s.start_frame<=frame).map(s=>{
   const b=s.clip_bbox,progress=frame>=s.end_frame?1:frameState({writing_spans:[s]},null,frame).progress;
   if(s.target_kind==='shape'&&b[2]===b[0])return [b[0]-1,b[1],b[2]+1,b[1]+(b[3]-b[1])*progress];
   return [b[0],b[1],b[0]+(b[2]-b[0])*progress,b[3]];
  });
 }
 function cameraAt(t,frame){return root.EC2Camera.cameraAt(t.cameras,frame).viewbox;}
 function mirrored(t,frame){return root.EC2Camera.cameraAt(t.cameras,frame).mirror;}
 function screen(pt,c,l){return root.EC2Camera.pageToScreen(pt,c,l);}
 function createRenderer(svg,glyphs,pencil,meta){
  const ns='http://www.w3.org/2000/svg',groups=new Map(),defs=document.createElementNS(ns,'defs');svg.append(defs);
  for(const g of Object.values(glyphs)){
   const entries=[];
   for(const id of g.svg_ids){
    const node=svg.querySelector('[id="'+id+'"]');if(!node)throw Error('missing pencil glyph '+id);
    const parent=node.parentNode,wrapper=document.createElementNS(ns,'g'),clip=document.createElementNS(ns,'clipPath'),rect=document.createElementNS(ns,'rect');
    clip.id='writing-'+id;clip.setAttribute('clipPathUnits','userSpaceOnUse');clip.append(rect);defs.append(clip);
    // Capture page→parent before wrapping; this matrix is independent of the camera.
    const matrix=parent.getScreenCTM().inverse().multiply(svg.getScreenCTM());
    rect.setAttribute('transform',`matrix(${matrix.a} ${matrix.b} ${matrix.c} ${matrix.d} ${matrix.e} ${matrix.f})`);
    parent.insertBefore(wrapper,node);wrapper.append(node);entries.push({node,wrapper,rect,clip,matrix});
   }
   groups.set(g.id,entries);
  }
  let state={visible:false,masked_ids:[]};
  function render(t,frame,camera,layout){
   const {span,progress}=frameState(t,glyphs,frame),done=new Set(t.events.filter(e=>e.frame<=frame).map(e=>e.id));
   const active=span?.kind==='draw'?span.id:null,masked=[];
   groups.forEach((entries,id)=>{
    const b=glyphs[id].bbox,current=id===active,parts=revealedPieces(t,id,frame),spatial=!!t.writing_unit_spans;
    for(const e of entries){
     e.node.style.opacity=done.has(id)||current||parts.length?'1':'0';
     if(spatial&&!done.has(id)){
      e.clip.replaceChildren();
      for(const part of parts){
       const rect=document.createElementNS(ns,'rect');
       rect.setAttribute('transform',`matrix(${e.matrix.a} ${e.matrix.b} ${e.matrix.c} ${e.matrix.d} ${e.matrix.e} ${e.matrix.f})`);
       rect.setAttribute('x',part[0]);rect.setAttribute('y',part[1]-1);
       rect.setAttribute('width',Math.max(0,part[2]-part[0]));rect.setAttribute('height',part[3]-part[1]+2);e.clip.append(rect);
      }
      e.wrapper.setAttribute('clip-path','url(#'+e.clip.id+')');
     }else if(current){
      const edge=b[0]+(b[2]-b[0])*progress;
      e.rect.setAttribute('x',b[0]-1);e.rect.setAttribute('y',b[1]-1);e.rect.setAttribute('height',b[3]-b[1]+2);
      e.rect.setAttribute('width',Math.max(0,edge-b[0]+1+(progress===1?1:0)));
      e.wrapper.setAttribute('clip-path','url(#'+e.clip.id+')');
     }else e.wrapper.removeAttribute('clip-path');
    }
    if(current)masked.push(id);
   });
   const g=span&&glyphs[span.id];
   let mirror=mirrored(t,frame);
   let show=!!g&&(span.target_kind==='shape'||!g.text.match(/^\s*$/)),tip=null,angle=0,bounds=null,length=t.writing.pencil_length_px;
   if(show){
    const b=span.clip_bbox||g.bbox,vertical=span.target_kind==='shape'&&b[2]===b[0],dest=screen([b[0]+(span.kind==='draw'?(b[2]-b[0])*progress:0),vertical?b[1]+(span.kind==='draw'?(b[3]-b[1])*progress:0):b[1]+.8*(b[3]-b[1])],camera,layout);
    tip=dest;
    if(span.kind==='move'&&span.from_id){
     const a=span.from_bbox||glyphs[span.from_id].bbox;
     const previousDraw=(t.writing_spans||[]).filter(s=>s.kind==='draw'&&s.id===span.from_id&&s.end_frame<=span.start_frame).at(-1);
     const previousFrame=previousDraw?previousDraw.end_frame-1:span.start_frame-1;
     const previous=screen([a[2],a[2]===a[0]?a[3]:a[1]+.8*(a[3]-a[1])],cameraAt(t,previousFrame),layout);
     tip=[previous[0]+(dest[0]-previous[0])*progress,previous[1]+(dest[1]-previous[1])*progress-(span.lifted?8*Math.sin(Math.PI*progress):0)];
    }
    angle=span.kind==='draw'?t.writing.tilt_degrees*Math.sin(2*Math.PI*progress):0;

   }
   state={active_id:span?.id||null,kind:span?.kind||null,progress,visible:show,tip_screen:tip,pencil_length_px:length,pencil_bounds:bounds,tilt_degrees:angle,mirror,masked_ids:masked,owner:'writing'};
   return state;
  }
  return {render,snapshot:()=>({...state,...(root.solutionPen?.snapshot().owner==='writing'?root.solutionPen.snapshot():{})})};
 }
 const api={frameState,createRenderer,revealedPieces};if(typeof module!=='undefined')module.exports=api;root.EC2Writing=api;
})(typeof window==='undefined'?globalThis:window);
