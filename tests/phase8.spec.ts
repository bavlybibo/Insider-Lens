import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const pointer=JSON.parse(readFileSync('public/data/phase8/index.json','utf8'));
const study=JSON.parse(readFileSync('public'+pointer.file,'utf8'));
const binOracle=JSON.parse(readFileSync('reports/phase8/DISPLAY_BIN_RECOUNT.json','utf8'));
const binProps=(features:any[])=>features.map(f=>{const {i,j,count,positive,invalid}=f.properties;return {i,j,count,positive,invalid};}).sort((a,b)=>a.i-b.i||a.j-b.j);
async function ready(page:any){await page.goto('/?region=canada&lab=1&study=phase8');await expect(page.getByTestId('fire-signal-bridge')).toContainText('16 positive VIIRS 375 m pixels',{timeout:30000});}
async function map(page:any){await ready(page);await page.getByRole('button',{name:'Explore June 13 fire signal on map',exact:true}).click();await expect(page.getByTestId('canada-map')).toHaveAttribute('data-mask-centers','9238');await expect(page.getByTestId('canada-map')).toHaveAttribute('data-ready','true');}

test('event result reports actual positives, limited timing and no qualified denominator',async({page})=>{
 await ready(page);const result=page.getByTestId('fire-signal-bridge');await expect(result).toContainText('22.37 MW');await expect(result).toContainText('75.17 seconds');await expect(result).toContainText('No coefficient fitted');await expect(result).toContainText('G4 adjustment withheld');await result.getByText('Historical evidence retained by each source',{exact:true}).click();await expect(result).toContainText('702');await expect(result).toContainText('155');
});

test('aggregates, native drilldown, source selection, calendar and CSV preserve every identity',async({page})=>{
 await map(page);const el=page.getByTestId('canada-map');await expect(el).toHaveAttribute('data-render-mode','5km-aggregate');
 await expect.poll(()=>el.evaluate((e:any)=>e.scientificMap.getSource('eg-ca-support-bins')?.serialize().data.features.reduce((n:number,f:any)=>n+f.properties.count,0))).toBe(9238);
 const b=await el.evaluate((e:any)=>e.scientificMap.getSource('eg-ca-support-bins').serialize().data.features);expect(b.length).toBeLessThan(150);expect(binOracle.mapped_centers_sha256).toBe(study.independent.mapped_centers_sha256);expect(binProps(b)).toEqual(binOracle.products.VNP14IMG);expect(b.reduce((n:number,f:any)=>n+f.properties.positive,0)).toBe(16);
 await expect.poll(()=>el.evaluate((e:any)=>e.scientificMap.queryRenderedFeatures({layers:['eg-ca-support-bins']}).length)).toBeGreaterThan(0);
 expect(await el.evaluate((e:any)=>e.scientificMap.getLayoutProperty('eg-ca-support','visibility'))).toBe('none');
 await page.getByText('Inspect centers & support',{exact:true}).click();await page.getByRole('button',{name:'Inspect native centers',exact:true}).click();await expect(el).toHaveAttribute('data-render-mode','native');await expect.poll(()=>el.evaluate((e:any)=>e.scientificMap.queryRenderedFeatures({layers:['eg-ca-support']}).length)).toBeGreaterThan(0);
 for(const product of ['VNP14IMG','MYD14','VNP14']){
  await page.getByLabel('Observation mask product',{exact:true}).selectOption(product);const raw=JSON.parse(readFileSync('public/data/phase8/'+study.id+`/development-${product}.json`,'utf8'));
  await expect(el).toHaveAttribute('data-mask-centers',String(raw.points.length));await expect.poll(()=>el.evaluate((e:any)=>e.scientificMap.getSource('eg-ca-support').serialize().data.features.length)).toBe(raw.points.length);
  await expect.poll(()=>el.evaluate((e:any)=>e.scientificMap.getSource('eg-ca-support-bins').serialize().data.features.reduce((n:number,f:any)=>n+f.properties.count,0))).toBe(raw.points.length);expect(binProps(await el.evaluate((e:any)=>e.scientificMap.getSource('eg-ca-support-bins').serialize().data.features))).toEqual(binOracle.products[product]);
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export displayed observation centers CSV',exact:true}).click();const csv=readFileSync((await (await download).path())!,'utf8');const rows=csv.trim().split('\r\n').slice(2).map(r=>[...r.matchAll(/"((?:[^\"]|\"\")*)"/g)].map(m=>m[1]));
  expect(rows.map(r=>r.slice(8,15).map(Number))).toEqual(raw.points);expect(rows.every(r=>r[17]==='UNKNOWN'&&r[18]==='ADJUSTMENT_WITHHELD'&&r[6].startsWith('2023-06-13'))).toBe(true);
 }
 const calendar=page.getByRole('region',{name:'Observation study UTC calendar',exact:true});await expect(calendar).toContainText('June 2023');await expect(calendar.getByRole('button',{name:/2023-06-07/})).toBeDisabled();await expect(calendar.getByRole('button',{name:/2023-06-13/})).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'Return to native history',exact:true}).click();await expect(page.getByLabel('Canada year',{exact:true})).toHaveValue('2023');await expect(page.getByRole('region',{name:'Canada UTC historical calendar',exact:true})).toBeVisible();
});

test('corrupt event evidence fails closed without replacing native or Phase7 releases',async({page})=>{
 await page.route('**/data/phase8/**/bridge.json',r=>r.fulfill({body:'{}',contentType:'application/json'}));await page.goto('/?region=canada&lab=1&study=phase8');await expect(page.getByTestId('fire-signal-bridge').getByRole('alert')).toContainText('checksum mismatch');await expect(page.getByRole('button',{name:'Explore June 13 fire signal on map',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Scientific Bridge · new observation search',exact:true}).click();await expect(page.getByTestId('scientific-bridge')).toContainText('78,923');
});

test('late mask response cannot override a newer source selection',async({page})=>{
 await map(page);await page.route('**/data/phase8/**/development-MYD14.json',async r=>{await new Promise(resolve=>setTimeout(resolve,1200));await r.continue();});
 await page.getByLabel('Observation mask product',{exact:true}).selectOption('MYD14');await page.getByLabel('Observation mask product',{exact:true}).selectOption('VNP14');await expect(page.getByTestId('canada-map')).toHaveAttribute('data-observation','development-VNP14');await page.waitForTimeout(1400);await expect(page.getByTestId('canada-map')).toHaveAttribute('data-observation','development-VNP14');
});

for(const width of [1440,390,320])test(`event map and keyboard controls remain usable at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});await map(page);expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);await expect(page.getByLabel('Observation support legend',{exact:true})).toContainText('16 positive thermal pixels');
 await page.getByText('Inspect centers & support',{exact:true}).click();await page.getByRole('button',{name:'Inspect native centers',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByTestId('canada-map')).toHaveAttribute('data-render-mode','native');
});
