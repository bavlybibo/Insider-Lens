import {test,expect} from '@playwright/test';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const manifest=JSON.parse(readFileSync('docs/PUBLIC_RUNTIME_MANIFEST.json','utf8'));
const parse=(s:string)=>{const lines=s.trim().split('\r\n').filter(l=>!l.startsWith('#')).map(l=>[...l.matchAll(/"((?:[^"]|"")*)"/g)].map(m=>m[1].replaceAll('""','"'))),h=lines.shift()!;return lines.map(r=>Object.fromEntries(h.map((k,i)=>[k,r[i]])));};

test('anonymous static Canada journeys use only same-origin hash-verified scientific JSON',async({page,baseURL})=>{
 test.setTimeout(120_000);
 const origin=new URL(baseURL!).origin,requests:{path:string;status:number;hash:string;bytes:number}[]=[],errors:string[]=[],failures:string[]=[],pending:Promise<void>[]=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{const u=new URL(r.url());if(u.pathname.startsWith('/data/')&&u.origin!==origin)failures.push('external scientific origin');if(u.protocol==='file:')failures.push('private file request');});
 page.on('response',r=>{const u=new URL(r.url());if(u.origin!==origin||!u.pathname.startsWith('/data/'))return;pending.push((async()=>{const b=await r.body(),hash=createHash('sha256').update(b).digest('hex'),a=manifest.files[u.pathname];requests.push({path:u.pathname,status:r.status(),hash,bytes:b.length});if(r.status()!==200||!a||a.bytes!==b.length||a.sha256!==hash)failures.push('scientific response mismatch: '+u.pathname);})().catch(()=>{failures.push('unreadable scientific response: '+u.pathname);}));});
 const start=Date.now();await page.goto('/?region=canada&view=retention');
 const app=page.getByTestId('canada-investigation'),card=page.getByTestId('retention-map-answer');await expect(app).toHaveAttribute('data-retention-ready','true');const answer_ms=Date.now()-start;
 for(const [g,n] of [['MODIS_ONLY','34'],['SHARED','199'],['VIIRS_ONLY','335']])await expect(card.locator(`[data-group=${g}] b`)).toHaveText(n);
 await expect(card).toContainText('10,524 retained records · 28 dates');
 await page.waitForFunction(()=>{const m=(document.querySelector('[data-testid=canada-map]') as any)?.scientificMap;return m?.getLayer('eg-retention-grid')&&m.queryRenderedFeatures({layers:['eg-retention-grid']}).length>0&&m.queryRenderedFeatures().some((f:any)=>!String(f.source).startsWith('eg-'));});
 const geography_ms=Date.now()-start;
 const out=process.env.INSIDER_LENS_CAPTURE_DIR??'reports/cloudflare/preview';mkdirSync(out,{recursive:true});
 await page.screenshot({path:out+'/retention-1440.png'});
 const exported=async(name='Export Evidence Retention keys CSV')=>{const event=page.waitForEvent('download');await page.getByRole('button',{name,exact:true}).click();return parse(readFileSync((await(await event).path())!,'utf8'));};
 let rows=await exported();expect(rows).toHaveLength(568);expect(rows.filter(r=>r.positive_key_group==='MODIS_ONLY')).toHaveLength(34);expect(rows.filter(r=>r.positive_key_group==='SHARED')).toHaveLength(199);expect(rows.filter(r=>r.positive_key_group==='VIIRS_ONLY')).toHaveLength(335);
 const policies=[];
 for(const [name,records,keys] of [['MODIS only',2139,233],['VIIRS only',8385,534],['Both native',10524,568]] as const){const t=Date.now();await card.getByRole('button',{name,exact:true}).click();await expect(card).toContainText(records.toLocaleString('en-US')+' retained records');const policy_ms=Date.now()-t,r=await exported();expect(r.filter(r=>r.checked_sources_retains_key==='true')).toHaveLength(keys);expect(r.reduce((n,r)=>n+Number(r.checked_sources_retained_records),0)).toBe(records);policies.push({name,records,keys,policy_ms});}
 await page.getByRole('button',{name:'1 · Before VIIRS',exact:true}).click();await expect(card).toContainText('12,744 records / 2113 keys / 30 dates excluded');await expect(card).toContainText('S-NPP not yet in era');rows=await exported();expect(rows).toHaveLength(2113);expect(rows.every(r=>r.source_evidence_states.includes('SOURCE_NOT_YET_IN_ERA'))).toBe(true);
 await card.getByRole('button',{name:'Both native',exact:true}).click();await expect(card).toContainText('12,744 retained records · 30 dates');await page.screenshot({path:out+'/history-2010.png'});
 await page.getByRole('button',{name:'2 · Overlap era',exact:true}).click();await expect(card).toContainText('10,524 retained records');
 await page.getByRole('button',{name:/^2023-06-07 UTC retention:/}).click();rows=await exported();expect(rows.every(r=>r.utc_day==='2023-06-07')).toBe(true);await page.getByRole('button',{name:'Clear cell/date',exact:true}).click();
 await page.getByRole('button',{name:'Canada Evidence Passport',exact:true}).click();await expect(page.getByTestId('canada-passport')).toContainText('8,355,817');await expect(page.getByTestId('canada-passport')).toContainText('independent human scientific review is not performed');await page.getByRole('button',{name:'Close Canada Evidence Passport',exact:true}).click();
 await page.setViewportSize({width:1920,height:1080});await page.screenshot({path:out+'/retention-1920.png'});expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(1920);
 await page.goto('/?region=canada&lab=1&study=phase10');await expect(app).toHaveAttribute('data-triangle-selection','F01');await expect(app).toHaveAttribute('data-investigation-scope','2023-06-13-L2-experiment');await expect(page.getByRole('region',{name:'Canada UTC historical calendar',exact:true})).not.toBeVisible();await page.getByRole('button',{name:'Evidence & result',exact:true}).click();await expect(page.getByTestId('qualification-passport')).toContainText('All 16 remain UNKNOWN_SUPPORT');
 await page.screenshot({path:out+'/bridge.png'});const bridge=await exported('Export selected triangular evidence CSV');expect(bridge).toHaveLength(3);expect(bridge.every(r=>r.g4==='ADJUSTMENT_WITHHELD'&&r.physical_shared_support==='UNKNOWN')).toBe(true);
 await Promise.all(pending);expect(errors).toEqual([]);expect(failures).toEqual([]);
 const heap=await page.evaluate(()=>(performance as any).memory?.usedJSHeapSize??null);
 writeFileSync(out+'/browser-evidence.json',JSON.stringify({origin,anonymous:true,serviceWorkers:'blocked',answer_ms,geography_ms,policies,heap_snapshot_bytes:heap,errors,failures,science_requests:requests},null,2)+'\n');
});
