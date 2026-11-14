"""Acquire exact named Aqua inputs and conditionally the frozen replication375 pair."""
import argparse
import datetime as dt
import hashlib
from http.cookiejar import CookieJar
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import Request,build_opener,HTTPCookieProcessor
from phase6_access import SafeRedirect,validate_token
from phase7_contract import ROOT,OUT
from phase7_discovery import immutable,digest

def run(private_file):
    p=Path(private_file).resolve();assert p.is_file() and not p.is_relative_to(ROOT);token=validate_token(p.read_text(encoding='utf-8-sig').strip())
    original=json.loads((OUT/'L2_DOWNLOAD_MANIFEST.json').read_text());controls=json.loads((OUT/'PROVIDER_CONTROLS.json').read_text());c=json.loads((OUT/'SEARCH_CONTRACT.json').read_text())
    receipts=list(original['receipts']);total=original['total_bytes'];op=build_opener(SafeRedirect(),HTTPCookieProcessor(CookieJar()))
    requests=[]
    for r in controls['results']:
        if r['purpose'].startswith('exact named'):
            assert r.get('status')==206 and r.get('hdf4_signature');requests.append({'split':r['split'],'product':'MYD03','url':r['url'],'purpose':'exact named input replaces discovery geolocation only in new audit version'})
    immutable(OUT/'EXACT_ACQUISITION_SCOPE.json',{'parent_scope_sha256':digest(OUT/'ACQUISITION_SCOPE.json'),'requests':requests,
        'conditional_replication375':'after full exact input name/signature/read success, primary40deg view and10min metadata conditions; original stage2 rule unchanged',
        'max_total_payload_bytes':c['budgets']['max_payload_bytes'],'old_artifacts':'all retained; exact-instance audit is a new version'})
    for i in range(4):
        if i==2:
            support=json.loads((OUT/'SUPPORT_AUDIT.json').read_text());v=support['results']['replication'];assert v['midpoint_offset_minutes']<=10
            assert all(x['view_sensitivity']['40']['aoi_centers_within_view']>0 for x in v['products'].values())
            candidate=json.loads((OUT/'REPLICATION_CANDIDATE.json').read_text())['candidate']
            for product in ['VNP14IMG','VNP03IMG']:
                g=candidate['associated'][product][0];requests.append({'split':'replication','product':product,'url':g['data_urls'][0],'purpose':'frozen stage2 after exact lineage and view screen'})
        req=requests[i];url=req['url'];folder=ROOT/'data/acquisition/phase7/exact'/req['split'];folder.mkdir(parents=True,exist_ok=True);target=folder/Path(urlparse(url).path).name;receipt=target.with_suffix(target.suffix+'.receipt.json')
        if target.exists():r=json.loads(receipt.read_text());assert digest(target)==r['sha256'] and r['url']==url
        else:
            assert shutil.disk_usage(ROOT).free>c['budgets']['min_free_disk_reserve_bytes']+200000000
            h=hashlib.sha256();count=0;sig=b'';temp=target.with_suffix(target.suffix+'.part')
            with op.open(Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'EmberGuard-exact-lineage/1.0'}),timeout=45) as response:
                with temp.open('xb') as f:
                    while chunk:=response.read(1024*1024):
                        if not sig:sig=chunk[:8]
                        count+=len(chunk);assert total+count<=c['budgets']['max_payload_bytes'];f.write(chunk);h.update(chunk)
                assert sig.startswith(b'\x0e\x03\x13\x01') or sig==b'\x89HDF\r\n\x1a\n'
                r={**req,'file':target.relative_to(ROOT).as_posix(),'bytes':count,'sha256':h.hexdigest(),'status':response.status,'final_host':urlparse(response.url).hostname,'hdf_signature':True,'acquired_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
            temp.rename(target);immutable(receipt,r)
        receipts.append(r);total+=r['bytes'];print(json.dumps({k:r[k] for k in ['split','product','status','bytes','sha256']}),flush=True)
    token=None
    immutable(OUT/'L2_EXACT_DOWNLOAD_MANIFEST.json',{'parent_manifest_sha256':digest(OUT/'L2_DOWNLOAD_MANIFEST.json'),'science_files':len(receipts),'total_bytes':total,'receipts':receipts,
        'choice':'later exact MYD03 receipt for same split overrides discovery-only MYD03 in new exact audit; old8-file analysis retained'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--token-file',required=True);a=p.parse_args();run(a.token_file)
