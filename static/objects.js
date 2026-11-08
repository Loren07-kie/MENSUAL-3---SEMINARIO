'use strict';
let objectFile = null;
let objectStream = null;
let objectCameraToken = 0;
let objectPreviewURL = null;
let objectCatalog = [];
let catalogLimit = 60;

function setObjectFile(file) {
  if (!file) return false;
  if (file.size > 8*1024*1024) { toast('Elige una fotografía de hasta 8 MB.'); return false; }
  if (!['image/jpeg','image/png','image/webp'].includes(file.type)) { toast('Usa una imagen JPG, PNG o WebP.'); return false; }
  objectFile = file;
  if (objectPreviewURL) URL.revokeObjectURL(objectPreviewURL);
  objectPreviewURL = URL.createObjectURL(file);
  $('object-preview').src = objectPreviewURL;
  $('object-preview-wrap').hidden = false;
  $('object-drop').querySelector('strong').textContent = file.name || 'Fotografía lista';
  return true;
}

async function recognizeObject() {
  if (!objectFile) throw new Error('Elige una foto, toma una captura o prueba un ejemplo.');
  const form = new FormData();
  form.append('image', objectFile);
  const data = await api('/api/objects', {method:'POST',body:form});
  const first = data.predictions[0];
  $('object-name').textContent = first.name;
  $('object-confidence').textContent = `${first.probability.toFixed(1)}% de probabilidad estimada · etiqueta original: ${first.original}`;
  $('object-probabilities').innerHTML = data.predictions.map(p=>`<div class="object-probability"><div><strong>${escapeHTML(p.name)}</strong><small>${escapeHTML(p.original)}</small></div><span>${p.probability.toFixed(1)}%</span><div class="object-probability-track"><b style="width:${p.probability}%"></b></div></div>`).join('');
  $('object-model-preview').src = data.preview;
  $('object-model-preview').hidden = false;
  $('object-result-note').textContent = data.uncertain ? 'Hay dudas entre varias categorías. Acerca el objeto, simplifica el fondo y prueba otro ángulo.' : 'Compara la propuesta con lo que realmente fotografiaste. Una probabilidad alta también puede acompañar un error.';
  $('object-result-note').classList.toggle('uncertain',data.uncertain);
  saveExperiment('objetos','Objeto: '+first.name,`${first.probability.toFixed(1)}% · MobileNetV2 · 1.000 categorías`,{category:first.original,probability:first.probability,predictions:data.predictions});
}

$('object-input').addEventListener('change',e=>setObjectFile(e.target.files[0]));
$('classify-object').addEventListener('click',()=>busy($('classify-object'),recognizeObject));
['dragenter','dragover'].forEach(event=>$('object-drop').addEventListener(event,e=>{e.preventDefault();$('object-drop').classList.add('dragover');}));
['dragleave','drop'].forEach(event=>$('object-drop').addEventListener(event,e=>{e.preventDefault();$('object-drop').classList.remove('dragover');}));
$('object-drop').addEventListener('drop',e=>setObjectFile(e.dataTransfer.files[0]));
document.querySelectorAll('[data-object-sample]').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{
  const id=button.dataset.objectSample;
  const response=await fetch('/static/object-'+id+'.jpg');
  if(!response.ok)throw new Error('No se pudo cargar la foto de ejemplo.');
  const blob=await response.blob();
  if(setObjectFile(new File([blob],'ejemplo-'+id+'.jpg',{type:'image/jpeg'})))await recognizeObject();
})));

window.stopObjectCamera = function() {
  objectCameraToken++;
  if(objectStream)objectStream.getTracks().forEach(t=>t.stop());
  objectStream=null;
  $('object-video').srcObject=null;
  $('object-camera-box').hidden=true;
};
$('object-camera').addEventListener('click',()=>busy($('object-camera'),async()=>{
  if(!navigator.mediaDevices?.getUserMedia)throw new Error('Tu navegador no ofrece cámara. Puedes subir una fotografía.');
  window.stopObjectCamera();
  stopCamera();
  const token=objectCameraToken;
  try {
    const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}},audio:false});
    if(token!==objectCameraToken){stream.getTracks().forEach(t=>t.stop());return;}
    objectStream=stream;$('object-video').srcObject=stream;$('object-camera-box').hidden=false;
  } catch {throw new Error('No se pudo abrir la cámara. Revisa el permiso o utiliza una foto.');}
}));
$('object-stop-camera').addEventListener('click',window.stopObjectCamera);
$('object-capture').addEventListener('click',()=>busy($('object-capture'),async()=>{
  const video=$('object-video');
  if(!video.videoWidth)throw new Error('Espera a que la cámara esté lista.');
  const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;
  canvas.getContext('2d').drawImage(video,0,0);
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.92));
  if(!blob)throw new Error('No se pudo capturar la imagen.');
  setObjectFile(new File([blob],'captura-objeto.jpg',{type:'image/jpeg'}));
  window.stopObjectCamera();
  await recognizeObject();
}));
window.addEventListener('pagehide',()=>{window.stopObjectCamera();if(objectPreviewURL)URL.revokeObjectURL(objectPreviewURL);});
document.addEventListener('visibilitychange',()=>{if(document.hidden){window.stopObjectCamera();stopCamera();}});
document.addEventListener('keydown',e=>{if(e.key==='Escape')window.stopObjectCamera();});

function renderCatalog() {
  const term=$('catalog-search').value.toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const group=$('catalog-group').value;
  const filtered=objectCatalog.filter(c=>{
    const normalized=(c.name+' '+c.original).toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    const isObject=c.id>=398&&c.id<=969;
    return normalized.includes(term)&&(group==='all'||(group==='objects'?isObject:!isObject));
  });
  $('catalog-count').textContent=filtered.length+' de 1.000 categorías';
  $('object-catalog').innerHTML=filtered.length?filtered.slice(0,catalogLimit).map(c=>`<div class="catalog-item"><span>${String(c.id+1).padStart(4,'0')}</span><strong>${escapeHTML(c.name)}</strong><small>${escapeHTML(c.original)}</small></div>`).join(''):'<p class="catalog-empty">No hay una clase con ese nombre. Busca un término parecido o consulta la etiqueta en inglés.</p>';
  $('catalog-more').hidden=filtered.length<=catalogLimit;
}
['catalog-search','catalog-group'].forEach(id=>$(id).addEventListener(id==='catalog-search'?'input':'change',()=>{catalogLimit=60;renderCatalog();}));
$('catalog-more').addEventListener('click',()=>{catalogLimit+=60;renderCatalog();});
api('/api/objects/catalog').then(data=>{objectCatalog=data.classes;renderCatalog();}).catch(()=>{$('catalog-count').textContent='No se pudo cargar el catálogo';});
