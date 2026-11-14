import {verifiedJson,caProject,caUnproject} from './canada';
import type {TriangleSelection} from './triangular';
export type StudySplit='development'|'replication';
export type MaskProduct='MYD14'|'VNP14'|'VNP14IMG';
export type MaskPoint=[number,number,number,number,number,number,number];
type ProductEvidence={aoi_pixel_centers:number;mask_counts:Record<string,number>;view_zenith_min_degrees:number;view_zenith_max_degrees:number;exact_geolocation_input_identity:boolean;support_states_at_centers:Record<string,number>;positive_mask_centers?:number;native_frp_mw_sum?:number};
export type EventHistory={totals:Record<string,{records:number;occupied_cell_days:number}>;calendar:{date:string;sources:Record<string,{records:number;occupied_cell_days:number;observation_support:string}>}[]};
type ObservationBase={id:string;root:string;contract_sha256:string;support_sha256:string;parent_canada:string;g4:string;metadata_queries:number;ranked_pairs:number;science_files:number;downloaded_bytes:number;qualified_shared_support_m2:null;fit:boolean;generalization:boolean;holdouts_opened:boolean;independent:{state:string;support_audit_sha256:string;mapped_centers_sha256:string;checks:unknown[]};artifacts:Record<string,{sha256:string;bytes:number;points?:number}>;splits:Record<StudySplit,{aoi_wsen:number[];searched_days:string[];date:string;offset_minutes:number;aqua_start:string;aqua_end:string;viirs_start:string;viirs_end:string;proxy_distance_km:number;failures:string[];products:Record<MaskProduct,ProductEvidence>}>};
export type ObservationStudy=ObservationBase&{phase?:8;native_history?:EventHistory;maximum_scan_bound_separation_seconds?:number};
export type ObservationView={study:ObservationStudy;split:StudySplit;product:MaskProduct;points:MaskPoint[];triangle?:TriangleSelection};
export function centerSupport(mask:number){return [0,1,2,4].includes(mask)?'CLOUD_OR_INVALID':'UNKNOWN_SUPPORT';}
export async function loadObservation(signal:AbortSignal,parent:string,phase:7|8=7){
 const p=await fetch(`/data/phase${phase}/index.json`,{signal}).then(r=>{if(!r.ok)throw Error('Observation study index unavailable');return r.json();});
 const b=await verifiedJson<ObservationStudy>(p.file,p.sha256,signal);
 if(b.id!==p.id||b.parent_canada!==parent||b.g4!=='ADJUSTMENT_WITHHELD'||b.fit||b.generalization||b.holdouts_opened||b.qualified_shared_support_m2!==null||b.independent.state!=='PASS'||b.independent.support_audit_sha256!==b.support_sha256||b.artifacts['SUPPORT_AUDIT.json'].sha256!==b.support_sha256)throw Error('Observation evidence acceptance failed');
 if(phase===8&&(b.phase!==8||!b.native_history))throw Error('Event experiment identity missing');
 return {...b,root:p.file.slice(0,p.file.lastIndexOf('/')+1)};
}
export function aggregateObservation(points:MaskPoint[],width=5000){
 const bins=new Map<string,{i:number;j:number;count:number;positive:number;invalid:number}>();
 for(const p of points){const [x,y]=caProject(p[2],p[3]),i=Math.floor(x/width),j=Math.floor(y/width),key=`${i}:${j}`,b=bins.get(key)??{i,j,count:0,positive:0,invalid:0};b.count++;if([7,8,9].includes(p[4]))b.positive++;if([0,1,2,4].includes(p[4]))b.invalid++;bins.set(key,b);}
 return {type:'FeatureCollection' as const,features:[...bins.values()].map(b=>({type:'Feature' as const,geometry:{type:'Point' as const,coordinates:caUnproject((b.i+.5)*width,(b.j+.5)*width)},properties:{...b,width,support:'UNKNOWN_SUPPORT'}}))};
}
export async function loadObservationView(study:ObservationStudy,split:StudySplit,product:MaskProduct,signal:AbortSignal):Promise<ObservationView>{
 const name=`${split}-${product}.json`,a=study.artifacts[name];const data=await verifiedJson<{fields:string[];points:MaskPoint[]}>(study.root+name,a.sha256,signal);
 if(data.points.length!==a.points||data.points.length!==study.splits[split].products[product].aoi_pixel_centers||data.fields.join(',')!=='line,sample,lon,lat,mask,qa,view_zenith_degrees')throw Error('Mask-center identity mismatch');
 return {study,split,product,points:data.points};
}
export function observationCsv(v:ObservationView){
 const spec=v.study.splits[v.split],name=`${v.split}-${v.product}.json`;
 const headers=['experiment_id','contract_sha256','support_audit_sha256','center_artifact_sha256','split','product','acquisition_start_utc','acquisition_end_utc','line','sample','longitude','latitude','native_mask','raw_algorithm_qa','view_zenith_degrees','support_state','exact_named_geo_input','qualified_shared_support_m2','g4'];
 const rows=v.points.map(p=>[v.study.id,v.study.contract_sha256,v.study.support_sha256,v.study.artifacts[name].sha256,v.split,v.product,v.product==='MYD14'?spec.aqua_start:spec.viirs_start,v.product==='MYD14'?spec.aqua_end:spec.viirs_end,...p.slice(0,2),p[2],p[3],p[4],p[5],p[6],centerSupport(p[4]),String(spec.products[v.product].exact_geolocation_input_identity),'UNKNOWN','ADJUSTMENT_WITHHELD']);
 const quote=(x:unknown)=>'"'+String(x).replaceAll('"','""')+'"';
 return '# Native mask centers; acquisition interval is not exact pixel time; no footprint or opportunity denominator.\r\n'+[headers,...rows].map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n';
}
