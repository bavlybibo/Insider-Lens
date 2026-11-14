import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {evidenceFinding} from '../src/evidenceFinding';
import {CA_SOURCES,selectedCells,type CaCatalog,type CaQuery,type CaChunk} from '../src/canada';
import {positiveKeys} from '../src/evidenceRetention';
const read=(p:string)=>JSON.parse(readFileSync(p,'utf8'));
const c=read('public'+read('public/data/canada/index.json').file) as CaCatalog;
const fixture=read('reports/phase12/PARTITION.json');
const base:CaQuery={area:'south',month:'2023-06',pc:'SP',flag:'ALL',sources:CA_SOURCES,cell:null,day:null};
const getKeys=(q:CaQuery)=>positiveKeys(selectedCells(c.coverage.filter(e=>e.month===q.month&&e.pc===q.pc).map(e=>read('public'+c.root+e.file) as CaChunk),{...q,sources:CA_SOURCES}),q.flag);

test('judge finding matches all 12 independently accepted scopes and native filters',()=>{
 for(const v of fixture.cases){const q:CaQuery={...base,month:v.month,flag:v.flag,area:v.id==='overlap'?'south':'canada',rect:v.rect??undefined};const keys=getKeys(q);expect(keys.map(k=>[k.i,k.j,k.date,...k.records,k.group])).toEqual(v.rows);const a=evidenceFinding(c,q,keys,true);expect(a.scope).toContain(v.rect?'rectangle':v.id==='overlap'?'Southern':'Canada');expect(a.period).toBe(v.month);expect(a.flag).toBe(v.flag);expect(a.referenceKeys).toBe(v.rows.length);expect(a.copy).not.toMatch(/C:\\|Users\\|eyJ/);expect(a.copy).toContain('ADJUSTMENT_WITHHELD');if(v.rows.length){expect(a.retainedRecords).toBe(v.records.reduce((x:number,y:number)=>x+y,0));}else{expect(a.state).toBe('UNKNOWN');expect(a.retainedRecords).toBeNull();}}
});
test('source policies retain exact keys, source records and unavailable-era semantics',()=>{
 const keys=getKeys(base);const m=evidenceFinding(c,{...base,sources:CA_SOURCES.slice(0,2)},keys,true),v=evidenceFinding(c,{...base,sources:['SNPP_VIIRS']},keys,true);expect(m.finding).toContain('excludes 335 reference keys');expect(m.retainedRecords).toBe(2139);expect(v.finding).toContain('excludes 34 reference keys');expect(v.retainedRecords).toBe(8385);
 const before={...base,area:'canada' as const,month:'2010-06',sources:['SNPP_VIIRS'] as CaQuery['sources']};const a=evidenceFinding(c,before,getKeys(before),true);expect(a.state).toBe('ERA_UNAVAILABLE');expect(a.finding).toContain('2,113 other-native positive keys');expect(a.retainedRecords).toBeNull();expect(a.finding).not.toContain('0 source records');
});
test('unknown, unacquired and withheld findings never reuse stale numeric answers',()=>{
 const keys=getKeys(base);for(const ready of [false]){const a=evidenceFinding(c,{...base,month:'2022-06'},keys,ready,'load pending');expect(a.state).toBe('UNKNOWN');expect(a.finding).not.toContain('568');expect(a.retainedRecords).toBeNull();}
 const missing={...base,month:'2026-11'};expect(evidenceFinding(c,missing,[],true).state).toBe('NOT_ACQUIRED');expect(evidenceFinding(c,{...base,month:'2024-06'},[],false).state).toBe('WITHHELD');
});
for(const [width,height] of [[1440,900],[1920,1080]])test(`desktop judge ${width}: scope, policy, copy and selected evidence remain synchronized`,async({page})=>{
 await page.setViewportSize({width,height});await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async(text:string)=>{(window as any).__copiedFinding=text;}}}));
 await page.goto('/?region=canada&view=retention');const finding=page.getByTestId('desktop-evidence-finding'),card=page.getByTestId('retention-map-answer');await expect(finding).toHaveAttribute('data-state','NATIVE_POSITIVES');await expect(finding).toContainText('Southern Canada study tract');await expect(finding).toContainText('34 MODIS-only + 199 shared + 335 VIIRS-only = 568');
 await finding.locator('summary').click();await expect(finding).toContainText('W/S/E/N -120, 49, -110, 55');expect((await card.boundingBox())!.height).toBeLessThan((await page.getByTestId('canada-map').boundingBox())!.height-70);await finding.locator('summary').click();
 await card.getByRole('button',{name:'MODIS only',exact:true}).click();await expect(finding).toContainText('excludes 335 reference keys');await page.getByRole('button',{name:'Copy current scientific finding'}).click();expect(await page.evaluate(()=>(window as any).__copiedFinding)).toContain('2,139 source records');expect(await page.evaluate(()=>(window as any).__copiedFinding)).toContain(c.candidate);
 await page.getByRole('button',{name:'Cells, dates & evidence',exact:true}).click();await page.locator('#retention-cell-list').selectOption('ca-laea60n100w-wgs84-o0-v1:10000:-108:-64');await expect(finding).toContainText('cell -108:-64');await expect(finding).toContainText('92 source records');await page.getByRole('button',{name:'Close Evidence Retention · cells and dates',exact:true}).click();
 await page.getByRole('button',{name:'Clear cell/date',exact:true}).click();await page.getByRole('button',{name:'1 · Before VIIRS',exact:true}).click();await expect(finding).toHaveAttribute('data-state','ERA_UNAVAILABLE');await card.getByRole('button',{name:'Both native',exact:true}).click();await expect(finding).toContainText('12,744 source records');await expect(finding).toContainText('Not yet in era');await card.getByRole('button',{name:'VIIRS only',exact:true}).click();await expect(finding).toHaveAttribute('data-state','ERA_UNAVAILABLE');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);const map=await page.getByTestId('canada-map').boundingBox(),box=await card.boundingBox();expect(map!.width*map!.height/(width*height)).toBeGreaterThan(.7);expect(box!.height).toBeLessThan(map!.height-70);
});
test('desktop finding follows UTC day, native D/N and processing changes',async({page})=>{
 await page.goto('/?region=canada&view=retention');const finding=page.getByTestId('desktop-evidence-finding');await expect(finding).toHaveAttribute('data-state','NATIVE_POSITIVES');await page.getByRole('button',{name:'Night',exact:true}).click();await expect(finding).toContainText('Night N');await page.getByRole('button',{name:/^2023-06-13 UTC retention:/}).click();await expect(finding).toContainText('2023-06-13 UTC');const q=JSON.parse((await page.getByTestId('canada-investigation').getAttribute('data-selection'))!);expect((await finding.innerText())).toContain(evidenceFinding(c,q,getKeys(q),true).finding);
 await page.locator('#ca-year').selectOption('2026');await page.locator('#ca-month').selectOption('11');await expect(finding).toHaveAttribute('data-state','NOT_ACQUIRED');await expect(finding).toContainText('NOT ACQUIRED');
});
test('existing narrow layout keeps its prior card and excludes desktop-only controls',async({page})=>{
 await page.setViewportSize({width:390,height:900});await page.goto('/?region=canada&view=retention');await expect(page.locator('[data-retention-ready=true]')).toBeVisible();await expect(page.getByTestId('desktop-evidence-finding')).toHaveCount(0);expect((await page.getByTestId('retention-map-answer').boundingBox())!.height).toBeLessThan(160);expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(390);
});
