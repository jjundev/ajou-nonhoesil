/* The only owner of the pencil image's CSS state. */
(function(root){
 function createController(element,meta,settings){
  let state={visible:false};
  function apply(writing,annotation){
   if(writing?.visible&&annotation?.visible)throw Error('original and annotation writing overlap');
   const selected=annotation?.visible?annotation:writing?.visible?writing:{visible:false};
   state={...selected,pencil_length_px:settings.pencil_length_px||160,pencil_bounds:null};
   element.style.opacity=state.visible?'1':'0';
   if(!state.visible)return state;
   const tip=state.tip_screen,angle=state.tilt_degrees||0,length=state.pencil_length_px;
   if(!tip?.every(Number.isFinite)||Math.abs(angle)>2.0001)throw Error('invalid pencil state');
   const scale=length/Math.hypot(meta.end_px[0]-meta.tip_px[0],meta.end_px[1]-meta.tip_px[1]),rad=angle*Math.PI/180;
   const [x0,y0,x1,y1]=meta.visible_bounds_px;
   function bounds(mirror){const cs=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]].map(([x,y])=>{x=(x-meta.tip_px[0])*scale*(mirror?-1:1);y=(y-meta.tip_px[1])*scale;return [tip[0]+x*Math.cos(rad)-y*Math.sin(rad),tip[1]+x*Math.sin(rad)+y*Math.cos(rad)];});return [Math.min(...cs.map(p=>p[0])),Math.min(...cs.map(p=>p[1])),Math.max(...cs.map(p=>p[0])),Math.max(...cs.map(p=>p[1]))];}
   const fits=b=>b[0]>=0&&b[1]>=0&&b[2]<=1920&&b[3]<=900;
   let mirror=!!state.mirror,b= bounds(mirror);
   if(state.owner==='writing'&&!fits(b)&&fits(bounds(!mirror))){mirror=!mirror;b=bounds(mirror);}
   state.mirror=mirror;state.pencil_bounds=b;
   element.style.width=meta.width+'px';element.style.height=meta.height+'px';element.style.transformOrigin=meta.tip_px[0]+'px '+meta.tip_px[1]+'px';
   element.style.transform=`translate(${tip[0]-meta.tip_px[0]}px,${tip[1]-meta.tip_px[1]}px) rotate(${angle}deg) scale(${mirror?-scale:scale},${scale})`;
   return state;
  }
  return {apply,snapshot:()=>state};
 }
 const api={createController};if(typeof module!=='undefined')module.exports=api;root.EC2Pencil=api;
})(typeof window==='undefined'?globalThis:window);
