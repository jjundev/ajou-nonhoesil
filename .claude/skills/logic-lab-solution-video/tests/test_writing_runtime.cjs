const test=require('node:test'), assert=require('node:assert/strict');
test('draw/move endpoints and backward frameState',()=>{
 const {frameState}=require('../assets/writing.js');
 const t={writing_spans:[{kind:'move',start_frame:0,end_frame:1,id:'g'},{kind:'draw',start_frame:1,end_frame:6,id:'g'}]};
 assert.equal(frameState(t,{},0).progress,1);
 assert.deepEqual([1,3,5].map(f=>frameState(t,{},f).progress),[0,.5,1]);
 assert.equal(frameState(t,{},6).span,null);
 assert.equal(frameState(t,{},3).progress,.5);
});
test('piece clips accumulate on direct and reverse seek',()=>{
 const api=require('../assets/writing.js');assert.equal(typeof api.revealedPieces,'function');
 const t={writing_spans:[{id:'bar',kind:'draw',start_frame:0,end_frame:3,clip_bbox:[0,0,10,1]},
 {id:'bar',kind:'draw',start_frame:5,end_frame:8,clip_bbox:[10,0,20,1]}]};
 assert.deepEqual(api.revealedPieces(t,'bar',4),[[0,0,10,1]]);
 assert.deepEqual(api.revealedPieces(t,'bar',6),[[0,0,10,1],[10,0,15,1]]);
 api.revealedPieces(t,'bar',9);assert.deepEqual(api.revealedPieces(t,'bar',1),[[0,0,5,1]]);
});
