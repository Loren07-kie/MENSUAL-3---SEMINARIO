'use strict';
const APPEARANCE_VERSION='1.2.2';
let appearanceModels=null,appearanceEpoch=0;
const appearanceAutoValues=new Map();
const appearanceFields=['hairColor','eyeColor','skinTone'];
const appearanceIds={hairColor:'personal-hair-color',eyeColor:'personal-eye-color',skinTone:'personal-skin-tone'};
const appearanceLabels={hairColor:'Cabello',eyeColor:'Ojos',skinTone:'Piel visible'};
const appearanceEdited=new Set();
for(const id of Object.values(appearanceIds))$(id).addEventListener('change',()=>appearanceEdited.add(id));
function appearanceStatus(text){$('appearance-status').textContent=text;}
async function loadAppearanceModels(){
  if(!appearanceModels)appearanceModels=(async()=>{
    const {FilesetResolver,FaceLandmarker,ImageSegmenter}=await import(`https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${APPEARANCE_VERSION}/vision_bundle.mjs`);
    const files=await FilesetResolver.forVisionTasks(`https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${APPEARANCE_VERSION}/wasm`);
    const face=await FaceLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task',delegate:'CPU'},runningMode:'IMAGE',numFaces:2,outputFaceBlendshapes:false,outputFacialTransformationMatrixes:false});
    try{
      const segmenter=await ImageSegmenter.createFromOptions(files,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite',delegate:'CPU'},runningMode:'IMAGE',outputCategoryMask:true,outputConfidenceMasks:false});
      return {face,segmenter};
    }catch(error){face.close();throw error;}
  })().catch(error=>{appearanceModels=null;throw error;});
  return appearanceModels;
}
function resetAppearance(){appearanceEpoch++;for(const [id,value] of appearanceAutoValues){if($(id).value===value&&!appearanceEdited.has(id))$(id).value='';}appearanceAutoValues.clear();$('appearance-analyze').disabled=false;$('appearance-results').hidden=true;$('appearance-items').replaceChildren();$('appearance-canvas').getContext('2d').clearRect(0,0,$('appearance-canvas').width,$('appearance-canvas').height);appearanceStatus('Sube o toma una fotografía para sugerir colores visibles automáticamente.');}
window.addEventListener('nexo-photo-cleared',resetAppearance);
window.addEventListener('nexo-photo-ready',()=>{analyzeAppearance(false);});
window.addEventListener('nexo-account-changed',resetAppearance);
$('appearance-analyze').addEventListener('click',()=>analyzeAppearance(true));
$('appearance-sample').addEventListener('click',()=>busy($('appearance-sample'),async()=>{const response=await fetch('/static/portrait-example.webp');if(!response.ok)throw new Error('No se pudo cargar el ejemplo.');const blob=await response.blob();window.stopPersonalCamera?.();usePersonalPhoto(new File([blob],'retrato-ficticio-de-ejemplo.webp',{type:'image/webp'}));}));
async function analyzeAppearance(force){
  const photo=$('personal-photo-preview');if(photo.hidden||!photo.src)return appearanceStatus('Primero toma o elige una fotografía.');
  const epoch=++appearanceEpoch;const button=$('appearance-analyze');button.disabled=true;
  appearanceStatus('Preparando el análisis en tu dispositivo. La primera vez se descargan los modelos; tu foto no se envía.');
  try{
    await photo.decode();const models=await loadAppearanceModels();if(epoch!==appearanceEpoch)return;
    const canvas=$('appearance-canvas');const factor=Math.min(1,1100/Math.max(photo.naturalWidth,photo.naturalHeight));canvas.width=Math.round(photo.naturalWidth*factor);canvas.height=Math.round(photo.naturalHeight*factor);
    const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(photo,0,0,canvas.width,canvas.height);
    const result=models.face.detect(canvas);const faces=result.faceLandmarks||[];
    if(!faces.length)throw new Error('No encontramos un rostro claro. Usa una foto frontal, con buena luz y sin cubrir los ojos.');
    if(faces.length>1)throw new Error('Hay más de un rostro. Usa una fotografía de una sola persona.');
    const points=faces[0];const xs=points.slice(0,468).map(p=>p.x*canvas.width),ys=points.slice(0,468).map(p=>p.y*canvas.height);
    const bounds={x:Math.min(...xs),y:Math.min(...ys),w:Math.max(...xs)-Math.min(...xs),h:Math.max(...ys)-Math.min(...ys)};
    if(bounds.w<120)throw new Error('El rostro ocupa muy pocos píxeles. Acerca la cámara o recorta una foto de mayor resolución.');
    const image=ctx.getImageData(0,0,canvas.width,canvas.height),C=window.NexoAppearanceColors;
    let hair={rgb:null,count:0},skin={rgb:null,count:0};
    models.segmenter.segment(canvas,seg=>{
      try{const mask=seg.categoryMask;if(!mask)return;const values=mask.getAsUint8Array();hair=C.sampleMask(image,values,mask.width,mask.height,1);skin=C.sampleMask(image,values,mask.width,mask.height,3,bounds);}finally{seg.close?.();}
    });
    const iris=C.sampleIris(image,points);
    const output={hairColor:{rgb:hair.rgb,value:hair.count>=30?C.hair(hair.rgb):''},eyeColor:{rgb:iris.rgb,value:iris.count>=15?C.eyes(iris.rgb):''},skinTone:{rgb:skin.rgb,value:skin.count>=30?C.skin(skin.rgb):''}};
    if(epoch!==appearanceEpoch)return;
    let count=0;
    for(const key of appearanceFields){const suggestion=output[key],field=$(appearanceIds[key]);if(suggestion.value&&(force||!field.value||!appearanceEdited.has(field.id))){field.value=suggestion.value;appearanceAutoValues.set(field.id,suggestion.value);if(force)appearanceEdited.delete(field.id);count++;}}
    personalForm.dispatchEvent(new Event('change',{bubbles:true}));
    ctx.strokeStyle='#f17b44';ctx.lineWidth=2;ctx.strokeRect(bounds.x,bounds.y,bounds.w,bounds.h);
    ctx.strokeStyle='#67cbe5';for(const eye of iris.regions){ctx.beginPath();ctx.arc(eye.x,eye.y,eye.r*1.3,0,Math.PI*2);ctx.stroke();}
    $('appearance-items').replaceChildren();
    for(const key of appearanceFields){const item=document.createElement('div');item.className='appearance-result-item';const dot=document.createElement('span');dot.className='appearance-swatch';dot.style.background=output[key].rgb?C.hex(output[key].rgb):'var(--soft)';const text=document.createElement('div');const strong=document.createElement('strong');strong.textContent=appearanceLabels[key];const small=document.createElement('small');small.textContent=output[key].value||'No se pudo determinar';text.append(strong,small);item.append(dot,text);$('appearance-items').append(item);}
    $('appearance-results').hidden=false;appearanceStatus(`Análisis listo: ${count} campo(s) actualizado(s). Revisa los colores sugeridos; la luz, el tinte y los lentes de contacto pueden alterar el resultado. Tipo, largo y uso de lentes se completan manualmente.`);
  }catch(error){if(epoch===appearanceEpoch){$('appearance-results').hidden=true;appearanceStatus(error.message?.startsWith('No ')||error.message?.startsWith('Hay ')||error.message?.startsWith('El rostro')?error.message:'No se pudieron cargar los modelos de análisis. Revisa tu conexión e inténtalo otra vez; puedes completar la ficha manualmente.');}}
  finally{if(epoch===appearanceEpoch)button.disabled=false;}
}
resetAppearance();
