'use strict';
let authUser=null,authCSRF='',authMode='login',authLastFocus=null;
const authOverlay=$('auth-overlay');
function setAuthFeedback(message){$('auth-feedback').textContent=message;$('auth-feedback').hidden=!message;}
function setAuthMode(mode){
  authMode=mode;const creating=mode==='register';
  $('auth-name-wrap').hidden=!creating;$('auth-confirm-wrap').hidden=!creating;
  $('auth-name').required=creating;$('auth-confirm').required=creating;
  $('auth-password').minLength=creating?10:1;$('auth-password').autocomplete=creating?'new-password':'current-password';
  $('auth-password').value='';$('auth-confirm').value='';$('auth-password').type='password';$('auth-show-password').setAttribute('aria-pressed','false');$('auth-show-password').setAttribute('aria-label','Mostrar contraseña');
  $('auth-title').textContent=creating?'Aquí empiezas tú.':'Qué bueno verte.';
  $('auth-subtitle').textContent=creating?'Crea tu cuenta. Nosotros ponemos el laboratorio; tú, las ideas.':'Inicia sesión y hagamos espacio para tus ideas.';
  $('auth-submit').innerHTML=creating?'Crear mi cuenta <i class="bi bi-arrow-up-right"></i>':'Entrar a mi laboratorio <i class="bi bi-arrow-up-right"></i>';
  document.querySelectorAll('[data-auth-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.authMode===mode)));
  setAuthFeedback('');
}
function updateAuthUser(user){
  const changed=authUser?.id!==user?.id;
  authUser=user;window.nexoUser=user;
  const name=user?.name||'Visitante';const initials=user?name.split(/\s+/).slice(0,2).map(p=>p[0]).join('').toLocaleUpperCase('es'):'NL';
  $('home-title').textContent=user?'Hola, '+name.split(/\s+/)[0]+'.':'Hola, qué gusto verte.';
  $('profile-name').textContent=name;$('profile-subtitle').textContent=user?'@'+user.username:'Explora a tu ritmo';
  $('profile-avatar').textContent=initials;$('top-user-avatar').textContent=initials;
  $('account-open').hidden=!!user;$('account-logout').hidden=!user;
  $('profile-account').ariaLabel=user?'Cerrar sesión':'Iniciar sesión';$('profile-account').title=user?'Cerrar sesión':'Iniciar sesión';
  $('profile-account').innerHTML=`<i class="bi bi-${user?'box-arrow-right':'box-arrow-in-right'}"></i>`;
  if(changed)window.dispatchEvent(new Event('nexo-account-changed'));
}
function showAuth(){
  stopCamera();window.stopObjectCamera?.();window.stopPersonalCamera?.();
  closeMenu();authLastFocus=document.activeElement;authOverlay.hidden=false;document.body.classList.add('auth-is-open');
  document.querySelector('.app-shell').inert=true;$('sidebar').inert=true;
  requestAnimationFrame(()=>$('auth-dialog').focus());
}
function closeAuth(){
  authOverlay.hidden=true;document.body.classList.remove('auth-is-open');
  document.querySelector('.app-shell').inert=false;$('sidebar').inert=false;
  $('auth-password').value='';$('auth-confirm').value='';setAuthFeedback('');
  try{sessionStorage.setItem('nexo-auth-dismissed','yes');}catch{}
  if(authLastFocus?.isConnected)authLastFocus.focus();
}
async function refreshAuth(){const data=await api('/api/auth/me');authCSRF=data.csrf;updateAuthUser(data.user);return data;}
async function authPost(path,data){
  if(!authCSRF)await refreshAuth();
  const response=await fetch('/api/auth/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':authCSRF},credentials:'same-origin',body:JSON.stringify(data||{})});
  let result;try{result=await response.json();}catch{throw new Error('No se pudo contactar con el acceso de usuarios. Inténtalo en unos segundos.');}
  if(!response.ok){if(result.code==='csrf')await refreshAuth();throw new Error(result.error||'No se pudo completar la solicitud.');}
  authCSRF=result.csrf;return result;
}
document.querySelectorAll('[data-auth-mode]').forEach(b=>b.addEventListener('click',()=>setAuthMode(b.dataset.authMode)));
['auth-close','auth-guest'].forEach(id=>$(id).addEventListener('click',closeAuth));
$('account-open').addEventListener('click',()=>{setAuthMode('login');showAuth();});
$('auth-show-password').addEventListener('click',()=>{const visible=$('auth-password').type==='password';$('auth-password').type=visible?'text':'password';$('auth-show-password').setAttribute('aria-pressed',String(visible));$('auth-show-password').setAttribute('aria-label',visible?'Ocultar contraseña':'Mostrar contraseña');});
$('auth-form').addEventListener('submit',async e=>{
  e.preventDefault();if(!$('auth-form').reportValidity())return;
  if(authMode==='register'&&$('auth-password').value!==$('auth-confirm').value){setAuthFeedback('Las contraseñas no coinciden. Revisa ambos campos.');return;}
  const button=$('auth-submit');if(button.disabled)return;const original=button.innerHTML;button.disabled=true;button.innerHTML='<span class="button-spinner"></span> Preparando tu espacio…';setAuthFeedback('');
  try{const result=await authPost(authMode,{name:$('auth-name').value,username:$('auth-username').value,password:$('auth-password').value});updateAuthUser(result.user);closeAuth();location.hash='inicio';toast('Qué bueno tenerte aquí, '+result.user.name.split(/\s+/)[0]+'.');}
  catch(error){setAuthFeedback(error.message);}
  finally{button.disabled=false;button.innerHTML=original;}
});
async function logoutAccount(){
  try{await authPost('logout');updateAuthUser(null);window.resetPersonalCard?.();setAuthMode('login');showAuth();toast('Sesión cerrada. Tu ficha local se limpió.');}
  catch(error){toast(error.message);}
}
$('account-logout').addEventListener('click',logoutAccount);
$('profile-account').addEventListener('click',()=>{if(authUser)logoutAccount();else{setAuthMode('login');showAuth();}});
authOverlay.addEventListener('keydown',e=>{
  if(e.key==='Escape'){e.stopPropagation();closeAuth();return;}
  if(e.key!=='Tab')return;
  const focusable=[...authOverlay.querySelectorAll('a,button,input,[tabindex="0"]')].filter(el=>!el.disabled&&el.getClientRects().length);
  const first=focusable[0],last=focusable.at(-1);
  if(e.shiftKey&&(document.activeElement===first||document.activeElement===$('auth-dialog'))){e.preventDefault();last?.focus();}
  else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
});
setAuthMode('login');
refreshAuth().then(data=>{let dismissed=false;try{dismissed=sessionStorage.getItem('nexo-auth-dismissed')==='yes';}catch{}if(!data.user&&!dismissed)showAuth();}).catch(()=>{updateAuthUser(null);toast('No pudimos comprobar tu sesión. Puedes seguir explorando y probar el acceso más tarde.');});
