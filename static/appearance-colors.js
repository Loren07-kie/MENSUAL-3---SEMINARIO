/* Clasificación de color aparente; no deduce identidad ni atributos demográficos. */
(function(root){
  function median(values){const a=[...values].sort((x,y)=>x-y);return a.length?a[Math.floor(a.length/2)]:0;}
  function colorOf(samples){if(samples.length<12)return null;return [0,1,2].map(c=>median(samples.map(p=>p[c])));}
  function hsv(rgb){const [r,g,b]=rgb.map(v=>v/255),max=Math.max(r,g,b),min=Math.min(r,g,b),d=max-min;let h=0;if(d){h=max===r?((g-b)/d)%6:max===g?(b-r)/d+2:(r-g)/d+4;h=(h*60+360)%360;}return {h,s:max?d/max:0,v:max};}
  function lightness(rgb){const a=rgb.map(c=>{c/=255;return c<=.04045?c/12.92:((c+.055)/1.055)**2.4;});const y=.2126*a[0]+.7152*a[1]+.0722*a[2];return y>.008856?116*Math.cbrt(y)-16:903.3*y;}
  function hair(rgb){if(!rgb)return '';const {h,s,v}=hsv(rgb);if(v<.23)return 'Negro';if(s<.16&&v>.55)return 'Canoso / blanco';if(s<.2&&v<.55)return 'Castaño oscuro';if(h>55&&h<300&&s>.28)return 'Teñido / varios colores';if((h<18||h>345)&&s>.45&&v>.38)return 'Pelirrojo';if(h>=28&&h<=65&&v>.58)return 'Rubio';return v<.48?'Castaño oscuro':'Castaño claro';}
  function eyes(rgb){if(!rgb)return '';const {h,s,v}=hsv(rgb);if(v<.25)return 'Marrón oscuro';if(s<.17)return 'Gris';if(h>=170&&h<=270&&s>.18)return 'Azul';if(h>=65&&h<170&&s>.2)return 'Verde';if(h>=35&&h<65&&v>.35)return 'Avellana';return v<.48?'Marrón oscuro':'Marrón claro';}
  function skin(rgb){if(!rgb)return '';const {h,s}=hsv(rgb);if(s>.35&&h>85&&h<310)return '';const l=lightness(rgb);return l>80?'Muy claro':l>66?'Claro':l>50?'Intermedio':l>35?'Moreno':'Oscuro';}
  function hex(rgb){return rgb?'#'+rgb.map(v=>Math.round(v).toString(16).padStart(2,'0')).join(''):'';}
  function sampleMask(image,mask,mw,mh,label,bounds){
    const samples=[];const {width,height,data}=image;
    for(let y=0;y<mh;y+=2)for(let x=0;x<mw;x+=2){
      if(mask[y*mw+x]!==label)continue;
      const px=Math.min(width-1,Math.floor((x+.5)*width/mw)),py=Math.min(height-1,Math.floor((y+.5)*height/mh));
      if(bounds&&(px<bounds.x||px>bounds.x+bounds.w||py<bounds.y||py>bounds.y+bounds.h))continue;
      const k=(py*width+px)*4,p=[data[k],data[k+1],data[k+2]];const c=hsv(p);
      if(c.v>.97&&c.s<.08)continue;
      samples.push(p);
    }
    return {rgb:colorOf(samples),count:samples.length};
  }
  function sampleIris(image,points){
    const all=[];const regions=[];
    for(const [center,border] of [[468,[469,470,471,472]],[473,[474,475,476,477]]]){
      if(!points[center]||border.some(i=>!points[i]))continue;
      const cx=points[center].x*image.width,cy=points[center].y*image.height;
      const radius=median(border.map(i=>Math.hypot(points[i].x*image.width-cx,points[i].y*image.height-cy)));
      if(radius<4)continue;
      regions.push({x:cx,y:cy,r:radius});
      for(let y=Math.max(0,Math.floor(cy-radius));y<Math.min(image.height,cy+radius);y++)for(let x=Math.max(0,Math.floor(cx-radius));x<Math.min(image.width,cx+radius);x++){
        const distance=Math.hypot(x-cx,y-cy)/radius;if(distance<.42||distance>.83)continue;
        const k=(y*image.width+x)*4,p=[image.data[k],image.data[k+1],image.data[k+2]],c=hsv(p);
        if(c.v<.13||c.v>.93||c.s<.035)continue;
        all.push(p);
      }
    }
    return {rgb:colorOf(all),count:all.length,regions};
  }
  const api={median,colorOf,hsv,lightness,hair,eyes,skin,hex,sampleMask,sampleIris};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.NexoAppearanceColors=api;
})(typeof window==='undefined'?globalThis:window);
