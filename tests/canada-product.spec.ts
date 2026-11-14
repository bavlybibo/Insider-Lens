import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const pointer=JSON.parse(readFileSync('public/data/canada/index.json','utf8'));
const catalog=JSON.parse(readFileSync('public'+pointer.file,'utf8'));
const ready=async(page:any)=>{await page.goto('/?region=canada');await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true',{timeout:30000});await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:30000});await expect.poll(()=>page.getByTestId('canada-map').evaluate((el:any)=>el.scientificMap.queryRenderedFeatures({layers:['eg-ca-fill']}).length)).toBeGreaterThan(0);};
const csvRows=(s:string)=>{const parse=(line:string)=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'));const rows=s.trim().split('\r\n');const head=parse(rows.shift()!);return rows.map(parse).map(r=>Object.fromEntries(head.map((h,i)=>[h,r[i]])));};

test('existing region picker opens Canada, preserves the original Portugal release and provides multi-year evidence',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Filters',exact:true}).click();await page.locator('#region').selectOption('canada');await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');await expect(page.getByTestId('canada-answer')).toContainText('not zero');
 for(const source of ['AQUA_MODIS','TERRA_MODIS']){const c=catalog.coverage.find((c:any)=>c.source===source&&c.month==='2010-06'&&c.pc==='SP');await expect(page.getByTestId('ca-summary-'+source)).toContainText(c.records.toLocaleString('en-US'));}
 await page.getByRole('button',{name:'2 · Native overlap',exact:true}).click();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');await expect(page.getByTestId('canada-answer')).toContainText('Agreement is not calibration');
 await page.getByRole('button',{name:'Canada filters',exact:true}).click();await page.locator('#ca-region').selectOption('portugal');await expect(page.getByTestId('investigation')).toHaveAttribute('data-release','eg-9a6ad9ccfda103bf80926db6');await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
});

test('theme preserves actual map values; D/N, source lens and exact scientific exports retain one cohort',async({page})=>{
 await ready(page);await page.getByRole('button',{name:'2 · Native overlap',exact:true}).click();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');
 const map=page.getByTestId('canada-map');await expect(map).toHaveAttribute('data-ready','true');const selection=await page.getByTestId('canada-investigation').getAttribute('data-selection');
 const values=()=>map.evaluate((el:any)=>el.scientificMap.getSource('eg-ca').serialize().data);
 await expect.poll(async()=>(await values()).features.length).toBeGreaterThan(0);const before=await values();
 await page.getByRole('button',{name:'Toggle Canada cartographic theme',exact:true}).click();expect(await values()).toEqual(before);await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-selection',selection!);
 await page.getByRole('button',{name:'Canada acquisition N',exact:true}).click();
 const expected=catalog.coverage.filter((c:any)=>c.month==='2023-06'&&c.pc==='SP').reduce((n:number,c:any)=>n+c.days.reduce((s:number,d:any)=>s+d.N,0),0);
 const event=page.waitForEvent('download');await page.getByRole('button',{name:'Export Canada scientific CSV',exact:true}).click();const rows=csvRows(readFileSync((await (await event).path())!,'utf8'));expect(rows.reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(expected);expect(rows.every(r=>r.daynight_filter==='N'&&r.processing_class==='SP'&&r.adjustment==='ADJUSTMENT_WITHHELD')).toBe(true);
});

test('Memory source retention and unknown opportunity cannot unlock a harmonized series',async({page})=>{
 await ready(page);await page.getByRole('button',{name:'Memory Loss',exact:true}).click();await page.getByRole('button',{name:'VIIRS only',exact:true}).click();await expect(page.getByTestId('canada-answer')).toContainText('Not yet in era');await expect(page.getByTestId('ca-summary-SNPP_VIIRS')).toContainText('—');
 await page.getByRole('button',{name:'Canada Evidence Passport',exact:true}).click();await expect(page.getByTestId('canada-passport')).toContainText('NOT IDENTIFIABLE FROM HOTSPOT-ONLY ARCHIVES');await expect(page.getByRole('button',{name:'Validated bridge · not scientifically released',exact:true})).toBeDisabled();
});

test('an unavailable or corrupt independent native acceptance artifact withholds Canada totals',async({page})=>{
 await page.route('**/native-oracle.json',r=>r.fulfill({status:200,body:'{}',contentType:'application/json'}));await page.goto('/?region=canada');await expect(page.getByRole('alert')).toContainText('checksum mismatch');await expect(page.getByTestId('canada-investigation')).toHaveCount(0);
});

test('agency context opens the independently recounted cell without asserting an event match',async({page})=>{
 await ready(page);await page.getByRole('button',{name:'Canada Evidence Passport',exact:true}).click();await page.getByText('Independent Canadian context',{exact:true}).click();await page.getByRole('button',{name:'Inspect the agency-context cell',exact:true}).click();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');await expect(page.getByTestId('canada-answer')).toContainText('ca-laea60n100w-wgs84-o0-v1:10000:-106:-44');await expect(page.getByTestId('ca-summary-SNPP_VIIRS')).toContainText('302');await expect(page.getByTestId('canada-answer')).toContainText('29 records / 4 occupied cell-days');
});

test('bounded selected-cell keyboard investigation and export use exact source/day keys',async({page})=>{
 await ready(page);const scope=catalog.coverage.find((c:any)=>c.month==='2010-06'&&c.source==='AQUA_MODIS'&&c.pc==='SP');const artifact=JSON.parse(readFileSync('public'+catalog.root+scope.file,'utf8'));const [i,j,days]=artifact.cells[0];const cell=`ca-laea60n100w-wgs84-o0-v1:10000:${i}:${j}`;
 await page.getByRole('button',{name:'Canada filters',exact:true}).click();await page.locator('#ca-cell').fill(cell);await page.getByRole('button',{name:'Inspect cell',exact:true}).click();await expect(page.getByTestId('canada-answer')).toContainText(cell);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export Canada scientific CSV',exact:true}).click();const rows=csvRows(readFileSync((await (await download).path())!,'utf8'));expect(rows.filter(r=>r.source==='AQUA_MODIS').reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(days.reduce((n:number,d:number[])=>n+d[1]+d[2],0));expect(rows.filter(r=>r.occupied_cell_days==='1').every(r=>r.cell_id===cell)).toBe(true);const camera=await page.getByTestId('canada-map').evaluate((el:any)=>[...el.scientificMap.getCenter().toArray(),el.scientificMap.getZoom()]);await page.locator('#ca-year').selectOption('2011');await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');expect(JSON.parse((await page.getByTestId('canada-investigation').getAttribute('data-selection'))!).cell).toBe(cell);expect(await page.getByTestId('canada-map').evaluate((el:any)=>[...el.scientificMap.getCenter().toArray(),el.scientificMap.getZoom()])).toEqual(camera);await expect.poll(()=>page.getByTestId('canada-map').evaluate((el:any)=>el.scientificMap.getSource('eg-ca-selection').serialize().data.features.length)).toBe(1);
});

test('SP/NRT boundaries and checksum rejection do not show stale data or pool products',async({page})=>{
 await ready(page);await page.locator('#ca-year').selectOption('2026');await page.locator('#ca-month').selectOption('11');await page.getByRole('button',{name:'Canada filters',exact:true}).click();await page.locator('#ca-pc').selectOption('NRT');await page.getByRole('button',{name:'Close Canada investigation filters',exact:true}).click();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');await expect(page.getByTestId('canada-answer')).toContainText('15:40 UTC');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export Canada scientific CSV',exact:true}).click();const rows=csvRows(readFileSync((await (await download).path())!,'utf8'));expect(rows.every(r=>r.processing_class==='NRT')).toBe(true);
 await page.route('**/canada/ca-*/AQUA_MODIS-SP-2010-06.json',r=>r.fulfill({status:200,body:'{}',contentType:'application/json'}));await page.goto('/?region=canada');await expect(page.getByRole('alert')).toContainText('checksum mismatch');await expect(page.getByRole('button',{name:'Export Canada scientific CSV',exact:true})).toBeDisabled();await expect(page.getByTestId('ca-summary-AQUA_MODIS')).toContainText('—');
});

