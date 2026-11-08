const test=require('node:test');
const assert=require('node:assert/strict');
const C=require('../static/appearance-colors.js');
test('colores aparentes de cabello distinguen negro, canas y tinte',()=>{
  assert.equal(C.hair([25,21,19]),'Negro');assert.equal(C.hair([180,178,177]),'Canoso / blanco');assert.equal(C.hair([40,50,190]),'Teñido / varios colores');
});
test('colores de iris distinguen azul, verde y marrón sin inferir otros atributos',()=>{
  assert.equal(C.eyes([55,95,145]),'Azul');assert.equal(C.eyes([55,100,50]),'Verde');assert.equal(C.eyes([50,32,20]),'Marrón oscuro');
});
test('la piel describe luminosidad visible y rechaza iluminación fuertemente azul',()=>{
  assert.equal(C.skin([228,202,181]),'Muy claro');assert.equal(C.skin([95,70,52]),'Oscuro');assert.equal(C.skin([30,60,180]),'');
});
test('el muestreo usa solo la clase segmentada y respeta el recorte del rostro',()=>{
  const width=40,height=40,data=new Uint8ClampedArray(width*height*4);for(let i=0;i<data.length;i+=4){data.set([20,30,40,255],i);}
  const mask=new Uint8Array(width*height);for(let y=0;y<height;y++)for(let x=0;x<20;x++)mask[y*width+x]=1;
  const found=C.sampleMask({width,height,data},mask,width,height,1);assert.deepEqual(found.rgb,[20,30,40]);
  const missing=C.sampleMask({width,height,data},mask,width,height,1,{x:25,y:0,w:10,h:40});assert.equal(missing.rgb,null);
});
test('una imagen sin iris suficiente no inventa el color de ojos',()=>{
  const output=C.sampleIris({width:100,height:100,data:new Uint8ClampedArray(40000)},[]);assert.equal(output.rgb,null);assert.equal(output.count,0);
});
test('los resultados solo ofrecen categorías de color y permiten ausencia de datos',()=>{
  assert.equal(C.hair(null),'');assert.equal(C.eyes(null),'');assert.equal(C.skin(null),'');assert.equal(C.colorOf([[3,4,5]]),null);assert.equal(C.hex([0,128,255]),'#0080ff');
});
