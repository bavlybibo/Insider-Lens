import { test,expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const raw=JSON.parse(readFileSync('reports/DAY_NIGHT_RECONCILIATION.json','utf8'));
const ready=async(page:any)=>{await page.goto('/');await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:30000});};
const map=async(page:any)=>page.getByTestId('geographic-map');
const densityData=async(page:any)=>(await map(page)).evaluate((el:any)=>el.scientificMap.getSource('eg-density').serialize().data);
const csv=(text:string)=>{const p=(line:string)=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'));const lines=text.trim().split('\r\n'),h=p(lines.shift()!);return lines.map(p).map(v=>Object.fromEntries(h.map((k,i)=>[k,v[i]])));};

test('Heat Atlas uses source-specific fixed-distance values without changing selection or export',async({page})=>{
  await ready(page);const id=await page.getByTestId('investigation').getAttribute('data-selection');
  await page.locator('#render-mode').selectOption('heat');await expect(await map(page)).toHaveAttribute('data-heat-ready','true');
  await expect(page.locator('.quantitative-legend')).toContainText('Aqua MODIS');await expect(page.locator('.quantitative-legend')).toContainText('records/km²');
  await expect(page.locator('.quantitative-legend')).toContainText('Relative within this source/time selection');
  const before=await densityData(page);expect(before.features.length).toBeGreaterThan(0);
  await (await map(page)).evaluate((el:any)=>el.scientificMap.jumpTo({center:[-8,40],zoom:10}));
  expect(await densityData(page)).toEqual(before);await expect(await map(page)).toHaveAttribute('data-bandwidth-km','10');
  await page.locator('#atlas-source').selectOption('SNPP_VIIRS');await expect(page.locator('.quantitative-legend')).toContainText('S-NPP VIIRS');
  await expect(await map(page)).toHaveAttribute('data-heat-ready','true');expect(await densityData(page)).not.toEqual(before);
  await page.locator('#bandwidth').selectOption('5');await expect(await map(page)).toHaveAttribute('data-heat-ready','true');await expect(await map(page)).toHaveAttribute('data-bandwidth-km','5');
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
  const download=page.waitForEvent('download');await page.getByTestId('export').click();const rows=csv(readFileSync((await (await download).path())!,'utf8'));
  expect(rows.reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(2279);expect(rows.every(r=>r.selection_id===id)).toBe(true);
  await page.getByRole('button',{name:'Evidence Passport',exact:true}).click();await page.getByText('Heat Atlas: source lens, units and method',{exact:true}).click();
  await expect(page.locator('.heat-method')).toContainText('weight1');await expect(page.locator('.heat-method')).toContainText('No land mask');
});

test('quantitative cells reconcile source lens and distinguish records from cell-days',async({page})=>{
  await ready(page);await page.locator('#render-mode').selectOption('grid');
  const values=()=>page.getByTestId('geographic-map').evaluate((el:any)=>el.scientificMap.getSource('eg-cells').serialize().data.features.map((f:any)=>f.properties.value));
  await expect.poll(async()=>(await values()).reduce((a:number,b:number)=>a+b,0)).toBe(32);
  await page.locator('#metric').selectOption('records');await expect.poll(async()=>(await values()).reduce((a:number,b:number)=>a+b,0)).toBe(238);
  await page.getByRole('button',{name:'Acquisition class: Night N',exact:true}).click();await expect.poll(async()=>(await values()).reduce((a:number,b:number)=>a+b,0)).toBe(129);
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('129');await expect(page).toHaveURL(/dn=N/);
});

test('paired Day/Night maps synchronize camera and export independently raw-reconciled cohorts',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Compare Day and Night maps',exact:true}).click();
  for(const flag of ['D','N'])await expect(page.getByTestId(`pane-${flag}`).getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:30000});
  await expect(page.getByTestId('pane-D').locator('header')).toContainText('109 records / 24 cell-days');await expect(page.getByTestId('pane-N').locator('header')).toContainText('129 records / 17 cell-days');
  await page.getByTestId('pane-D').getByTestId('geographic-map').evaluate((el:any)=>el.scientificMap.jumpTo({center:[-7.9,40.1],zoom:9.2}));
  const view=await page.getByTestId('pane-N').getByTestId('geographic-map').evaluate((el:any)=>[...el.scientificMap.getCenter().toArray(),el.scientificMap.getZoom()]);
  expect(view[0]).toBeCloseTo(-7.9,8);expect(view[1]).toBeCloseTo(40.1,8);expect(view[2]).toBeCloseTo(9.2,8);
  for(const flag of ['D','N']){
    const download=page.waitForEvent('download');await page.getByRole('button',{name:`Export ${flag==='D'?'Day':'Night'} scientific CSV`,exact:true}).click();const rows=csv(readFileSync((await (await download).path())!,'utf8'));
    const expected=raw.groups.filter((g:any)=>g.source==='AQUA_MODIS'&&g.flag===flag),keys=new Set(expected.map((g:any)=>g.day+'|'+g.cell));
    expect(rows.length).toBe(keys.size);expect(rows.reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(raw.totals.AQUA_MODIS[flag].records);expect(rows.every(r=>r.daynight_filter===flag&&r.source==='AQUA_MODIS')).toBe(true);
  }
});

test('mobile comparison uses full-width Day and Night maps with native counts',async({page})=>{
  await page.setViewportSize({width:390,height:844});await ready(page);await page.locator('#atlas-source').selectOption('SNPP_VIIRS');await page.getByRole('button',{name:'Compare Day and Night maps',exact:true}).click();
  await expect(page.getByTestId('pane-D').locator('header')).toContainText('574 records / 43 cell-days');
  await expect(page.getByTestId('geographic-map')).toHaveCount(1);expect((await page.getByTestId('geographic-map').boundingBox())!.width).toBeGreaterThan(360);
  await page.getByRole('button',{name:'Night N',exact:true}).click();await expect(page.getByTestId('pane-N').locator('header')).toContainText('1467 records / 46 cell-days');
  await expect(page.getByTestId('geographic-map')).toHaveCount(1);expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(390);
});

test('Memory Loss Lab distinguishes provider-era history from staged and released measurements',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Memory Loss',exact:true}).click();await page.getByRole('button',{name:'New only',exact:true}).click();
  await expect(page.getByTestId('memory-answer')).toContainText('before S-NPP FIRMS begins 2012-01-20');
  await page.locator('#era-year').focus();await page.keyboard.press('Home');for(let i=0;i<8;i++)await page.keyboard.press('ArrowRight');
  await expect(page).toHaveURL(/month=2008-06/);await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('—');await expect(page.locator('.memory-levels')).toContainText('UNAVAILABLE');
  await expect(page.getByRole('button',{name:/Validated bridge/})).toBeDisabled();await expect(page.getByTestId('memory-lab')).toContainText('Eligible complete historical months: 0');
  await page.getByRole('button',{name:'Inspect the 2017 evidence',exact:true}).click();await expect(page.getByTestId('memory-lab')).toContainText('57 records / 4 cell-days');await expect(page.getByTestId('memory-lab')).toContainText('484 records / 4 cell-days');
  await page.getByText('Real historical work · five more months audited',{exact:true}).click();await expect(page.locator('.staged-expansion')).toContainText('not released history');await expect(page.locator('.staged-expansion')).toContainText('85 / 28');
});

