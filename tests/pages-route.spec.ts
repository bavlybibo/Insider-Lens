import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const canada='/?region=canada&view=retention';
test('direct Canada does not depend on the Portugal release',async({page})=>{
 const portugal:string[]=[];page.on('request',r=>{if(/\/data\/(catalog|eg-[^/]+)\.json/.test(new URL(r.url()).pathname))portugal.push(r.url());});
 await page.route('**/data/catalog.json',r=>r.fulfill({status:503,body:'unavailable'}));
 await page.goto(canada);await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-retention-ready','true');expect(portugal).toEqual([]);
});
test('region navigation commits the URL and survives refresh, back and forward',async({page})=>{
 await page.goto('/?month=2017-06&sources=AQUA_MODIS%2CSNPP_VIIRS&dn=ALL');await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('2,041');
 await page.getByRole('button',{name:'Filters',exact:true}).click();await page.locator('#region').selectOption('canada');await expect(page).toHaveURL(/region=canada/);await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');
 await page.reload();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');await expect(page.getByTestId('investigation')).toHaveCount(0);
 await page.goBack();await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');await page.goForward();await expect(page.getByTestId('canada-investigation')).toHaveAttribute('data-ready','true');
});
test('a failed lazy Canada module displays an error boundary instead of an empty root',async({page})=>{
 await page.route('**/assets/CanadaWorkspace-*.js',r=>r.abort('failed'));
 await page.goto(canada);const fallback=page.getByTestId('workspace-error');await expect(fallback).toBeVisible();await expect(fallback.getByRole('alert')).toContainText('withheld');await expect(fallback.getByRole('button',{name:'Reload investigation',exact:true})).toBeVisible();await expect(page.getByTestId('retention-map-answer')).toHaveCount(0);
});
test('a corrupt Canada receipt remains visibly withheld without fabricated totals',async({page})=>{
 await page.route('**/data/canada/**/catalog.json',r=>r.fulfill({body:'{}',contentType:'application/json'}));await page.goto(canada);await expect(page.getByRole('alert')).toContainText('checksum mismatch');await expect(page.getByTestId('retention-map-answer')).toHaveCount(0);await expect(page.getByRole('button',{name:'Return to Portugal release',exact:true})).toBeVisible();
});
test('direct retention refresh and repeated visits keep exact public evidence without errors',async({page})=>{
 const errors:string[]=[],consoleErrors:string[]=[],failed:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text());});page.on('requestfailed',r=>{if(new URL(r.url()).origin===new URL(page.url()).origin)failed.push(r.url());});
 await page.addInitScript(()=>{(window as any).__rejections=[];addEventListener('unhandledrejection',e=>(window as any).__rejections.push(String(e.reason)));});
 for(let i=0;i<3;i++){
  if(i===1)await page.reload();else await page.goto(canada);const app=page.getByTestId('canada-investigation'),card=page.getByTestId('retention-map-answer');await expect(app).toHaveAttribute('data-retention-ready','true');await expect(card).toContainText('10,524 retained records · 28 dates');for(const [group,n] of [['MODIS_ONLY','34'],['SHARED','199'],['VIIRS_ONLY','335']])await expect(card.locator(`[data-group=${group}] b`)).toHaveText(n);await expect(page).toHaveURL(/region=canada&view=retention/);
  await page.waitForFunction(()=>{const m=(document.querySelector('[data-testid=canada-map]') as any)?.scientificMap;return m?.getLayer('eg-retention-grid')&&m.queryRenderedFeatures({layers:['eg-retention-grid']}).length>0;});
  const examples=page.waitForResponse('**/data/canada/**/examples.json');await page.getByRole('button',{name:'Canada Evidence Passport',exact:true}).click();await expect(page.getByTestId('canada-passport')).toContainText('8,355,817');await (await examples).finished();await page.getByRole('button',{name:'Close Canada Evidence Passport',exact:true}).click();
  const d=page.waitForEvent('download');await page.getByRole('button',{name:'Export Evidence Retention keys CSV',exact:true}).click();const csv=readFileSync((await(await d).path())!,'utf8');expect(csv.trim().split('\r\n')).toHaveLength(569);
 }
 expect(errors).toEqual([]);expect(consoleErrors).toEqual([]);expect(failed).toEqual([]);expect(await page.evaluate(()=>(window as any).__rejections)).toEqual([]);
});
