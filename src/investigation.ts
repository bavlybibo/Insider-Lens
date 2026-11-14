import { selectedMonth, summarize, type Detection, type Release, type Selection } from './science';

export type InvestigationJob = 'explore' | 'compare' | 'history' | 'memory';
export type AnswerState = 'ANSWERED' | 'PARTIAL' | 'UNKNOWN' | 'UNAVAILABLE';
export const QUESTIONS: Record<InvestigationJob,string> = {
  explore:'What was recorded here, and when?', compare:'Can these instruments be compared fairly?', history:'Was this period historically unusual?',
  memory:'What historical information disappears?',
};
export function investigationAnswer(job: InvestigationJob, release: Release, selection: Selection, records: Detection[]) {
  const available=release.months.includes(selectedMonth(selection));
  const lanes=selection.sources.map(source=>({source,name:release.sources[source].name,...summarize(records.filter(r=>r.source===source))}));
  let state: AnswerState, answer:string, cannot:string, why:string, next:string;
  if(job==='history'||job==='memory') {
    state='UNKNOWN'; answer='Not yet evaluable. There is no qualified multi-year, same-season baseline for this selection.';
    cannot='Classify this period as unusual, severe or an operational fire risk.';
    why='The release contains one diagnostic month, with unknown delivery completeness and observation support.';
    next='Qualify repeated same-month Standard Processing deliveries and source-specific observation denominators.';
  } else if(!available) {
    state='UNAVAILABLE'; answer=`No source extract is released for ${selectedMonth(selection)}. Quantities are unavailable.`;
    cannot='Interpret missing history as zero activity.'; why='This period has not passed the data-delivery and independent recount contract.';
    next='Inspect historical availability and the missing delivery evidence.';
  } else if(!records.length) {
    state='UNKNOWN'; answer='No matching records occur in the supplied extract. Valid observation coverage is unknown.';
    cannot='Say the instruments observed a fire-free place or time.'; why='Detection-only files do not include valid non-fire masks or complete acquisition inventories.';
    next='Change the date/filter or inspect what observation evidence is missing.';
  } else if(job==='compare') {
    state='PARTIAL'; answer=selection.sources.length>1 ? 'Native measurements can be read side by side. A fair normalized sensor comparison is not established.' : 'One source is selected. Add a second native lane to inspect the reported measurements.';
    cannot='Turn a detection-count ratio into a ratio of physical fires, or equate equal cell-days with equal sensitivity.';
    why='MODIS 1 km and VIIRS 375 m nominal pixels, detection tests, acquisition times and valid observation support differ.';
    next='Acquire compatible L2 fire masks, QA, geolocation and pass inventories before matched-support comparison.';
  } else {
    state='ANSWERED'; answer=lanes.map(l=>`${l.name}: ${l.records.toLocaleString('en-US')} records on ${l.detection_days} UTC dates, occupying ${l.occupied_cell_days} cell-days`).join('; ')+'.';
    cannot='Infer unique fires, burned area, severity or complete monthly activity from these records.';
    why='A cell-day counts a distinct (source, fixed 10 km cell, UTC date) once, regardless of repeated pixels or passes.';
    next=selection.cell ? 'Select a reported date, or compare the source lanes and inspect their evidence.' : 'Select an occupied cell, or follow the verified June observation story.';
  }
  return {job,state,question:QUESTIONS[job],answer,cannot,why,next,lanes,available,
    dates:[...new Set(records.map(r=>r.day))].sort(),
    support:{records:available ? 'AVAILABLE_IN_DIAGNOSTIC' : 'UNAVAILABLE',swath:'NOT_QUALIFIED',l2:'NOT_QUALIFIED'},
    harmonization:'ADJUSTMENT_WITHHELD',seasonality:'NOT_YET_EVALUABLE'};
}

export type GeographicBounds = [[number,number],[number,number]];
export function activityBounds(records: Detection[]): GeographicBounds | null {
  if(!records.length)return null;
  return [[Math.min(...records.map(r=>r.longitude)),Math.min(...records.map(r=>r.latitude))],
    [Math.max(...records.map(r=>r.longitude)),Math.max(...records.map(r=>r.latitude))]];
}
export function shiftMonth(month:string, delta:number) {
  const date=new Date(`${month}-01T00:00:00Z`); date.setUTCMonth(date.getUTCMonth()+delta);
  return date.toISOString().slice(0,7);
}
