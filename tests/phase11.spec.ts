import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {CA_SOURCES,caCsv,selectedCells,type CaCatalog,type CaChunk,type CaQuery} from '../src/canada';
import {POLICIES,coverageState,retention,retentionCsv,seasonalCsv,seasonalEligibility,seasonalPatterns,type Policy} from '../src/nativeHistory';
const read=(p:string)=>JSON.parse(readFileSync(p,'utf8'));
const catalog=read('public'+read('public/data/canada/index.json').file) as CaCatalog;
const fixture=read('reports/phase11/NATIVE_RETENTION.json');
const chunks=(month:string)=>catalog.coverage.filter(e=>e.month===month&&e.pc==='SP').map(e=>read('public'+catalog.root+e.file) as CaChunk);
const query=(scope:any):CaQuery=>({cell:null,sources:CA_SOURCES,pc:'SP',...scope});
const parseCsv=(s:string)=>{const rows=s.trim().split('\r\n').map(line=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'))),header=rows.shift()!;return rows.map(row=>Object.fromEntries(header.map((h,i)=>[h,row[i]])));};
async function ready(page:any){await page.goto('/?region=canada');await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');}
async function overlap(page:any){await ready(page);await page.getByRole('button',{name:'Read Canada scientific answer →',exact:true}).isVisible().then(async(v:boolean)=>{if(v)await page.getByRole('button',{name:'Read Canada scientific answer →',exact:true}).click();});await page.getByRole('button',{name:'2 · Native overlap',exact:true}).click();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');}

test('108 AOI/date/DN retention scopes reconcile all 324 independent raw-oracle policy results',()=>{
 for(const c of fixture.cases){const q=query(c.scope),native=selectedCells(chunks(q.month),q);expect(retention(native,q.flag)).toEqual(c.policies);}
});
test('annual patterns match 648 independent source scopes, including dates, versions and month lengths',()=>{
 for(const year of ['2022','2023'])for(const area of ['canada','south','north'])for(const flag of ['ALL','D','N']){
  const q=query({month:year+'-06',area,flag,day:7}),raw=Array.from({length:12},(_,i)=>chunks(year+'-'+String(i+1).padStart(2,'0'))).flat(),rows=seasonalPatterns(catalog,raw,q);
  for(const row of rows)for(const s of row.sources){const expected=fixture.seasonal.find((v:any)=>v.scope.month===row.month&&v.scope.area===area&&v.scope.flag===flag&&v.source===s.source);expect([s.records,s.cell_days,s.dates_with_records,s.versions,s.month_has_acquired_rows,row.month_length]).toEqual([expected.records,expected.cell_days,expected.dates_with_records,expected.native_versions,expected.month_has_acquired_rows,expected.month_length]);}
 }
});
test('missing month, version break, month length and sensor selection never manufacture anomaly eligibility',()=>{
 const q=query({month:'2023-06',area:'canada',flag:'ALL',day:null}),all=Array.from({length:12},(_,i)=>chunks('2023-'+String(i+1).padStart(2,'0'))).flat();
 const c=structuredClone(catalog);c.coverage=c.coverage.filter(e=>!(e.source==='AQUA_MODIS'&&e.month==='2023-05'&&e.pc==='SP'));
 let rows=seasonalPatterns(c,all.filter(e=>!(e.source==='AQUA_MODIS'&&e.month==='2023-05')),q),e=seasonalEligibility(rows,'AQUA_MODIS');expect(e.represented_months).toBe(11);expect(e.normalized_rate).toBe(false);expect(e.anomaly).toBe('WITHHELD');expect(rows[4].sources[0].month_has_acquired_rows).toBe(false);
 const feb=c.coverage.find(e=>e.month==='2023-02'&&e.source==='AQUA_MODIS'&&e.pc==='SP')! as typeof c.coverage[number]&{native_versions:string[]};feb.native_versions=['6.03'];rows=seasonalPatterns(c,all,q);expect(seasonalEligibility(rows,'AQUA_MODIS').same_literal_lineage).toBe(false);expect(rows[1].month_length).toBe(28);expect(rows[3].month_length).toBe(30);expect(rows[4].month_length).toBe(31);
 expect(seasonalPatterns(catalog,all,{...q,sources:['SNPP_VIIRS']}).every(r=>r.sources.length===1)).toBe(true);
 expect(()=>seasonalPatterns(catalog,all.filter(e=>e.month!=='2023-05'),q)).toThrow('Annual artifact missing');
 const exported=parseCsv(seasonalCsv(c,q,rows));expect(exported.find(r=>r.month==='2023-05'&&r.source==='AQUA_MODIS')!.reported_records).toBe('');expect(exported.every(r=>r.anomaly==='WITHHELD'&&r.observation_opportunity==='UNKNOWN')).toBe(true);
});
test('retention unions include full UTC dates, collapse D/N keys and preserve source rows',()=>{
 const base:CaChunk={candidate:catalog.candidate,grid:catalog.grid.grid_id,source:'AQUA_MODIS',pc:'SP',month:'2023-06',cells:[[0,0,[[1,2,3]]]]};
 const r=retention([base,{...base,source:'TERRA_MODIS'},{...base,source:'SNPP_VIIRS'},{...base,month:'2023-07'}],'ALL');expect(r.ALL_NATIVE.records).toBe(20);expect(r.ALL_NATIVE.union_cell_days).toBe(2);expect(r.ALL_NATIVE.dates_with_records).toEqual(['2023-06-01','2023-07-01']);expect(r.MODIS_ONLY.union_cell_days).toBe(2);expect(r.VIIRS_ONLY.exclusive_dates_lost).toEqual(['2023-07-01']);
});
test('all policy CSVs retain exact independent counts, date sets, provenance and null unsupported quantities',()=>{
 for(const c of fixture.cases){const q=query(c.scope),native=selectedCells(chunks(q.month),q),rows=parseCsv(retentionCsv(catalog,q,native));expect(rows).toHaveLength(3);for(const row of rows){const r=c.policies[row.policy];expect([+row.records_retained,+row.records_excluded_by_policy,+row.union_positive_cell_days,+row.dates_with_records,row.utc_dates]).toEqual([r.records,r.excluded_records,r.union_cell_days,r.dates_with_records.length,r.dates_with_records.join(';')]);for(const source of POLICIES[row.policy as Policy]){const a=catalog.archives.find(a=>a.request===(source==='SNPP_VIIRS'?'845606':'845605'))!;expect(row.source_archive_member_sha256).toContain(a.zip_sha256);expect(row.source_archive_member_sha256).toContain(a.members.find(m=>m.processing_class==='SP')!.sha256);}expect(row.valid_nondetections).toBe('');expect(row.physical_fires_lost).toBe('');expect(row.adjustment).toBe('ADJUSTMENT_WITHHELD');}
  expect(parseCsv(caCsv(catalog,q,native)).reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(c.policies.ALL_NATIVE.records);
 }
});
test('coverage separates eras, missing processing months, positive records and unknown local support',()=>{
 const q=query({month:'2010-06',area:'canada',flag:'ALL',day:null});expect(coverageState(catalog,'SNPP_VIIRS',q,0).code).toBe('SOURCE_NOT_YET_IN_ERA');expect(coverageState(catalog,'AQUA_MODIS',{...q,month:'2026-11'},0).code).toBe('MONTH_NOT_ACQUIRED');expect(coverageState(catalog,'AQUA_MODIS',q,0).code).toBe('ACQUIRED_SUPPORT_UNKNOWN');expect(coverageState(catalog,'AQUA_MODIS',q,5993).code).toBe('POSITIVE_REPORTED');
});

test('Memory Loss displays quantitative policies and exports exact source-separated evidence',async({page})=>{
 await overlap(page);await page.getByRole('button',{name:'Memory Loss',exact:true}).click();const table=page.getByTestId('retention-result');await expect(table.locator('tr[data-policy=ALL_NATIVE]')).toContainText('378,701');await expect(table.locator('tr[data-policy=ALL_NATIVE]')).toContainText('13,025');await page.getByRole('button',{name:'MODIS only',exact:true}).click();await expect(table).toContainText('317,681 acquired records excluded');
 const event=page.waitForEvent('download');await page.getByRole('button',{name:'Export retention evidence CSV',exact:true}).click();const rows=parseCsv(readFileSync((await (await event).path())!,'utf8'));expect(rows.find(r=>r.policy==='MODIS_ONLY')!.records_retained).toBe('61020');expect(rows.find(r=>r.policy==='ALL_NATIVE')!.union_positive_cell_days).toBe('13025');
 await page.getByRole('button',{name:'VIIRS only',exact:true}).click();await expect(table).toContainText('61,020 acquired records excluded');await expect(page.getByTestId('canada-map')).toHaveAttribute('data-source','SNPP_VIIRS');
});
test('filtered native map, selected-source export and retention use identical pilot/day/night scope',async({page})=>{
 await overlap(page);await page.getByRole('button',{name:'Canada filters',exact:true}).click();await page.locator('#ca-area').selectOption('south');await page.getByRole('button',{name:'Close Canada investigation filters',exact:true}).click();await page.getByRole('button',{name:'Canada acquisition N',exact:true}).click();await page.getByRole('button',{name:'Explore',exact:true}).click();await page.getByRole('button',{name:/^2023-06-07 UTC:/}).click();await page.getByRole('button',{name:'Memory Loss',exact:true}).click();
 const expected=fixture.cases.find((c:any)=>c.scope.month==='2023-06'&&c.scope.area==='south'&&c.scope.flag==='N'&&c.scope.day===7).policies.ALL_NATIVE;
 const event=page.waitForEvent('download');await page.getByRole('button',{name:'Export retention evidence CSV',exact:true}).click();const rows=parseCsv(readFileSync((await (await event).path())!,'utf8'));expect(+rows.find(r=>r.policy==='ALL_NATIVE')!.records_retained).toBe(expected.records);
 const native=page.waitForEvent('download');await page.getByRole('button',{name:'Export Canada scientific CSV',exact:true}).click();const records=parseCsv(readFileSync((await (await native).path())!,'utf8'));expect(records.reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(expected.records);expect(records.every(r=>r.daynight_filter==='N')).toBe(true);
});
test('annual comparison is on demand, source-specific and exports missing SP months as unknown',async({page})=>{
 await overlap(page);await page.getByRole('button',{name:'History & eras',exact:true}).click();await page.getByRole('button',{name:'Load annual positive patterns',exact:true}).click();await expect(page.getByTestId('seasonal-patterns')).toContainText('Observed-positive patterns only');const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export annual patterns CSV',exact:true}).click();const rows=parseCsv(readFileSync((await (await download).path())!,'utf8'));expect(rows).toHaveLength(36);expect(rows.every(r=>r.extract_completeness==='UNKNOWN'&&r.adjustment==='ADJUSTMENT_WITHHELD'&&JSON.parse(r.scope).month===r.month&&JSON.parse(r.scope).day===null)).toBe(true);
 await page.locator('#ca-year').selectOption('2026');await page.getByRole('button',{name:'Load annual positive patterns',exact:true}).click();await expect(page.getByTestId('seasonal-patterns')).toContainText('8/12 archive months');await expect(page.getByTestId('seasonal-patterns')).toContainText('7/12 archive months');await page.locator('#ca-year').selectOption('2024');await expect(page.getByTestId('canada-answer')).toContainText('sealed 2024 partition');await expect(page.getByTestId('seasonal-patterns')).toHaveCount(0);
});
test('corrupt annual artifact withholds the entire annual answer while native June export survives',async({page})=>{
 await overlap(page);await page.route('**/SNPP_VIIRS-SP-2023-05.json',r=>r.fulfill({body:'{}',contentType:'application/json'}));await page.getByRole('button',{name:'History & eras',exact:true}).click();await page.getByRole('button',{name:'Load annual positive patterns',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Annual summary withheld');await expect(page.getByTestId('seasonal-patterns')).toHaveCount(0);await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');await expect(page.getByRole('button',{name:'Export Canada scientific CSV',exact:true})).toBeEnabled();
});
for(const width of [390,320])test(`mobile ${width}: retention table, source states, keyboard and map remain bounded`,async({page})=>{
 await page.setViewportSize({width,height:900});await overlap(page);await page.getByRole('button',{name:'Memory Loss',exact:true}).click();const el=page.getByTestId('retention-result');await expect(el.locator('tr[data-policy=ALL_NATIVE]')).toBeInViewport();expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);expect((await page.getByTestId('canada-map').boundingBox())!.height).toBeGreaterThan(350);await page.getByRole('button',{name:'VIIRS only',exact:true}).focus();await page.keyboard.press('Enter');await expect(el).toHaveAttribute('data-policy','VIIRS_ONLY');await page.locator('#ca-year').selectOption('2010');await expect(page.getByTestId('ca-summary-SNPP_VIIRS')).toContainText('Not yet in era');
});
test('forced fallback keeps coverage states separate from observation QA and native counts',async({page})=>{
 await page.route('https://tiles.openfreemap.org/**',r=>r.abort());await ready(page);await expect(page.getByTestId('canada-map')).toHaveAttribute('data-basemap','coarse-context');await expect(page.getByTestId('ca-summary-AQUA_MODIS')).toContainText('5,993');await expect(page.getByText('Coarse Natural Earth context · not observation QA',{exact:true})).toBeVisible();await expect(page.locator('.fallback-places')).toContainText('Canada');
});

 test('custom single-platform selection is not mislabeled as the two-platform MODIS policy',async({page})=>{
 await overlap(page);await page.getByRole('checkbox',{name:'Canada Terra MODIS',exact:true}).uncheck();await page.getByRole('checkbox',{name:'Canada S-NPP VIIRS',exact:true}).uncheck();await page.getByRole('button',{name:'Memory Loss',exact:true}).click();await expect(page.getByTestId('retention-result')).toHaveAttribute('data-policy','CUSTOM');await expect(page.getByRole('button',{name:'MODIS only',exact:true})).toHaveAttribute('aria-pressed','false');await expect(page.getByTestId('retention-result')).toContainText('349,452 acquired records excluded');const d=page.waitForEvent('download');await page.getByRole('button',{name:'Export Canada scientific CSV',exact:true}).click();const rows=parseCsv(readFileSync((await (await d).path())!,'utf8'));expect(rows.every(r=>r.source==='AQUA_MODIS')).toBe(true);expect(rows.reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(29249);
 });
