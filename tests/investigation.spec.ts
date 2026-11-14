import { test, expect } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
const release = JSON.parse(readFileSync('public/data/release.json', 'utf8'));
type Raw = { source: string; day: string; cell: string };
const expected = (sources: string[], day?: string) => release.records.filter((r: Raw) => sources.includes(r.source) && (!day || r.day === day));
const occupancy = (rows: Raw[]) => new Set(rows.map(r => `${r.source}|${r.day}|${r.cell}`)).size;

test('real source totals and one identity on every scientific surface', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Evidence Passport',exact:true}).click();
  await expect(page.getByTestId('occupancy-AQUA_MODIS')).toHaveText('32');
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
  await expect(page.getByTestId('occupancy-SNPP_VIIRS')).toHaveText('65');
  await expect(page.getByTestId('records-SNPP_VIIRS')).toHaveText('2,041');
  await expect(page.getByTestId('evidence-records')).toHaveText('2,279');
  const signatures = await page.locator('[data-selection]').evaluateAll(nodes => nodes.map(n => n.getAttribute('data-selection')));
  expect(new Set(signatures).size).toBe(1);
  expect(errors).toEqual([]);
});

test('day and platform selections reconcile and Terra remains a separate lane', async ({ page }) => {
  await page.goto('/'); await expect(page.getByTestId('investigation')).toBeVisible();
  await page.getByTestId('day-2017-06-18').click();
  await page.getByRole('checkbox', { name: 'S-NPP VIIRS', exact: true }).uncheck();
  const rows = expected(['AQUA_MODIS'], '2017-06-18');
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText(rows.length.toLocaleString('en-US'));
  await expect(page.getByTestId('occupancy-AQUA_MODIS')).toHaveText(String(occupancy(rows)));
  await page.getByRole('button', { name: 'Reset date & cell' }).click();
  await page.getByRole('checkbox', { name: 'Terra MODIS', exact: true }).check();
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
  await expect(page.getByTestId('records-TERRA_MODIS')).toHaveText('172');
  await expect(page.getByTestId('occupancy-TERRA_MODIS')).toHaveText('24');
});

test('scientific CSV exports every independently verified occupied key and multiplicity', async ({ page }) => {
  await page.goto('/'); await expect(page.getByTestId('investigation')).toBeVisible();
  const downloadPromise = page.waitForEvent('download'); await page.getByTestId('export').click();
  const download = await downloadPromise; const path = await download.path();
  const text = readFileSync(path!, 'utf8');
  const lines = text.trim().split('\r\n');
  const parse = (line: string) => [...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m => m[1].replaceAll('""', '"'));
  const headers = parse(lines.shift()!); const rows = lines.map(parse).map(values => Object.fromEntries(headers.map((h, i) => [h, values[i]])));
  const originals: Raw[] = expected(['AQUA_MODIS', 'SNPP_VIIRS']);
  const keys = new Map<string, number>();
  originals.forEach(r => { const key = `${r.source}|${r.day}|${r.cell}`; keys.set(key, (keys.get(key) ?? 0) + 1); });
  expect(rows).toHaveLength(97); expect(rows).toHaveLength(keys.size);
  for (const row of rows) {
    expect(row.release_id).toBe(release.releaseId);
    expect(row.selection_id).toBe(await page.getByTestId('investigation').getAttribute('data-selection'));
    expect(Number(row.reported_detections)).toBe(keys.get(`${row.source}|${row.utc_day}|${row.cell_id}`));
    expect(row.occupied_cell_days).toBe('1'); expect(row.observation_support).toBe('OBSERVATION_UNKNOWN');
    expect(row.extract_completeness).toBe('UNKNOWN'); expect(row.adjustment_status).toBe('ADJUSTMENT_WITHHELD');
    expect(row.source_csv_sha256).toHaveLength(64);
    expect(row.source_zip_sha256).toHaveLength(64);
    expect(row.query_start_utc_inclusive).toBe('2017-06-01T00:00:00Z');
    expect(row.query_end_utc_exclusive).toBe('2017-07-01T00:00:00Z');
    expect(row.aoi_bbox_wsen).toBe('[-8.7,39.3,-7.2,40.8]');
  }
  expect(rows.reduce((sum, row) => sum + Number(row.reported_detections), 0)).toBe(2279);
});

