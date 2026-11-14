import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,mkdir,readFile,rm,symlink} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {ALLOWED,ROOT,sha256,checkBytes,validateRestoreManifest,downloadPinned,restorePublicArtifacts,safeFile} from '../scripts/public-artifacts.mjs';
import {dependencyGraph,verifyRuntime} from '../scripts/verify-runtime.mjs';

test('restore manifest is exactly the three public pinned receipts',async()=>{
  const m=JSON.parse(await readFile(path.join(ROOT,'docs/PUBLIC_ARTIFACT_RESTORE.json'),'utf8'));
  assert.deepEqual(validateRestoreManifest(m),ALLOWED);
  for(const key of ['file','url','bytes','sha256']){const bad=structuredClone(m);bad.artifacts[0][key]='untrusted';assert.throws(()=>validateRestoreManifest(bad),/allowlist/);}
  assert.throws(()=>validateRestoreManifest({artifacts:[...m.artifacts,m.artifacts[0]]}),/allowlist/);
});
test('download enforces TLS origin policy, redirect refusal and bytes before writing',async()=>{
  const bytes=Buffer.from('{"real":"fixture"}'),a={bytes:bytes.length,sha256:sha256(bytes),url:ALLOWED[0].url};
  const good=async(url,options)=>{assert.equal(url,a.url);assert.equal(options.redirect,'error');assert(options.signal);assert(options.headers['User-Agent'].startsWith('Insider-Lens'));return new Response(bytes);};
  assert.deepEqual(await downloadPinned(a,good),bytes);
  for(const response of [()=>new Response('missing',{status:404}),()=>new Response('login',{status:403}),()=>new Response('x'.repeat(bytes.length+1)),()=>new Response('x'.repeat(bytes.length)),()=>new Response(bytes.subarray(1))])
    await assert.rejects(()=>downloadPinned(a,async()=>response()));
  await assert.rejects(()=>downloadPinned(a,async()=>{throw Error('network unavailable');}));
  await assert.rejects(()=>downloadPinned({...a,url:'http://untrusted.test/receipt.json'},good),/Untrusted/);
  assert.throws(()=>checkBytes(bytes,{...a,sha256:'0'.repeat(64)}),/mismatch/);
});
test('restoration refuses to overwrite existing corrupt science and never fetches private files',async()=>{
  const dir=await mkdtemp(path.join(os.tmpdir(),'insider-lens-restore-'));
  try{
    await mkdir(path.join(dir,'docs'));await writeFile(path.join(dir,'docs/PUBLIC_ARTIFACT_RESTORE.json'),JSON.stringify({artifacts:ALLOWED}));
    const file=await safeFile(dir,ALLOWED[0].file);await mkdir(path.dirname(file),{recursive:true});await writeFile(file,'bad');
    let fetched=false;await assert.rejects(()=>restorePublicArtifacts(dir,async()=>{fetched=true;throw Error();}),/mismatch/);
    assert.equal(fetched,false);assert.equal(await readFile(file,'utf8'),'bad');
    for(const unsafe of ['../token.txt','/private','data/../../private','data\\private','C:/private','data//private'])await assert.rejects(()=>safeFile(dir,unsafe),/Unsafe/);
    await symlink(path.join(dir,'docs'),path.join(dir,'linked'),'junction');await assert.rejects(()=>safeFile(dir,'linked/secret'),/symlink/);
  }finally{assert(path.resolve(dir).startsWith(path.resolve(os.tmpdir())+path.sep+'insider-lens-restore-'));await rm(dir,{recursive:true,force:true});}
});
test('dependency crawl checks pointers, complete coverage, artifacts and independent receipts',()=>{
  const spec={bytes:1,sha256:'abc'},inv={'/data/index.json':spec,'/data/catalog.json':spec,'/data/chunk.json':spec,'/data/oracle.json':spec,'/data/phase11/NASA_SUPPORT_DRAFT.md':spec};
  const docs={'/data/index.json':{file:'/data/catalog.json',sha256:'abc',oracle_file:'/data/oracle.json',oracle_sha256:'abc'},'/data/catalog.json':{root:'/data/',coverage:[{file:'chunk.json',...spec}],artifacts:{'oracle.json':spec}}};
  assert(dependencyGraph(docs,inv).get('/data/chunk.json').has('/data/catalog.json'));
  for(const field of ['file','sha256','bytes']){const bad=structuredClone(docs);bad['/data/catalog.json'].coverage[0][field]='wrong';assert.throws(()=>dependencyGraph(bad,inv));}
  const bad=structuredClone(docs);bad['/data/index.json'].file='C:/private/catalog.json';assert.throws(()=>dependencyGraph(bad,inv));
});
test('all preserved public science files match the committed runtime manifest',async()=>{
  const r=await verifyRuntime();assert.equal(r.files,787);assert.equal(r.missing.length,0);
  assert(r.resources.find(r=>r.path.endsWith('/catalog.json')&&r.path.includes('/canada/')).required_by.includes('/data/canada/index.json'));
});
