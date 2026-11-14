import { test,expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const release=JSON.parse(readFileSync('public/data/release.json','utf8'));
const ready=async(page:any)=>{await page.goto('/');await expect(page.getByTestId('investigation')).toBeVisible();};

test('observation story answers facts, comparison trap and historical unknown without changing source truth',async({page})=>{
  await ready(page);await expect(page.getByTestId('answer-surface')).toContainText('ANSWERED');
  await page.getByRole('button',{name:'Follow the observation story',exact:true}).click();
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('57');await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('484');
  await expect(page.getByTestId('scientific-answer')).toContainText('57 records on 4 UTC dates');
  await expect(page.getByTestId('scientific-answer')).toContainText('484 records on 4 UTC dates');
  const id=await page.getByTestId('investigation').getAttribute('data-selection');
  await page.getByRole('button',{name:'Next: compare the instruments →',exact:true}).click();
  await expect(page.getByTestId('answer-surface')).toContainText('PARTIAL');await expect(page.locator('.comparison-lane')).toHaveCount(2);
  await page.getByRole('button',{name:'What can’t we conclude? +',exact:true}).click();
  await expect(page.locator('#answer-reasoning')).toContainText('ratio of physical fires');
  await page.getByRole('button',{name:'Next: was it unusual? →',exact:true}).click();
  await expect(page.getByTestId('scientific-answer')).toContainText('Not yet evaluable');await expect(page.getByTestId('answer-surface')).toContainText('UNKNOWN');
  await expect(page.getByRole('heading',{name:'Was this period historically unusual?',level:2})).toBeInViewport();
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
  await page.getByText('Historical acquisition: an audited next step',{exact:true}).click();
  await expect(page.locator('.candidate-progress')).toContainText('outside this scientific release');
});

test('empty-date and unavailable-month answers cannot be mistaken for observed zero',async({page})=>{
  await ready(page);await page.getByTestId('day-2017-06-01').click();
  await expect(page.getByTestId('answer-surface')).toContainText('UNKNOWN');await expect(page.getByTestId('scientific-answer')).toContainText('Valid observation coverage is unknown');
  await page.getByRole('button',{name:'Next month',exact:true}).click();await expect(page.getByTestId('scientific-answer')).toContainText('Quantities are unavailable');
  await expect(page.getByTestId('answer-surface')).toContainText('UNAVAILABLE');await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('—');
  await page.getByRole('button',{name:'Scientific limits',exact:true}).click();
  await expect(page.locator('.opportunity-ladder')).toContainText('Selected-period detection extract unavailable');
  await page.getByRole('button',{name:'Evidence Passport',exact:true}).click();
  await page.getByRole('button',{name:'Previous month',exact:true}).click();await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
});

test('metric readout and calendar change units while export and scientific identity stay fixed',async({page})=>{
  await ready(page);const id=await page.getByTestId('investigation').getAttribute('data-selection');
  await page.locator('#metric').selectOption('records');
  await expect(page.locator('[data-testid="summary-AQUA_MODIS"] .source-metric>strong')).toHaveText('238');
  await expect(page.getByTestId('occupancy-AQUA_MODIS')).toHaveText('32');
  await expect(page.getByTestId('day-2017-06-18')).toHaveAttribute('aria-label',/reported records/);
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
  await page.locator('#metric').selectOption('occupied_cell_days');
  await expect(page.locator('[data-testid="summary-AQUA_MODIS"] .source-metric>strong')).toHaveText('32');
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
});

test('map record drill-down identifies the exact original source row and UTC',async({page})=>{
  await page.goto('/?month=2017-06&cell=g:-2:-1');
  await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:45000});
  await page.locator('#render-mode').selectOption('points');await page.getByRole('button',{name:'Reset to evidence selection',exact:true}).click();
  await expect.poll(async()=>page.getByTestId('geographic-map').evaluate(el=>(el as any).scientificMap.queryRenderedFeatures({layers:['eg-detections']}).length)).toBeGreaterThan(0);
  const point=await page.getByTestId('geographic-map').evaluate(el=>{const m=(el as any).scientificMap,f=m.queryRenderedFeatures({layers:['eg-detections']})[0],p=m.project(f.geometry.coordinates);return {id:f.properties.id,x:p.x,y:p.y};});
  const raw=release.records.find((r:any)=>r.id===point.id),box=(await page.getByTestId('geographic-map').boundingBox())!;
  await page.mouse.click(box.x+point.x,box.y+point.y);
  await expect(page.getByRole('dialog',{name:'Selected native records'})).toBeVisible();
  await expect(page.getByTestId('record-detail')).toContainText(raw.id);await expect(page.getByTestId('record-detail')).toContainText(raw.utc);
  await expect(page.getByTestId('record-detail')).toContainText(`native confidence ${raw.confidence}`);
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',new RegExp(raw.day));
});