test('empty dates remain explicitly unknown rather than observed fire-free', async ({ page }) => {
  await page.goto('/'); await expect(page.getByTestId('investigation')).toBeVisible();
  await page.getByTestId('day-2017-06-01').click();
  await expect(page.getByText('No records match this selection', { exact: false })).toContainText('not an observed fire-free result');
  await expect(page.getByTestId('evidence-records')).toHaveText('0');
  await expect(page.getByTestId('evidence-surface')).toContainText('OBSERVATION SUPPORT UNKNOWN');
});

test('rendered real geography and newest map selection agree', async ({ page }) => {
  await page.goto('/'); await expect(page.getByTestId('investigation')).toBeVisible();
  await expect(page.getByText('Geographic basemap rendered', { exact: true })).toBeVisible({ timeout: 45_000 });
  await page.getByTestId('day-2017-06-18').click();
  await page.getByTestId('day-2017-06-20').click();
  await page.getByTestId('day-2017-06-21').click();
  await expect.poll(async () => page.getByTestId('geographic-map').evaluate(element => {
    const map = (element as any).scientificMap;
    return map?.getSource('eg-points')?.serialize().data.features.length;
  })).toBe(expected(['AQUA_MODIS', 'SNPP_VIIRS'], '2017-06-21').length);
  const geography = await page.getByTestId('geographic-map').evaluate(element => (element as any).scientificMap.queryRenderedFeatures().filter((f: any) => !String(f.source).startsWith('eg-')).length);
  expect(geography).toBeGreaterThan(0);
  await page.getByRole('button', { name: 'All dates', exact: true }).click();
  await expect(page.getByTestId('records-AQUA_MODIS')).toHaveText('238');
  mkdirSync('reports/screenshots', { recursive: true });
  await page.screenshot({ path: 'reports/screenshots/desktop.png', fullPage: true });
});

test('mobile layout and keyboard alternative remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto('/');
  await expect(page.getByTestId('investigation')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip map to activity calendar' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'June 2017', exact: true })).toBeInViewport();
  await page.locator('#cell').selectOption({ index: 1 });
  const signature = await page.getByTestId('investigation').getAttribute('data-selection');
  expect(signature).toContain('|g:');
  await expect(page.getByText('Geographic basemap rendered', { exact: true })).toBeVisible({ timeout: 45_000 });
  mkdirSync('reports/screenshots', { recursive: true });
  await page.screenshot({ path: 'reports/screenshots/mobile.png', fullPage: true });
});

test('artifact corruption withholds results', async ({ page }) => {
  await page.route('**/data/eg-*.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...release, records: [] }) }));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('checksum mismatch');
  await expect(page.getByTestId('investigation')).toHaveCount(0);
});

test('empty exports retain evidence and never invent observed-zero occupancy', async ({ page }) => {
  await page.goto('/'); await expect(page.getByTestId('investigation')).toBeVisible();
  await page.getByTestId('day-2017-06-01').click();
  const downloadPromise = page.waitForEvent('download'); await page.getByTestId('export').click();
  const download = await downloadPromise;
  const lines = readFileSync((await download.path())!, 'utf8').trim().split('\r\n');
  const parse = (line: string) => [...line.matchAll(/"((?:[^"]|"")*)"/g)].map(m => m[1].replaceAll('""', '"'));
  const headers = parse(lines.shift()!); const values = lines.map(parse).map(row => Object.fromEntries(headers.map((h, i) => [h, row[i]])));
  expect(values).toHaveLength(2);
  for (const row of values) {
    expect(row.row_kind).toBe('NO_RECORDS_IN_EXTRACT_SUPPORT_UNKNOWN');
    expect(row.occupied_cell_days).toBe('');
    expect(row.reported_detections).toBe('0');
    expect(row.observation_support).toBe('OBSERVATION_UNKNOWN');
    expect(row.query_start_utc_inclusive).toBe('2017-06-01T00:00:00Z');
    expect(row.query_end_utc_exclusive).toBe('2017-06-02T00:00:00Z');
    expect(row.release_id).toBe(release.releaseId);
  }
});
