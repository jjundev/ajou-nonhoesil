/* Frame is the only clock: jumping backward reconstructs every visible state. */
(function(){
 const T=window.solutionTimeline, L=window.solutionLayout||{height:900}, nodes=new Map();
 document.documentElement.style.setProperty('--pdf-height',L.height+'px');
 document.querySelectorAll('[data-reveal]').forEach(n=>{const k=n.getAttribute('data-reveal');if(!nodes.has(k))nodes.set(k,[]);nodes.get(k).push(n);});
 const answer=document.querySelector('#answer-page>svg'), problem=document.getElementById('problem-page'), host=document.getElementById('answer-page'), cursor=document.getElementById('cursor');
 const pencil=T.writing?.mode==='pencil', renderer=pencil?EC2Writing.createRenderer(answer,window.solutionGlyphs,document.getElementById('pencil'),window.pencilMeta):null;
 window.solutionWriting=renderer;
 const annotation=window.solutionAnnotationsData?EC2Annotations.createRenderer(answer,window.solutionAnnotationsData):null;
 window.solutionAnnotations=annotation;
 const controller=window.pencilMeta?EC2Pencil.createController(document.getElementById('pencil'),window.pencilMeta,T.writing||{}):null;
 window.solutionPen=controller;
 const initial=T.segments.filter(s=>s.kind==='problem').at(-1)?.end_sample/800||0;
 window.renderSolutionFrame=function(frame){
   // GSAP rounds time/values; 67 can arrive as 66.999999 on a frame seek.
   frame=Math.max(0,Math.min(T.total_frames-1,Math.floor(frame+1e-5)));
   const shown=new Set(T.events.filter(e=>e.frame<=frame).map(e=>e.id));
   nodes.forEach((ns,k)=>{if(pencil&&window.solutionGlyphs[k])return;ns.forEach(n=>n.style.opacity=shown.has(k)?'1':'0');});
   problem.style.opacity=frame<initial?'1':'0'; host.style.opacity=frame<initial?'0':'1';
   const camera=EC2Camera.cameraAt(T.cameras,frame).viewbox;
   answer.setAttribute('viewBox',camera.join(' '));
   const writingState=renderer?renderer.render(T,frame,camera,L):{visible:false};
   const annotationState=annotation?annotation.render(T.teaching,frame,camera,L):{visible:false};
   if(controller)controller.apply(writingState,annotationState);
   if(pencil){cursor.style.opacity='0';return;}
   const segment=T.segments.find(s=>s.kind==='write'&&s.start_sample/800<=frame&&frame<s.end_sample/800);
   const done=frame>=T.events.at(-1).frame;
   if(segment&&!done){
     const last=T.events.filter(e=>e.kind==='glyph'&&e.frame<=frame).at(-1), g=window.solutionGlyphs[last?.id];
     if(g){
       const [x,y,w,h]=camera,scale=Math.min(1920/w,L.height/h),left=(1920-w*scale)/2,top=(L.height-h*scale)/2;
       cursor.style.left=(left+(g.bbox[2]-x)*scale+3)+'px';cursor.style.top=(top+(g.bbox[1]-y)*scale)+'px';cursor.style.opacity='1';
     }else cursor.style.opacity='0';
   }else cursor.style.opacity='0';
 };
 const clock={frame:0};
 const tl=gsap.timeline({paused:true,onUpdate:()=>window.renderSolutionFrame(clock.frame)});
 tl.fromTo(clock,{frame:0},{frame:T.total_frames,duration:T.total_frames/30,ease:'none',immediateRender:false},0);
 window.__timelines=window.__timelines||{};
 window.__timelines['solution']=tl;
 window.renderSolutionFrame(0);
})();
