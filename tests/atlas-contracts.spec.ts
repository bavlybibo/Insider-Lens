import { test,expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { investigationAnswer,activityBounds,shiftMonth } from '../src/investigation';
import { readSelection } from '../src/selection';
import { select,scientificCsv,selectionId,type Release } from '../src/science';
const release:Release=JSON.parse(readFileSync('public/data/release.json','utf8'));

test('facts, interpretations and unsupported questions have separate answer states',()=>{
  const selection=readSelection('?month=2017-06&cell=g:-2:-1',release), records=select(release.records,selection);
  const facts=investigationAnswer('explore',release,selection,records);
  expect(facts.state).toBe('ANSWERED');expect(facts.lanes.map(l=>[l.records,l.occupied_cell_days,l.detection_days])).toEqual([[57,4,4],[484,4,4]]);
  expect(facts.dates).toEqual(['2017-06-18','2017-06-19','2017-06-20','2017-06-21']);
  const compare=investigationAnswer('compare',release,selection,records);expect(compare.state).toBe('PARTIAL');expect(compare.cannot).toContain('physical fires');
  const history=investigationAnswer('history',release,selection,records);expect(history.state).toBe('UNKNOWN');expect(history.seasonality).toBe('NOT_YET_EVALUABLE');
  const empty=readSelection('?month=2017-06&day=2017-06-01',release);
  expect(investigationAnswer('explore',release,empty,[]).state).toBe('UNKNOWN');
  const missing=readSelection('?month=2013-01',release);
  expect(investigationAnswer('explore',release,missing,[]).state).toBe('UNAVAILABLE');
});

test('336 scientific filter states reconcile exact exported multiplicities and no unsupported opportunity',()=>{
  for(let mask=1;mask<8;mask++)for(const dn of ['ALL','D','N'])for(const month of ['2017-06','2016-02'])for(const cell of ['', 'g:-2:-1'])for(const dayNumber of ['', '01','18','21']) {
    const sources=['AQUA_MODIS','SNPP_VIIRS','TERRA_MODIS'].filter((_,i)=>mask&(1<<i));
    const params=new URLSearchParams({month,sources:sources.join(','),dn,cell});if(dayNumber)params.set('day',`${month}-${dayNumber}`);
    const selection=readSelection('?'+params,release), rows=select(release.records,selection), csv=scientificCsv(release,selection,rows);
    const parse=(line:string)=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'));
    const lines=csv.trim().split('\r\n'),headers=parse(lines.shift()!),exported=lines.map(parse).map(row=>Object.fromEntries(headers.map((h,i)=>[h,row[i]])));
    const keys=new Map<string,number>();for(const r of rows){const key=`${r.source}|${r.day}|${r.cell}`;keys.set(key,(keys.get(key)??0)+1);}
    expect(exported.reduce((sum,r)=>sum+Number(r.reported_detections),0)).toBe(rows.length);
    for(const row of exported){
      expect(row.selection_id).toBe(selectionId(release.releaseId,selection));expect(row.observation_support).toBe('OBSERVATION_UNKNOWN');expect(row.adjustment_status).toBe('ADJUSTMENT_WITHHELD');
      if(row.row_kind==='OCCUPIED_CELL_DAY'){expect(Number(row.reported_detections)).toBe(keys.get(`${row.source}|${row.utc_day}|${row.cell_id}`));expect(row.occupied_cell_days).toBe('1');}
      else expect(row.occupied_cell_days).toBe('');
    }
    for(const job of ['explore','compare','history'] as const){const result=investigationAnswer(job,release,selection,rows);expect(result.lanes.reduce((sum,l)=>sum+l.records,0)).toBe(rows.length);expect(result.harmonization).toBe('ADJUSTMENT_WITHHELD');}
  }
});

test('camera bounds use only supplied records and month navigation is UTC-safe',()=>{
  const original=[...release.policy.aoi];expect(activityBounds([])).toBeNull();
  const bounds=activityBounds(release.records)!;
  for(const r of release.records){expect(r.longitude).toBeGreaterThanOrEqual(bounds[0][0]);expect(r.latitude).toBeLessThanOrEqual(bounds[1][1]);}
  expect(release.policy.aoi).toEqual(original);expect(shiftMonth('2013-01',-1)).toBe('2012-12');expect(shiftMonth('2016-12',1)).toBe('2017-01');
});

test('staged historical progress is hash-bound to its audit and never a released month',()=>{
  const bytes=readFileSync('reports/HISTORICAL_CANDIDATE_AUDIT.json'),report=JSON.parse(bytes.toString()),status=JSON.parse(readFileSync('src/history-status.json','utf8'));
  expect(status.report_sha256).toBe(createHash('sha256').update(bytes).digest('hex'));
  expect(status.candidate_id).toBe(report.candidate_id);expect(status.state).toBe('AUDITED_STAGED_NOT_QUALIFIED');expect(status.g4).toBe('ADJUSTMENT_WITHHELD');
  expect(release.months).toEqual(['2017-06']);expect(select(release.records,readSelection('?month=2013-01',release))).toEqual([]);
});

test('bundled cartographic context has reproducible public-domain provenance and finite regional geometry',()=>{
  const bytes=readFileSync('public/basemap/iberia-countries.geojson'),manifest=JSON.parse(readFileSync('public/basemap/provenance.json','utf8'));
  expect(createHash('sha256').update(bytes).digest('hex')).toBe(manifest.derived_sha256);
  expect(bytes.length).toBe(manifest.derived_bytes);expect(manifest.license).toBe('public domain');expect(manifest.scale).toBe('1:50 million');
  const countries=JSON.parse(bytes.toString('utf8'));expect(countries.features.map((f:any)=>f.properties.name).sort()).toEqual(['France','Morocco','Portugal','Spain']);
  for(const f of countries.features)for(const polygon of f.geometry.coordinates)for(const ring of polygon)for(const [lon,lat]of ring){expect(Number.isFinite(lon)&&Number.isFinite(lat)).toBe(true);expect(lon).toBeGreaterThan(-20);expect(lon).toBeLessThan(10);expect(lat).toBeGreaterThan(20);expect(lat).toBeLessThan(60);}
});
