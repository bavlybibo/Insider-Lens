import {useEffect,useState} from 'react';
import type {Map as GeographicMap} from 'maplibre-gl';
import {areaBounds,type CaQuery} from './canada';

/** Geographic label anchors only. Never an observation/coverage or boundary layer. */
export function FallbackPlaces({map,area}:{map:GeographicMap;area:CaQuery['area']}){
 const [positions,setPositions]=useState<{name:string;x:number;y:number}[]>([]);
 useEffect(()=>{
  const b=areaBounds[area];
  const anchors:{name:string;lon:number;lat:number}[]=area==='canada'?[{name:'Canada',lon:-100,lat:60},{name:'United States',lon:-100,lat:42},{name:'Greenland',lon:-42,lat:72}]:[{name:area==='south'?'Southern study tract':'Northern study tract',lon:(b[0]+b[2])/2,lat:(b[1]+b[3])/2}];
  const update=()=>{const size=map.getContainer().getBoundingClientRect();setPositions(anchors.map(a=>{const p=map.project([a.lon,a.lat]);return {name:a.name,x:p.x,y:p.y};}).filter(p=>p.x>65&&p.x<size.width-65&&p.y>100&&p.y<size.height-80));};
  update();map.on('move',update);map.on('resize',update);return()=>{map.off('move',update);map.off('resize',update);};
 },[map,area]);
 return <div className="fallback-places" aria-label="Coarse geographic labels; not observation coverage">{positions.map(p=><span key={p.name} style={{left:p.x,top:p.y}}>{p.name}</span>)}</div>;
}
