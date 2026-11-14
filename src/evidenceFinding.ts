import {areaBounds,CA_NAMES,CA_SOURCES,type CaCatalog,type CaQuery} from './canada';
import {coverageState} from './nativeHistory';
import {partitionCounts,retainedRecords,type PositiveKey} from './evidenceRetention';

/** Presentation of the committed native query; no new scientific estimator. */
export function evidenceFinding(c:CaCatalog,q:CaQuery,keys:PositiveKey[],ready:boolean,error='') {
 const fmt=(n:number)=>n.toLocaleString('en-US');
 const period=q.month+(q.day?'-'+String(q.day).padStart(2,'0'):'');
 const area=q.rect?'Committed research rectangle':q.area==='south'?'Southern Canada study tract':q.area==='north'?'Northern Canada study tract':'Canada acquired extract';
 const bounds=q.rect??areaBounds[q.area];
 const cell=q.cell?' · cell '+q.cell.split(':').slice(-2).join(':'):'';
 const scope=area+cell;
 const sources=q.sources.map(s=>CA_NAMES[s]).join(' + ');
 const policy=q.sources.length===3?'Both native':q.sources.length===1&&q.sources[0]==='SNPP_VIIRS'?'VIIRS only':q.sources.length===2&&!q.sources.includes('SNPP_VIIRS')?'MODIS only':'Checked sources';
 const lanes=q.sources.map(s=>({source:s,...coverageState(c,s,q,keys.reduce((n,k)=>n+k.records[CA_SOURCES.indexOf(s)],0))}));
 const counts=partitionCounts(keys),records=keys.reduce((n,k)=>n+retainedRecords(k,q),0);
 const retained=keys.filter(k=>retainedRecords(k,q)>0),dates=new Set(retained.map(k=>k.date)).size;
 let state='NATIVE_POSITIVES',finding='';
 if(!ready){state=q.month.startsWith('2024')?'WITHHELD':'UNKNOWN';finding=state==='WITHHELD'?'Retention analysis is WITHHELD for the sealed 2024 partition.':'Evidence UNKNOWN while the committed query and independent acceptance are verified.';}
 else if(lanes.length&&lanes.every(l=>l.code==='SOURCE_NOT_YET_IN_ERA'||l.code==='SOURCE_ERA_ENDED')){state='ERA_UNAVAILABLE';finding=`${sources}: instrument-era evidence is UNAVAILABLE for ${period} UTC. ${fmt(keys.length)} other-native positive keys preserve acquired evidence. Unavailable history is not observed zero.`;}
 else if(lanes.length&&lanes.every(l=>l.code==='MONTH_NOT_ACQUIRED')){state='NOT_ACQUIRED';finding=`Selected source/product evidence is NOT ACQUIRED for ${period} UTC. No fire-free period or zero activity is inferred.`;}
 else if(!retained.length){state='UNKNOWN';finding='No reported-positive keys from the checked sources in this scope. Observation support is UNKNOWN; this does not establish a fire-free period.';}
 else{const unavailable=lanes.some(l=>l.code==='SOURCE_NOT_YET_IN_ERA'||l.code==='SOURCE_ERA_ENDED'||l.code==='MONTH_NOT_ACQUIRED');finding=unavailable?`${fmt(keys.length)} positive cell-day keys preserve the available native record. `:`${fmt(counts.MODIS_ONLY)} MODIS-only + ${fmt(counts.SHARED)} shared + ${fmt(counts.VIIRS_ONLY)} VIIRS-only = ${fmt(keys.length)} native reference keys. `;finding+=`${policy} retains ${fmt(records)} source records on ${dates} UTC dates.`;if(keys.length>retained.length)finding+=` It excludes ${fmt(keys.length-retained.length)} reference keys reported by other native sources.`;}
 const limitation='Same cell/day is not simultaneous observation support. Exclusive keys are not missed fires. Calibrated continuity: ADJUSTMENT_WITHHELD.';
 const eraNotes=lanes.filter(l=>l.code==='SOURCE_NOT_YET_IN_ERA'||l.code==='SOURCE_ERA_ENDED'||l.code==='MONTH_NOT_ACQUIRED').map(l=>CA_NAMES[l.source]+': '+l.label);
 return {scope,bounds:[...bounds],period,sources,policy,flag:q.flag,processing:q.pc,state,finding,limitation,eraNotes,
  referenceKeys:ready?keys.length:null,retainedRecords:state==='NATIVE_POSITIVES'?records:null,retainedDates:state==='NATIVE_POSITIVES'?dates:null,
  copy:`Insider Lens — ${scope}; bounds W/S/E/N ${bounds.join(', ')}; ${period} UTC; fixed 10 km equal-area cells; ${q.pc}; native ${q.flag}; ${sources}. ${finding} ${limitation} Provenance: ${c.candidate}; /data/phase12/INDEPENDENT_PARTITION.json. Source ZIP SHA-256: ${[...new Set(q.sources.map(s=>c.archives.find(a=>a.request===(s==='SNPP_VIIRS'?'845606':'845605'))?.zip_sha256))].filter(Boolean).join('; ')}. Query: ${JSON.stringify(q)}.`};
}