test('mobile memory sheet has an accessible close and focus return',async({page})=>{
  await page.setViewportSize({width:320,height:844});await ready(page);const button=page.getByRole('button',{name:'Memory Loss',exact:true});await button.click();
  await expect(page.getByRole('dialog',{name:'Evidence Passport'})).toBeVisible();await expect(page.getByTestId('memory-lab')).toBeVisible();await page.keyboard.press('Escape');await expect(button).toBeFocused();
});

test('HTTP200 provider error payload is rejected as geography and coarse context remains truthful',async({page})=>{
  await page.route('https://tiles.openfreemap.org/**',route=>route.fulfill({status:200,contentType:'application/json',body:'{"error":"upstream unavailable"}'}));await ready(page);
  await expect(page.getByTestId('geographic-map')).toHaveAttribute('data-basemap','coarse-context');await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
});

test('density click opens a real contributing archive record',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Minimize scientific answer',exact:true}).click();await page.locator('#render-mode').selectOption('heat');await expect(await map(page)).toHaveAttribute('data-heat-ready','true');
  await expect.poll(async()=>(await map(page)).evaluate((el:any)=>el.scientificMap.queryRenderedFeatures({layers:['eg-density-fill']}).length)).toBeGreaterThan(0);
  const target=await (await map(page)).evaluate((el:any)=>{const m=el.scientificMap;for(const f of m.queryRenderedFeatures({layers:['eg-density-fill']})){const ring=f.geometry.coordinates[0],center=[ring.reduce((s:number,p:number[])=>s+p[0],0)/ring.length,ring.reduce((s:number,p:number[])=>s+p[1],0)/ring.length],point=m.project(center);if(point.x>340&&point.x<el.clientWidth-210&&point.y>90&&point.y<el.clientHeight-180)return {x:point.x,y:point.y};}return null;});
  expect(target).not.toBeNull();const box=(await (await map(page)).boundingBox())!;await page.mouse.click(box.x+target!.x,box.y+target!.y);
  await expect(page.getByTestId('record-detail')).toContainText('Underlying detection');await expect(page.getByTestId('record-detail')).toContainText(/844805:\d+/);await expect(page.getByTestId('record-detail')).toContainText('not a physical fire count');
});

