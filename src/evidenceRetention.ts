import {CA_GRID,CA_SOURCES,caUnproject,cellId,verifiedJson,type CaCatalog,type CaChunk,type CaQuery,type NativeFlag} from './canada';
import {coverageState} from './nativeHistory';
export const GROUPS=['MODIS_ONLY','SHARED','VIIRS_ONLY'] as const;
export type KeyGroup=typeof GROUPS[number];
export const GROUP_NAMES={MODIS_ONLY:'MODIS-only positive keys',SHARED:'Shared positive keys',VIIRS_ONLY:'VIIRS-only positive keys'};
export const GROUP_COLORS={MODIS_ONLY:'#bb651f',SHARED:'#76529b',VIIRS_ONLY:'#087c80',MIXED:'#768c7b'};
export type PositiveKey={i:number;j:number;date:string;records:[number,number,number];group:KeyGroup};
export function positiveKeys(native:CaChunk[],flag:NativeFlag):PositiveKey[]{
 const keys=new Map<string,PositiveKey>();
 for(const c of native)for(const [i,j,days] of c.cells)for(const [d,nd,nn] of days){
  const n=flag==='D'?nd:flag==='N'?nn:nd+nn;if(!n)continue;
  const date=`${c.month}-${String(d).padStart(2,'0')}`,id=`${i}:${j}:${date}`,key=keys.get(id)??{i,j,date,records:[0,0,0],group:'MODIS_ONLY'};key.records[CA_SOURCES.indexOf(c.source)]+=n;keys.set(id,key);
 }
 return [...keys.values()].map(k=>({...k,group:k.records[0]+k.records[1]>0?(k.records[2]>0?'SHARED':'MODIS_ONLY'):'VIIRS_ONLY'} as PositiveKey)).sort((a,b)=>a.i-b.i||a.j-b.j||a.date.localeCompare(b.date));
}
export const partitionCounts=(keys:PositiveKey[])=>Object.fromEntries(GROUPS.map(g=>[g,keys.filter(k=>k.group===g).length])) as Record<KeyGroup,number>;
export const retainedRecords=(k:PositiveKey,q:CaQuery)=>CA_SOURCES.reduce((n,s,i)=>n+(q.sources.includes(s)?k.records[i]:0),0);
export function retentionGeometry(keys:PositiveKey[],q:CaQuery){
 const cells=new Map<string,{i:number;j:number;counts:Record<KeyGroup,number>;kept:Record<KeyGroup,number>;masks:Record<KeyGroup,number>[]} >();
 for(const k of keys){const id=cellId(k.i,k.j),v=cells.get(id)??{i:k.i,j:k.j,counts:{MODIS_ONLY:0,SHARED:0,VIIRS_ONLY:0},kept:{MODIS_ONLY:0,SHARED:0,VIIRS_ONLY:0},masks:Array.from({length:8},()=>({MODIS_ONLY:0,SHARED:0,VIIRS_ONLY:0}))};v.counts[k.group]++;if(retainedRecords(k,q)>0)v.kept[k.group]++;for(let mask=1;mask<8;mask++)if(k.records.some((n,i)=>n>0&&(mask&(1<<i))))v.masks[mask][k.group]++;cells.set(id,v);}
 const polygons:GeoJSON.Feature[]=[],marks:GeoJSON.Feature[]=[];
 for(const [id,c] of cells){const groups=GROUPS.filter(g=>c.counts[g]>0),ring:number[][]=[];
  for(const [ax,ay,bx,by] of [[0,0,1,0],[1,0,1,1],[1,1,0,1],[0,1,0,0]])for(let k=0;k<5;k++)ring.push(caUnproject((c.i+ax+(bx-ax)*k/5)*10000,(c.j+ay+(by-ay)*k/5)*10000));ring.push(ring[0]);
  polygons.push({type:'Feature',geometry:{type:'Polygon',coordinates:[ring]},properties:{cell:id,group:groups.length===1?groups[0]:'MIXED',kept:GROUPS.reduce((n,g)=>n+c.kept[g],0),keys:GROUPS.reduce((n,g)=>n+c.counts[g],0),...Object.fromEntries(c.masks.map((v,m)=>['kept_'+m,GROUPS.reduce((n,g)=>n+v[g],0)]))}});
  for(const g of groups)marks.push({type:'Feature',geometry:{type:'Point',coordinates:caUnproject((c.i+.5)*10000,(c.j+.5)*10000)},properties:{cell:id,group:g,count:c.counts[g],kept:c.kept[g],...Object.fromEntries(c.masks.map((v,m)=>['kept_'+m,v[g]])),offset:g==='MODIS_ONLY'?-9:g==='SHARED'?0:9}});
 }
 return {cells:{type:'FeatureCollection',features:polygons} as GeoJSON.FeatureCollection,marks:{type:'FeatureCollection',features:marks} as GeoJSON.FeatureCollection};
}
export function positiveKeyCsv(c:CaCatalog,q:CaQuery,keys:PositiveKey[]){
 const header=['schema','candidate','scope','cell_id','utc_day','positive_key_group','AQUA_MODIS_records','TERRA_MODIS_records','SNPP_VIIRS_records','MODIS_ONLY_retains_key','VIIRS_ONLY_retains_key','ALL_NATIVE_retains_key','checked_sources_retained_records','checked_sources_retains_key','native_acquisition_flag','grid','cell_width_m','source_lineage_and_hashes','observation_opportunity','extract_completeness','coincident_sensor_match','physical_fires_missed','calibrated_harmonization'];
 const lineage=CA_SOURCES.map(s=>{const a=c.archives.find(a=>a.request===(s==='SNPP_VIIRS'?'845606':'845605'))!,m=a.members.find(m=>m.processing_class===q.pc),e=c.coverage.find(e=>e.month===q.month&&e.source===s&&e.pc===q.pc) as typeof c.coverage[number]&{native_versions?:string[]}|undefined;return `${s}:${q.pc}:literal=${e?.native_versions?.join('|')??'unavailable'}:zip=${a.zip_sha256}:member=${m?.sha256??'unavailable'}:chunk=${e?.sha256??'unavailable'}`;}).join(';');
 const rows=keys.map(k=>['positive-key-partition-v1',c.candidate,JSON.stringify(q),cellId(k.i,k.j),k.date,k.group,...k.records,k.records[0]+k.records[1]>0,k.records[2]>0,true,retainedRecords(k,q),retainedRecords(k,q)>0,q.flag,CA_GRID,10000,lineage,'UNKNOWN','UNKNOWN','','','ADJUSTMENT_WITHHELD']);
 if(!keys.length)rows.push(['positive-key-partition-v1',c.candidate,JSON.stringify(q),q.cell??'',q.month,'NO_REPORTED_KEYS_SUPPORT_UNKNOWN',...Array(8).fill(''),q.flag,CA_GRID,10000,lineage,'UNKNOWN','UNKNOWN','','','ADJUSTMENT_WITHHELD']);
 header.push('source_evidence_states','production_vintage');
 const states=CA_SOURCES.map((s,i)=>`${s}:${coverageState(c,s,q,keys.reduce((n,k)=>n+k.records[i],0)).code}`).join(';');
 return [header,...rows.map(r=>[...r,states,'UNVERIFIED'])].map(r=>r.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
}
export async function loadPartitionAcceptance(c:CaCatalog,signal?:AbortSignal){
 const response=await fetch('/data/phase12/index.json',{signal,cache:'no-cache'});if(!response.ok)throw Error('Independent retention acceptance unavailable');const p=await response.json();
 if(p.candidate!==c.candidate||p.file!=='/data/phase12/PARTITION.json'||p.oracle_file!=='/data/phase12/INDEPENDENT_PARTITION.json')throw Error('Retention acceptance identity mismatch');
 const [a,o]=await Promise.all([verifiedJson<{candidate:string;catalog_sha256:string;cases:{id:string;month:string;flag:NativeFlag;rect:number[]|null;rows:(number|string)[][];counts:Record<string,number>}[];g4:string}>(p.file,p.sha256,signal),verifiedJson<{state:string;production_sha256:string;cases_verified:number;holdouts_queried:boolean;fit:boolean;g4:string}>(p.oracle_file,p.oracle_sha256,signal)]);
 const parent=await fetch('/data/canada/index.json',{signal}).then(r=>r.json());
 if(a.candidate!==c.candidate||a.catalog_sha256!==parent.sha256||o.state!=='PASS'||o.production_sha256!==p.sha256||o.cases_verified!==12||o.holdouts_queried||o.fit||a.g4!=='ADJUSTMENT_WITHHELD'||o.g4!==a.g4)throw Error('Retention independent recount not accepted');
 const primary=a.cases.find(v=>v.id==='overlap'&&v.flag==='ALL');if(!primary||primary.counts.MODIS_ONLY!==34||primary.counts.SHARED!==199||primary.counts.VIIRS_ONLY!==335||primary.rows.length!==568)throw Error('Retention partition reference mismatch');
 return {sha256:p.sha256,oracle_sha256:p.oracle_sha256,cases:a.cases};
}
