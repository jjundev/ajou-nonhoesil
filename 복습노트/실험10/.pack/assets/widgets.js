'use strict';
let printState=[];
let printMoves=[];
let printing=false;
window.addEventListener('beforeprint',()=>{
  if(printing)return;
  printing=true;
  // Biology's template moves direct card details into a non-printing sidebar.
  // Move those same nodes back for print, preserving their UI state and order.
  document.querySelectorAll('.aid[data-card-id]').forEach(group=>{
    const card=document.getElementById(group.dataset.cardId);
    if(!card)return;
    [...group.children].filter(d=>d.tagName==='DETAILS').forEach(d=>{
      printMoves.push([d,group,d.nextSibling]);card.appendChild(d);
    });
  });
  printState=[...document.querySelectorAll('details')].map(d=>[d,d.open]);
  printState.forEach(([d])=>d.open=true);
});
window.addEventListener('afterprint',()=>{
  printState.forEach(([d,open])=>d.open=open);
  [...printMoves].reverse().forEach(([d,parent,next])=>parent.insertBefore(d,next));
  printState=[];printMoves=[];printing=false;
});
document.querySelectorAll('[data-widget="mux2"]').forEach(widget=>{
  const update=()=>{const select=widget.querySelector('[name="S"]');const input=widget.querySelector('[name="I'+select.value+'"]');widget.querySelector('output').textContent=input.checked?'1':'0'};
  widget.addEventListener('change',update);update();
});
