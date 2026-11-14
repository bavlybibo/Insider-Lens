import type { FeatureCollection, Polygon } from 'geojson';

export type SourceId = 'AQUA_MODIS' | 'TERRA_MODIS' | 'SNPP_VIIRS';
export const SOURCES: SourceId[] = ['AQUA_MODIS', 'SNPP_VIIRS', 'TERRA_MODIS'];
export interface Detection {
  id: string; row: number; request: string; source: SourceId; longitude: number; latitude: number;
  utc: string; day: string; cell: string; confidence: string; version: string; frp: number;
  daynight: string; type: string; scan: number; track: number; brightness: number; brightness2: number;
  nativeInstrument: string; nativeSatellite: string;
}
export interface Summary { records: number; occupied_cell_days: number; detection_days: number; occupied_cells: number }
export interface Manifest {
  filename: string; request_id: string; zip_sha256: string; csv_sha256: string; csv_name: string;
  zip_bytes: number; csv_bytes: number; rows: number; accepted: number; excluded: number; exact_duplicates: number;
  categories: Record<string, Record<string, number>>; missing: Record<string, number>; diagnostics: Record<string, number>;
  numeric_ranges: Record<string, { min: number; max: number }>;
  observed_utc: { first: string; last: string }; collection: string; monthly_production_version: string;
}
export interface Release {
  schemaVersion: number; releaseId: string; records: Detection[]; months: string[];
  sources: Record<SourceId, { name: string; color: string; archive: string; platform: string }>;
  summary: Record<SourceId, Summary>; manifests: Manifest[];
  cells: FeatureCollection<Polygon, { cell: string }>;
  verification: { state: string; occupied_key_sha256: string; method: string; independent_human_review: string };
  policy: { crs: string; cell_width_m: number; id: string; case: string; observation_support: string; adjustment: string; aoi: number[]; extract_completeness: string };
}
export interface Selection { sources: SourceId[]; day: string | null; cell: string | null; month?: string; daynight?: 'ALL' | 'D' | 'N' }
export function selectedMonth(selection: Selection) { return selection.month ?? selection.day?.slice(0, 7) ?? '2017-06'; }
export function queryBounds(selection: Selection) {
  const month = selectedMonth(selection);
  const start = `${selection.day ?? `${month}-01`}T00:00:00Z`;
  const date = new Date(start);
  const end = selection.day ? new Date(date.getTime() + 86_400_000) : new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1));
  return { start, end: end.toISOString().replace('.000Z', 'Z') };
}
export function selectionId(releaseId: string, selection: Selection) {
  return `${releaseId}|${[...selection.sources].sort().join('+')}|${selection.day ?? selectedMonth(selection)}|${selection.cell ?? 'AOI'}|DN:${selection.daynight ?? 'ALL'}`;
}
export function select(records: Detection[], selection: Selection) {
  return records.filter(r => selection.sources.includes(r.source) && r.day.startsWith(selectedMonth(selection)) &&
    (!selection.day || r.day === selection.day) && (!selection.cell || r.cell === selection.cell) &&
    (!selection.daynight || selection.daynight === 'ALL' || r.daynight === selection.daynight));
}
export function summarize(records: Detection[]): Summary {
  return { records: records.length, occupied_cell_days: new Set(records.map(r => `${r.source}|${r.day}|${r.cell}`)).size,
    detection_days: new Set(records.map(r => r.day)).size, occupied_cells: new Set(records.map(r => r.cell)).size };
}
export function occupiedRows(records: Detection[]) {
  const grouped = new Map<string, { source: SourceId; day: string; cell: string; records: number }>();
  for (const r of records) {
    const key = `${r.source}|${r.day}|${r.cell}`;
    const row = grouped.get(key) ?? { source: r.source, day: r.day, cell: r.cell, records: 0 };
    row.records += 1; grouped.set(key, row);
  }
  return [...grouped.values()].sort((a, b) => `${a.source}|${a.day}|${a.cell}`.localeCompare(`${b.source}|${b.day}|${b.cell}`));
}
export function scientificCsv(release: Release, selection: Selection, records: Detection[]): string {
  const id = selectionId(release.releaseId, selection);
  const { start, end } = queryBounds(selection);
  const available = release.months.includes(selectedMonth(selection));
  const headers = ['release_id', 'selection_id', 'source', 'utc_day', 'cell_id', 'occupied_cell_days', 'reported_detections', 'observation_support', 'extract_completeness', 'adjustment_status', 'source_csv_sha256', 'grid', 'confidence_policy', 'type_policy', 'row_kind', 'unit', 'query_start_utc_inclusive', 'query_end_utc_exclusive', 'aoi_bbox_wsen', 'cell_width_m', 'request_id', 'source_zip_sha256', 'native_version', 'production_vintage', 'uncertainty', 'daynight_filter', 'selection_schema', 'source_credit'];
  const occupied = occupiedRows(records);
  const exportRows: { source: SourceId; day: string; cell: string; records: number; occupied: number | ''; kind: string }[] = occupied.map(r => ({ ...r, occupied: 1, kind: 'OCCUPIED_CELL_DAY' }));
  // Preserve query metadata for selected lanes with no records. Blank occupancy is
  // deliberately distinct from an observed zero under unknown opportunity.
  for (const source of selection.sources) if (!records.some(r => r.source === source)) exportRows.push({ source,
    day: selection.day ?? '', cell: selection.cell ?? '', records: 0, occupied: '', kind: available ? 'NO_RECORDS_IN_EXTRACT_SUPPORT_UNKNOWN' : 'SOURCE_EXTRACT_UNAVAILABLE' });
  const rows = exportRows.map(r => {
    const manifest = release.manifests[r.source === 'SNPP_VIIRS' ? 1 : 0];
    return [release.releaseId, id, r.source, r.day, r.cell, r.occupied, available ? r.records : '',
      'OBSERVATION_UNKNOWN', 'UNKNOWN', 'ADJUSTMENT_WITHHELD', manifest.csv_sha256,
      release.policy.crs, 'all valid native classes', 'no Type filter; production vintage unverified',
      r.kind, 'occupied_cell_day', start, end, JSON.stringify(release.policy.aoi), release.policy.cell_width_m,
      manifest.request_id, manifest.zip_sha256, Object.keys(manifest.categories.version).join(';'), 'UNVERIFIED', 'NOT_QUANTIFIED',
      selection.daynight ?? 'ALL', '2', 'NASA FIRMS / University of Maryland standard archive; source lineage caveats retained'];
  });
  const quote = (v: unknown) => `"${String(v).replaceAll('"', '""')}"`;
  return [headers, ...rows].map(row => row.map(quote).join(',')).join('\r\n') + '\r\n';
}

