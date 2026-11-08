'use strict';
const personalForm=$('personal-form');
let personalPhotoURL=null;
let personalPhotoToken=0;
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
window.resetPersonalCard=function(){personalForm.reset();clearPersonalPhoto();updatePersonal();};
personalForm.addEventListener('input',updatePersonal);personalForm.addEventListener('change',updatePersonal);
$('personal-photo-input').addEventListener('change',()=>{
  const file=$('personal-photo-input').files[0];if(!file)return;
  if(file.size>8*1024*1024||!['image/jpeg','image/png','image/webp'].includes(file.type)){toast('Elige una foto JPG, PNG o WebP de hasta 8 MB.');$('personal-photo-input').value='';return;}
  clearPersonalPhoto();const token=personalPhotoToken;const url=URL.createObjectURL(file);personalPhotoURL=url;
  const image=new Image();image.onload=()=>{if(token!==personalPhotoToken)return;$('personal-photo-preview').src=url;$('personal-photo-preview').hidden=false;$('personal-photo-placeholder').hidden=true;$('personal-remove-photo').hidden=false;};
  image.onerror=()=>{if(token===personalPhotoToken){clearPersonalPhoto();toast('No pudimos abrir esa fotografía. Prueba con otra.');}};image.src=url;
});
$('personal-remove-photo').addEventListener('click',clearPersonalPhoto);
$('personal-reset').addEventListener('click',()=>{const data=personalValues();if(data.name||data.notes||Object.keys(personalLabels).some(k=>data[k])||personalPhotoURL||data.gender!=='Prefiero no indicarlo'){if(!confirm('¿Limpiar tu ficha y quitar la fotografía de esta página?'))return;}window.resetPersonalCard();});
personalForm.addEventListener('submit',e=>{e.preventDefault();downloadJSON({project:'Nexo Lab',type:'Ficha personal autodescrita',created:new Date().toISOString(),...personalValues()},'nexo-mi-ficha.json');toast('Tu ficha se descargó sin fotografía.');});
window.addEventListener('pagehide',clearPersonalPhoto);window.addEventListener('nexo-account-changed',()=>window.resetPersonalCard());
updatePersonal();