test('camera actions and focus change navigation, preserve science and respect usable content',async({page})=>{
  await ready(page);await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:45000});
  const id=await page.getByTestId('investigation').getAttribute('data-selection');
  const before=(await page.getByTestId('geographic-map').boundingBox())!;
  await page.getByRole('button',{name:'Fit detected activity',exact:true}).click();
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
  await expect(page.getByRole('status').filter({hasText:'Camera fitted to selected reported detections'})).toHaveCount(1);
  await page.getByRole('button',{name:'Map focus',exact:true}).click();
  await expect(page.locator('.answer-overlay')).toHaveCount(0);
  const after=(await page.getByTestId('geographic-map').boundingBox())!;expect(after.height).toBeGreaterThan(before.height+100);
  await page.getByRole('button',{name:'Exit map focus',exact:true}).click();
  await page.getByRole('button',{name:'Fit study area',exact:true}).click();
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
  expect(release.policy.aoi).toEqual([-8.7,39.3,-7.2,40.8]);
});

for(const [width,height] of [[1440,900],[1920,1080],[390,844],[320,844]])test(`atlas content and calendar fit ${width}×${height}`,async({page})=>{
  await page.setViewportSize({width,height});await ready(page);
  await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:45000});
  const geometry=await page.getByTestId('geographic-map').evaluate(el=>{const r=el.getBoundingClientRect(),w=document.querySelector('.workspace')!.getBoundingClientRect();return {y:r.y,fraction:r.height/w.height,overflow:document.documentElement.scrollWidth>innerWidth};});
  expect(geometry.y).toBeLessThanOrEqual(190);expect(geometry.fraction).toBeGreaterThanOrEqual(.55);expect(geometry.overflow).toBe(false);
  await expect(page.getByRole('button',{name:'Previous month',exact:true})).toBeInViewport();await expect(page.getByRole('button',{name:'Next month',exact:true})).toBeInViewport();
  await expect(page.getByRole('button',{name:'Scroll calendar later',exact:true})).toBeInViewport();
  await expect(page.getByTestId('calendar-surface')).toBeInViewport();
  if(width<801){
    await page.getByRole('button',{name:'Read scientific answer →',exact:true}).click();await expect(page.getByRole('dialog',{name:'Evidence Passport'})).toBeVisible();
    await expect(page.getByTestId('scientific-answer')).toContainText('238 records');
    await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Read scientific answer →',exact:true})).toBeFocused();
  }
});

test('opportunity evidence ladder and 750 m hypothesis remain explicitly unqualified',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Scientific limits',exact:true}).click();
  await expect(page.locator('.opportunity-ladder')).toContainText('Swath geometry not qualified');await expect(page.locator('.opportunity-ladder')).toContainText('L2 valid observation / QA not qualified');
  await page.getByRole('tab',{name:'history',exact:true}).click();await page.getByText('Research hypothesis: VIIRS 750 m continuity',{exact:true}).click();
  await expect(page.getByRole('tabpanel')).toContainText('not a demonstrated harmonization solution');await expect(page.getByRole('tabpanel')).toContainText('375 m product');
});

test('manual basemap recovery retains the loaded release and scientific selection',async({page})=>{
  await page.route('https://tiles.openfreemap.org/**',route=>route.abort());
  await page.goto('/?month=2017-06&cell=g:-2:-1');
  await expect(page.getByRole('button',{name:'Retry detailed basemap',exact:true})).toBeVisible({timeout:15000});
  const id=await page.getByTestId('investigation').getAttribute('data-selection');
  await page.unroute('https://tiles.openfreemap.org/**');
  await page.getByRole('button',{name:'Retry detailed basemap',exact:true}).click();
  await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:45000});
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('57');await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('484');
});

test('corrupt offline geography fails closed without blocking scientific records or CSV',async({page})=>{
  await page.route('https://tiles.openfreemap.org/**',route=>route.abort());
  await page.route('**/basemap/iberia-countries.geojson',route=>route.fulfill({contentType:'application/json',body:'{"type":"FeatureCollection","features":[]}'}));
  await page.goto('/?month=2017-06&cell=g:-2:-1');
  await expect(page.getByText('Geographic basemap unavailable. Native coordinates, calendar and export remain available.',{exact:true})).toBeVisible({timeout:15000});
  await expect(page.getByText('Geographic basemap rendered',{exact:true})).toHaveCount(0);
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('57');await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('484');
  const download=page.waitForEvent('download');await page.getByTestId('export').click();expect((await download).suggestedFilename()).toContain('2017-06');
});
