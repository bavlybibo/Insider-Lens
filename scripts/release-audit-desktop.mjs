import {chromium,expect} from '@playwright/test';
import {mkdirSync,writeFileSync} from 'node:fs';
const label=process.argv[2]||'before';mkdirSync('reports/release-audit',{recursive:true});
const browser=await chromium.launch({args:['--enable-unsafe-swiftshader','--enable-precise-memory-info']}),runs=[];
for(const width of [1440,1920,1440]){
 const height=width===1920?1080:900,context=await browser.newContext({viewport:{width,height}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));const t=Date.now();
 await page.goto('http://127.0.0.1:5174/?region=canada&view=retention');await page.locator('[data-retention-ready=true]').waitFor();const answer_ms=Date.now()-t;
 await page.waitForFunction(()=>{const m=document.querySelector('[data-testid=canada-map]')?.scientificMap;return m?.getLayer('eg-retention-grid')&&m.queryRenderedFeatures({layers:['eg-retention-grid']}).length>0&&m.queryRenderedFeatures().some(f=>!String(f.source).startsWith('eg-'));});
 await page.waitForTimeout(500);const geography_ms=Date.now()-t;
 if(runs.length<2)await page.screenshot({path:`reports/release-audit/${label}-${width}.png`,fullPage:true});
 const start=Date.now();await page.getByTestId('retention-map-answer').getByRole('button',{name:'VIIRS only',exact:true}).click();await expect(page.getByTestId('retention-map-answer')).toContainText('8,385 retained records · 27 dates');const policy_ms=Date.now()-start;
 const sizes=await page.evaluate(()=>{const m=document.querySelector('[data-testid=canada-map]').getBoundingClientRect(),c=document.querySelector('[data-testid=retention-map-answer]').getBoundingClientRect();return {viewport_width:innerWidth,viewport_height:innerHeight,page_width:document.documentElement.scrollWidth,map_width:m.width,map_height:m.height,card_width:c.width,card_height:c.height,heap_snapshot_bytes:performance.memory?.usedJSHeapSize};});
 runs.push({width,height,answer_ms,geography_ms,policy_ms,...sizes,errors});await context.close();
}
await browser.close();writeFileSync(`reports/release-audit/${label}-performance.json`,JSON.stringify({conditions:'Fresh Chromium/SwiftShader contexts; built5174preview; first geographic rendering plus500ms settle; snapshots exclude worker/GPU/peak; three mixed-size runs, not a controlled hardware benchmark.',runs},null,2));console.log(JSON.stringify(runs));
