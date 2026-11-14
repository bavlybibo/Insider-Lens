import {caCsv,caSummary,cellId,verifiedJson,type CaCatalog,type CaChunk,type CaQuery} from './canada';
import type {SourceId} from './science';
export interface BridgePoint {lon:number;lat:number;source:SourceId;utc:string;dn:string;cell:string;raw_sha256:string;native:Record<string,unknown>}
interface Totals {records:number;cell_days:number}
interface Timing {minutes:number;same_cell_day_same_flag_candidate_keys:number;qualified_opportunities:null}
export interface BridgeRelease {
 id:string;parent_candidate:string;classification:string;contract_sha256:string;scientific_release:string;
 contract:{aoi_wsen:number[];development:string[];replication:string[];grid:{id:string};sources:SourceId[]};
 common:{cohort_records:number;g4:string;results:Record<string,{scales:Record<string,{baseline:Record<SourceId,Totals>;timing:Timing[]}>;quality_sensitivity:Record<string,Record<SourceId,Totals>>}>};
 independent:{state:string;audit_sha256:string;research_rows_sha256:string;matching_checks:{split:string;width_m:number;minutes:number;min_same_flag_positive_offset_minutes:number|null}[]};l2_independent:{state:string;l2_audit_sha256:string};
 l2:{science_files:number;downloaded_bytes:number;state:string;qualified_observation_denominator:null;rejections:string[];nominal_offsets_minutes:Record<string,number>};
 l2_products:Record<string,Record<string,{aoi_pixel_centers:number;mask_counts:Record<string,number>;view_zenith_min_degrees:number;view_zenith_max_degrees:number;exact_geolocation_input_identity:boolean;view_sensitivity:Record<string,{aoi_centers_within_view:number}>}>>;
 chunks:CaChunk[];rows:BridgePoint[];evidence_sha256:Record<string,string>;
}
export async function loadBridge(signal:AbortSignal,parent:string){
 const response=await fetch('/data/phase6/index.json',{signal});if(!response.ok)throw Error('Research result unavailable');
 const pointer=await response.json();if(!/^\/data\/phase6\/p6-[a-f0-9-]+\/bridge.json$/.test(pointer.file)||!/^[a-f0-9]{64}$/.test(pointer.sha256))throw Error('Invalid research pointer');
 const b=await verifiedJson<BridgeRelease>(pointer.file,pointer.sha256,signal);
 if(b.id!==pointer.id||b.parent_candidate!==parent||b.independent.state!=='PASS'||b.l2_independent.state!=='PASS'||b.independent.audit_sha256!==b.evidence_sha256['COMMON_SUPPORT_AUDIT.json']||b.l2_independent.l2_audit_sha256!==b.evidence_sha256['L2_SUPPORT_AUDIT.json']||b.independent.research_rows_sha256!==b.evidence_sha256['RESEARCH_ROWS.json']||b.common.g4!=='ADJUSTMENT_WITHHELD'||b.l2.qualified_observation_denominator!==null)throw Error('Research acceptance mismatch');
 const counts=caSummary(b.chunks);if(b.rows.length!==b.common.cohort_records||Object.values(counts).reduce((n,v)=>n+v.records,0)!==b.rows.length)throw Error('Research cohort mismatch');
 return b;
}
export function bridgePoints(b:BridgeRelease,q:CaQuery){return b.rows.filter(r=>q.sources.includes(r.source)&&(!q.cell||r.cell===q.cell)&&(!q.day||Number(r.utc.slice(8,10))===q.day)&&(q.flag==='ALL'||r.dn===q.flag));}
export function bridgeCsv(c:CaCatalog,b:BridgeRelease,q:CaQuery,chunks:CaChunk[]){
 // Preserve the existing native export, add explicit experimental membership and
 // hashes; never imply the bounded cohort is the original whole-month extract.
 const csv=caCsv(c,q,chunks).trimEnd().split('\r\n');
 const parse=(s:string)=>[...s.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'));
 const h=parse(csv[0]),area=h.indexOf('area_membership'),selection=h.indexOf('selection_id');
 const rows=csv.slice(1).map(s=>{const r=parse(s);r[area]='raw pixel center inside -120,49,-110,55; frozen six UTC dates only; not full footprint support';r[selection]=JSON.stringify({...q,experiment:b.id});r[h.indexOf('observation_support')]='OBSERVATION_UNKNOWN';const source=r[h.indexOf('source')];const archive=c.archives.find(a=>a.request===(source==='SNPP_VIIRS'?'845606':'845605'))!;r[h.indexOf('zip_sha256')]=archive.zip_sha256;r[h.indexOf('member_sha256')]=archive.members.find(m=>m.processing_class==='SP')!.sha256;return [...r,b.id,b.contract_sha256,b.evidence_sha256['RESEARCH_ROWS.json'],'B1_GEOMETRY_ONLY'];});
 return [[...h,'experiment_id','cohort_contract_sha256','research_rows_sha256','method'],...rows].map(r=>r.map(v=>'"'+v.replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
}
export function bridgeScope(b:BridgeRelease){return `Frozen southern pilot · 1–3 / 8–10 June 2022 UTC · ${b.common.cohort_records} native records; no qualified shared exposure`;}
export const bridgeCell=(i:number,j:number)=>cellId(i,j);
