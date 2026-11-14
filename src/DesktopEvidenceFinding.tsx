import {useMemo,useState} from 'react';
import {evidenceFinding} from './evidenceFinding';
import type {CaCatalog,CaQuery} from './canada';
import type {PositiveKey} from './evidenceRetention';
import './desktopEvidenceFinding.css';

/** Desktop-only judge context. Existing mobile components and styles are unchanged. */
export function DesktopEvidenceFinding({catalog,query,keys,ready,error}:{catalog:CaCatalog;query:CaQuery;keys:PositiveKey[];ready:boolean;error:string}) {
 const answer=useMemo(()=>evidenceFinding(catalog,query,keys,ready,error),[catalog,query,keys,ready,error]),[copied,setCopied]=useState('');
 async function copy(){try{await navigator.clipboard.writeText(answer.copy);setCopied('Current finding copied.');}catch{setCopied('Clipboard unavailable. Use the exact evidence CSV.');}}
 return <div className="desktop-evidence-finding" data-testid="desktop-evidence-finding" data-state={answer.state}>
  <details className="desktop-evidence-scope"><summary><strong>{answer.scope}</strong><span>{answer.period} UTC · {query.pc} · 10 km · {query.flag==='ALL'?'Day + night':query.flag==='D'?'Day D':'Night N'}</span><span>{answer.sources}</span></summary>
   <dl><dt>Geographic bounds</dt><dd>W/S/E/N {answer.bounds.map(n=>Number(n.toFixed(6))).join(', ')}° · fixed cell centers</dd><dt>Selected sources</dt><dd>{answer.sources||'No sources selected'}</dd><dt>Processing</dt><dd>{query.pc==='SP'?'Standard Processing (SP)':'Near Real-Time (NRT)'} · vintage unverified</dd><dt>Comparability</dt><dd>UNQUALIFIED · common observation support UNKNOWN</dd></dl>
  </details>
  <p className="desktop-finding-text" aria-live="polite">{answer.finding}</p>
  {answer.eraNotes.length>0&&answer.state==='NATIVE_POSITIVES'&&<p className="desktop-era-context">{answer.eraNotes.join('; ')}. Era availability is not observation opportunity.</p>}
  <div className="desktop-finding-foot"><span title="Unknown common observation opportunity; counts are source-specific positives, not calibrated sensor accuracy.">Comparison UNQUALIFIED</span><button onClick={copy} aria-label="Copy current scientific finding">Copy finding</button></div>
  <span role="status" className="sr-only">{copied}</span>
 </div>;
}
