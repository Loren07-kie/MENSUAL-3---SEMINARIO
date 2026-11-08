'use strict';
function applyTheme(theme) {
  document.documentElement.dataset.theme=theme;
  document.querySelectorAll('[data-theme-choice]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.themeChoice===theme)));
  const colors={beige:'#f3eadb',dark:'#151619',white:'#ffffff'};
  document.querySelector('meta[name="theme-color"]').setAttribute('content',colors[theme]);
  try{localStorage.setItem('nexo-theme',theme);}catch{}
  window.dispatchEvent(new Event('resize'));
}
document.querySelectorAll('[data-theme-choice]').forEach(button=>button.addEventListener('click',()=>applyTheme(button.dataset.themeChoice)));
applyTheme(document.documentElement.dataset.theme||'beige');
const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)');
if('IntersectionObserver' in window&&!reduceMotion.matches){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target);}}),{threshold:.06});
  document.querySelectorAll('.lab-card,.objects-discovery,.learning-card,.journey-panel,.daily-note,.objects-banner').forEach((el,i)=>{el.classList.add('reveal');el.style.setProperty('--reveal-delay',(i%3)*70+'ms');observer.observe(el);});
}
const hero=document.querySelector('.hero-panel');
if(hero&&!reduceMotion.matches&&matchMedia('(pointer:fine)').matches){
  let frame=null;
  hero.addEventListener('pointermove',event=>{
    if(frame)return;
    frame=requestAnimationFrame(()=>{const r=hero.getBoundingClientRect();hero.style.setProperty('--move-x',((event.clientX-r.left)/r.width-.5)*12+'px');hero.style.setProperty('--move-y',((event.clientY-r.top)/r.height-.5)*8+'px');frame=null;});
  });
  hero.addEventListener('pointerleave',()=>{hero.style.setProperty('--move-x','0px');hero.style.setProperty('--move-y','0px');});
}
const progress=document.createElement('div');progress.className='reading-progress';progress.setAttribute('aria-hidden','true');document.body.append(progress);
function updateProgress(){const total=document.documentElement.scrollHeight-innerHeight;progress.style.transform=`scaleX(${total>0?Math.min(1,scrollY/total):0})`;}
addEventListener('scroll',updateProgress,{passive:true});addEventListener('hashchange',()=>requestAnimationFrame(updateProgress));updateProgress();
