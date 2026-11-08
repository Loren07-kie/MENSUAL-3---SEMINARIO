const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const {File}=require('node:buffer');

function setup(getUserMedia){
  const elements=new Map(),windowHandlers={},documentHandlers={},messages=[],calls={draw:0,network:0};
  const element=id=>{
    if(!elements.has(id))elements.set(id,{hidden:true,value:'',files:[],textContent:'',handlers:{},videoWidth:1280,videoHeight:720,
      addEventListener(type,fn){(this.handlers[type]??=[]).push(fn);},
      async fire(type,event={}){for(const fn of this.handlers[type]||[])await fn(event);},
      removeAttribute(key){delete this[key];},play:async()=>{},reset(){},querySelector(){return {value:'Prefiero no indicarlo'};}});
    return elements.get(id);
  };
  const window={dispatchEvent(event){for(const fn of windowHandlers[event.type]||[])fn(event);},addEventListener:(type,fn)=>(windowHandlers[type]??=[]).push(fn),stopObjectCamera(){}};
  const canvas={getContext:()=>({translate(){},scale(){},drawImage(){calls.draw++;}}),toBlob:cb=>cb(new Blob(['photo'],{type:'image/jpeg'}))};
  const document={hidden:false,addEventListener:(type,fn)=>(documentHandlers[type]??=[]).push(fn),createElement:()=>canvas};
  const location={hash:'#ficha'};
  const context={$,window,document,location,navigator:{mediaDevices:{getUserMedia}},Blob,File,Event,
    FormData:class{get(k){return k==='gender'?'Prefiero no indicarlo':'';}},
    Image:class{set src(value){this.onload?.();}},
    URL:{createObjectURL:()=> 'blob:local-photo',revokeObjectURL(){}},
    toast:message=>messages.push(message),confirm:()=>true,downloadJSON(){},stopCamera(){},
    fetch(){calls.network++;throw Error('La ficha no debe enviar fotografías.');},
    busy:async(_button,work)=>{try{await work();}catch(error){messages.push(error.message);}},
  };
  function $(id){return element(id);}
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/personal.js'),'utf8'),context);
  return {element,window,document,location,messages,calls,canvas,windowHandlers,documentHandlers};
}
function stream(){const track={stops:0,stop(){this.stops++;},addEventListener(){}};return {track,getTracks:()=>[track],getVideoTracks:()=>[track]};}

test('solicita solo video frontal; captura una foto local y apaga la cámara',async()=>{
  const media=stream();let constraints;const s=setup(async value=>{constraints=value;return media;});
  await s.element('personal-camera-open').fire('click');
  assert.equal(constraints.audio,false);assert.equal(constraints.video.facingMode.ideal,'user');
  assert.equal(s.element('personal-camera-box').hidden,false);assert.equal(s.calls.draw,0);
  await s.element('personal-camera-capture').fire('click');
  assert.equal(s.calls.draw,1);assert.equal(media.track.stops,1);
  assert.equal(s.element('personal-camera-box').hidden,true);
  assert.equal(s.element('personal-photo-preview').src,'blob:local-photo');assert.equal(s.element('personal-photo-preview').hidden,false);
  assert.equal(s.calls.network,0);
});

test('si se abandona la ficha mientras se espera permiso, detiene el stream tardío',async()=>{
  let resolve;const s=setup(()=>new Promise(r=>{resolve=r;}));
  const pending=s.element('personal-camera-open').fire('click');
  s.location.hash='#inicio';s.windowHandlers.hashchange.forEach(fn=>fn());
  const media=stream();resolve(media);await pending;
  assert.equal(media.track.stops,1);assert.equal(s.element('personal-camera-video').srcObject,null);
  assert.equal(s.element('personal-camera-box').hidden,true);
});

test('un permiso rechazado muestra cómo habilitar la cámara y limpia la vista',async()=>{
  const s=setup(async()=>{const error=Error('denied');error.name='NotAllowedError';throw error;});
  await s.element('personal-camera-open').fire('click');
  assert.match(s.messages[0],/Permite el acceso/);assert.equal(s.element('personal-camera-box').hidden,true);
});

test('ocultar la página y reiniciar la ficha no dejan la cámara encendida',async()=>{
  const media=stream();const s=setup(async()=>media);
  await s.element('personal-camera-open').fire('click');s.document.hidden=true;
  s.documentHandlers.visibilitychange.forEach(fn=>fn());s.window.resetPersonalCard();
  assert.equal(media.track.stops,1);assert.equal(s.element('personal-camera-video').srcObject,null);
});

test('cerrar durante la conversión de una captura cancela su incorporación',async()=>{
  const media=stream(),s=setup(async()=>media);let finish;
  s.canvas.toBlob=callback=>{finish=callback;};
  await s.element('personal-camera-open').fire('click');
  const pending=s.element('personal-camera-capture').fire('click');s.window.stopPersonalCamera();
  finish(new Blob(['photo'],{type:'image/jpeg'}));await pending;
  assert.equal(s.element('personal-photo-preview').hidden,true);assert.equal(media.track.stops,1);assert.equal(s.calls.network,0);
});
