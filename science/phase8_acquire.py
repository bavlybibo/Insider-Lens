"""Bounded exact-input acquisition for the frozen event; no outcome-based selection."""
import argparse
import datetime as dt
import hashlib
from http.cookiejar import CookieJar
import json
import re
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPCookieProcessor
from phase6_access import SafeRedirect, validate_token
from phase6_l2 import SD, SDC, h5py, plain, process
from pyproj import Transformer
from phase8_contract import ROOT, OUT, sha, immutable

def run(private_file, detail=False):
    private=Path(private_file).resolve()
    assert private.is_file() and not private.is_relative_to(ROOT)
    token=validate_token(private.read_text(encoding='utf-8-sig').strip())
    op=build_opener(SafeRedirect(),HTTPCookieProcessor(CookieJar()))
    c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());pair=json.loads((OUT/'CANDIDATE_1.json').read_text())['pair']
    receipts=[]
    folder=ROOT/'data/acquisition/phase8/l2';folder.mkdir(parents=True,exist_ok=True)
    def get(product,url):
        u=urlparse(url);assert u.scheme=='https' and (u.hostname or '').endswith('.nasa.gov')
        target=folder/Path(u.path).name;rp=target.with_suffix(target.suffix+'.receipt.json')
        # Include all previously acquired payloads in the cumulative budget.
        used=sum(p.stat().st_size for p in folder.iterdir() if p.suffix in ['.hdf','.nc'])
        if target.exists():
            r=json.loads(rp.read_text());assert r['url']==url and sha(target)==r['sha256']
        else:
            assert shutil.disk_usage(ROOT).free>c['budget']['minimum_free_bytes']+200000000
            tmp=target.with_suffix(target.suffix+'.part');h=hashlib.sha256();size=0;sig=b''
            with op.open(Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'EmberGuard-frozen-event/1.0'}),timeout=60) as response:
                with tmp.open('xb') as f:
                    while block:=response.read(1024*1024):
                        if not sig:sig=block[:8]
                        size+=len(block);assert used+size<=c['budget']['max_payload_bytes']
                        assert shutil.disk_usage(ROOT).free>c['budget']['minimum_free_bytes']
                        f.write(block);h.update(block)
                assert sig.startswith(b'\x0e\x03\x13\x01') or sig==b'\x89HDF\r\n\x1a\n'
                r={'product':product,'file':target.relative_to(ROOT).as_posix(),'url':url,'bytes':size,'sha256':h.hexdigest(),
                   'status':response.status,'final_host':urlparse(response.url).hostname,'acquired_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                   'selection_sha256':sha(OUT/'CANDIDATE_1.json'),'hdf_signature':True}
            tmp.rename(target);immutable(rp,r)
        receipts.append(r);print(json.dumps({k:r[k] for k in ['product','bytes','sha256']}),flush=True)
        return target
    for product in ['MYD14','VNP14']+(['VNP14IMG'] if detail else []):
        if product=='VNP14IMG':
            assert pair['maximum_interval_endpoint_separation_minutes']<=10 and pair['midpoint_offset_minutes']<=5
            prior={r['product']:ROOT/r['file'] for r in receipts};transform=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True)
            for source,geo in [('MYD14','MYD03'),('VNP14','VNP03MOD')]:
                screen=process(prior[source],prior[geo],source,c,transform)
                assert screen['exact_geolocation_input_identity'] and screen['view_sensitivity']['40']['aoi_centers_within_view']>0
            # No positive-pixel, FRP, agreement or confidence outcome enters this gate.
        g=pair['aqua'] if product=='MYD14' else pair['viirs750'] if product=='VNP14' else pair['associated'][product][0]
        fire=get(product,g['data_urls'][0])
        if product=='MYD14':
            f=SD(str(fire),SDC.READ);name=Path(f.attributes()['MOD03 input file']).name;f.end();geo='MYD03'
        else:
            with h5py.File(fire,'r') as f:
                v=plain(f.attrs.get('InputFileGeo',f.attrs.get('InputPointer','')));names=re.findall(r'VNP03(?:IMG|MOD)\.A\d{7}\.\d{4}\.002\.\d+\.nc',str(v));assert len(names)==1;name=names[0]
            geo='VNP03IMG' if product=='VNP14IMG' else 'VNP03MOD'
        assert name.startswith(geo+'.') and '/' not in name
        get(geo,'https://data.laadsdaac.earthdatacloud.nasa.gov/prod-lads/'+geo+'/'+name)
    token=None
    immutable(OUT/('DETAIL_DOWNLOAD_MANIFEST.json' if detail else 'L2_DOWNLOAD_MANIFEST.json'),{
        'contract_sha256':sha(OUT/'COHORT_CONTRACT.json'),'candidate_sha256':sha(OUT/'CANDIDATE_1.json'),
        'receipts':receipts,'science_files':len(receipts),'total_bytes':sum(r['bytes'] for r in receipts),
        'authentication':'private file only, in-memory cookies, safe NASA redirects; secrets never persisted',
        'selection':'one metadata-eligible pair; no outcome-driven replacement'})

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--token-file',required=True);a.add_argument('--detail',action='store_true');v=a.parse_args();run(v.token_file,v.detail)
