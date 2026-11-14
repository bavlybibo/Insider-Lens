import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const pointer=JSON.parse(readFileSync('public/data/phase6/index.json','utf8'));
const bundle=JSON.parse(readFileSync('public'+pointer.file,'utf8'));
const ready=async(page:any)=>{await page.goto('/?region=canada&lab=1');await expect(page.getByTestId('bridge-lab')).toContainText('Same cell-day fails the timing test',{timeout:30000});};
const parseCsv=(text:string)=>{const rows=text.trim().split('\r\n').map(line=>[...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"')));const h=rows.shift()!;return rows.map(r=>Object.fromEntries(h.map((k,i)=>[k,r[i]])));};

test('measured bridge shows the rejected L2 support and a preserved baseline',async({page})=>{
 await ready(page);await expect(page.getByRole('button',{name:'Calibrated · withheld',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Native',exact:true}).click();await expect(page.getByTestId('bridge-lab')).toContainText('Preserved baseline, no adjustment');
 await page.getByRole('button',{name:'Matched observation',exact:true}).click();await expect(page.getByTestId('bridge-lab')).toContainText('361.6 MB');await expect(page.getByTestId('bridge-lab')).toContainText('No qualified shared denominator');await expect(page.getByTestId('bridge-lab')).toContainText('51.79–65.54');
});

test('frozen cohort drives map, UTC dates, raw centers and selected CSV; full release is recoverable',async({page})=>{
 await ready(page);await page.getByRole('button',{name:'Inspect frozen pilot on map',exact:true}).click();const app=page.getByTestId('canada-investigation');await expect(app).toHaveAttribute('data-experiment',bundle.id);await expect(app).toHaveAttribute('data-ready','true');
 await expect(page.getByTestId('ca-summary-AQUA_MODIS')).toContainText('2');await expect(page.getByTestId('ca-summary-SNPP_VIIRS')).toContainText('75');
 await expect(page.locator('.ca-days button:disabled')).toHaveCount(30-bundle.contract.development.length-bundle.contract.replication.length);
 await expect(page.getByTestId('canada-map')).toHaveAttribute('data-ready','true');await expect.poll(()=>page.getByTestId('canada-map').evaluate((e:any)=>e.scientificMap.getSource('eg-ca-centers')?.serialize().data.features.length)).toBe(75);
 for(const flag of ['ALL','D','N']){
  await page.getByRole('button',{name:'Canada acquisition '+flag,exact:true}).click();const event=page.waitForEvent('download');await page.getByRole('button',{name:'Export Canada scientific CSV',exact:true}).click();const rows=parseCsv(readFileSync((await (await event).path())!,'utf8'));
  for(const source of bundle.contract.sources){const expected=bundle.rows.filter((r:any)=>r.source===source&&(flag==='ALL'||r.dn===flag)).length;expect(rows.filter(r=>r.source===source).reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(expected);}
  expect(rows.every(r=>r.experiment_id===bundle.id&&r.cohort_contract_sha256===bundle.contract_sha256&&r.adjustment==='ADJUSTMENT_WITHHELD')).toBe(true);expect(rows.every(r=>r.area_membership.includes('frozen six UTC dates'))).toBe(true);
  expect(rows.every(r=>r.observation_support==='OBSERVATION_UNKNOWN'&&r.zip_sha256.length===64&&r.member_sha256.length===64)).toBe(true);
  const centers=bundle.rows.filter((r:any)=>r.source==='SNPP_VIIRS'&&(flag==='ALL'||r.dn===flag)).length;
  await expect.poll(()=>page.getByTestId('canada-map').evaluate((e:any)=>e.scientificMap.getSource('eg-ca-centers').serialize().data.features.length)).toBe(centers);
 }
 await page.getByRole('button',{name:'Canada acquisition ALL',exact:true}).click();
 const cell=bundle.rows.find((r:any)=>r.source==='AQUA_MODIS').cell;
 await page.getByRole('button',{name:'Canada filters',exact:true}).click();await page.locator('#ca-cell').fill(cell);await page.getByRole('button',{name:'Inspect cell',exact:true}).click();
 await expect(page.getByTestId('canada-answer')).toContainText('Contributing pixel centers');
 await expect.poll(()=>page.getByTestId('canada-map').evaluate((e:any)=>e.scientificMap.getSource('eg-ca-centers').serialize().data.features.length)).toBe(bundle.rows.filter((r:any)=>r.source==='SNPP_VIIRS'&&r.cell===cell).length);
 const selected=page.waitForEvent('download');await page.getByRole('button',{name:'Export Canada scientific CSV',exact:true}).click();const selectedRows=parseCsv(readFileSync((await (await selected).path())!,'utf8'));
 expect(selectedRows.filter(r=>Number(r.reported_detections)>0).every(r=>r.cell_id===cell)).toBe(true);expect(selectedRows.reduce((n,r)=>n+Number(r.reported_detections),0)).toBe(bundle.rows.filter((r:any)=>r.cell===cell).length);
 await page.getByRole('button',{name:'Return to full native month',exact:true}).click();await expect(app).toHaveAttribute('data-experiment','');await expect(page.locator('.ca-days button:disabled')).toHaveCount(0);
});

test('corrupt research evidence withholds experiment without breaking native Canada',async({page})=>{
 await page.route('**/phase6/**/bridge.json',r=>r.fulfill({body:'{}',contentType:'application/json'}));await page.goto('/?region=canada&lab=1');await expect(page.getByTestId('bridge-lab').getByRole('alert')).toContainText('checksum mismatch');await expect(page.getByRole('button',{name:'Inspect frozen pilot on map',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Close Bridge laboratory',exact:true}).click();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');await expect(page.getByTestId('ca-summary-AQUA_MODIS')).toContainText('5,993');
});

for(const width of [1440,390,320])test(`bridge result is keyboard accessible and bounded at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});await ready(page);expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);
 const box=(await page.getByRole('button',{name:'Matched observation',exact:true}).boundingBox())!;expect(box.height).toBeGreaterThanOrEqual(40);
 await page.getByRole('button',{name:'Matched observation',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByTestId('bridge-lab')).toContainText('Actual masks acquired; sample rejected');await page.keyboard.press('Escape');
 if(width<800)await expect(page.getByRole('dialog',{name:'Bridge laboratory',exact:true})).not.toBeVisible();else await expect(page.getByRole('complementary',{name:'Bridge laboratory',exact:true})).toBeHidden();
});
