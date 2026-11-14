"""Private-file-only Earthdata GET with cookies, safe redirects and frozen budget."""
import argparse
import datetime as dt
import hashlib
from http.cookiejar import CookieJar
import json
from pathlib import Path
import shutil
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPCookieProcessor
from phase6_access import SafeRedirect, validate_token
from phase7_contract import ROOT, OUT
from phase7_discovery import immutable,digest

DATA=ROOT/'data/acquisition/phase7/l2'

def run(private_file):
    p=Path(private_file).resolve();assert p.is_file() and not p.is_relative_to(ROOT),'Private token file must exist outside project'
    token=validate_token(p.read_text(encoding='utf-8-sig').strip());assert token
    c=json.loads((OUT/'SEARCH_CONTRACT.json').read_text())
    discovery=json.loads((OUT/'DISCOVERY.json').read_text())
    scope={'contract_sha256':digest(OUT/'SEARCH_CONTRACT.json'),'discovery_sha256':digest(OUT/'DISCOVERY.json'),
           'stage1_products':['MYD14','MYD03','VNP14','VNP03MOD'],
           'stage2_products':['VNP14IMG','VNP03IMG'],
           'stage2_condition':'only after primary40deg view/timing and exact-lineage eligibility; no new candidate chosen from fire outcome',
           'budget_bytes':c['budgets']['max_payload_bytes'],'auth':'operator confirmed both chat-exposed tokens revoked; new private file supplied; contents never exported',
           'auth_confirmation_client_date':'2026-11-14','cookies':'in-memory CookieJar only; no credential cookie persistence'}
    immutable(OUT/'ACQUISITION_SCOPE.json',scope)
    receipts=[];attempts=[];total=0
    opener=build_opener(SafeRedirect(),HTTPCookieProcessor(CookieJar()))
    for split,spec in discovery['splits'].items():
        selected=spec['candidate']
        if not selected:continue
        files={'MYD14':selected['aqua'],'VNP14':selected['viirs750'],**{k:v[0] for k,v in selected['associated'].items()}}
        for product in scope['stage1_products']:
            g=files[product];url=g['data_urls'][0];u=urlparse(url)
            assert u.scheme=='https' and (u.hostname or '').endswith('.nasa.gov')
            filename=Path(u.path).name;folder=DATA/split;folder.mkdir(parents=True,exist_ok=True);target=folder/filename
            rpath=target.with_suffix(target.suffix+'.receipt.json')
            if target.exists():
                r=json.loads(rpath.read_text());assert r['url']==url and r['sha256']==digest(target)
                total+=r['bytes'];receipts.append(r);continue
            assert shutil.disk_usage(ROOT).free>=c['budgets']['min_free_disk_reserve_bytes']+g['reported_bytes']
            temp=target.with_suffix(target.suffix+'.part');h=hashlib.sha256();count=0;signature=b''
            try:
                with opener.open(Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'EmberGuard-frozen-support/1.0'}),timeout=45) as response:
                    with temp.open('xb') as f:
                        while chunk:=response.read(1024*1024):
                            if not signature:signature=chunk[:8]
                            count+=len(chunk)
                            assert total+count<=c['budgets']['max_payload_bytes'],'Frozen payload budget exceeded'
                            f.write(chunk);h.update(chunk)
                    assert signature.startswith(b'\x0e\x03\x13\x01') or signature==b'\x89HDF\r\n\x1a\n','Response is not HDF'
                    r={'split':split,'product':product,'granule':g['id'],'concept_id':g['concept_id'],'collection':g['collection'],
                       'file':target.relative_to(ROOT).as_posix(),'url':url,'bytes':count,'sha256':h.hexdigest(),'status':response.status,
                       'final_host':urlparse(response.url).hostname,'acquired_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                       'selection_sha256':digest(OUT/f'{split.upper()}_CANDIDATE.json'),'hdf_signature':True}
                temp.rename(target);immutable(rpath,r);receipts.append(r);total+=count
                print(json.dumps({'split':split,'product':product,'status':r['status'],'bytes':count,'sha256':r['sha256']}),flush=True)
            except (HTTPError,URLError,TimeoutError,OSError) as e:
                if temp.exists():temp.unlink()
                attempts.append({'split':split,'product':product,'url':url,'category':type(e).__name__,'status':getattr(e,'code',None)})
                print(json.dumps(attempts[-1]),flush=True)
    token=None
    result={'scope_sha256':digest(OUT/'ACQUISITION_SCOPE.json'),'science_files':len(receipts),'total_bytes':total,'receipts':receipts,'failed_attempts':attempts,
            'authentication':'private-file bearer with in-memory cookies; no secret/cookie persisted','stage2':'NOT YET ELIGIBLE; stage1 geometry and exact lineage first'}
    immutable(OUT/'L2_DOWNLOAD_MANIFEST.json',result)
    print(json.dumps({'science_files':len(receipts),'total_bytes':total,'failed_attempts':len(attempts)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--token-file',required=True);a=p.parse_args();run(a.token_file)
