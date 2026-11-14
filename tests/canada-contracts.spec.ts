import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {availability,caProject,caUnproject,era,selectedCells,caSummary,caCsv,concordance,CA_SOURCES,type CaCatalog,type CaChunk,type CaQuery} from '../src/canada';
const read=(p:string)=>JSON.parse(readFileSync(p,'utf8'));
const catalog=()=>read('public'+read('public/data/canada/index.json').file) as CaCatalog;

test('Canada ellipsoidal grid matches independent PROJ fixtures at south, Arctic, dateline and origin',()=>{
 const fixtures=read('reports/CANADA_GRID_VALIDATION.json');
 for(const f of fixtures.checks){const xy=caProject(f.lon,f.lat);expect(Math.hypot(xy[0]-f.x_m,xy[1]-f.y_m)).toBeLessThan(.002);const p=caUnproject(...xy);expect(p[1]).toBeCloseTo(f.lat,7);expect(((p[0]-f.lon+540)%360)-180).toBeCloseTo(0,7);expect(Math.abs(f.area_relative_error)).toBeLessThan(.00002);}
});

test('every published source/product/month reconciles exact D/N multiplicities and union occupied keys',()=>{
 const c=catalog();let total=0;let nonadditive=0;
 for(const scope of c.coverage){const data=read('public'+c.root+scope.file) as CaChunk;const q:CaQuery={month:scope.month,pc:scope.pc,flag:'ALL',sources:[scope.source],area:'canada',day:null,cell:null};const all=caSummary(selectedCells([data],q))[scope.source];expect(all.records).toBe(scope.records);expect(all.cell_days).toBe(scope.cell_days);total+=all.records;
  const d=caSummary(selectedCells([data],{...q,flag:'D'}),'D')[scope.source],n=caSummary(selectedCells([data],{...q,flag:'N'}),'N')[scope.source];expect(d.records+n.records).toBe(all.records);expect(d.cell_days+n.cell_days).toBeGreaterThanOrEqual(all.cell_days);if(d.cell_days+n.cell_days>all.cell_days)nonadditive++;
  expect(d.records).toBe(scope.days.reduce((n,d)=>n+d.D,0));expect(n.records).toBe(scope.days.reduce((n,d)=>n+d.N,0));expect(d.cell_days).toBe(scope.days.reduce((n,d)=>n+d.D_cell_days,0));expect(n.cell_days).toBe(scope.days.reduce((n,d)=>n+d.N_cell_days,0));
 }
 expect(total).toBe(c.oracle.raw_identity_and_projected_5km_keys.keys);expect(nonadditive).toBeGreaterThan(0);
});

test('source era, product delivery, unknown opportunity and export fail closed remain independent',()=>{
 const c=catalog();expect(era('SNPP_VIIRS','2010-06')).toBe('SOURCE_NOT_YET_IN_ERA');expect(era('SNPP_VIIRS','2012-01')).toContain('PARTIAL');expect(era('SNPP_VIIRS','2012-01',19)).toBe('SOURCE_NOT_YET_IN_ERA');expect(era('SNPP_VIIRS','2026-11',3)).toBe('SOURCE_ERA_ENDED');expect(era('SNPP_VIIRS','2026-11')).toContain('1540');expect(availability(c,'SNPP_VIIRS','2011-06','SP')).toBe('SOURCE_NOT_YET_IN_ERA');expect(availability(c,'AQUA_MODIS','2010-06','NRT')).toBe('PERIOD_NOT_REPRESENTED_IN_ACQUIRED_PRODUCT');
 const q:CaQuery={month:'2010-06',pc:'SP',flag:'ALL',sources:['SNPP_VIIRS'],day:null,cell:null,area:'canada'};const csv=caCsv(c,q,[]);expect(csv).toContain('SOURCE_NOT_YET_IN_ERA');expect(csv).toContain('ADJUSTMENT_WITHHELD');expect(csv).not.toContain('VALID_OBSERVATION_WITH_NO_QUALIFIED_DETECTION');
});

test('northern/southern fixed-cell pilot filters reconcile every independent raw-derived year/source/DN case',()=>{
 const c=catalog(),oracle=read('reports/CANADA_PILOT_RECONCILIATION.json');
 for(const f of oracle.cases){const chunks=c.coverage.filter(d=>d.pc==='SP'&&d.month===f.month).map(d=>read('public'+c.root+d.file));const q:CaQuery={month:f.month,pc:'SP',flag:f.flag,sources:[f.source],day:null,cell:null,area:f.area};const measured=caSummary(selectedCells(chunks,q),q.flag)[f.source as keyof ReturnType<typeof caSummary>];expect(measured.records).toBe(f.records);expect(measured.cell_days).toBe(f.cell_days);}
});

test('positive-only concordance is a set union and excludes unselected native D/N days',()=>{
 const c=catalog();const chunks=c.coverage.filter(d=>d.pc==='SP'&&d.month==='2023-06').map(d=>read('public'+c.root+d.file));const q:CaQuery={month:'2023-06',pc:'SP',flag:'N',sources:CA_SOURCES,day:1,cell:null,area:'canada'};const selected=selectedCells(chunks,q);const v=concordance(selected);expect(v.shared+v.modisOnly+v.viirsOnly).toBe(v.union);for(const chunk of selected)for(const cell of chunk.cells)for(const d of cell[2]){expect(d[0]).toBe(1);expect(d[2]).toBeGreaterThan(0);}
 const csv=caCsv(c,q,selected);expect(csv).toContain('OBSERVATION_UNKNOWN');expect(csv).toContain('UNVERIFIED');expect(csv).toContain('no Type filter');
});
