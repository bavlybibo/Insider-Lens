import {CA_NAMES,CA_SOURCES,availability,caSummary,era,selectedCells,type CaCatalog,type CaChunk,type CaQuery,type NativeFlag} from './canada';
import type {SourceId} from './science';

export const POLICIES={MODIS_ONLY:CA_SOURCES.slice(0,2),VIIRS_ONLY:CA_SOURCES.slice(2),ALL_NATIVE:CA_SOURCES} as const;
export type Policy=keyof typeof POLICIES;
export const POLICY_NAMES:Record<Policy,string>={MODIS_ONLY:'MODIS only',VIIRS_ONLY:'VIIRS only',ALL_NATIVE:'Both native'};
export function retention(chunks:CaChunk[],flag:NativeFlag){
 const lanes=Object.fromEntries(CA_SOURCES.map(s=>[s,{records:0,keys:new Set<string>(),dates:new Set<string>()}])) as Record<SourceId,{records:number;keys:Set<string>;dates:Set<string>}>;
 for(const c of chunks)for(const [i,j,days] of c.cells)for(const [d,nd,nn] of days){
  const n=flag==='D'?nd:flag==='N'?nn:nd+nn;if(!n)continue;
  const date=`${c.month}-${String(d).padStart(2,'0')}`,lane=lanes[c.source];lane.records+=n;lane.keys.add(`${i}:${j}:${date}`);lane.dates.add(date);
 }
 const fullKeys=new Set(CA_SOURCES.flatMap(s=>[...lanes[s].keys])),fullDates=new Set(CA_SOURCES.flatMap(s=>[...lanes[s].dates]));
 const total=CA_SOURCES.reduce((n,s)=>n+lanes[s].records,0);
 return Object.fromEntries((Object.keys(POLICIES) as Policy[]).map(p=>{
  const sources=POLICIES[p],keys=new Set(sources.flatMap(s=>[...lanes[s].keys])),dates=new Set(sources.flatMap(s=>[...lanes[s].dates]));
  const records=sources.reduce((n,s)=>n+lanes[s].records,0);
  return [p,{records,source_cell_days:Object.fromEntries(sources.map(s=>[s,lanes[s].keys.size])),union_cell_days:keys.size,dates_with_records:[...dates].sort(),excluded_records:total-records,exclusive_cell_days_lost:[...fullKeys].filter(k=>!keys.has(k)).length,exclusive_dates_lost:[...fullDates].filter(d=>!dates.has(d)).sort()}];
 })) as Record<Policy,{records:number;source_cell_days:Partial<Record<SourceId,number>>;union_cell_days:number;dates_with_records:string[];excluded_records:number;exclusive_cell_days_lost:number;exclusive_dates_lost:string[]}>;
}
export function coverageState(c:CaCatalog,s:SourceId,q:CaQuery,reported:number){
 const e=era(s,q.month,q.day),a=availability(c,s,q.month,q.pc,q.day);
 if(e==='SOURCE_NOT_YET_IN_ERA')return {code:e,label:'Not yet in era',detail:'Instrument-era evidence unavailable; not a zero.'};
 if(e==='SOURCE_ERA_ENDED')return {code:e,label:'Source era ended',detail:'New S-NPP delivery unavailable; not a zero.'};
 if(a==='SOURCE_PRODUCT_NOT_ACQUIRED'||a==='PERIOD_NOT_REPRESENTED_IN_ACQUIRED_PRODUCT')return {code:'MONTH_NOT_ACQUIRED',label:'Month not acquired',detail:'Operational-era period is not represented by this acquired processing class.'};
 if(reported>0)return {code:'POSITIVE_REPORTED',label:'Positive records',detail:`${reported.toLocaleString('en-US')} records in this selection; archive completeness unqualified; observation opportunity unknown.`};
 return {code:'ACQUIRED_SUPPORT_UNKNOWN',label:'Support unknown',detail:'Archive spans this period; no selected positive rows. Completeness and observation opportunity unqualified; no valid non-detection inferred.'};
}
export function retentionCsv(c:CaCatalog,q:CaQuery,chunks:CaChunk[]){
 const result=retention(chunks,q.flag),summary=caSummary(chunks,q.flag);
 const head=['schema','candidate_id','policy','scope','grid','cell_m','records_retained','records_excluded_by_policy','union_positive_cell_days','dates_with_records','utc_dates','exclusive_cell_days_excluded','exclusive_dates_excluded',...CA_SOURCES.flatMap(s=>[s+'_records',s+'_cell_days']), 'source_archive_member_sha256','observation_opportunity','extract_completeness','valid_nondetections','physical_fires_lost','adjustment'];
 const rows=(Object.keys(POLICIES) as Policy[]).map(p=>{
  const r=result[p],sources=POLICIES[p];
  const hashes=sources.map(s=>{const a=c.archives.find(a=>a.request===(s==='SNPP_VIIRS'?'845606':'845605'));return `${s}:${a?.zip_sha256}:${a?.members.find(m=>m.processing_class===q.pc)?.sha256}`;}).join(';');
  return ['native-evidence-retention-v1',c.candidate,p,JSON.stringify({...q,sources}),c.grid.grid_id,10000,r.records,r.excluded_records,r.union_cell_days,r.dates_with_records.length,r.dates_with_records.join(';'),r.exclusive_cell_days_lost,r.exclusive_dates_lost.join(';'),...CA_SOURCES.flatMap<unknown>(s=>sources.includes(s)?[summary[s].records,r.source_cell_days[s]]:['','']),hashes,'UNKNOWN','UNKNOWN','','','ADJUSTMENT_WITHHELD'];
 });
 return [head,...rows].map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
}
export function seasonalPatterns(c:CaCatalog,chunks:CaChunk[],q:CaQuery){
 return Array.from({length:12},(_,i)=>{
  const month=q.month.slice(0,4)+'-'+String(i+1).padStart(2,'0'),scope={...q,month,day:null};
  const selected=selectedCells(chunks.filter(v=>v.month===month),scope),summary=caSummary(selected,q.flag);
  const entries=q.sources.map(s=>c.coverage.find(e=>e.month===month&&e.pc===q.pc&&e.source===s));
  for(const entry of entries)if(entry&&!chunks.some(v=>v.month===month&&v.source===entry.source&&v.pc===q.pc))throw Error('Annual artifact missing; summary withheld');
  return {month,month_length:new Date(Date.UTC(Number(month.slice(0,4)),i+1,0)).getUTCDate(),sources:q.sources.map(s=>{const entry=entries.find(e=>e?.source===s) as typeof c.coverage[number]&{native_versions?:string[]}|undefined;return {source:s,...summary[s],dates_with_records:retention(selected.filter(v=>v.source===s),q.flag).ALL_NATIVE.dates_with_records,coverage:coverageState(c,s,scope,summary[s].records),versions:entry?.native_versions??[],month_has_acquired_rows:!!entry};})};
 });
}
export function seasonalEligibility(rows:ReturnType<typeof seasonalPatterns>,source:SourceId){
 const lanes=rows.flatMap(r=>r.sources.filter(s=>s.source===source));
 const acquired=lanes.filter(s=>s.month_has_acquired_rows);
 const versions=new Set(acquired.flatMap(s=>s.versions));
 return {represented_months:acquired.length,versions:[...versions],same_literal_lineage:versions.size===1,normalized_rate:false,anomaly:'WITHHELD',reason:`${acquired.length}/12 archive-represented months; ${CA_NAMES[source]} only; opportunity and completeness unknown. Month length is context, not exposure.`};
}
export function seasonalCsv(c:CaCatalog,q:CaQuery,rows:ReturnType<typeof seasonalPatterns>){
 const header=['schema','candidate_id','scope','month','source','processing_class','native_flag','calendar_days_not_exposure','reported_records','occupied_cell_days','dates_with_records','utc_dates','native_version','month_state','month_artifact_sha256','observation_opportunity','extract_completeness','anomaly','adjustment'];
 const values=rows.flatMap(r=>r.sources.map(s=>['native-positive-patterns-v1',c.candidate,JSON.stringify({...q,month:r.month,day:null}),r.month,s.source,q.pc,q.flag,r.month_length,s.month_has_acquired_rows?s.records:'',s.month_has_acquired_rows?s.cell_days:'',s.month_has_acquired_rows?s.dates_with_records.length:'',s.dates_with_records.join(';'),s.versions.join(';'),s.coverage.code,c.coverage.find(e=>e.source===s.source&&e.pc===q.pc&&e.month===r.month)?.sha256??'','UNKNOWN','UNKNOWN','WITHHELD','ADJUSTMENT_WITHHELD']));
 return [header,...values].map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
}
