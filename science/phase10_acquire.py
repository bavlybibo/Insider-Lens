"""One metadata-selected MODLL payload. Private token stays out of output."""
import json,time,hashlib
from pathlib import Path
from urllib.request import Request,build_opener
from urllib.parse import urlparse
from urllib.error import HTTPError,URLError
from phase6_access import SafeRedirect,validate_token
from phase10_contract import ROOT,OUT,sha,immutable,freeze

def run():
    freeze();folder=ROOT/'data/acquisition/phase10';folder.mkdir(exist_ok=True)
    cmr=folder/'MODLL_CMR.json'
    temporary=ROOT/'data/acquisition/phase10-cmr-temp.json'
    if not cmr.exists():temporary.rename(cmr)
    entries=json.loads(cmr.read_text(encoding='utf-8'))['feed']['entry']
    gs=[g for g in entries if g['producer_granule_id'].startswith('VNP03MODLL.A2023164.1042.002.')];assert len(gs)==1
    g=gs[0];url=next(l['href'] for l in g['links'] if l['href'].startswith('https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/') and l['href'].endswith('.h5'))
    # Published size exceeded the initial operational guess before any payload read.
    # This supplement changes only the acquisition cap, never qualification criteria.
    immutable(OUT/'ACQUISITION_SCOPE.json',{'reason':'CMR reports69.9717588424683MiB, above initial64MB operational cap. Before acquisition, allow one80MB matching MODLL file; no scientific threshold or cohort change.','parent_contract_sha256':sha(OUT/'QUALIFICATION_CONTRACT.json'),'metadata_sha256':sha(cmr),'granule':g['producer_granule_id'],'concept':g['id'],'url':url,'reported_mb':g['granule_size'],'max_science_bytes':80000000,'max_science_files':1})
    name=urlparse(url).path.rsplit('/',1)[-1];target=folder/name;receipt=OUT/'MODLL_DOWNLOAD.json'
    if target.exists():
        r=json.loads(receipt.read_text(encoding='utf-8'));assert sha(target)==r['sha256'];print(json.dumps({'state':'CACHED_VERIFIED','bytes':r['bytes'],'sha256':r['sha256']}));return
    private=Path.home()/'.secrets/earthdata_token.txt';assert not private.resolve().is_relative_to(ROOT)
    token=validate_token(private.read_text(encoding='utf-8-sig').strip());assert token
    begin=time.monotonic();count=0;digest=hashlib.sha256();partial=target.with_suffix('.h5.part');assert not partial.exists()
    try:
        req=Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'EmberGuard-phase10-bounded-qualification/1.0'})
        with build_opener(SafeRedirect()).open(req,timeout=25) as response:
            assert response.status==200 and 'html' not in response.headers.get('Content-Type','')
            expected=int(response.headers.get('Content-Length','0'));assert expected<=80000000
            with partial.open('xb') as f:
                while True:
                    block=response.read(1024*1024)
                    if not block:break
                    count+=len(block);assert count<=80000000 and time.monotonic()-begin<150
                    digest.update(block);f.write(block)
            assert not expected or count==expected
            with partial.open('rb') as f:assert f.read(8)==b'\x89HDF\r\n\x1a\n'
            partial.rename(target)
            immutable(receipt,{'state':'ACQUIRED','file':target.relative_to(ROOT).as_posix(),'granule':g['producer_granule_id'],'concept':g['id'],'url':url,'bytes':count,'sha256':digest.hexdigest(),'final_host':urlparse(response.url).hostname,'authenticated':True,'elapsed_seconds':round(time.monotonic()-begin,3)})
            print(json.dumps({'state':'ACQUIRED','bytes':count,'sha256':digest.hexdigest()}))
    except (HTTPError,URLError,TimeoutError,AssertionError) as e:
        r={'state':'FAILED','category':type(e).__name__,'http_status':e.code if isinstance(e,HTTPError) else None,'partial_bytes':count,'no_response_headers_or_secrets_logged':True}
        (OUT/'ACCESS_FAILURE.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r));raise RuntimeError('Bounded MODLL acquisition failed; see redacted receipt') from None
if __name__=='__main__':run()
