import { lazy,Suspense,useCallback,useMemo,useRef,useState } from 'react';
import type { Map as MapInstance } from 'maplibre-gl';
import { select,selectionId,scientificCsv,summarize,type Release,type Selection,type SourceId,type Detection } from './science';
import { utcInstants } from './atlas';
import { useMobile } from './Panel';
import type { RenderMode } from './FireMap';
const FireMap=lazy(()=>import('./FireMap').then(m=>({default:m.FireMap})));
export function DayNightCompare({release,selection,mode,lensSource,metric,bandwidth,onCell,onRecord,camera,axis='daynight',showCenters=false,onMethod}:{release:Release;selection:Selection;mode:RenderMode;lensSource:SourceId;metric:'records'|'occupied_cell_days';bandwidth:5|10;onCell:(cell:string)=>void;onRecord:(r:Detection)=>void;camera:{id:number;target:'study'|'activity'|'selection'};axis?:'daynight'|'sources';showCenters?:boolean;onMethod?:(source:SourceId)=>void}){
  const mobile=useMobile(),[active,setActive]=useState<'D'|'N'>('D'),[attempt,setAttempt]=useState(0);
  const [chosen,setChosen]=useState<SourceId[]>(selection.sources.slice(0,2));
  const left=selection.sources.includes(chosen[0])?chosen[0]:selection.sources[0];
  const right=selection.sources.includes(chosen[1])&&chosen[1]!==left?chosen[1]:selection.sources.find(s=>s!==left)??left;
  const maps=useRef<Partial<Record<'D'|'N',MapInstance>>>({}),syncing=useRef(false);
  const register=useCallback((flag:'D'|'N',map:MapInstance|null)=>{
    if(!map){delete maps.current[flag];return;}maps.current[flag]=map;
    map.on('move',()=>{if(syncing.current)return;syncing.current=true;try{const other=maps.current[flag==='D'?'N':'D'];if(other)other.jumpTo({center:map.getCenter(),zoom:map.getZoom(),bearing:map.getBearing(),pitch:map.getPitch()});}finally{syncing.current=false;}});
  },[]);
  const dayReady=useCallback((map:MapInstance|null)=>register('D',map),[register]),nightReady=useCallback((map:MapInstance|null)=>register('N',map),[register]);
  const lanes=useMemo(()=>(['D','N'] as const).map((flag,index)=>{
    const source=axis==='sources'?(index===0?left:right):lensSource;
    const query={...selection,sources:[source],daynight:axis==='sources'?selection.daynight:flag};const records=select(release.records,query);
    return {flag,source,title:axis==='sources'?release.sources[source].name:flag==='D'?'Day':'Night',query,records,summary:summarize(records),times:utcInstants(records),signature:selectionId(release.releaseId,query)};
  }),[release,selection,lensSource,axis,left,right]);
  function exportLane(flag:'D'|'N'){
    const lane=lanes.find(l=>l.flag===flag)!,blob=new Blob([scientificCsv(release,lane.query,lane.records)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=`insider-lens-${lane.source}-${selection.day??selection.month}-${lane.query.daynight}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);
  }
  const available=release.months.includes(selection.month??'');
  const sourceControls=<div className="source-pair-controls">{[left,right].map((source,index)=><label key={index}><span>{index===0?'Left':'Right'} native lane</span><select aria-label={`${index===0?'Left':'Right'} comparison source`} value={source} onChange={e=>setChosen(index===0?[e.target.value as SourceId,right]:[left,e.target.value as SourceId])}>{selection.sources.map(s=><option key={s} value={s} disabled={s===(index===0?right:left)}>{release.sources[s].name}</option>)}</select></label>)}</div>;
  return <section className={`dn-comparison comparison-${axis}`} aria-label={axis==='sources'?'Synchronized native source investigation':'Synchronized Day and Night investigation'} data-testid={axis==='sources'?'source-compare':'daynight-compare'}>
    <div className="dn-context">{axis==='sources'?(mobile?<details className="source-pair-settings" onKeyDown={e=>{if(e.key==='Escape'){const menu=e.currentTarget;menu.open=false;menu.querySelector('summary')?.focus();}}}><summary>Lanes</summary>{sourceControls}</details>:sourceControls):<strong>{release.sources[lensSource].name}</strong>}<span>Same footprint / UTC scope · not comparable exposure</span>{mobile&&<div role="group" aria-label="Full-width acquisition-class map">{lanes.map(l=><button key={l.flag} aria-pressed={active===l.flag} onClick={()=>setActive(l.flag)}>{axis==='sources'?l.title:l.flag==='D'?'Day D':'Night N'}</button>)}</div>}</div>
    <div className="dn-maps">{lanes.filter(l=>!mobile||l.flag===active).map(lane=><div className={`dn-pane ${lane.query.daynight==='N'?'night-pane':'day-pane'}`} key={mobile?'mobile':lane.flag} data-testid={axis==='sources'?`source-pane-${lane.source}`:`pane-${lane.flag}`} data-release={release.releaseId} data-selection={lane.signature}>
      <header><div><b>{lane.title} <span>{axis==='sources'?`Native ${lane.query.daynight??'ALL'} · own scale`:`NASA flag ${lane.flag}`}</span></b><small>{available?`${lane.summary.records} records / ${lane.summary.occupied_cell_days} cell-days`:'Extract unavailable'}</small></div><button onClick={()=>exportLane(lane.flag)} aria-label={`Export ${lane.title} scientific CSV`}>↓ CSV</button></header>
      <div className="dn-map"><Suspense fallback={<p>Opening native {lane.flag} geography…</p>}><FireMap key={attempt} release={release} records={lane.records} mode={mode} selectedCell={selection.cell} selectionId={lane.signature} period={selection.day??selection.month??'2017-06'} resetKey={0} camera={camera} leftInset={0} comparisonPane theme={lane.query.daynight==='N'?'night':'day'} lensSource={lane.source} metric={metric} bandwidth={bandwidth} showCenters={showCenters} onMethod={()=>onMethod?.(lane.source)} onCell={onCell} onRecord={onRecord} onRetry={()=>setAttempt(v=>v+1)} onMapReady={lane.flag==='D'?dayReady:nightReady}/></Suspense></div>
      <details className="overpass-context"><summary>UTC acquisition timestamps · {lane.times.length} distinct instants</summary><p>Native acquisition class {lane.query.daynight??'ALL'}; dates remain UTC. Instants are not a pass inventory or exposure denominator.</p>{lane.times.length?<ul>{lane.times.map(t=><li key={t}><time>{t}</time></li>)}</ul>:<p>No reported records; valid observation unknown.</p>}</details>
    </div>)}</div>
    <p className="dn-interpretation">{axis==='sources'?'Native measurements side by side · 1 km MODIS / 375 m VIIRS nominal pixels. Separate scales; no correction factor or fair normalized comparison is established.':'D + N partitions records. Occupied cell-days can overlap between classes. Differences do not establish a diurnal fire-frequency trend.'}</p>
  </section>;
}
