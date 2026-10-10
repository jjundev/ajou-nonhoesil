import fs from 'node:fs';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const argv=process.argv.slice(2), opt=k=>argv.includes('--'+k)?argv[argv.indexOf('--'+k)+1]:undefined;
const require=createRequire(opt('puppeteer-package'));
const puppeteer=require('puppeteer-core');
const browser=await puppeteer.launch({executablePath:opt('chrome'),headless:true,args:['--no-sandbox','--allow-file-access-from-files',...(opt('mode')==='gate'?['--disable-gpu']:[])]});
try {
 const page=await browser.newPage();
 const mode=opt('mode');
 const file=opt('svg')||opt('entry');
 await page.setViewport({width:1200,height:850,deviceScaleFactor:1});
 if(mode==='inventory') {
   const svg=fs.readFileSync(file,'utf8');
   await page.setContent(svg);
   const result=await page.evaluate(()=>{
     const all=[...document.querySelectorAll('svg use[data-text],svg path,svg rect,svg line,svg circle,svg ellipse,svg polygon,svg image')].filter(n=>!n.closest('defs'));
     return all.map((n,i)=>{
       const b=n.getBBox(),m=n.getCTM();
       const points=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
       return {id:'sv-'+i,index:i,tag:n.tagName,text:n.getAttribute('data-text'),bbox:[Math.min(...points.map(p=>p.x)),Math.min(...points.map(p=>p.y)),Math.max(...points.map(p=>p.x)),Math.max(...points.map(p=>p.y))]};
     });
   });
   console.log(JSON.stringify(result));
 } else if(mode==='gate') {
   const dest=opt('dest'); fs.mkdirSync(dest,{recursive:true});
   const layers=JSON.parse(fs.readFileSync(opt('layers'),'utf8'));
   const original=fs.readFileSync(layers.original_svg,'utf8'), animated=fs.readFileSync(layers.animated_svg,'utf8');
   const [w,h]=await (async()=>{await page.setContent(original);return page.evaluate(()=>{const b=document.querySelector('svg').viewBox.baseVal;return [Math.ceil(b.width*2),Math.ceil(b.height*2)];});})();
   await page.setViewport({width:w,height:h});
   const shot=async(svg,name,action)=>{
     await page.setContent('<style>html,body{margin:0;background:white}svg{width:100vw;height:100vh}</style>'+svg);
     if(action) await page.evaluate(action);
     await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
     await page.screenshot({path:dest+'/'+name+'.png'});
   };
   await shot(original,'original');
   await shot(animated,'empty');
   await shot(animated,'removed',()=>document.querySelectorAll('[data-reveal]').forEach(n=>n.remove()));
   await shot(animated,'complete',()=>document.querySelectorAll('[data-reveal]').forEach(n=>n.style.opacity='1'));
   await shot(animated,'partial',()=>{const nodes=[...document.querySelectorAll('[data-reveal]')];nodes.slice(0,Math.floor(nodes.length/2)).forEach(n=>n.style.opacity='1');});
   console.log(JSON.stringify({width:w,height:h,evidence:['original.png','empty.png','removed.png','complete.png','partial.png']}));
 } else if(mode==='writing-flow') {
   const {writingFlowCheck}=await import('./writing_flow_check.mjs');console.log(JSON.stringify(await writingFlowCheck(page,opt)));
 } else if(mode==='teaching') {
   const {teachingCheck}=await import('./teaching_check.mjs');console.log(JSON.stringify(await teachingCheck(page,opt)));
 } else if(mode==='timeline') {
   await page.setViewport({width:1920,height:1080});
   await page.goto(pathToFileURL(file).href);
   await page.waitForFunction(()=>typeof window.renderSolutionFrame==='function');
   await page.evaluate(async()=>{for(const im of document.images)await im.decode();});
   const end=await page.evaluate(()=>window.solutionTimeline.total_frames-1);
   const sequence=[0,end,Math.floor(end/2),0];
   const shots=[];
   for(const f of sequence){await page.evaluate(f=>window.renderSolutionFrame(f),f);shots.push((await page.screenshot()).toString('base64'));}
   await page.evaluate(f=>window.renderSolutionFrame(f),Math.floor(end/2));
   const direct=(await page.screenshot()).toString('base64');
   const state=await page.evaluate(()=>({cursor:document.getElementById('cursor').style.opacity,box:document.getElementById('pdf-viewport').getBoundingClientRect().toJSON()}));
   await page.evaluate(f=>window.renderSolutionFrame(f),end);
   const last=await page.evaluate(()=>document.getElementById('cursor').style.opacity);
   const svg=await page.evaluate(()=>document.querySelector('#answer-page>svg').getBoundingClientRect().toJSON());
   let writing;
   const pencil=await page.evaluate(()=>window.solutionTimeline.writing?.mode==='pencil');
   if(pencil){
    const layers=opt('layers')?JSON.parse(fs.readFileSync(opt('layers'),'utf8')):null;
    const original=layers?fs.readFileSync(layers.original_svg,'utf8'):null;
    const dest=opt('dest');if(dest)fs.mkdirSync(dest,{recursive:true});
    const result=await page.evaluate(()=>{
     const t=window.solutionTimeline,gs=window.solutionGlyphs,l=window.solutionLayout;
     let tip_error_px=0,bounds_ok=true,inactive_hidden=true,order_ok=true;
     const draws=t.writing_spans.filter(s=>s.kind==='draw');
     let prev=-1;
     for(const s of t.writing_spans){order_ok&&=Number.isInteger(s.start_frame)&&Number.isInteger(s.end_frame)&&s.start_frame>=prev&&s.end_frame>s.start_frame&&s.end_frame<=t.total_frames;prev=s.end_frame;}
     for(const e of t.events.filter(e=>e.kind==='glyph'&&gs[e.id].text.trim()))order_ok&&=draws.filter(s=>s.id===e.id&&s.end_frame===e.frame).length===1;
     for(const s of draws){const last=draws.filter(d=>d.id===s.id).at(-1);order_ok&&=t.events.filter(e=>e.id===s.id&&e.frame===last.end_frame).length===1;}
     for(const s of t.writing_spans){for(let f=s.start_frame;f<s.end_frame;f++){
      window.renderSolutionFrame(f);const a=window.solutionWriting.snapshot();
      if(a.visible){const b=a.pencil_bounds;bounds_ok&&=b.every(Number.isFinite)&&b[0]>=0&&b[1]>=0&&b[2]<=1920&&b[3]<=900&&Math.abs(a.tilt_degrees)<=2.0001;
       if(s.kind==='draw'){
        const cam=[...t.cameras].reverse().find(k=>k.at_frame<=f).viewbox,sc=Math.min(1920/cam[2],l.height/cam[3]),g=s.clip_bbox||gs[s.id].bbox;
        const expected=[(1920-cam[2]*sc)/2+(g[0]+(g[2]-g[0])*a.progress-cam[0])*sc,(l.height-cam[3]*sc)/2+((s.target_kind==='shape'&&g[2]===g[0]?g[1]+(g[3]-g[1])*a.progress:g[1]+.8*(g[3]-g[1]))-cam[1])*sc];
        const im=document.getElementById('pencil'),matrix=new DOMMatrix(getComputedStyle(im).transform),m=window.pencilMeta;
        const point=new DOMPoint(m.tip_px[0],m.tip_px[1]);
        // CSS transform-origin contributes T(origin)*matrix*T(-origin).
        const transformed=new DOMPoint(0,0).matrixTransform(matrix);
        const actual=[m.tip_px[0]+transformed.x,m.tip_px[1]+transformed.y];
        tip_error_px=Math.max(tip_error_px,Math.hypot(actual[0]-expected[0],actual[1]-expected[1]));
        const end=new DOMPoint(m.end_px[0]-m.tip_px[0],m.end_px[1]-m.tip_px[1]).matrixTransform(matrix);
        bounds_ok&&=Math.abs(Math.hypot(end.x-transformed.x,end.y-transformed.y)-t.writing.pencil_length_px)<=.5;
       }
      }else if(s.target_kind==='shape'||gs[s.id].text.trim())bounds_ok=false;
     }}
     for(const f of [0,t.total_frames-1,...t.segments.map(s=>s.end_sample/800-1)]){window.renderSolutionFrame(f);if(!window.EC2Writing.frameState(t,gs,f).span)inactive_hidden&&=!window.solutionWriting.snapshot().visible&&(window.solutionPen?.snapshot().owner==='annotation'||getComputedStyle(document.getElementById('pencil')).opacity==='0');}
     return {tip_error_px,bounds_ok,inactive_hidden,order_ok};
    });
    let precomplete_diff=0,complete_diff=0,hidden_leaks=0,seek_equal=true,gsap_seek_equal=true;const gsap_debug=[];
    const spans=await page.evaluate(()=>window.solutionTimeline.writing_spans.filter(s=>s.kind==='draw'));
    for(const s of [spans[0],spans[Math.floor(spans.length/2)],spans.at(-1)].filter(Boolean)){
     const f=s.start_frame+Math.floor((s.end_frame-s.start_frame)/2);
     const ok=await page.evaluate(f=>{window.renderSolutionFrame(f);const expected=JSON.stringify(window.solutionWriting.snapshot());window.__timelines.solution.seek(0,false);window.__timelines.solution.seek(f/30,false);return {equal:expected===JSON.stringify(window.solutionWriting.snapshot()),expected:JSON.parse(expected),actual:window.solutionWriting.snapshot(),clock:window.__timelines.solution.getChildren()[0].targets()[0].frame};},f);gsap_seek_equal&&=ok.equal;if(!ok.equal)gsap_debug.push({frame:f,...ok});
    }
    const selected=[];
    for(const id of new Set(spans.map(s=>s.step_id))){const group=spans.filter(s=>s.step_id===id);selected.push(group[0],group[Math.floor(group.length/2)],group.at(-1));}
    const extra=await page.evaluate(()=>[...window.solutionTimeline.cameras.map(k=>k.at_frame),...window.solutionTimeline.writing_spans.filter(s=>s.kind==='move'&&s.lifted).flatMap(s=>[s.start_frame,Math.floor((s.start_frame+s.end_frame-1)/2),s.end_frame-1])]);
    const frames=[...new Set([...selected.flatMap(s=>[s.start_frame,Math.floor((s.start_frame+s.end_frame-1)/2),s.end_frame-1]),...extra])];
    const shot=async(f,name)=>{await page.evaluate(f=>{window.renderSolutionFrame(f);document.getElementById('pencil').style.opacity='0';const a=document.getElementById('teaching-annotations');if(a)a.style.opacity='0';},f);return page.screenshot(dest?{path:dest+'/'+name+'.png'}:{});};
    if(original){
     for(const f of [...frames,end]){
      const actual=await shot(f,'writing-'+f);
      const state=await page.evaluate(f=>({t:window.solutionTimeline,g:window.solutionGlyphs,active:window.EC2Writing.frameState(window.solutionTimeline,window.solutionGlyphs,f),camera:document.querySelector('#answer-page>svg').getAttribute('viewBox')}),f);
      await page.evaluate(({original,state,f,layers})=>{
       const host=document.getElementById('answer-page'),old=host.firstElementChild;old.style.opacity='0';
       const parser=new DOMParser(),ref=parser.parseFromString(original,'image/svg+xml').documentElement;host.append(ref);ref.id='writing-reference';ref.setAttribute('viewBox',state.camera);
       [...ref.querySelectorAll('use[data-text],path,rect,line,circle,ellipse,polygon,image')].filter(n=>!n.closest('defs')).forEach((n,i)=>n.id='sv-'+i);
       const done=new Set(state.t.events.filter(e=>e.frame<=f).map(e=>e.id));const active=state.active.span?.kind==='draw'?state.active.span.id:null;
       for(const obj of [...layers.glyphs,...layers.shapes])for(const id of obj.svg_ids){
        const node=ref.querySelector('[id="'+id+'"]');if(!node)throw Error('oracle missing '+id);
        if(state.t.writing_unit_spans&&!done.has(obj.id)){
         const ns=ref.namespaceURI,parts=state.t.writing_spans.filter(s=>s.kind==='draw'&&s.id===obj.id&&s.start_frame<=f);
         if(!parts.length){node.remove();continue;}
         const clip=document.createElementNS(ns,'clipPath');clip.id='reference-'+id;clip.setAttribute('clipPathUnits','userSpaceOnUse');
         const parent=node.parentNode,m=parent.getScreenCTM().inverse().multiply(ref.getScreenCTM());
         for(const part of parts){
          const b=part.clip_bbox,p=f>=part.end_frame?1:(f-part.start_frame)/(part.end_frame-part.start_frame-1),r=document.createElementNS(ns,'rect');
          r.setAttribute('transform',`matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e} ${m.f})`);const vertical=part.target_kind==='shape'&&b[2]===b[0];r.setAttribute('x',b[0]-(vertical?1:0));r.setAttribute('y',b[1]-1);r.setAttribute('width',vertical?2:Math.max(0,(b[2]-b[0])*p));r.setAttribute('height',(b[3]-b[1])*(vertical?p:1)+2);clip.append(r);
         }
         const defs=document.createElementNS(ns,'defs');defs.append(clip);ref.append(defs);const w=document.createElementNS(ns,'g');parent.insertBefore(w,node);w.append(node);w.setAttribute('clip-path','url(#'+clip.id+')');continue;
        }
        if(!done.has(obj.id)&&obj.id!==active){node.remove();continue;}
        if(obj.id===active&&state.active.progress<1){
         const ns=ref.namespaceURI,clip=document.createElementNS(ns,'clipPath'),r=document.createElementNS(ns,'rect');clip.id='reference-'+id;clip.setAttribute('clipPathUnits','userSpaceOnUse');
         const parent=node.parentNode,m=parent.getScreenCTM().inverse().multiply(ref.getScreenCTM()),b=obj.bbox;
         r.setAttribute('transform',`matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e} ${m.f})`);r.setAttribute('x',b[0]-1);r.setAttribute('y',b[1]-1);r.setAttribute('width',1+(b[2]-b[0])*state.active.progress);r.setAttribute('height',b[3]-b[1]+2);clip.append(r);
         const defs=document.createElementNS(ns,'defs');defs.append(clip);ref.append(defs);const w=document.createElementNS(ns,'g');parent.insertBefore(w,node);w.append(node);w.setAttribute('clip-path','url(#'+clip.id+')');
        }
       }
      },{original,state,f,layers});
      // Hide the original SVG without changing layout: the reference is absolute.
      await page.evaluate(()=>{const r=document.getElementById('writing-reference');r.style.position='absolute';r.style.left='0';r.style.top='0';});
      const expected=await page.screenshot(dest?{path:dest+'/reference-'+f+'.png'}:{});
      const diff=Buffer.from(actual).equals(Buffer.from(expected))?0:1;
      if(f===end)complete_diff+=diff;
      else if(state.active.progress===1)precomplete_diff+=diff;
      else hidden_leaks+=diff;
      await page.evaluate(()=>{document.getElementById('writing-reference').remove();document.querySelector('#answer-page>svg').style.opacity='1';});
      await page.evaluate(()=>window.renderSolutionFrame(0));const back=await shot(f,'seek-'+f);seek_equal&&=Buffer.from(actual).equals(Buffer.from(back));
     }
    }else {precomplete_diff=complete_diff=hidden_leaks=null;}
    await page.evaluate(f=>window.renderSolutionFrame(f),end);
    const final_visible=await page.evaluate(()=>window.solutionWriting.snapshot().visible||getComputedStyle(document.getElementById('pencil')).opacity!=='0');
    const expectedTimeline=opt('timeline')?JSON.parse(fs.readFileSync(opt('timeline'),'utf8')):null;
    const timeline_equal=expectedTimeline?await page.evaluate(t=>{const current=window.solutionTimeline;return JSON.stringify({...current,cameras:[]})===JSON.stringify({...t,cameras:[]});},expectedTimeline):true;
    writing={...result,timeline_equal,gsap_seek_equal,gsap_debug,seek_equal,precomplete_diff,complete_diff,hidden_leaks,final_visible,evidence:dest?fs.readdirSync(dest).filter(n=>n.endsWith('.png')).map(n=>dest+'/'+n):[]};
   }
   console.log(JSON.stringify({seek_equal:shots[0]===shots[3]&&shots[2]===direct,final_cursor:last,viewport:state.box,svg,writing}));
 } else throw new Error('unknown mode');
} finally {await browser.close();}
