import { test,expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { density,kernel,project,unproject,quantitativeCells } from '../src/atlas';
import { memoryEvidence } from '../src/memory';
import { select,scientificCsv,type Release,type SourceId } from '../src/science';
const release:Release=JSON.parse(readFileSync('public/data/release.json','utf8'));
const raw=JSON.parse(readFileSync('reports/DAY_NIGHT_RECONCILIATION.json','utf8'));
const csvRows=(text:string)=>{const parse=(line:string)=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'));const lines=text.trim().split('\r\n'),header=parse(lines.shift()!);return lines.map(parse).map(row=>Object.fromEntries(header.map((h,i)=>[h,row[i]])));};

test('visual LAEA forward/inverse agrees with independent PROJ fixtures',()=>{
  const fixtures=JSON.parse(readFileSync('reports/ATLAS_PROJ_FIXTURES.json','utf8'));
  for(const f of fixtures.forward){const xy=project(...f.lonlat as [number,number]);expect(Math.hypot(xy[0]-f.xy[0],xy[1]-f.xy[1])).toBeLessThan(.001);}
  for(const f of fixtures.inverse){const ll=unproject(...f.xy as [number,number]);expect(Math.hypot(ll[0]-f.lonlat[0],ll[1]-f.lonlat[1])).toBeLessThan(1e-8);}
});
test('fixed-distance density has declared normalization, finite support and AOI clipping',()=>{
  expect(kernel(0,10)).toBeCloseTo(2/(Math.PI*100),12);expect(kernel(10,10)).toBe(0);expect(kernel(11,10)).toBe(0);
  for(const h of [5,10]){let integral=0;const dr=h/10000;for(let i=0;i<10000;i++){const r=(i+.5)*dr;integral+=kernel(r,h)*2*Math.PI*r*dr;}expect(integral).toBeCloseTo(1,6);}
  const r=release.records[0],one=density([r],10,release.policy.aoi),two=density([r,r],10,release.policy.aoi);
  expect(one.features.length).toBeGreaterThan(0);expect(two.features.map(f=>f.properties.value)).toEqual(one.features.map(f=>f.properties.value*2));
  for(const f of one.features)for(const [lon,lat]of f.geometry.coordinates[0]){expect(lon).toBeGreaterThanOrEqual(-8.7);expect(lon).toBeLessThanOrEqual(-7.2);expect(lat).toBeGreaterThanOrEqual(39.3);expect(lat).toBeLessThanOrEqual(40.8);}
});
test('all source/day/cell/DN queries and scientific CSV reconcile against original-archive groups',()=>{
  expect(raw.release_sha256).toBe(createHash('sha256').update(readFileSync('public/data/release.json')).digest('hex'));
  const cells=[null,...new Set<string>(raw.groups.map((g:any)=>g.cell))],days=[null,...Array.from({length:30},(_,i)=>`2017-06-${String(i+1).padStart(2,'0')}`)];
  for(const source of Object.keys(release.sources) as SourceId[])for(const day of days)for(const cell of cells)for(const flag of ['ALL','D','N'] as const){
    const query={sources:[source],month:'2017-06',day,cell,daynight:flag},records=select(release.records,query);
    const scope=JSON.stringify(query);
    const groups=raw.groups.filter((g:any)=>g.source===source&&(!day||g.day===day)&&(!cell||g.cell===cell)&&(flag==='ALL'||g.flag===flag));
    const keys=new Set(groups.map((g:any)=>`${g.day}|${g.cell}`));
    assert.equal(records.length,groups.reduce((sum:number,g:any)=>sum+g.records,0),scope);
    const exported=csvRows(scientificCsv(release,query,records));
    assert.equal(exported.reduce((sum,r)=>sum+Number(r.reported_detections),0),records.length,scope);
    assert.equal(exported.filter(r=>r.row_kind==='OCCUPIED_CELL_DAY').length,keys.size,scope);
    assert.equal(exported.every(r=>r.daynight_filter===flag&&r.observation_support==='OBSERVATION_UNKNOWN'&&r.adjustment_status==='ADJUSTMENT_WITHHELD'),true,scope);
    for(const metric of ['records','occupied_cell_days'] as const){const grid=quantitativeCells(release,records,metric);assert.equal(grid.features.reduce((n,f)=>n+f.properties.value,0),metric==='records'?records.length:keys.size,scope);}
  }
});
test('record partition is additive but occupied key partition overlaps',()=>{
  for(const source of Object.keys(raw.totals)){const t=raw.totals[source];expect(t.D.records+t.N.records).toBe(t.ALL.records);expect(t.D.occupied_cell_days+t.N.occupied_cell_days).toBeGreaterThan(t.ALL.occupied_cell_days);}
  expect(raw.reference_cell.AQUA_MODIS.ALL.records).toBe(57);expect(raw.reference_cell.SNPP_VIIRS.ALL.records).toBe(484);expect(raw.other_or_missing_flags).toBe(0);
});
test('memory distinguishes exact provider eras, local staging, released diagnostics and withheld bridge',()=>{
  const query=(month:string)=>({sources:['AQUA_MODIS','SNPP_VIIRS'] as SourceId[],month,day:null,cell:null});
  const early=memoryEvidence(release,query('2000-06'));expect(early.every(e=>!e.potential)).toBe(true);
  const old=memoryEvidence(release,query('2008-06'));expect(old.find(e=>e.id==='AQUA_MODIS')?.potential).toBe(true);expect(old.find(e=>e.id==='SNPP_VIIRS')?.potential).toBe(false);expect(old.every(e=>e.measurement==='UNAVAILABLE')).toBe(true);
  const stage=memoryEvidence(release,query('2013-06'),['2013-01','2013-06']);expect(stage.find(e=>e.id==='AQUA_MODIS')?.delivery).toBe('STAGED_UNQUALIFIED');expect(stage.every(e=>e.complete==='UNKNOWN')).toBe(true);
  const current=memoryEvidence(release,query('2017-06'));expect(current.find(e=>e.id==='SNPP_VIIRS')?.measurement).toBe('DIAGNOSTIC_RELEASED');expect(current.every(e=>e.bridge==='NOT_SCIENTIFICALLY_RELEASED')).toBe(true);
  expect(memoryEvidence(release,query('2026-12')).find(e=>e.id==='SNPP_VIIRS')?.potential).toBe(false);
  expect(current.find(e=>e.id==='NOAA20')?.potential).toBe(false);
});
test('five historical months stay hash-bound staged data outside the release',()=>{
  const report=JSON.parse(readFileSync('reports/HISTORICAL_PHASE3_AUDIT.json','utf8')),status=JSON.parse(readFileSync('src/history-expansion.json','utf8'));
  expect(status.report_sha256).toBe(createHash('sha256').update(readFileSync('reports/HISTORICAL_PHASE3_AUDIT.json')).digest('hex'));
  expect(report.months.map((m:any)=>m.month)).toEqual(['2013-02','2013-03','2013-04','2013-05','2013-06']);expect(release.months).toEqual(['2017-06']);expect(report.additional_qualified_released_months).toBe(0);expect(report.holdouts_accessed).toBe(false);
});
