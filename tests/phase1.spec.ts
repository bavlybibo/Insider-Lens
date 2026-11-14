import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const release = JSON.parse(readFileSync('public/data/release.json', 'utf8'));
const parseCsv = (text: string) => {
  const parse = (line: string) => [...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m => m[1].replaceAll('""','"'));
  const lines = text.trim().split('\r\n'), headers = parse(lines.shift()!);
  return lines.map(parse).map(values => Object.fromEntries(headers.map((h,i) => [h,values[i]])));
};

test('reference cell explains per-date multiplicities and every CSV key reconciles', async ({ page }) => {
  await page.goto('/?month=2017-06&cell=g:-2:-1');
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('57');
  await expect(page.getByTestId('occupancy-AQUA_MODIS')).toHaveText('4');
  await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('484');
  await expect(page.getByTestId('occupancy-SNPP_VIIRS')).toHaveText('4');
  await page.getByRole('button',{name:'Evidence Passport',exact:true}).click();
  await expect(page.getByText('Aqua MODIS: 57 records → 4 occupied cell-days')).toBeVisible();
  await expect(page.getByText('S-NPP VIIRS: 484 records → 4 occupied cell-days')).toBeVisible();
  await page.getByRole('checkbox', { name:'Terra MODIS',exact:true }).check();
  await expect(page.getByTestId('records-TERRA_MODIS')).toHaveText('45');
  await expect(page.getByTestId('occupancy-TERRA_MODIS')).toHaveText('3');
  const keys = new Map<string,number>();
  for (const r of release.records.filter((r:any) => r.cell === 'g:-2:-1')) {
    const key = `${r.source}|${r.day}|${r.cell}`; keys.set(key,(keys.get(key) ?? 0)+1);
    await expect(page.getByTestId(`day-${r.day}`)).toHaveAttribute('aria-label',/Observation support unknown/);
  }
  const pending = page.waitForEvent('download'); await page.getByTestId('export').click();
  const rows = parseCsv(readFileSync((await (await pending).path())!,'utf8'));
  expect(rows).toHaveLength(11);
  for (const row of rows) {
    expect(Number(row.reported_detections)).toBe(keys.get(`${row.source}|${row.utc_day}|${row.cell_id}`));
    expect(row.source_credit).toContain('NASA FIRMS'); expect(row.adjustment_status).toBe('ADJUSTMENT_WITHHELD');
  }
});

test('URL back/forward, daynight filtering and rapid selections remain coherent', async ({ page }) => {
  await page.goto('/'); await expect(page.getByTestId('investigation')).toBeVisible();
  await page.locator('#cell').selectOption('g:-2:-1');
  await page.getByTestId('day-2017-06-21').click();
  await page.goBack(); await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('57');
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',/2017-06\|g:-2:-1/);
  await page.goForward(); await expect(page.getByTestId('day-2017-06-21')).toHaveAttribute('aria-pressed','true');
  await page.getByRole('button', {name:'Filters',exact:true}).click();
  await page.locator('#daynight').selectOption('N');
  await page.getByRole('button', {name:'Close Investigation filters'}).click();
  const rows = release.records.filter((r:any) => ['AQUA_MODIS','SNPP_VIIRS'].includes(r.source) && r.cell === 'g:-2:-1' && r.day === '2017-06-21' && r.daynight === 'N');
  await expect(page.getByTestId('evidence-records')).toHaveText(rows.length.toLocaleString('en-US'));
  await expect(page).toHaveURL(/dn=N/);
  for (const day of ['18','19','20','21']) await page.getByTestId(`day-2017-06-${day}`).click();
  expect(new Set(await page.locator('[data-selection]').evaluateAll(nodes => nodes.map(n=>n.getAttribute('data-selection')))).size).toBe(1);
  const pending = page.waitForEvent('download'); await page.getByTestId('export').click();
  const exported = parseCsv(readFileSync((await (await pending).path())!,'utf8'));
  expect(exported.reduce((sum,r)=>sum+Number(r.reported_detections),0)).toBe(rows.length);
  expect(exported.every(r=>r.daynight_filter==='N' && r.query_end_utc_exclusive==='2017-06-22T00:00:00Z')).toBe(true);
});

test('adaptive rendering and source filtering preserve camera and scientific counts; outside AOI is unavailable', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:45000});
  await page.getByTestId('geographic-map').evaluate(el=>(el as any).scientificMap.jumpTo({center:[-8,40],zoom:11}));
  await expect(page.getByTestId('geographic-map')).toHaveAttribute('data-representation','Reported pixel centers');
  await page.getByTestId('day-2017-06-18').click();
  const camera = await page.getByTestId('geographic-map').evaluate(el=> {const m=(el as any).scientificMap;return [m.getCenter().lng,m.getCenter().lat,m.getZoom()];});
  expect(camera).toEqual([-8,40,11]);
  const before = await page.getByTestId('summary-surface').innerText();
  for(const mode of ['grid','points','auto']) await page.locator('#render-mode').selectOption(mode);
  expect(await page.getByTestId('summary-surface').innerText()).toBe(before);
  await page.getByTestId('geographic-map').evaluate(el=>(el as any).scientificMap.jumpTo({center:[25,30],zoom:9}));
  await expect(page.getByText('Outside supplied extract',{exact:false})).toContainText('not available here');
  expect(await page.getByTestId('summary-surface').innerText()).toBe(before);
});