export async function loadRelease(signal: AbortSignal): Promise<Release> {
  const catalogResponse = await fetch('/data/catalog.json', { signal, cache: 'no-cache' });
  if (!catalogResponse.ok) throw new Error('Release catalog is unavailable.');
  const catalog: { file: string; sha256: string; releaseId: string } = await catalogResponse.json();
  if (!/^eg-[a-f0-9]{24}\.json$/.test(catalog.file)) throw new Error('Invalid release filename.');
  const response = await fetch(`/data/${catalog.file}`, { signal });
  if (!response.ok) throw new Error('The scientific artifact is unavailable.');
  const bytes = await response.arrayBuffer();
  const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2, '0')).join('');
  if (hash !== catalog.sha256) throw new Error('Artifact checksum mismatch. Scientific totals are withheld.');
  const release: Release = JSON.parse(new TextDecoder().decode(bytes));
  if (release.schemaVersion !== 1 || release.releaseId !== catalog.releaseId || release.verification.state !== 'PASS') throw new Error('The release has not passed numerical reconciliation.');
  for (const source of SOURCES) {
    const measured = summarize(release.records.filter(r => r.source === source));
    for (const key of Object.keys(measured) as (keyof Summary)[]) if (measured[key] !== release.summary[source][key]) throw new Error('Release summary mismatch.');
  }
  return release;
}
