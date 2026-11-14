import {useEffect,useMemo,useState} from 'react';
import {CA_COLORS,CA_NAMES,CA_SOURCES,caSummary,era,loadChunks,type CaCatalog,type CaChunk,type CaQuery} from './canada';
import {POLICIES,POLICY_NAMES,coverageState,retention,retentionCsv,seasonalCsv,seasonalEligibility,seasonalPatterns,type Policy} from './nativeHistory';
import './nativeHistory.css';
const fmt=(n:number)=>n.toLocaleString('en-US');
const save=(text:string,name:string)=>{const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);};

export function CoverageMatrix({catalog,query,native,ready}:{catalog:CaCatalog;query:CaQuery;native:CaChunk[];ready:boolean}){
 const summary=caSummary(native,query.flag);
 return <details className="native-coverage" data-testid="coverage-matrix"><summary>Coverage & comparability <span>Unknown opportunity · native only</span></summary>
  <table><caption>Selected AOI / UTC window / {query.pc}; archive presence is distinct from observation coverage.</caption><thead><tr><th>Source</th><th>Evidence state</th><th>Lineage</th></tr></thead><tbody>{CA_SOURCES.map(s=>{const state=coverageState(catalog,s,query,summary[s].records),versions=(catalog.coverage.find(e=>e.source===s&&e.pc===query.pc&&e.month===query.month) as typeof catalog.coverage[number]&{native_versions?:string[]})?.native_versions??[];return <tr key={s} data-state={ready?state.code:'CHECKING'}><th>{CA_NAMES[s]}</th><td title={state.detail}>{ready?state.label:'Checking…'}<small>{state.detail}</small></td><td>{versions.join(' / ')||'—'}</td></tr>;})}</tbody></table>
  <p>Native quantities and hashes verified. Extract completeness unqualified. Qualified valid observations without positives: <b>not established</b>. Calibrated continuity: <b>G4 withheld</b>. Sensor-era availability does not certify an acquired or cloud-free observation.</p><p>A future response-weighted support test needs applicable thermal-response and registration uncertainty; an artificial hard optical boundary is not required. The fixed sixteen candidates remain UNKNOWN_SUPPORT. <a href="/data/phase11/NASA_SUPPORT_DRAFT.md" download>NASA technical support draft · not sent</a>.</p>
 </details>;
}

export function RetentionResult({catalog,query,native,ready,onMap}:{catalog:CaCatalog;query:CaQuery;native:CaChunk[];ready:boolean;onMap?:()=>void}){
 const result=useMemo(()=>retention(native,query.flag),[native,query.flag]);
 const policy=(Object.keys(POLICIES) as Policy[]).find(p=>POLICIES[p].length===query.sources.length&&POLICIES[p].every(s=>query.sources.includes(s)));
 const selected=policy?result[policy]:retention(native.filter(c=>query.sources.includes(c.source)),query.flag).ALL_NATIVE;
 const excluded=result.ALL_NATIVE.records-selected.records;
 return <div className="retention-result" data-testid="retention-result" data-policy={policy??'CUSTOM'}>
  <p className="retention-question">What we preserve by keeping both satellite histories</p>
  <table><caption>Same area / UTC window · 10 km · {query.flag}. Records ≠ fires; opportunity unknown.</caption><thead><tr><th>Policy</th><th>Records</th><th>Cell-days<sup>∪</sup></th><th>Dates<sup>∪</sup></th></tr></thead><tbody>{(Object.keys(POLICIES) as Policy[]).map(p=><tr key={p} data-policy={p} aria-current={p===policy?'true':undefined}><th>{POLICY_NAMES[p]}</th><td>{ready?fmt(result[p].records):'—'}</td><td>{ready?fmt(result[p].union_cell_days):'—'}</td><td>{ready?result[p].dates_with_records.length:'—'}</td></tr>)}</tbody></table>
  {onMap&&<button onClick={onMap}>Open Evidence Retention map</button>}
  <p className="retention-verdict" role="status">{ready?<><b>{fmt(excluded)} acquired records excluded</b> by {policy?POLICY_NAMES[policy].toLowerCase():'the checked source policy'}; {fmt(result.ALL_NATIVE.union_cell_days-selected.union_cell_days)} positive cell-day keys and {result.ALL_NATIVE.dates_with_records.length-selected.dates_with_records.length} dates available only in excluded lanes.</>:'Recounting current evidence…'}</p>
  <details><summary>Source-specific measures & exact date sets</summary>{ready?<>{CA_SOURCES.map(s=><p key={s}>{CA_NAMES[s]}: <b>{fmt(result.ALL_NATIVE.source_cell_days[s]??0)} source-specific occupied cell-days</b> · {era(s,query.month,query.day)==='SOURCE_NOT_YET_IN_ERA'?'Not yet in era':era(s,query.month,query.day)}.</p>)}{(Object.keys(POLICIES) as Policy[]).map(p=><p key={p}><b>{POLICY_NAMES[p]}</b> · {Object.entries(result[p].source_cell_days).map(([s,k])=>`${CA_NAMES[s as keyof typeof CA_NAMES]} ${fmt(k!)} cell-days`).join('; ')}: {result[p].dates_with_records.join(', ')||'No reported dates; valid observation unknown'}.<br/>Exclusive excluded dates: {result[p].exclusive_dates_lost.join(', ')||'none among acquired records'}.</p>)}<p>∪ counts distinct cell/date or date keys once across included sources. Records retain source identity. These unions describe evidence retention, not calibrated activity, equal sensitivity or physical fires lost. Unobserved history cannot be quantified.</p></>:<p>Checking current evidence…</p>}</details>
  <button disabled={!ready} onClick={()=>save(retentionCsv(catalog,query,native),`insider-lens-retention-${query.pc}-${query.month}.csv`)}>Export retention evidence CSV</button>
 </div>;
}