test('unavailable historical months have no zero totals and exports retain unavailable scope', async ({ page }) => {
  await page.goto('/?month=2016-02');
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('—');
  await expect(page.getByTestId('evidence-records')).toHaveText('Unavailable');
  await expect(page.getByTestId('day-2016-02-29')).toBeAttached();
  await expect(page.getByTestId('day-2016-02-01')).toHaveAttribute('aria-label',/Source extract unavailable/);
  const pending=page.waitForEvent('download'); await page.getByTestId('export').click();
  const rows=parseCsv(readFileSync((await (await pending).path())!,'utf8'));
  expect(rows).toHaveLength(2);
  for(const r of rows){expect(r.reported_detections).toBe('');expect(r.occupied_cell_days).toBe('');expect(r.row_kind).toBe('SOURCE_EXTRACT_UNAVAILABLE');expect(r.query_end_utc_exclusive).toBe('2016-03-01T00:00:00Z');}
});

test('mobile modal focus, Escape, evidence tabs and first-viewport map/calendar are accessible', async ({ page }) => {
  await page.setViewportSize({width:390,height:844}); await page.goto('/');
  await expect(page.getByTestId('investigation')).toBeVisible();
  const evidence = page.getByRole('button',{name:'Evidence Passport',exact:true});
  await evidence.click(); await expect(page.getByRole('dialog',{name:'Evidence Passport'})).toBeVisible();
  const tab = page.getByRole('tab',{name:'selection',exact:true}); await tab.focus(); await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab',{name:'sources',exact:true})).toBeFocused();
  await expect(page.getByRole('tabpanel')).toContainText('Original archive rows and hashes are immutable');
  await page.keyboard.press('End'); await expect(page.getByRole('tab',{name:'history'})).toBeFocused();
  await expect(page.getByRole('tabpanel')).toContainText('Not qualified · not included');
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog',{name:'Evidence Passport'})).not.toBeVisible();
  await expect(evidence).toBeFocused();
  await page.getByRole('button',{name:'Filters',exact:true}).click();
  await page.locator('#daynight').selectOption('D'); await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog',{name:'Investigation filters'})).not.toBeVisible();
  await expect(page.getByTestId('investigation')).toHaveAttribute('data-selection',/DN:D$/);
  await expect(page.getByTestId('calendar-surface')).toBeInViewport();
  const box=await page.getByTestId('geographic-map').boundingBox(); expect(box!.height).toBeGreaterThan(300); expect(box!.y).toBeLessThan(240);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(390);
});

test('blocked provider renders verified coarse geography, while evidence and export stay usable', async ({ page }) => {
  await page.route('https://tiles.openfreemap.org/**',route=>route.abort());
  await page.goto('/');
  await expect(page.getByTestId('investigation')).toBeVisible();
  await expect(page.getByText('Geographic basemap rendered',{exact:true})).toBeVisible({timeout:15000});
  await expect(page.getByTestId('geographic-map')).toHaveAttribute('data-basemap','coarse-context');
  await expect(page.locator('.coarse-context')).toContainText('no street detail or observation QA');
  expect(await page.getByTestId('geographic-map').evaluate(el=>(el as any).scientificMap.queryRenderedFeatures({layers:['offline-land']}).length)).toBeGreaterThan(0);
  for(const [width,height]of [[1440,900],[320,844]]){
    await page.setViewportSize({width,height});
    const status=(await page.locator('.map-status').boundingBox())!,legend=(await page.locator('.map-legend').boundingBox())!,credit=(await page.locator('.maplibregl-ctrl-attrib').boundingBox())!;
    expect(status.y+status.height).toBeLessThanOrEqual(legend.y);expect(legend.y+legend.height).toBeLessThanOrEqual(credit.y);
  }
  await page.getByTestId('day-2017-06-18').click();
  const pending=page.waitForEvent('download');await page.getByTestId('export').click(); expect((await pending).suggestedFilename()).toContain('2017-06-18');
});

test('WebGL failure leaves scientific calendar, table, Passport and export functional', async ({ page }) => {
  await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind:any,...args:any[]){if(String(kind).startsWith('webgl'))return null;return (original as any).call(this,kind,...args); } as any;});
  await page.goto('/');
  await expect(page.getByText('Geographic map unavailable on this device.',{exact:false})).toBeVisible();
  await page.getByTestId('day-2017-06-18').click(); await expect(page.getByTestId('evidence-records')).not.toHaveText('0');
  await page.getByRole('button',{name:'Data table',exact:true}).click(); await expect(page.getByRole('dialog',{name:'Selected native records'})).toBeVisible();
  await page.keyboard.press('Escape');
  const pending=page.waitForEvent('download');await page.getByTestId('export').click();expect((await pending).suggestedFilename()).toContain('2017-06-18');
});

test('Passport separates numerical parity, Type/vintage caveat, swath limits and source credits', async ({ page }) => {
  await page.goto('/'); await expect(page.getByTestId('investigation')).toBeVisible();
  await page.getByRole('button',{name:'Evidence Passport',exact:true}).click();
  await expect(page.locator('.evidence-statuses')).toHaveText(/RECOUNT VERIFIED.*ARCHIVE COMPLETENESS UNKNOWN.*OBSERVATION SUPPORT UNKNOWN.*HARMONIZATION WITHHELD/);
  await page.getByRole('tab',{name:'quality',exact:true}).click();
  await expect(page.getByRole('tabpanel')).toContainText('Swath ≠ cloud-free observation');
  await expect(page.getByRole('tabpanel')).toContainText('monthly versions 1/2');
  await expect(page.getByRole('tabpanel')).toContainText('G4 has not been executed');
  await page.getByRole('tab',{name:'sources',exact:true}).click();
  for(const m of release.manifests) await expect(page.getByRole('tabpanel')).toContainText(m.zip_sha256);
  await expect(page.getByRole('link',{name:'Official FIRMS citation & disclaimer guidance ↗'})).toHaveAttribute('href','https://firms.modaps.eosdis.nasa.gov/download/Readme.txt');
});

