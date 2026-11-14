"""Exact named input probes, with cookies and redacted receipts, no substitution."""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPCookieProcessor
from phase6_access import SafeRedirect,validate_token
from phase7_contract import ROOT,OUT
from phase7_discovery import immutable,digest

def run(private_file):
    p=Path(private_file).resolve();assert p.is_file() and not p.is_relative_to(ROOT)
    token=validate_token(p.read_text(encoding='utf-8-sig').strip());opener=build_opener(SafeRedirect(),HTTPCookieProcessor(CookieJar()))
    audit=json.loads((OUT/'SUPPORT_AUDIT.json').read_text());results=[]
    for split,r in audit['results'].items():
        expected=r['products']['MYD14']['geolocation_input_named'][0];day=expected.split('.')[1][5:]
        url=f'https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MYD03/2022/{day}/{expected}'
        result={'split':split,'expected_input':expected,'url':url,'method':'authenticated GET Range0-7, cookies in memory'}
        try:
            with opener.open(Request(url,headers={'Authorization':'Bearer '+token,'Range':'bytes=0-7','User-Agent':'EmberGuard-frozen-lineage/1.0'}),timeout=35) as response:
                raw=response.read(8);result.update(status=response.status,final_host=urlparse(response.url).hostname,
                    bytes_sampled=len(raw),hdf4_signature=raw.startswith(b'\x0e\x03\x13\x01'),sample_sha256=__import__('hashlib').sha256(raw).hexdigest())
        except HTTPError as e:result.update(status=e.code,final_host=urlparse(e.url).hostname,error_category='HTTPError')
        except (URLError,TimeoutError) as e:result.update(status=None,error_category=type(e).__name__)
        result['meaning']='Response alone does not prove archive absence, entitlement or compatible arrays; full file would require receipt and decoding'
        results.append(result);print(json.dumps(result),flush=True)
    token=None
    immutable(OUT/'EXACT_GEO_ACCESS.json',{'support_audit_sha256':digest(OUT/'SUPPORT_AUDIT.json'),'results':results,
        'auth_control':'8 complete Phase7 HDF science files succeeded using same private credential; provider-specific failures remain distinct'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--token-file',required=True);a=p.parse_args();run(a.token_file)
