import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const pointer=JSON.parse(readFileSync('public/data/phase7/index.json','utf8'));
const study=JSON.parse(readFileSync('public'+pointer.file,'utf8'));
async function ready(page:any){await page.goto('/?region=canada&lab=1');await page.getByRole('button',{name:'Scientific Bridge · new observation search',exact:true}).click();await expect(page.getByTestId('scientific-bridge')).toContainText('78,923',{timeout:30000});}

test('new experiment reports measured failure and near-nadir replication without a fitted bridge',async({page})=>{
 await ready(page);const lab=page.getByTestId('scientific-bridge');await expect(lab).toContainText('450.8 MB');await expect(lab).toContainText('G4 adjustment withheld');await expect(lab).toContainText('0.04–7.97°');await expect(lab).toContainText('39.96–45.71°');await expect(lab).toContainText('No fire-class pixels');
});

test('map, study calendar and center export reconcile exactly for both sources and dates',async({page})=>{
 await ready(page);await page.getByRole('button',{name:'Map replication VNP14 mask centers',exact:true}).click();const map=page.getByTestId('canada-map');await expect(map).toHaveAttribute('data-mask-centers','11663');await expect(map).toHaveAttribute('data-ready','true');
 await expect(page.getByLabel('Canada year',{exact:true})).toBeHidden();
 for(const [split,day] of [['replication',23],['development',15]] as const){
  if(day===15)await page.getByRole('button',{name:'June 15 UTC · mask acquired; support unqualified',exact:true}).click();
  for(const product of (split==='replication'?['MYD14','VNP14','VNP14IMG']:['MYD14','VNP14'])){
   await page.getByLabel('Observation mask product',{exact:true}).selectOption(product);
   const name=`${split}-${product}.json`,raw=JSON.parse(readFileSync('public/data/phase7/'+study.id+'/'+name,'utf8'));
   await expect(map).toHaveAttribute('data-observation',split+'-'+product);await expect(map).toHaveAttribute('data-mask-centers',String(raw.points.length));
   await expect.poll(()=>map.evaluate((e:any)=>e.scientificMap.getSource('eg-ca-support')?.serialize().data.features.length)).toBe(raw.points.length);
   const data=await map.evaluate((e:any)=>e.scientificMap.getSource('eg-ca-support').serialize().data.features);expect(data.map((p:any)=>[p.properties.line,p.properties.sample,...p.geometry.coordinates,p.properties.mask,p.properties.qa,p.properties.zenith])).toEqual(raw.points);
   const event=page.waitForEvent('download');await page.getByRole('button',{name:'Export displayed observation centers CSV',exact:true}).click();const csv=readFileSync((await (await event).path())!,'utf8');
   const rows=csv.trim().split('\r\n').slice(2).map(r=>[...r.matchAll(/"((?:[^\"]|\"\")*)"/g)].map(m=>m[1]));expect(rows).toHaveLength(raw.points.length);
   expect(rows.map(r=>r.slice(8,15).map(Number))).toEqual(raw.points);expect(rows.every(r=>['UNKNOWN_SUPPORT','CLOUD_OR_INVALID'].includes(r[15])&&r[17]==='UNKNOWN'&&r[18]==='ADJUSTMENT_WITHHELD')).toBe(true);
   expect(rows.every(r=>r[3]===study.artifacts[name].sha256&&r[6].startsWith('2022-06-'+day))).toBe(true);
  }
 }
 await expect(page.getByRole('button',{name:'June 16 UTC · not acquired in this experiment',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Return to native history',exact:true}).click();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-observation','');await expect(page.getByTestId('ca-summary-AQUA_MODIS')).toContainText('5,993');await expect(page.getByRole('region',{name:'Canada UTC historical calendar',exact:true})).toBeVisible();
});

test('checksum failure withholds new overlay and leaves native history available',async({page})=>{
 await page.route('**/data/phase7/**/bridge.json',r=>r.fulfill({body:'{}',contentType:'application/json'}));await page.goto('/?region=canada&lab=1');await page.getByRole('button',{name:'Scientific Bridge · new observation search',exact:true}).click();await expect(page.getByTestId('scientific-bridge').getByRole('alert')).toContainText('checksum mismatch');await expect(page.getByRole('button',{name:'Map replication VNP14 mask centers',exact:true})).toHaveCount(0);
});

test('late native-history delivery cannot move the observation camera off its frozen AOI',async({page})=>{
 await page.route('**/canada/**/AQUA_MODIS-SP-2010-06.json',async r=>{await new Promise(resolve=>setTimeout(resolve,3000));await r.continue();});
 await ready(page);await page.getByRole('button',{name:'Map replication VNP14IMG mask centers',exact:true}).click();
 await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');
 const map=page.getByTestId('canada-map');await expect(map).toHaveAttribute('data-ready','true');
 await expect.poll(()=>map.evaluate((e:any)=>Math.abs(e.scientificMap.getCenter().lat-53.5))).toBeLessThan(1);
 await expect.poll(()=>map.evaluate((e:any)=>e.scientificMap.queryRenderedFeatures({layers:['eg-ca-support']}).length)).toBeGreaterThan(0);
});

for(const width of [1440,390,320])test(`actual mask map remains dismissible and bounded at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});await ready(page);await page.getByRole('button',{name:'Map development VNP14 mask centers',exact:true}).click();await expect(page.getByTestId('canada-map')).toHaveAttribute('data-mask-centers','8984');expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);await expect(page.getByLabel('Observation support legend',{exact:true})).toContainText('not observation footprint');await page.getByRole('button',{name:'Return to native history',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-observation','');
});
