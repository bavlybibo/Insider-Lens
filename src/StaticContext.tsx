import { useEffect,useState } from 'react';
import { loadCoarseContext,type ContextCountries } from './basemap';
import type { Release } from './science';
/** Verified geometry fallback; never used to calculate activity or opportunity. */
export function StaticContext({release}:{release:Release}){
  const [countries,setCountries]=useState<ContextCountries|null>(null),[error,setError]=useState(false);
  useEffect(()=>{const controller=new AbortController();loadCoarseContext(controller.signal).then(r=>setCountries(r.countries)).catch(()=>{if(!controller.signal.aborted)setError(true);});return()=>controller.abort();},[]);
  const xy=([lon,lat]:number[])=>[(lon+10)*120,(42-lat)*157];
  const path=(rings:number[][][])=>rings.map(ring=>ring.map((p,i)=>`${i?'L':'M'}${xy(p).join(',')}`).join(' ')+'Z').join(' ');
  const [w,s,e,n]=release.policy.aoi,top=xy([w,n]),bottom=xy([e,s]);
  return <figure className="static-context" aria-label="Static geographic context for the fixed Portugal study area" data-testid="static-context">
    {countries?<svg viewBox="0 0 480 480" role="img" aria-labelledby="static-map-title"><title id="static-map-title">Verified Natural Earth country outlines and fixed study AOI. Schematic WGS84 context; no observation mask or fire inference.</title><defs><clipPath id="static-frame"><rect width="480" height="480"/></clipPath></defs><g clipPath="url(#static-frame)"><rect width="480" height="480" fill="#dce9e4"/>{countries.features.map(f=><path key={f.properties.name} d={f.geometry.coordinates.map(p=>path(p)).join(' ')} fill="#f2eee0" stroke="#7f9583" strokeWidth="1.3" fillRule="evenodd"/>)}<rect x={top[0]} y={top[1]} width={bottom[0]-top[0]} height={bottom[1]-top[1]} fill="none" stroke="#245d4c" strokeWidth="2" strokeDasharray="6 4"/><text x="175" y="360" fill="#315445" fontFamily="Georgia" fontSize="20">Portugal</text><text x={top[0]+6} y={top[1]+19} fontSize="12" fill="#245d4c">Fixed scientific AOI</text></g></svg>:<p>{error?'Static country geometry unavailable.':'Loading verified static context…'}</p>}
    <figcaption>Static country context · <a href="https://www.naturalearthdata.com/" target="_blank" rel="noreferrer">Natural Earth</a> 1:50 million · schematic WGS84 view. Native records remain in the calendar, table and CSV; no observation QA inferred.</figcaption>
  </figure>;
}
