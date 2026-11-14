import { useEffect, useRef, useState } from 'react';
import { investigationAnswer, type InvestigationJob } from './investigation';
import { type Detection, type Release, type Selection } from './science';
import { REFERENCES } from './evidence';
import historyStatus from './history-status.json';
import expansion from './history-expansion.json';

export function AnswerCard({job,release,selection,records,signature,showEvidence,story,setJob,onClose,compact=false}:{
  job:InvestigationJob;release:Release;selection:Selection;records:Detection[];signature:string;
  showEvidence:(tab?:string)=>void;story:()=>void;setJob:(job:InvestigationJob)=>void;onClose:()=>void;
  compact?:boolean;
}) {
  const [details,setDetails]=useState(false);
  const element=useRef<HTMLElement>(null);
  useEffect(()=>{
    if(element.current)element.current.scrollTop=0;
    const sheet=element.current?.closest('.panel-scroll');if(sheet)sheet.scrollTop=0;
  },[job,signature]);
  const result=investigationAnswer(job,release,selection,records);
  return <section ref={element} className={`answer-card answer-${job} ${compact?'compact-answer':''}`} aria-label="Scientific answer" data-testid="answer-surface" data-selection={signature} data-release={release.releaseId}>
    <div className="answer-topline"><span className={`answer-state state-${result.state}`}>{result.state}</span><span className="atlas-caption">NATIVE EVIDENCE ATLAS</span><button className="icon-button" aria-label="Minimize scientific answer" onClick={onClose}>−</button></div>
    <span className="finding-label">{job==='explore'?'01 / The observed record':job==='compare'?'02 / The comparison boundary':'03 / The historical question'}</span><h2>{result.question}</h2>{compact&&job==='explore'&&result.state==='ANSWERED'?<div className="compact-facts" data-testid="scientific-answer">{result.lanes.map(l=><p key={l.source}><strong>{l.name}</strong><span>{l.records.toLocaleString('en-US')} records on {l.detection_days} UTC dates · {l.occupied_cell_days} cell-days</span></p>)}</div>:<p className="answer-statement" data-testid="scientific-answer">{result.answer}</p>}
    <div className="answer-scope">{selection.cell ?? 'Central Portugal'} · {selection.day ?? selection.month} UTC · {selection.daynight==='ALL'?'day & night':selection.daynight==='D'?'daytime':'nighttime'}</div>
    {job==='compare' && <div className="comparison-lanes">{result.lanes.map(lane=><div key={lane.source} className="comparison-lane"><h3><i className={`source-shape shape-${lane.source}`} style={{color:release.sources[lane.source].color}}/>{lane.name}</h3><p><b>{result.available?lane.records.toLocaleString('en-US'):'—'}</b> native records</p><p><b>{result.available?lane.occupied_cell_days:'—'}</b> occupied cell-days</p><small>{result.available?lane.detection_days:'—'} UTC detection dates · {lane.source==='SNPP_VIIRS'?'375 m':'1 km'} nominal pixels</small></div>)}</div>}
    {job==='history' && <div className="history-slices"><h3>Same calendar month · training years</h3><div>{Array.from({length:6},(_,i)=>2013+i).map(year=>{const month=`${year}-${selection.month?.slice(5)??'06'}`,present=release.months.includes(month);return <span key={year} className={present?'diagnostic':'unavailable'}><b>{year}</b><small>{present?'Diagnostic only':(month===historyStatus.month||expansion.months.some(m=>m.month===month))?'Staged, unqualified':'No extract'}</small></span>;})}</div><p>No eligible seasonal baseline or anomaly score is released.</p><details className="candidate-progress"><summary>Historical acquisition: an audited next step</summary><p>Two official NASA Portugal 2013 SP country files acquired. January 2013, chosen before inspecting counts, passed the existing native audit and independent raw recount. It remains staged, outside this scientific release.</p><p>Five further months, February–June2013, now pass native audits and independent recounts. June has Aqua8 records/5 cell-days, Terra4/3 and S-NPP85/28. Production-vintage, delivery lineage and valid support remain unqualified; these are not released comparable months.</p><ul>{historyStatus.qualification_blockers.map(reason=><li key={reason}>{reason}</li>)}</ul><code>{historyStatus.candidate_id}</code><p>Audit report SHA-256</p><code>{historyStatus.report_sha256}</code></details></div>}
    <button className="answer-disclosure" onClick={()=>setDetails(v=>!v)} aria-expanded={details} aria-controls="answer-reasoning">{details?'Hide reasoning':'What can’t we conclude?'} <span>{details?'−':'+'}</span></button>
    {details && <div id="answer-reasoning" className="answer-reasoning"><h3>What we cannot say</h3><p>{result.cannot}</p><h3>Why</h3><p>{result.why}</p>{job==='compare'&&<><h3>Plausible interpretations, not measured causes</h3><p>Finer pixels and different passes may contribute to record multiplicity. These extracts do not isolate those effects or identify shared physical fires.</p></>}<h3>Next evidence needed</h3><p>{result.next}</p></div>}
    <div className="answer-actions"><button onClick={()=>showEvidence(job==='history'?'history':'selection')}>Show why →</button><button onClick={()=>showEvidence('quality')}>Scientific limits</button></div>
    {selection.cell==='g:-2:-1' && result.available && <div className="story-continuation"><p>Each source retains its own UTC dates and record multiplicity.</p><button onClick={()=>setJob(job==='explore'?'compare':job==='compare'?'history':'explore')}>{job==='explore'?'Next: compare the instruments':job==='compare'?'Next: was it unusual?':'Return to observed facts'} →</button></div>}
    {!(selection.cell==='g:-2:-1' && selection.month==='2017-06') && <button className="observation-story" aria-label="Follow the observation story" onClick={story}><span>OBSERVATION STORY · 18–21 JUN 2017</span><strong>Four dates. Two instruments.</strong><span>Follow the verified cell example →</span></button>}
    {job==='history' && <a className="history-source-link" href={REFERENCES.archive} target="_blank" rel="noreferrer">Official historical data sources ↗</a>}
  </section>;
}
