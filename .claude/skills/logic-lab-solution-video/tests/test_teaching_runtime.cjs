const {test}=require('node:test'),assert=require('node:assert/strict');
let camera;try{camera=require('../assets/camera.js');}catch{}
test('camera interpolation is pure',()=>{
 assert.ok(camera,'shared camera missing');
 const keys=[{at_frame:0,viewbox:[0,0,400,300]},{at_frame:12,viewbox:[100,60,200,150],transition_frames:12}];
 assert.deepEqual(camera.cameraAt(keys,12).viewbox,[0,0,400,300]);
 assert.deepEqual(camera.cameraAt(keys,18).viewbox,[50,30,300,225]);
 assert.deepEqual(camera.cameraAt(keys,24).viewbox,[100,60,200,150]);
 assert.deepEqual(camera.cameraAt(keys,18).viewbox,[50,30,300,225]);
 assert.deepEqual(camera.cameraAt([{at_frame:0,viewbox:[0,0,400,300]},{at_frame:12,viewbox:[1,2,3,4]}],12).viewbox,[1,2,3,4]);
});
let annotations;try{annotations=require('../assets/annotations.js');}catch{}
test('annotation frame state is seek safe',()=>{
 assert.ok(annotations,'annotation renderer missing');
 const t={spans:[{id:'a',unit_index:0,kind:'draw',start_frame:20,end_frame:25,hide_frame:80}]};
 assert.equal(annotations.frameState(t,20).progress,0);assert.equal(annotations.frameState(t,22).progress,.5);assert.equal(annotations.frameState(t,24).progress,1);
 assert.deepEqual(annotations.frameState(t,26).visible_ids,['a']);assert.deepEqual(annotations.frameState(t,80).visible_ids,[]);
 assert.deepEqual(annotations.frameState(t,19).visible_ids,[]);assert.equal(annotations.frameState(t,22).progress,.5);
});
let pencil;try{pencil=require('../assets/pencil.js');}catch{}
test('one pen selects owner and refuses concurrent drawing',()=>{
 assert.ok(pencil,'single pencil controller missing');
 const elem={style:{}},meta={width:500,height:500,tip_px:[0,500],end_px:[500,0],visible_bounds_px:[0,0,500,500]},ctrl=pencil.createController(elem,meta,{pencil_length_px:160,tilt_degrees:2});
 const off={visible:false},on={visible:true,tip_screen:[900,400],tilt_degrees:0,mirror:false,owner:'annotation'};
 assert.equal(ctrl.apply(off,on).owner,'annotation');assert.equal(elem.style.opacity,'1');assert.equal(ctrl.apply(off,off).visible,false);
 assert.throws(()=>ctrl.apply(on,on),/overlap/);
});
