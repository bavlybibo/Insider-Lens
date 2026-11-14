import type { FeatureCollection,Polygon } from 'geojson';
import { type Detection,type Release,type SourceId } from './science';

export const ATLAS_METHOD='eg-descriptive-density-v1';
export const SAMPLE_M=2000;
export const PALETTES:Record<SourceId,[string,string,string]>={AQUA_MODIS:['#fff0ce','#e89937','#9c3519'],SNPP_VIIRS:['#d9f4eb','#31a9a8','#075963'],TERRA_MODIS:['#eee3fa','#b391cb','#603b85']};
const A=6378137,F=1/298.257223563,E2=2*F-F*F,E=Math.sqrt(E2),RAD=Math.PI/180;
const q=(p:number)=>{const s=Math.sin(p);return (1-E2)*(s/(1-E2*s*s)-Math.log((1-E*s)/(1+E*s))/(2*E));};
const QP=q(Math.PI/2),P0=40.05*RAD,B0=Math.asin(q(P0)/QP),RQ=A*Math.sqrt(QP/2),D=A*Math.cos(P0)/Math.sqrt(1-E2*Math.sin(P0)**2)/(RQ*Math.cos(B0));
/** WGS84 ellipsoidal LAEA, same declared CRS; checked against PROJ fixtures. */
export function project(lon:number,lat:number):[number,number]{
  const b=Math.asin(q(lat*RAD)/QP),delta=(lon+7.95)*RAD;
  const k=RQ*Math.sqrt(2/(1+Math.sin(B0)*Math.sin(b)+Math.cos(B0)*Math.cos(b)*Math.cos(delta)));
  return [k*D*Math.cos(b)*Math.sin(delta),k/D*(Math.cos(B0)*Math.sin(b)-Math.sin(B0)*Math.cos(b)*Math.cos(delta))];
}
export function unproject(x:number,y:number):[number,number]{
  const xx=x/D,yy=y*D,r=Math.hypot(xx,yy);if(r===0)return [-7.95,40.05];
  const c=2*Math.asin(r/(2*RQ)),b=Math.asin(Math.cos(c)*Math.sin(B0)+yy*Math.sin(c)*Math.cos(B0)/r);
  const target=QP*Math.sin(b);let p=b;
  for(let i=0;i<12;i++){const delta=(q(p)-target)/(2*(1-E2)*Math.cos(p)/(1-E2*Math.sin(p)**2)**2);p-=delta;if(Math.abs(delta)<1e-13)break;}
  return [-7.95+Math.atan2(xx*Math.sin(c),r*Math.cos(B0)*Math.cos(c)-yy*Math.sin(B0)*Math.sin(c))/RAD,p/RAD];
}
export function clipRing(points:number[][],bbox:number[]){
  let output=points.slice(0,-1);
  for(const [axis,bound,sign]of [[0,bbox[0],1],[0,bbox[2],-1],[1,bbox[1],1],[1,bbox[3],-1]]){
    const input=output;output=[];if(!input.length)break;
    for(let i=0;i<input.length;i++){
      const a=input[i],b=input[(i+1)%input.length],insideA=(a[axis]-bound)*sign>=0,insideB=(b[axis]-bound)*sign>=0;
      if(insideA)output.push(a);
      if(insideA!==insideB){const t=(bound-a[axis])/(b[axis]-a[axis]);const p=[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])];p[axis]=bound;output.push(p);}
    }
  }
  return output.length>=3?[...output,output[0]]:[];
}
export function kernel(distanceKm:number,hKm:number){return distanceKm<hKm?2/(Math.PI*hKm*hKm)*(1-(distanceKm/hKm)**2):0;}
export type Density=FeatureCollection<Polygon,{value:number;nearest:string;x_m:number;y_m:number}>;
export function density(records:Detection[],hKm:5|10,bbox:number[]):Density{
  const h=hKm*1000,h2=h*h,acc=new Map<string,{x:number;y:number;value:number;nearest:string;distance:number}>();
  for(const r of records){
    const [x,y]=project(r.longitude,r.latitude);
    for(let i=Math.floor((x-h)/SAMPLE_M);i<=Math.floor((x+h)/SAMPLE_M);i++)for(let j=Math.floor((y-h)/SAMPLE_M);j<=Math.floor((y+h)/SAMPLE_M);j++){
      const cx=(i+.5)*SAMPLE_M,cy=(j+.5)*SAMPLE_M,dist=(cx-x)**2+(cy-y)**2;if(dist>=h2)continue;
      const key=`${i}:${j}`,a=acc.get(key)??{x:cx,y:cy,value:0,nearest:r.id,distance:Infinity};
      a.value+=2/(Math.PI*hKm*hKm)*(1-dist/h2);if(dist<a.distance){a.nearest=r.id;a.distance=dist;}acc.set(key,a);
    }
  }
  const features:Density['features']=[];
  for(const a of acc.values()){
    const [lon,lat]=unproject(a.x,a.y);if(lon<bbox[0]||lon>bbox[2]||lat<bbox[1]||lat>bbox[3])continue;
    const half=SAMPLE_M/2,ring=clipRing([[-half,-half],[half,-half],[half,half],[-half,half],[-half,-half]].map(([dx,dy])=>unproject(a.x+dx,a.y+dy)),bbox);
    if(ring.length)features.push({type:'Feature',properties:{value:a.value,nearest:a.nearest,x_m:a.x,y_m:a.y},geometry:{type:'Polygon',coordinates:[ring]}});
  }
  return {type:'FeatureCollection',features};
}
export function quantitativeCells(release:Release,records:Detection[],metric:'records'|'occupied_cell_days'){
  const bins=new Map<string,{records:number;keys:Set<string>}>();
  for(const r of records){const b=bins.get(r.cell)??{records:0,keys:new Set<string>()};b.records++;b.keys.add(`${r.source}|${r.day}`);bins.set(r.cell,b);}
  return {type:'FeatureCollection' as const,features:release.cells.features.filter(f=>bins.has(f.properties.cell)).map(f=>{
    const b=bins.get(f.properties.cell)!;return {...f,properties:{cell:f.properties.cell,value:metric==='records'?b.records:b.keys.size,records:b.records,days:b.keys.size}};
  })};
}
export function utcInstants(records:Detection[]){return [...new Set(records.map(r=>r.utc))].sort();}
