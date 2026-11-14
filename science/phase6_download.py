"""Bounded authenticated retrieval of frozen, metadata-selected L2 samples."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
from phase6_access import SafeRedirect,validate_token

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/phase6';OUT=ROOT/'data/acquisition/phase6/l2'
def stamp(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()

def run(token_file):
    token_path=Path(token_file).resolve();assert not token_path.is_relative_to(ROOT)
    token=validate_token(token_path.read_text().strip());assert token
    c=json.loads((R/'COHORT_CONTRACT.json').read_text());access=json.loads((R/'ACCESS_AUDIT.json').read_text());OUT.mkdir(parents=True,exist_ok=True)
    selection=[]
    for day,ps in access['products'].items():
        aqua=ps['MYD14']['granules'][0]
        viirs=min(ps['VNP14']['granules'],key=lambda g:(abs(stamp(g['start'])-stamp(aqua['start'])),g['id']))
        offset=abs(stamp(aqua['start'])-stamp(viirs['start']))/60
        assert offset<=60, 'No pair within frozen sensitivity range'
        chosen={}
        for product,key in [('MYD14',aqua['key']),('MYD03',aqua['key']),('VNP14',viirs['key']),('VNP14IMG',viirs['key']),('VNP03IMG',viirs['key']),('VNP03MOD',viirs['key'])]:
            gs=[g for g in ps[product]['granules'] if g['key']==key];assert len(gs)==1
            chosen[product]=gs[0]
        selection.append({'day':day,'nominal_start_offset_minutes':offset,'primary_30min_eligible_metadata':offset<=30,'products':chosen})
    frozen={'policy':'first chronological Aqua each frozen day; closest nominal-start VNP14 <=60 min, deterministic ID tie break; all matching geolocation/375m by acquisition key; frozen before science payload read',
            'selection':selection,'contract_sha256':hashlib.sha256((R/'COHORT_CONTRACT.json').read_bytes()).hexdigest()}
    b=(json.dumps(frozen,indent=2,sort_keys=True)+'\n').encode();p=R/'L2_SELECTION.json'
    if p.exists():assert p.read_bytes()==b
    else:p.write_bytes(b)
    # Both complete 375m geolocation swaths exceed the frozen operational cap.
    # Keep the full primary triplet and an independent 750m replication pair;
    # never change the cohort/time thresholds in response to science outcomes.
    download_selection=[{**s,'products':{k:g for k,g in s['products'].items() if s['day']==c['l2_discovery_days'][0] or k not in ['VNP14IMG','VNP03IMG']}} for s in selection]
    scope={'reason':'Both complete triplets exceed 512MB frozen cap; retain complete primary triplet and 750m-only replication. No payload inspected before this reduction.',
           'products_by_day':{s['day']:list(s['products']) for s in download_selection}}
    scope_path=R/'L2_DOWNLOAD_SCOPE.json';scope_bytes=(json.dumps(scope,indent=2,sort_keys=True)+'\n').encode()
    if scope_path.exists():assert scope_path.read_bytes()==scope_bytes
    else:scope_path.write_bytes(scope_bytes)
    assert sum(g['reported_mb']*1048576 for s in download_selection for g in s['products'].values())<c['max_download_bytes'],'CMR estimate exceeds cap'
    assert shutil.disk_usage(OUT).free>c['max_download_bytes']+1000000000
    receipts=[];total=0
    for s in download_selection:
        folder=OUT/s['day'];folder.mkdir(exist_ok=True)
        for product,g in s['products'].items():
            url=g['data_urls'][0];name=Path(urlparse(url).path).name;assert '/' not in name and name not in ['.','..']
            path=folder/name;receipt_path=folder/(product+'.receipt.json')
            if path.exists():
                receipt=json.loads(receipt_path.read_text());assert receipt['url']==url
                with path.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==receipt['sha256']
                total+=receipt['bytes'];receipts.append(receipt);continue
            partial=path.with_suffix(path.suffix+'.part');assert not partial.exists(),'Inspect preserved partial file before retry'
            try:
                req=Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'EmberGuard-bounded-science/1.0'})
                with build_opener(SafeRedirect()).open(req,timeout=90) as response:
                    assert response.status==200, 'Full payload must be HTTP200, not range/HTML'
                    content=response.headers.get('Content-Type','');assert 'html' not in content
                    expected=int(response.headers.get('Content-Length','0'));assert 0<expected<=300000000 and total+expected<=c['max_download_bytes']
                    sha=hashlib.sha256();count=0
                    with partial.open('xb') as f:
                        while True:
                            chunk=response.read(1048576)
                            if not chunk:break
                            count+=len(chunk);assert count<=expected and total+count<=c['max_download_bytes'];f.write(chunk);sha.update(chunk)
                    assert count==expected
                    with partial.open('rb') as f:magic=f.read(8)
                    assert magic.startswith(b'\x0e\x03\x13\x01') or magic==b'\x89HDF\r\n\x1a\n', 'Not HDF4/HDF5'
                    partial.rename(path);total+=count
                    receipt={'day':s['day'],'product':product,'granule':g['id'],'collection':c['products'][product],
                        'url':url,'final_host':urlparse(response.url).hostname,'file':path.relative_to(ROOT).as_posix(),'bytes':count,'sha256':sha.hexdigest(),
                        'http_status':response.status,'content_type':content,'authenticated':True,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt)
                    print(json.dumps({'day':s['day'],'product':product,'bytes':count,'sha256':sha.hexdigest()}),flush=True)
            except (HTTPError,URLError,TimeoutError,AssertionError) as e:
                failure={'day':s['day'],'product':product,'url':url,'category':type(e).__name__,'status':e.code if isinstance(e,HTTPError) else None}
                (R/'DOWNLOAD_FAILURE.json').write_text(json.dumps(failure,indent=2));raise RuntimeError(json.dumps(failure)) from None
    (R/'L2_DOWNLOAD_MANIFEST.json').write_text(json.dumps({'science_files':len(receipts),'total_bytes':total,'receipts':receipts},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--token-file',required=True);a=p.parse_args();run(a.token_file)
