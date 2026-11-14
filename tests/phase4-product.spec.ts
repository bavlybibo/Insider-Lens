import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const release=JSON.parse(readFileSync('public/data/release.json','utf8'));
const ready=async(page:any)=>{await page.goto('/');await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:30000});};
const csv=(text:string)=>{const parse=(line:string)=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'));const lines=text.trim().split('\r\n'),head=parse(lines.shift()!);return lines.map(parse).map(values=>Object.fromEntries(head.map((key,i)=>[key,values[i]])));};

test('native Night flag drives real geographic paint, restores Day, and preserves native row identities',async({page})=>{
  await page.route('https://tiles.openfreemap.org/**',r=>r.abort());await ready(page);
  const map=page.getByTestId('geographic-map'),id=await page.getByTestId('investigation').getAttribute('data-selection');
  const before=await map.evaluate((el:any)=>el.scientificMap.getPaintProperty('offline-land','fill-color'));
  await page.getByRole('button',{name:'Acquisition class: Night N',exact:true}).click();
  await expect(map).toHaveAttribute('data-theme','night');
  await expect.poll(()=>map.evaluate((el:any)=>el.scientificMap.getPaintProperty('offline-land','fill-color'))).toBe('#193532');
  const ids=await map.evaluate((el:any)=>el.scientificMap.getSource('eg-points').serialize().data.features.map((f:any)=>f.properties.id).sort());
  expect(ids).toEqual(release.records.filter((r:any)=>['AQUA_MODIS','SNPP_VIIRS'].includes(r.source)&&r.daynight==='N').map((r:any)=>r.id).sort());
  expect(await map.evaluate((el:any)=>getComputedStyle(el.querySelector('canvas')).filter)).toBe('none');
  await page.getByRole('button',{name:'Acquisition class: All',exact:true}).click();await expect(map).toHaveAttribute('data-theme','day');
  await expect.poll(()=>map.evaluate((el:any)=>el.scientificMap.getPaintProperty('offline-land','fill-color'))).toBe(before);
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
});

test('linked source maps retain native identities, independent scales and exact lane exports',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Compare',exact:true}).click();await page.getByRole('button',{name:'Link source maps',exact:true}).click();
  for(const source of ['AQUA_MODIS','SNPP_VIIRS']){
    const pane=page.getByTestId(`source-pane-${source}`);await expect(pane.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:30000});
    const ids=await pane.getByTestId('geographic-map').evaluate((el:any)=>el.scientificMap.getSource('eg-points').serialize().data.features.map((f:any)=>f.properties.id).sort());
    expect(ids).toEqual(release.records.filter((r:any)=>r.source===source).map((r:any)=>r.id).sort());
    const download=page.waitForEvent('download');await pane.getByRole('button',{name:`Export ${release.sources[source].name} scientific CSV`,exact:true}).click();
    const rows=csv(readFileSync((await (await download).path())!,'utf8'));
    expect(rows.reduce((sum,r)=>sum+Number(r.reported_detections),0)).toBe(source==='AQUA_MODIS'?238:2041);expect(rows.every(r=>r.source===source)).toBe(true);
  }
  await page.getByTestId('source-pane-AQUA_MODIS').getByTestId('geographic-map').evaluate((el:any)=>el.scientificMap.jumpTo({center:[-7.8,40.2],zoom:9.4}));
  const camera=await page.getByTestId('source-pane-SNPP_VIIRS').getByTestId('geographic-map').evaluate((el:any)=>[...el.scientificMap.getCenter().toArray(),el.scientificMap.getZoom()]);
  expect(camera[0]).toBeCloseTo(-7.8,8);expect(camera[1]).toBeCloseTo(40.2,8);expect(camera[2]).toBeCloseTo(9.4,8);
  await page.getByRole('checkbox',{name:'Terra MODIS',exact:true}).check();await page.getByLabel('Right comparison source',{exact:true}).selectOption('TERRA_MODIS');
  await expect(page.getByTestId('source-pane-TERRA_MODIS').locator('header')).toContainText('172 records / 24 cell-days');
  await page.getByRole('checkbox',{name:'Terra MODIS',exact:true}).uncheck();await page.getByRole('checkbox',{name:'S-NPP VIIRS',exact:true}).uncheck();
  await expect(page.getByTestId('source-compare')).toHaveCount(0);await expect(page.getByTestId('scientific-answer')).toContainText('One source is selected');
});