export function HistoricalPatterns({catalog,query,metric,onMonth}:{catalog:CaCatalog;query:CaQuery;metric:'records'|'cell_days';onMonth:(m:string)=>void}){
 const [requested,setRequested]=useState(false),[loaded,setLoaded]=useState<{key:string;chunks:CaChunk[]}|null>(null),[error,setError]=useState('');
 const key=query.month.slice(0,4)+'|'+query.pc;
 useEffect(()=>{setRequested(false);setLoaded(null);setError('');},[key]);
 useEffect(()=>{if(!requested||key.startsWith('2024'))return;const c=new AbortController();setError('');
  Promise.all(Array.from({length:12},(_,i)=>loadChunks(catalog,key.slice(0,4)+'-'+String(i+1).padStart(2,'0'),query.pc,c.signal))).then(chunks=>{if(!c.signal.aborted)setLoaded({key,chunks:chunks.flat()});}).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
  return()=>c.abort();
 },[requested,key,catalog,query.pc]);
 const rows=useMemo(()=>loaded?.key===key?seasonalPatterns(catalog,loaded.chunks,query):null,[loaded,key,catalog,query]);
 if(key.startsWith('2024'))return <p>New annual-summary evaluation is withheld for the sealed 2024 partition. Existing native inventory remains unchanged.</p>;
 return <div className="historical-patterns"><p><b>Within-source annual context</b> · {query.month.slice(0,4)}, {query.area}, {query.pc}, native {query.flag}{query.cell?' · selected cell':''}. Uses full UTC months; selected day is excluded from this overview.</p>
  {!rows&&<button disabled={requested&&!error} onClick={()=>{setRequested(true);if(error){setRequested(false);setTimeout(()=>setRequested(true),0);}}}>Load annual positive patterns</button>}
  {error&&<p role="alert">Annual summary withheld: {error}</p>}
  {rows&&<div data-testid="seasonal-patterns"><div className="season-context">{query.month.slice(0,4)} · {query.area} · {query.pc} · positive patterns only</div><button onClick={()=>save(seasonalCsv(catalog,query,rows),`insider-lens-positive-patterns-${key.replace('|','-')}.csv`)}>Export annual patterns CSV</button>{query.sources.map(s=>{const eligibility=seasonalEligibility(rows,s),max=Math.max(1,...rows.flatMap(r=>r.sources.filter(v=>v.source===s).map(v=>v[metric])));return <section key={s} aria-label={CA_NAMES[s]+' annual positive pattern'}><h3><i style={{background:CA_COLORS[s]}}/>{CA_NAMES[s]} <small>{eligibility.represented_months}/12 archive months · code {eligibility.versions.join(' / ')||'unavailable'}</small></h3><div className="season-bars">{rows.map(r=>{const lane=r.sources.find(v=>v.source===s)!,unknown=!lane.month_has_acquired_rows||['MONTH_NOT_ACQUIRED','SOURCE_NOT_YET_IN_ERA','SOURCE_ERA_ENDED'].includes(lane.coverage.code);return <button key={r.month} aria-label={`${r.month} ${CA_NAMES[s]}: ${unknown?lane.coverage.label:`${lane.records} reported records, ${lane.cell_days} cell-days, ${lane.dates_with_records.length} dates with records`}; ${r.month_length} calendar days; observation opportunity unknown`} onClick={()=>onMonth(r.month)} aria-pressed={query.month===r.month}><i className={unknown?'season-unavailable':''} style={{height:unknown?28:Math.max(2,lane[metric]/max*35),background:unknown?undefined:CA_COLORS[s]}}/><b>{unknown?'—':fmt(lane[metric])}</b><span>{r.month.slice(5)}</span></button>;})}</div><p>{eligibility.same_literal_lineage?'Same literal code; upstream homogeneity remains unqualified.':'Lineage unavailable or mixed; no comparable seasonal baseline.'} Source-specific scale; {metric==='records'?'records':'occupied cell-days'}. Missing months stay unavailable. Month lengths vary, with no exposure normalization.</p></section>;})}<p><b>Observed-positive patterns only.</b> Coverage-conditioned seasonal baseline, anomaly significance, normalized frequency and climate trends are withheld. Shared scales or sums cannot calibrate the sensors.</p></div>}
 </div>;
}
