import type { FeatureCollection,MultiPolygon } from 'geojson';
import type { StyleSpecification } from 'maplibre-gl';
export type ContextCountries=FeatureCollection<MultiPolygon,{name:string;label?:number[]}>;
export async function loadCoarseContext(signal:AbortSignal) {
  const response=await fetch('/basemap/provenance.json',{signal});if(!response.ok)throw new Error('Coarse context manifest unavailable');
  const provenance=await response.json();
  const data=await fetch('/basemap/iberia-countries.geojson',{signal});if(!data.ok)throw new Error('Coarse context geometry unavailable');
  const bytes=await data.arrayBuffer();
  const checksum=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(checksum!==provenance.derived_sha256)throw new Error('Coarse context checksum mismatch');
  const countries:ContextCountries=JSON.parse(new TextDecoder().decode(bytes));
  if(countries.type!=='FeatureCollection'||countries.features.length!==4)throw new Error('Coarse context schema mismatch');
  for(const f of countries.features) {
    if(f.geometry.type!=='MultiPolygon'||!['Portugal','Spain','France','Morocco'].includes(f.properties.name))throw new Error('Invalid context country');
    for(const polygon of f.geometry.coordinates)for(const ring of polygon)for(const [lon,lat]of ring)if(!Number.isFinite(lon)||!Number.isFinite(lat)||Math.abs(lon)>180||Math.abs(lat)>90)throw new Error('Invalid context coordinate');
  }
  const style:StyleSpecification={version:8,sources:{'offline-countries':{type:'geojson',data:countries,attribution:'Made with <a href="https://www.naturalearthdata.com/">Natural Earth</a> · 1:50 million'}},layers:[
    {id:'offline-water',type:'background',paint:{'background-color':'#e1e9e5'}},
    {id:'offline-land',type:'fill',source:'offline-countries',paint:{'fill-color':'#f5f2e8'}},
    {id:'offline-borders',type:'line',source:'offline-countries',paint:{'line-color':'#819687','line-width':1.2}},
  ]};
  return {style,countries};
}