test('density inspection overlay and presentation keep sampled values, query identity and CSV unchanged',async({page})=>{
  await ready(page);await page.locator('#render-mode').selectOption('heat');const map=page.getByTestId('geographic-map');await expect(map).toHaveAttribute('data-heat-ready','true');
  const id=await page.getByTestId('investigation').getAttribute('data-selection');
  const data=()=>map.evaluate((el:any)=>el.scientificMap.getSource('eg-density').serialize().data);
  const before=await data();
  await page.getByRole('checkbox',{name:'Native centers',exact:true}).check();
  await expect.poll(()=>map.evaluate((el:any)=>el.scientificMap.getLayoutProperty('eg-detections','visibility'))).toBe('visible');expect(await data()).toEqual(before);
  await page.getByRole('checkbox',{name:'Native centers',exact:true}).uncheck();
  await expect.poll(()=>map.evaluate((el:any)=>el.scientificMap.getLayoutProperty('eg-detections','visibility'))).toBe('none');expect(await data()).toEqual(before);
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);
  await page.locator('#bandwidth').selectOption('5');await expect(map).toHaveAttribute('data-heat-ready','true');expect(await data()).not.toEqual(before);
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');await expect(page.getByTestId('occupancy-AQUA_MODIS')).toHaveText('32');
  const download=page.waitForEvent('download');await page.getByTestId('export').click();const rows=csv(readFileSync((await (await download).path())!,'utf8'));expect(rows.reduce((sum,r)=>sum+Number(r.reported_detections),0)).toBe(2279);
  await page.getByRole('button',{name:'Density method & evidence ↗',exact:true}).click();await expect(page.getByTestId('evidence-surface')).toBeVisible();
  await page.getByText('Heat Atlas: source lens, units and method',{exact:true}).click();await expect(page.locator('.heat-method')).toContainText('No extra interpolation or screen-space blur');
});

test('historical navigation retains UTC month and distinguishes staged years from qualified release',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'History',exact:true}).click();
  await expect(page.locator('.history-navigation')).toContainText('No qualified seasonal baseline');await page.getByRole('button',{name:'2013-06: staged, unqualified',exact:true}).click();
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('—');await expect(page.getByTestId('calendar-surface')).toContainText('June 2013');
  await expect(page.getByTestId('scientific-answer')).toContainText('Not yet evaluable');await page.getByRole('button',{name:'Memory Loss',exact:true}).click();
  await page.getByRole('button',{name:'New only',exact:true}).click();await expect(page.getByTestId('continuity-window')).toContainText('Excluded by source choice');
  await expect(page.getByTestId('continuity-window')).toContainText('VIIRS lane selected');await expect(page.getByTestId('continuity-window')).not.toContainText('Native detail retained');
  await expect(page.getByRole('button',{name:'Validated bridge · not scientifically released',exact:true})).toBeDisabled();
});

for(const width of [1440,1920,390,320])test(`mission map, floating Passport and native controls remain usable at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:width>800?900:844});await ready(page);
  const map=page.getByTestId('geographic-map'),before=(await map.boundingBox())!;
  expect(before.y).toBeLessThanOrEqual(150);expect(before.height).toBeGreaterThan(width>800?570:450);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);
  await page.getByRole('button',{name:'Evidence Passport',exact:true}).click();
  if(width>800){const after=(await map.boundingBox())!;expect(after.width).toBe(before.width);await expect(page.getByRole('complementary',{name:'Evidence Passport'})).toBeVisible();}
  else{await expect(page.getByRole('dialog',{name:'Evidence Passport'})).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Evidence Passport',exact:true})).toBeFocused();
    const id=await page.getByTestId('investigation').getAttribute('data-selection');await page.locator('.metric-menu summary').click();await page.locator('#metric').selectOption('records');await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',id!);await page.keyboard.press('Escape');await expect(page.locator('.metric-menu')).not.toHaveAttribute('open');
  }
});

test('mobile source comparison gives the map space and exposes lane choices on request',async({page})=>{
  await page.setViewportSize({width:320,height:844});await ready(page);await page.getByRole('checkbox',{name:'Terra MODIS',exact:true}).check();
  await page.getByRole('button',{name:'Compare',exact:true}).click();await page.getByRole('button',{name:'Link source maps',exact:true}).click();
  await expect(page.getByTestId('geographic-map')).toHaveCount(1);expect((await page.getByTestId('geographic-map').boundingBox())!.height).toBeGreaterThan(300);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(320);
  await page.locator('.source-pair-settings summary').click();await page.getByLabel('Right comparison source',{exact:true}).selectOption('TERRA_MODIS');await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Terra MODIS',exact:true}).click();await expect(page.getByTestId('source-pane-TERRA_MODIS').locator('header')).toContainText('172 records / 24 cell-days');
  await page.getByRole('button',{name:'Close source maps',exact:true}).click();await expect(page.getByTestId('source-compare')).toHaveCount(0);
});
