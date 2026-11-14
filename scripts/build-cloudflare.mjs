import {spawnSync} from 'node:child_process';
import {ROOT,restorePublicArtifacts} from './public-artifacts.mjs';
import {verifyRuntime} from './verify-runtime.mjs';

try {
  if(Number(process.versions.node.split('.')[0])!==22)throw Error('Cloudflare release build requires Node.js 22');
  if(process.env.NODE_TLS_REJECT_UNAUTHORIZED==='0')throw Error('TLS verification must remain enabled');
  await verifyRuntime({allowMissingRestorable:true});
  for(const r of await restorePublicArtifacts())console.log(`${r.state}: ${r.path}`);
  await verifyRuntime();
  // Pages may otherwise discover requirements.txt and install research Python.
  // With automatic installation disabled, install only lockfile-pinned JS tools.
  if(['1','true'].includes(process.env.SKIP_DEPENDENCY_INSTALL)) {
    const install=spawnSync(process.execPath,[process.env.npm_execpath,'ci','--include=dev','--no-audit','--no-fund'],{cwd:ROOT,stdio:'inherit'});
    if(install.error||install.status!==0)throw Error('Production dependency installation failed');
  }
  // Invoke the unchanged production script through npm's JS entry; portable on Windows/Linux.
  const r=spawnSync(process.execPath,[process.env.npm_execpath,'run','build'],{cwd:ROOT,stdio:'inherit'});
  if(r.error||r.status!==0)throw Error('Production build failed');
  const result=await verifyRuntime({directory:'dist',report:'reports/cloudflare/dist-resources'});
  console.log(`PASS: complete static release verified (${result.files} pinned runtime/entry assets). No Python or private credentials required.`);
}catch(e){
  // Do not log fetch/certificate stack traces, machine paths or receipt content.
  console.error('Cloudflare build stopped: '+(e.message.startsWith('Runtime')||e.message.startsWith('Required')||e.message.startsWith('Cloudflare')||e.message.startsWith('TLS')?e.message:'restoration, integrity or production check failed. No fallback data used.'));
  process.exitCode=1;
}
