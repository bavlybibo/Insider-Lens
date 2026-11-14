import { useEffect, useMemo, useRef, useState } from 'react';
import { selectedMonth, select, summarize, type Release, type Selection } from './science';
import { shiftMonth } from './investigation';
import expansion from './history-expansion.json';
import {useMobile} from './Panel';

export function CalendarDock({ release, selection, signature, update, focus=false, metric, setMetric,compact=false,history=false }: { release: Release; selection: Selection; signature: string; update: (fn: (s: Selection) => Selection) => void;focus?:boolean;metric:'occupied_cell_days'|'records';setMetric:(metric:'occupied_cell_days'|'records')=>void;compact?:boolean;history?:boolean }) {
  const [preferredExpanded, setExpanded] = useState(true);
  const mobile=useMobile();
  useEffect(()=>setExpanded(!compact),[compact]);
  const expanded=preferredExpanded&&!focus;
  const strip = useRef<HTMLDivElement>(null);
  const month = selectedMonth(selection), available = release.months.includes(month);
  function scrollToEvidence(){const target=selection.day??records[0]?.day; if(target)strip.current?.querySelector(`[data-testid="day-${target}"]`)?.scrollIntoView({block:'nearest',inline:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
  const count = new Date(Number(month.slice(0, 4)), Number(month.slice(5)), 0).getDate();
  const records = useMemo(() => select(release.records, { ...selection, day: null }), [release, selection]);
  useEffect(()=>{if(selection.cell||selection.day)scrollToEvidence();else if(strip.current)strip.current.scrollLeft=0;},[selection.cell,selection.day,month]);
  const days = Array.from({ length: count }, (_, i) => {
    const day = `${month}-${String(i + 1).padStart(2, '0')}`;
    return { day, values: selection.sources.map(source => ({ source, ...summarize(records.filter(r => r.source === source && r.day === day)) })) };
  });
  const maximum = Math.max(1, ...days.flatMap(d => d.values.map(v => v[metric])));
  const title = new Intl.DateTimeFormat('en', { timeZone: 'UTC', month: 'long', year: 'numeric' }).format(new Date(`${month}-01T12:00:00Z`));
  const metricControl=<><label className="sr-only" htmlFor="metric">Calendar metric</label><select id="metric" value={metric} onChange={e=>setMetric(e.target.value as typeof metric)}><option value="occupied_cell_days">Occupied cells / day</option><option value="records">Reported records / day</option></select></>;
  return <section id="calendar" tabIndex={-1} className={`calendar-dock ${expanded ? '' : 'collapsed'}`} data-testid="calendar-surface" data-release={release.releaseId} data-selection={signature} aria-label="Integrated UTC historical calendar" aria-describedby="calendar-context">
    <p id="calendar-context" className="sr-only">Month context for the selected source lanes, cell and day/night filter. The highlighted UTC date filters the map, totals, Passport and export. Calendar bars for other dates remain navigable context.</p>
    {history&&<div className="history-navigation" aria-label="Same UTC month historical evidence">{Array.from({length:6},(_,i)=>2013+i).map(year=>{const value=`${year}-${month.slice(5)}`,present=release.months.includes(value),staged=expansion.months.some(m=>m.month===value)||value==='2013-01';return <button key={year} aria-label={`${value}: ${present?'diagnostic only':staged?'staged, unqualified':'extract unavailable'}`} aria-pressed={value===month} onClick={()=>update(s=>({...s,month:value,day:null}))}><b>{year}</b><span>{present?'Diagnostic':staged?'Staged':'Unavailable'}</span></button>;})}<p>No qualified seasonal baseline<br/><b>Anomaly withheld</b></p></div>}
    <div className="calendar-heading"><div className="calendar-month"><button aria-label="Previous month" disabled={month<='2000-01'} onClick={()=>update(s=>({...s,month:shiftMonth(month,-1),day:null}))}>‹</button><div><span className="eyebrow">UTC HISTORICAL CALENDAR</span><h2>{title}</h2></div><button aria-label="Next month" disabled={month>='2029-12'} onClick={()=>update(s=>({...s,month:shiftMonth(month,1),day:null}))}>›</button></div>
      <div className="calendar-controls">{mobile?<details className="metric-menu" onKeyDown={e=>{if(e.key==='Escape'){const menu=e.currentTarget;menu.open=false;menu.querySelector('summary')?.focus();}}}><summary>Metric</summary><div>{metricControl}</div></details>:metricControl}
        <button className={!selection.day ? 'selected' : ''} onClick={() => update(s => ({ ...s, day: null }))}>All dates</button>
        <button className="jump-date" onClick={scrollToEvidence}>Jump to evidence</button>
        {!focus&&<button aria-label={expanded ? 'Collapse calendar' : 'Expand calendar'} aria-expanded={expanded} onClick={() => setExpanded(v => !v)}>{expanded ? '⌄' : '⌃'}</button>}</div></div>
    {expanded && <><div className="day-navigation">
      <div className="day-strip" ref={strip}>{days.map((d, i) => {
        const anyRecords = d.values.some(v => v.records > 0);
        const label = `${d.day}. ${!available ? 'Source extract unavailable.' : d.values.map(v => `${release.sources[v.source].name}: ${v[metric]} ${metric === 'records' ? 'reported records' : 'occupied cells'}`).join('. ')} Observation support unknown.`;
        return <button key={d.day} className={`calendar-day ${selection.day === d.day ? 'selected' : ''} ${anyRecords ? 'has-records' : 'unknown'}`} aria-label={label} aria-pressed={selection.day === d.day} data-testid={`day-${d.day}`} onClick={() => update(s => ({ ...s, day: s.day === d.day ? null : d.day }))}>
          <small>{['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'][new Date(`${d.day}T12:00:00Z`).getUTCDay()]}</small><span>{i + 1}</span>
          {anyRecords ? <div className="day-bars">{d.values.map(v => <i key={v.source} className={`bar-${v.source}`} style={{ height: `${Math.max(v[metric] ? 3 : 0, v[metric] / maximum * 28)}px`, background: release.sources[v.source].color }} />)}</div> : <span className="unknown-mark">—</span>}
        </button>;
      })}</div></div><div className="calendar-scroll-controls"><button aria-label="Scroll calendar earlier" onClick={() => strip.current?.scrollBy({ left: -240, behavior: 'instant' })}>← Earlier dates</button><span>One bar per selected source · {metric==='records'?'native records':'occupied cells'} per UTC date</span><button aria-label="Scroll calendar later" onClick={() => strip.current?.scrollBy({ left: 240, behavior: 'instant' })}>Later dates →</button></div>
      <div className="calendar-footnote"><span className="hatch-swatch"/>{available ? 'No record ≠ observed no detection' : 'No source extract for this month · totals unavailable'}<span>Source-specific bars · not normalized</span></div></>}
  </section>;
}
