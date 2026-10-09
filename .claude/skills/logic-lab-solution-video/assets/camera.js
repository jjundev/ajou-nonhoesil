(function(root){
 function cameraAt(keys,frame){
  let previous=keys[0],current=keys[0];
  for(let n=1;n<keys.length;n++){if(keys[n].at_frame>frame)break;previous=keys[n-1];current=keys[n];}
  const duration=current.transition_frames||0,u=duration?Math.max(0,Math.min(1,(frame-current.at_frame)/duration)):1,e=u*u*(3-2*u);
  return {viewbox:current.viewbox.map((v,i)=>previous.viewbox[i]+(v-previous.viewbox[i])*e),mirror:!!current.mirror};
 }
 function pageToScreen(point,view,layout){const s=Math.min(1920/view[2],layout.height/view[3]);return [(1920-view[2]*s)/2+(point[0]-view[0])*s,(layout.height-view[3]*s)/2+(point[1]-view[1])*s];}
 const api={cameraAt,pageToScreen};if(typeof module!=='undefined')module.exports=api;root.EC2Camera=api;
})(typeof window==='undefined'?globalThis:window);
