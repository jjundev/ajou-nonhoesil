'use strict';
let printState=[];
window.addEventListener('beforeprint',()=>{printState=[...document.querySelectorAll('details')].map(d=>[d,d.open]);printState.forEach(([d])=>d.open=true)});
window.addEventListener('afterprint',()=>{printState.forEach(([d,open])=>d.open=open);printState=[]});
document.querySelectorAll('[data-widget="mux2"]').forEach(widget=>{
  const update=()=>{const select=widget.querySelector('[name="S"]');const input=widget.querySelector('[name="I'+select.value+'"]');widget.querySelector('output').textContent=input.checked?'1':'0'};
  widget.addEventListener('change',update);update();
});
