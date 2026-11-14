import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { occupiedRows, queryBounds, scientificCsv, select, selectionId, summarize, type Release } from '../src/science';
import { readSelection, selectionSearch } from '../src/selection';
import { deliveryRegime, observationSupport } from '../src/evidence';
const release: Release = JSON.parse(readFileSync('public/data/release.json', 'utf8'));

test('native totals and reference cell obey source/cell/UTC set semantics', () => {
  const fixtures = { AQUA_MODIS: [238,32,57,4], TERRA_MODIS: [172,24,45,3], SNPP_VIIRS: [2041,65,484,4] };
  for (const [source, numbers] of Object.entries(fixtures)) {
    const rows = release.records.filter(r => r.source === source);
    expect([summarize(rows).records, summarize(rows).occupied_cell_days]).toEqual(numbers.slice(0,2));
    const cell = rows.filter(r => r.cell === 'g:-2:-1');
    expect([cell.length, occupiedRows(cell).length]).toEqual(numbers.slice(2));
  }
});

test('URL state validates dates, rejects unqualified platforms and round-trips all scientific filters', () => {
  const value = readSelection('?month=2017-06&sources=AQUA_MODIS,SNPP_VIIRS&cell=g:-2:-1&day=2017-06-21&dn=N', release);
  expect(readSelection(selectionSearch(value), release)).toEqual(value);
  expect(readSelection('?month=2017-02&day=2017-02-30&cell=g:999:999&dn=cloudfree&sources=NOAA20', release)).toMatchObject({ month:'2017-02', day:null, cell:null, daynight:'ALL', sources:['AQUA_MODIS','SNPP_VIIRS'] });
  expect(readSelection('?month=garbage&day=2017-07-01', release)).toMatchObject({ month:'2017-06', day:null });
});

test('daynight changes identity and CSV UTC scope, without changing immutable release', () => {
  const selection = readSelection('?month=2017-06&sources=AQUA_MODIS,SNPP_VIIRS&dn=N&day=2017-06-21&cell=g:-2:-1', release);
  const rows = select(release.records, selection);
  expect(rows.length).toBeGreaterThan(0);
  expect(rows.every(r => r.daynight === 'N' && r.day === '2017-06-21' && r.cell === 'g:-2:-1')).toBe(true);
  expect(selectionId(release.releaseId, selection)).not.toBe(selectionId(release.releaseId, {...selection,daynight:'ALL'}));
  expect(queryBounds(selection)).toEqual({ start:'2017-06-21T00:00:00Z',end:'2017-06-22T00:00:00Z' });
  const csv = scientificCsv(release, selection, rows);
  expect(csv).toContain('"daynight_filter"'); expect(csv).toContain('"N","2","NASA FIRMS');
  expect(csv).toContain(release.manifests[0].csv_sha256);
  expect(release.records).toHaveLength(2451);
});

test('missing months export null quantities and explicit unavailability; leap-month UTC bounds are correct', () => {
  const selection = readSelection('?month=2016-02', release);
  expect(queryBounds(selection)).toEqual({start:'2016-02-01T00:00:00Z',end:'2016-03-01T00:00:00Z'});
  const rows = select(release.records, selection); expect(rows).toEqual([]);
  const csv = scientificCsv(release,selection,rows);
  expect(csv.match(/SOURCE_EXTRACT_UNAVAILABLE/g)).toHaveLength(2);
  expect(csv).not.toContain('OCCUPIED_CELL_DAY'); expect(csv).not.toContain('OBSERVED_NO_DETECTION');
  expect(csv).toContain('"","","OBSERVATION_UNKNOWN"');
});

test('swath geometry, file presence and QA flags cannot independently create valid opportunity', () => {
  for (const evidence of [{}, {swath:true}, {swath:true,mask:true}, {mask:true,qa:true,geolocation:true}]) {
    expect(observationSupport(evidence)).toBe('OBSERVATION_UNKNOWN');
  }
  expect(observationSupport({mask:true,qa:true,geolocation:true,qualified:true})).toBe('SUPPORT_PRODUCT_REQUIRES_SCOPE_REVIEW');
  expect(release.policy.adjustment).toBe('ADJUSTMENT_WITHHELD');
});

test('historical S-NPP is retained and NOAA platforms cannot silently continue its lane', () => {
  expect(deliveryRegime('SNPP','2017-06-18')).toBe('HISTORICAL_PLATFORM_RECORD_NOT_A_COVERAGE_GUARANTEE');
  expect(deliveryRegime('SNPP','2026-11-03')).toBe('NEW_DELIVERY_ENDED_HISTORICAL_ARCHIVE_REMAINS');
  expect(deliveryRegime('SNPP','2026-11')).toBe('PERIOD_SPANS_DELIVERY_TRANSITION');
  expect(deliveryRegime('SNPP','2026-11-02')).toBe('PERIOD_SPANS_DELIVERY_TRANSITION');
  expect(deliveryRegime('SNPP','2026-11-02T15:39:59Z')).toBe('HISTORICAL_PLATFORM_RECORD_NOT_A_COVERAGE_GUARANTEE');
  expect(deliveryRegime('SNPP','2026-11-02T15:40:00Z')).toBe('NEW_DELIVERY_ENDED_HISTORICAL_ARCHIVE_REMAINS');
  for (const source of ['NOAA20','NOAA21']) expect(deliveryRegime(source,'2026-11-13')).toBe('NEW_REGIME_NOT_QUALIFIED');
  expect(Object.keys(release.sources).sort()).toEqual(['AQUA_MODIS','SNPP_VIIRS','TERRA_MODIS']);
});
