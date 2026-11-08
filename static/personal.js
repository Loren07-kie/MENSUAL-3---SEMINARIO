'use strict';
const personalForm=$('personal-form');
let personalPhotoURL=null;
let personalPhotoToken=0;
let personalCameraStream=null;
let personalCameraToken=0;
const personalLabels={hairColor:'Cabello',hairType:'Tipo',hairLength:'Largo',eyeColor:'Ojos',skinTone:'Tono de piel',glasses:'Lentes'};
function personalValues(){
  const form=new FormData(personalForm);
  const gender=form.get('gender')||'Prefiero no indicarlo';
  return {name:String(form.get('name')||'').trim(),gender:gender==='Otro'?(String(form.get('genderOther')||'').trim()||'Otro'):gender,
    ...Object.fromEntries(Object.keys(personalLabels).map(k=>[k,String(form.get(k)||'')])),notes:String(form.get('notes')||'').trim()};
}
function updatePersonal(){
  const selected=personalForm.querySelector('input[name="gender"]:checked')?.value;
  $('personal-gender-other-wrap').hidden=selected!=='Otro';
  $('personal-gender-other').disabled=selected!=='Otro';
  const data=personalValues();const parts=[];
  if(data.name)parts.push(data.name+'.');
  parts.push('Género: '+data.gender+'.');
  for(const [key,label] of Object.entries(personalLabels)){if(data[key])parts.push(label+': '+data[key].toLocaleLowerCase('es')+'.');}
  if(data.notes)parts.push(data.notes);
  $('personal-summary').textContent=parts.join(' ');
  $('personal-note-count').textContent=$('personal-notes').value.length+' / 400 caracteres';
}
function clearPersonalPhoto(){personalPhotoToken++;if(personalPhotoURL)URL.revokeObjectURL(personalPhotoURL);personalPhotoURL=null;$('personal-photo-preview').removeAttribute('src');$('personal-photo-preview').hidden=true;$('personal-photo-placeholder').hidden=false;$('personal-remove-photo').hidden=true;$('personal-photo-input').value='';}
window.stopPersonalCamera=function(){personalCameraToken++;if(personalCameraStream)personalCameraStream.getTracks().forEach(track=>track.stop());personalCameraStream=null;$('personal-camera-video').srcObject=null;$('personal-camera-box').hidden=true;$('personal-camera-status').textContent='';};
window.resetPersonalCard=function(){window.stopPersonalCamera();personalForm.reset();clearPersonalPhoto();updatePersonal();};
personalForm.addEventListener('input',updatePersonal);personalForm.addEventListener('change',updatePersonal);
function usePersonalPhoto(file){
  if(!file)return;
  if(file.size>8*1024*1024||!['image/jpeg','image/png','image/webp'].includes(file.type)){toast('Elige una foto JPG, PNG o WebP de hasta 8 MB.');$('personal-photo-input').value='';return;}
  clearPersonalPhoto();const token=personalPhotoToken;const url=URL.createObjectURL(file);personalPhotoURL=url;
  const image=new Image();image.onload=()=>{if(token!==personalPhotoToken)return;$('personal-photo-preview').src=url;$('personal-photo-preview').hidden=false;$('personal-photo-placeholder').hidden=true;$('personal-remove-photo').hidden=false;$('personal-camera-status').textContent='Tu fotografía está lista en la ficha. Puedes cambiarla o completar tus características.';};
  image.onerror=()=>{if(token===personalPhotoToken){clearPersonalPhoto();toast('No pudimos abrir esa fotografía. Prueba con otra.');}};image.src=url;
}
$('personal-photo-input').addEventListener('change',()=>{const file=$('personal-photo-input').files[0];window.stopPersonalCamera();usePersonalPhoto(file);});
$('personal-remove-photo').addEventListener('click',()=>{window.stopPersonalCamera();clearPersonalPhoto();});
$('personal-camera-open').addEventListener('click',()=>busy($('personal-camera-open'),async()=>{
  if(!navigator.mediaDevices?.getUserMedia)throw new Error('Este navegador no ofrece acceso a la cámara. Abre la página con HTTPS en Chrome, Edge o Safari, o sube una foto.');
  window.stopPersonalCamera();stopCamera();window.stopObjectCamera?.();
  const token=personalCameraToken;
  $('personal-camera-status').textContent='Esperando el permiso de tu cámara…';
  try{
    const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'user'},width:{ideal:1280},height:{ideal:720}},audio:false});
    if(token!==personalCameraToken){stream.getTracks().forEach(track=>track.stop());return;}
    personalCameraStream=stream;const video=$('personal-camera-video');video.srcObject=stream;$('personal-camera-box').hidden=false;
    await video.play();
    if(token!==personalCameraToken)return;
    $('personal-camera-status').textContent='Cámara encendida. Pulsa «Tomar mi foto» cuando estés listo.';
    stream.getVideoTracks().forEach(track=>track.addEventListener('ended',()=>{if(personalCameraStream===stream){window.stopPersonalCamera();$('personal-camera-status').textContent='La cámara se desconectó. Puedes abrirla otra vez.';}}));
  }catch(error){
    if(token!==personalCameraToken)return;
    window.stopPersonalCamera();
    const message=error.name==='NotAllowedError'?'Permite el acceso a la cámara desde el icono de permisos del navegador y vuelve a intentarlo.':error.name==='NotFoundError'?'No encontramos una cámara conectada. Conecta una o sube una fotografía.':error.name==='NotReadableError'?'La cámara está siendo utilizada por otra aplicación. Ciérrala allí y vuelve a intentarlo.':'No pudimos iniciar la cámara. Revisa su conexión y los permisos del navegador.';
    $('personal-camera-status').textContent=message;throw new Error(message);
  }
}));
$('personal-camera-close').addEventListener('click',window.stopPersonalCamera);
$('personal-camera-capture').addEventListener('click',()=>busy($('personal-camera-capture'),async()=>{
  const video=$('personal-camera-video');if(!video.videoWidth||!personalCameraStream)throw new Error('Espera a que la cámara muestre la imagen antes de tomar la foto.');
  const token=personalCameraToken;const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;
  const context=canvas.getContext('2d');context.translate(canvas.width,0);context.scale(-1,1);context.drawImage(video,0,0);
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.92));
  if(token!==personalCameraToken)return;
  if(!blob)throw new Error('No se pudo generar la fotografía. Vuelve a intentarlo.');
  window.stopPersonalCamera();usePersonalPhoto(new File([blob],'mi-foto-de-camara.jpg',{type:'image/jpeg'}));
}));
$('personal-reset').addEventListener('click',()=>{const data=personalValues();if(data.name||data.notes||Object.keys(personalLabels).some(k=>data[k])||personalPhotoURL||data.gender!=='Prefiero no indicarlo'){if(!confirm('¿Limpiar tu ficha y quitar la fotografía de esta página?'))return;}window.resetPersonalCard();});
personalForm.addEventListener('submit',e=>{e.preventDefault();downloadJSON({project:'Nexo Lab',type:'Ficha personal autodescrita',created:new Date().toISOString(),...personalValues()},'nexo-mi-ficha.json');toast('Tu ficha se descargó sin fotografía.');});
window.addEventListener('pagehide',()=>{window.stopPersonalCamera();clearPersonalPhoto();});window.addEventListener('nexo-account-changed',()=>window.resetPersonalCard());
window.addEventListener('hashchange',()=>{if(location.hash!=='#ficha')window.stopPersonalCamera();});
document.addEventListener('visibilitychange',()=>{if(document.hidden)window.stopPersonalCamera();});
document.addEventListener('keydown',event=>{if(event.key==='Escape')window.stopPersonalCamera();});
updatePersonal();
