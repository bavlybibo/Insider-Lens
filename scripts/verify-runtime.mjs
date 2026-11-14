import {readFile, mkdir, readdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {ALLOWED,ROOT,safeFile,sha256,checkBytes} from './public-artifacts.mjs';

const json=async p=>JSON.parse(await readFile(p,'utf8'));
export function dependencyGraph(documents,inventory) {
  const edges=new Map(Object.keys(inventory).map(p=>[p,new Set(['public runtime inventory'])]));
  const edge=(to,from,hash,bytes)=>{
    if(!/^\/(data|basemap)\/[a-zA-Z0-9_./-]+$/.test(to)||to.includes('..')||!inventory[to])
      throw Error(`Unpublished runtime dependency: ${from}`);
    if((hash&&inventory[to].sha256!==hash)||(bytes!==undefined&&inventory[to].bytes!==bytes))
      throw Error(`Runtime reference binding mismatch: ${from}`);
    edges.get(to).add(from);
  };
  for(const [name,d] of Object.entries(documents)) {
    // Top-level pointer files and their independently checked oracle pointers.
    if(name.endsWith('/index.json')||name==='/data/catalog.json'||name.endsWith('/oracle-index.json')) {
      if(d.file)edge(d.file.startsWith('/')?d.file:path.posix.dirname(name)+'/'+d.file,name,d.sha256,d.bytes);
      if(d.oracle_file)edge(d.oracle_file,name,d.oracle_sha256);
    }
    const base=path.posix.dirname(name)+'/';
    // Artifact tables are explicit deployed dependencies. Provenance archive/member
    // filenames, original local paths and L2 inputs are evidence, NOT fetch URLs.
    for(const [file,a] of Object.entries(d.artifacts??{}))edge(base+file,name,a.sha256,a.bytes);
    if(name.startsWith('/data/phase6/')&&d.evidence_sha256)
      for(const [file,hash] of Object.entries(d.evidence_sha256))edge(base+file,name,hash);
    if(Array.isArray(d.coverage)) {
      if(d.root!==base)throw Error('Canada runtime root mismatch');
      for(const c of d.coverage)edge(d.root+c.file,name,c.sha256,c.bytes);
    }
    if(name==='/basemap/provenance.json')edge('/basemap/iberia-countries.geojson',name,d.derived_sha256,d.derived_bytes);
  }
  // Hardcoded source links outside pointer tables, used by the active Phase11 view.
  edge('/data/phase11/NASA_SUPPORT_DRAFT.md','src/NativeInsights.tsx');
  return edges;
}
export async function verifyRuntime({root=ROOT,directory='public',allowMissingRestorable=false,origin,report}={}) {
  const m=await json(path.join(root,'docs/PUBLIC_RUNTIME_MANIFEST.json'));
  if(m.schema!==1||!m.files||Object.keys(m.files).length<700)throw Error('Runtime manifest invalid');
  const science=await json(path.join(root,'docs/PUBLIC_SCIENCE_SHA256.json'));
  for(const [p,hash] of Object.entries(science))if(p.startsWith('public/')&&m.files[p.slice(6)]?.sha256!==hash)
    throw Error('Runtime manifest differs from sealed science inventory');
  const docs={},rows=[],missing=[];
  for(const [p,a] of Object.entries(m.files)) {
    const f=await safeFile(path.join(root,directory),p.slice(1));
    let b;
    try {b=await readFile(f);}catch(e){if(e.code!=='ENOENT')throw e;missing.push(p);continue;}
    try {checkBytes(b,a);}catch{throw Error(`Runtime integrity mismatch: ${p}`);}
    if(p.endsWith('.json')||p.endsWith('.geojson'))docs[p]=JSON.parse(b.toString('utf8'));
    rows.push({path:p,present:true,size:b.length,hash:sha256(b),http_status:'not requested',required_by:[]});
  }
  if(missing.some(p=>!allowMissingRestorable||!ALLOWED.some(a=>a.file==='public'+p)))throw Error('Required runtime asset missing');
  // Graph is complete only after all three immutable receipts are available.
  const graph=missing.length?null:dependencyGraph(docs,m.files);
  for(const row of rows)row.required_by=[...(graph?.get(row.path)??['public runtime inventory'])];
  if(directory==='dist') {
    const html=await readFile(path.join(root,'dist/index.html'),'utf8');
    if(!html.includes('Insider Lens')||html.includes('/src/'))throw Error('Production entry point invalid');
    const entries=[...html.matchAll(/(?:src|href)="(\/assets\/[^"?#]+)[^"]*"/g)].map(x=>x[1]);
    if(!entries.some(p=>p.endsWith('.js')))throw Error('Built application entry missing');
    for(const p of entries){const b=await readFile(await safeFile(path.join(root,directory),p.slice(1)));rows.push({path:p,present:true,size:b.length,hash:sha256(b),http_status:'not requested',required_by:['dist/index.html']});}
    // Cloudflare asset limits, and no server-side/research payload accidentally copied.
    async function walk(dir){for(const e of await readdir(dir,{withFileTypes:true})){
      const p=path.join(dir,e.name);if(e.isSymbolicLink())throw Error('Dist symlink refused');
      if(e.isDirectory()){await walk(p);continue;}
      const b=await readFile(p),url='/'+path.relative(path.join(root,directory),p).split(path.sep).join('/');
      if(b.length>25*1024*1024||/\.(zip|hdf|h5|sqlite|db|py)$/i.test(e.name))throw Error('Unexpected research/oversize deployment asset');
      if(!rows.some(r=>r.path===url))rows.push({path:url,present:true,size:b.length,hash:sha256(b),http_status:'not requested',required_by:[url.startsWith('/assets/')?'Vite production bundle':'production entry / public inventory']});
    }}
    await walk(path.join(root,directory));
  }
  if(origin) {
    const u=new URL(origin);
    if(u.pathname!=='/'||u.search||u.hash||u.username||u.password||!(u.protocol==='https:'||(u.protocol==='http:'&&['127.0.0.1','localhost'].includes(u.hostname))))throw Error('Untrusted verification origin');
    let next=0;
    await Promise.all(Array.from({length:6},async()=>{while(next<rows.length){const row=rows[next++];try{const r=await fetch(u.origin+row.path,{redirect:'error',signal:AbortSignal.timeout(45_000),headers:{'Cache-Control':'no-cache','User-Agent':'Insider-Lens-runtime-verification/1.0'}});row.http_status=r.status;if(!r.ok)throw Error();const b=Buffer.from(await r.arrayBuffer());if(b.length!==row.size||sha256(b)!==row.hash)throw Error();}catch{row.present=false;}}}));
  }
  const summary={schema:1,directory,origin:origin??null,files:rows.length,bytes:rows.reduce((n,r)=>n+r.size,0),missing,pass:!rows.some(r=>!r.present),resources:rows};
  if(report){await mkdir(path.dirname(report),{recursive:true});await import('node:fs/promises').then(fs=>Promise.all([
    fs.writeFile(report+'.json',JSON.stringify(summary,null,2)+'\n'),
    fs.writeFile(report+'.tsv','PATH\tPRESENT\tSIZE\tHASH\tHTTP STATUS\tREQUIRED BY\n'+rows.map(r=>[r.path,r.present,r.size,r.hash,r.http_status,r.required_by.join('; ')].join('\t')).join('\n')+'\n')
  ]));}
  if(!summary.pass)throw Error('Runtime HTTP verification failed; inspect resource receipt');
  return summary;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  verifyRuntime({directory:process.argv[2]??'dist',origin:process.argv[3],report:process.argv[4]??'reports/cloudflare/runtime'}).then(r=>console.log(`PASS: ${r.files} runtime assets; ${r.bytes} bytes; all hash bindings verified.`)).catch(e=>{console.error(e.message);process.exitCode=1;});
}