test('density worker failure withholds the layer while preserving native quantities',async({page})=>{
  await page.route('**/*heat.worker*',route=>route.abort());await ready(page);await page.locator('#render-mode').selectOption('heat');
  await expect(page.getByText('Density worker unavailable. Native evidence remains available.',{exact:true})).toBeVisible();await expect(await map(page)).toHaveAttribute('data-heat-ready','false');
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('2,041');
});

test('WebGL failure uses verified static geographic context without claiming an observation mask',async({page})=>{
  await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind:any,...args:any[]){if(String(kind).startsWith('webgl'))return null;return (original as any).call(this,kind,...args);} as any;});
  await page.goto('/');await expect(page.getByTestId('static-context').locator('svg')).toBeVisible();await expect(page.getByTestId('static-context')).toContainText('no observation QA inferred');await expect(page.getByText('Geographic basemap rendered',{exact:true})).toHaveCount(0);
  await expect(page.locator('.map-watermark')).toBeHidden();await expect(page.locator('.map-legend')).toBeHidden();await expect(page.getByTestId('static-context').locator('figcaption')).toBeVisible();
});

test('valid style with stalled tiles falls back within the UI deadline and preserves user camera',async({page})=>{
  await page.route('https://tiles.openfreemap.org/styles/liberty',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({version:8,sources:{stalled:{type:'raster',tiles:['https://context-test.invalid/{z}/{x}/{y}.png'],tileSize:256}},layers:[{id:'stalled-geography',type:'raster',source:'stalled'}]})}));
  await page.route('https://context-test.invalid/**',async route=>{await new Promise(r=>setTimeout(r,9000));await route.abort().catch(()=>{});});
  await page.goto('/');await expect.poll(async()=>page.getByTestId('geographic-map').evaluate((el:any)=>Boolean(el.scientificMap?.getSource('eg-points')))).toBe(true);
  await page.getByTestId('geographic-map').evaluate((el:any)=>el.scientificMap.jumpTo({center:[-8,40],zoom:9}));
  await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:15000});await expect(page.getByTestId('geographic-map')).toHaveAttribute('data-basemap','coarse-context');
  expect(await page.getByTestId('geographic-map').evaluate((el:any)=>[...el.scientificMap.getCenter().toArray(),el.scientificMap.getZoom()])).toEqual([-8,40,9]);
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
});
