
document.getElementById('print').addEventListener('click',()=>window.print());
document.getElementById('jump').addEventListener('change',e=>{const el=document.querySelector(e.target.value);if(el)el.scrollIntoView()});
const navs=[...document.querySelectorAll('.toc a')];
const observer=new IntersectionObserver(entries=>{const active=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];if(active)navs.forEach(a=>a.classList.toggle('active',a.hash==='#'+active.target.id));},{rootMargin:'-90px 0px -65% 0px'});
document.querySelectorAll('.document h2').forEach(h=>observer.observe(h));
