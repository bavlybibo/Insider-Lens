// Only these previously public, immutable receipts may be downloaded by the build.
import {createHash} from 'node:crypto';
import {lstat, mkdir, readFile, realpath, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ORIGIN = 'https://emberguard-evidence-retention.musicalartichoke4.chatgpt.site';
export const ALLOWED = Object.freeze([
  ['public/data/canada/ca-92a935da01aecfa3e1d130b3/catalog.json',1568686,'ecebbb2614b6e60825752210cdc672a29b3e7e6ef956d59057ade4baa4cf1938'],
  ['public/data/phase6/p6-ab874a4a4d03-6e562cb1cbc4/bridge.json',89336,'caa8c20a6c37230f772b0301d3278d4df5c82d62c1be3b9a6ce1f8dc81b222e7'],
  ['public/data/phase6/p6-ab874a4a4d03-8218b6e3ca49/bridge.json',89299,'4d1e61a338923bafb7a28b213fe118e99d4e87c1ed52ba32693cadce60d4675c'],
].map(([file,bytes,sha256])=>Object.freeze({file,bytes,sha256,url:ORIGIN+file.slice(6)})));
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export function validateRestoreManifest(manifest) {
  if (!Array.isArray(manifest.artifacts) || manifest.artifacts.length !== ALLOWED.length ||
      ALLOWED.some((a,i)=>Object.keys(a).some(k=>manifest.artifacts[i]?.[k]!==a[k])))
    throw Error('Public restoration allowlist mismatch');
  return ALLOWED;
}
export function checkBytes(bytes, expected, label='Public artifact') {
  if (bytes.length !== expected.bytes || sha256(bytes) !== expected.sha256)
    throw Error(`${label}: size or SHA-256 mismatch`);
}
// Refuse traversal and symlinks/reparse points; never emit absolute local paths.
export async function safeFile(base, relative) {
  if (!relative || relative.includes('\\') || relative.split('/').some(p=>!p||p==='.'||p==='..') ||
      relative.includes(':') || path.isAbsolute(relative)) throw Error('Unsafe runtime path');
  const root=await realpath(base);
  let current=root;
  for (const part of relative.split('/')) {
    current=path.join(current,part);
    try { if ((await lstat(current)).isSymbolicLink()) throw Error('Runtime symlink refused'); }
    catch (e) { if(e.code!=='ENOENT') throw e; }
  }
  return current;
}
export async function downloadPinned(artifact, fetchImpl=fetch) {
  if(!ALLOWED.some(a=>a.url===artifact.url))throw Error('Untrusted public artifact URL');
  // Built-in fetch verifies TLS. Redirects are forbidden, including login pages.
  const r=await fetchImpl(artifact.url,{redirect:'error',signal:AbortSignal.timeout(60_000),
    headers:{'User-Agent':'Insider-Lens-public-artifact-restore/1.0','Accept':'application/json'}});
  if (!r.ok) throw Error(`Public artifact download failed: HTTP ${r.status}`);
  const chunks=[];let size=0;
  for await (const chunk of r.body) {
    size+=chunk.length;
    if(size>artifact.bytes) throw Error('Public artifact exceeds pinned size');
    chunks.push(chunk);
  }
  const bytes=Buffer.concat(chunks);checkBytes(bytes,artifact);
  return bytes;
}
export async function restorePublicArtifacts(root=ROOT,fetchImpl=fetch) {
  const manifest=JSON.parse(await readFile(path.join(root,'docs/PUBLIC_ARTIFACT_RESTORE.json'),'utf8'));
  const allowed=validateRestoreManifest(manifest),result=[];
  for (const artifact of allowed) {
    const target=await safeFile(root,artifact.file);
    let bytes;
    try { bytes=await readFile(target); } catch(e) { if(e.code!=='ENOENT')throw e; }
    if(bytes) { checkBytes(bytes,artifact);result.push({path:artifact.file,state:'verified-existing'});continue; }
    bytes=await downloadPinned(artifact,fetchImpl);
    await mkdir(path.dirname(target),{recursive:true});
    await safeFile(root,artifact.file);
    await writeFile(target,bytes,{flag:'wx'}); // Never overwrite an existing receipt.
    result.push({path:artifact.file,state:'restored-and-verified'});
  }
  return result;
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  restorePublicArtifacts().then(r=>console.log(JSON.stringify(r,null,2))).catch(()=>{
    console.error('Public artifact restoration failed; build stopped. No fallback data used.');process.exitCode=1;
  });
}