for(const [width,height] of [[1440,900],[1920,1080],[390,844],[320,844]])test(`Canada map/calendar/Passport remain legible and bounded at ${width}×${height}`,async({page})=>{
 await page.setViewportSize({width,height});await ready(page);const map=page.getByTestId('canada-map');const box=(await map.boundingBox())!;expect(box.width).toBe(width);expect(box.height).toBeGreaterThan(width>800?500:350);expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);
 expect((await page.locator('.ca-map-shell .map-status').boundingBox())!.width).toBeLessThan(320);
 expect(await map.evaluate((el:any)=>el.scientificMap.getCenter().lat)).toBeLessThan(70);
 if(width<=800){expect((await page.locator('.ca-days button').first().boundingBox())!.width).toBeGreaterThanOrEqual(24);await expect(page.getByRole('button',{name:'Canada acquisition N',exact:true})).toBeVisible();const year=(await page.locator('.canada-room .period-control').boundingBox())!;for(const button of await page.locator('.canada-room .investigation-bar nav button:visible').all()){const r=(await button.boundingBox())!;expect(r.x+r.width).toBeLessThanOrEqual(year.x-2);}for(const card of await page.locator('.canada-room .source-card').all()){const c=(await card.boundingBox())!;for(const text of await card.locator('label,small').all()){const r=(await text.boundingBox())!;expect(r.x+r.width).toBeLessThanOrEqual(c.x+c.width+2);}}}
 else{const legend=(await page.locator('.ca-legend').boundingBox())!,answer=(await page.getByTestId('canada-answer').boundingBox())!;expect(legend.x).toBeGreaterThan(answer.x+answer.width);}
 if(width>800)await page.getByRole('button',{name:'Close Canada scientific answer',exact:true}).click();else await expect(page.getByRole('button',{name:'Read Canada scientific answer →',exact:true})).toBeVisible();await page.getByRole('button',{name:'Canada Evidence Passport',exact:true}).click();if(width<=800){await expect(page.getByRole('dialog',{name:'Canada Evidence Passport',exact:true})).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Canada Evidence Passport',exact:true})).toBeFocused();}else{await expect(page.getByRole('complementary',{name:'Canada Evidence Passport',exact:true})).toBeVisible();expect((await map.boundingBox())!.width).toBe(box.width);}
});
