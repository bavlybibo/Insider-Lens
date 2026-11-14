"""Bounded same-provider controls distinguish legacy-route and exact-instance access."""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
from urllib.request import build_opener,Request,HTTPCookieProcessor
from phase6_access import SafeRedirect,validate_token
from phase7_contract import ROOT,OUT
from phase7_discovery import immutable

def run(private_file):
    p=Path(private_file).resolve();assert p.is_file() and not p.is_relative_to(ROOT)
    token=validate_token(p.read_text(encoding='utf-8-sig').strip())
    a=json.loads((OUT/'SUPPORT_AUDIT.json').read_text());m=json.loads((OUT/'L2_DOWNLOAD_MANIFEST.json').read_text());queries=[]
    for split,v in a['results'].items():
        expected=v['products']['MYD14']['geolocation_input_named'][0];current=next(r for r in m['receipts'] if r['split']==split and r['product']=='MYD03')
        cloud=current['url'].rsplit('/',1)[0]+'/'+expected
        doy=expected.split('.')[1][5:];legacy=f'https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MYD03/2022/{doy}/'+Path(current['file']).name
        queries.extend([{'split':split,'purpose':'exact named input at CMR-derived current cloud prefix','url':cloud},{'split':split,'purpose':'known acquired current input at legacy route control','url':legacy}])
    immutable(OUT/'PROVIDER_CONTROL_SCOPE.json',{'max_requests':4,'max_bytes_read_each':8,'queries':queries,'selection_changed':False})
    op=build_opener(SafeRedirect(),HTTPCookieProcessor(CookieJar()));results=[]
    for query in queries:
        r=dict(query)
        try:
            with op.open(Request(r['url'],headers={'Authorization':'Bearer '+token,'Range':'bytes=0-7'}),timeout=30) as response:
                raw=response.read(8);r.update(status=response.status,final_host=urlparse(response.url).hostname,hdf4_signature=raw.startswith(b'\x0e\x03\x13\x01'))
        except HTTPError as e:r.update(status=e.code,final_host=urlparse(e.url).hostname,error_category='HTTPError')
        except (TimeoutError,URLError) as e:r.update(status=None,error_category=type(e).__name__)
        results.append(r);print(json.dumps(r),flush=True)
    token=None
    immutable(OUT/'PROVIDER_CONTROLS.json',{'results':results,'limitation':'403/401 do not establish file absence; only successful full payload can qualify an exact instance'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--token-file',required=True);a=p.parse_args();run(a.token_file)
