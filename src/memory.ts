import type { Release,Selection } from './science';
import { queryBounds } from './science';
export const ERA_SOURCE='https://firms.modaps.eosdis.nasa.gov/content/descriptions/';
export const ERAS=[
  {id:'TERRA_MODIS',name:'Terra MODIS',start:'2000-11-01',end:null,color:'#84659d',href:ERA_SOURCE+'FIRMS_MODIS_Firehotspots.html'},
  {id:'AQUA_MODIS',name:'Aqua MODIS',start:'2002-07-03',end:null,color:'#bd592c',href:ERA_SOURCE+'FIRMS_MODIS_Firehotspots.html'},
  {id:'SNPP_VIIRS',name:'S-NPP VIIRS',start:'2012-01-20',end:'2026-11-02T15:40:00Z',color:'#087c89',href:ERA_SOURCE+'FIRMS_VIIRS_Firehotspots.html'},
  {id:'NOAA20',name:'NOAA-20',start:'2020-01-01',end:null,color:'#6c9394',href:ERA_SOURCE+'FIRMS_VIIRS_Firehotspots.html'},
  {id:'NOAA21',name:'NOAA-21',start:'2024-01-17',end:null,color:'#8a9e9a',href:ERA_SOURCE+'FIRMS_VIIRS_Firehotspots.html'},
] as const;
export function memoryEvidence(release:Release,selection:Selection,stagedMonths:string[]=['2013-01']){
  const month=selection.month??'2017-06',{start,end}=queryBounds({...selection,day:null}),delivered=release.months.includes(month);
  return ERAS.map(era=>({ ...era,potential:Date.parse(end)>Date.parse(era.start)&&(!era.end||Date.parse(start)<Date.parse(era.end)),
    delivery:delivered&&!era.id.startsWith('NOAA')?'DELIVERED_DIAGNOSTIC':stagedMonths.includes(month)&&!era.id.startsWith('NOAA')?'STAGED_UNQUALIFIED':'NOT_ACQUIRED',
    complete:'UNKNOWN',opportunity:'UNKNOWN',measurement:delivered&&!era.id.startsWith('NOAA')?'DIAGNOSTIC_RELEASED':'UNAVAILABLE',bridge:'NOT_SCIENTIFICALLY_RELEASED'}));
}
