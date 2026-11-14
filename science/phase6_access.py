"""Official CMR discovery and redacted, bounded Earthdata access diagnostics.

Only an explicit local EDL token environment/file is used. No token is logged.
Redirects carrying Authorization are restricted to NASA Earthdata domains.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/acquisition/phase6'
REPORTS = ROOT / 'reports/phase6'

def validate_token(token):
    if token and not re.fullmatch(r'[A-Za-z0-9._~+/=-]{1,16384}',token):
        raise ValueError('Invalid EDL token format; value redacted')
    return token

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        host = urlparse(newurl).hostname or ''
        if new and not (host.endswith('.nasa.gov') and urlparse(newurl).scheme == 'https'):
            new.remove_header('Authorization')
        return new

def get_metadata(url, path):
    receipt = path.with_suffix('.receipt.json')
    if path.exists():
        raw = path.read_bytes(); meta = json.loads(receipt.read_text())
        assert meta['url'] == url and meta['sha256'] == hashlib.sha256(raw).hexdigest()
    else:
        with build_opener().open(url, timeout=35) as r:
            raw = r.read(4000001); assert len(raw) <= 4000000
            meta = {'url': url, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                    'hits': int(r.headers.get('CMR-Hits', '0')), 'retrieved_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
        path.write_bytes(raw); receipt.write_text(json.dumps(meta, indent=2))
    return json.loads(raw), meta

def probe(url, method, token=None):
    validate_token(token)
    headers = {'User-Agent': 'EmberGuard-bounded-science-access/1.0'}
    if method == 'GET': headers['Range'] = 'bytes=0-7'
    if token: headers['Authorization'] = 'Bearer ' + token
    result = {'url': url, 'method': method, 'authenticated': bool(token), 'requested_range': 'bytes=0-7' if method == 'GET' else None}
    try:
        with build_opener(SafeRedirect()).open(Request(url, headers=headers, method=method), timeout=30) as r:
            payload = r.read(8) if method == 'GET' else b''
            result.update(status=r.status, final_host=urlparse(r.url).hostname, headers={k: v for k, v in r.headers.items() if k.lower() in ['content-type', 'content-length', 'www-authenticate', 'x-mitmproxy-blocked-reason', 'content-range', 'server']},
                          sample_bytes=len(payload), sample_sha256=hashlib.sha256(payload).hexdigest(),
                          hdf_signature=payload==b'\x89HDF\r\n\x1a\n' or payload.startswith(b'\x0e\x03\x13\x01'))
    except HTTPError as e:
        payload = e.read(4096)
        result.update(status=e.code, final_host=urlparse(e.url).hostname, headers={k: v for k, v in e.headers.items() if k.lower() in ['content-type', 'content-length', 'www-authenticate', 'x-mitmproxy-blocked-reason', 'server']},
                      error_bytes_sampled=len(payload), error_sha256=hashlib.sha256(payload).hexdigest())
    except (URLError, TimeoutError) as e:
        result.update(status=None, error_category=type(e).__name__)
    if result.get('headers', {}).get('X-Mitmproxy-Blocked-Reason') or any(k.lower() == 'x-mitmproxy-blocked-reason' for k in result.get('headers', {})):
        result['classification'] = 'NETWORK_GATEWAY_REJECTION_NOT_EARTHDATA_AUTH_DIAGNOSIS'
    elif result.get('final_host') == 'urs.earthdata.nasa.gov' or result.get('status') == 401:
        result['classification'] = 'EARTHDATA_AUTH_REQUIRED_OR_REJECTED'
    elif result.get('status') == 403:
        result['classification'] = 'FORBIDDEN_CAUSE_UNRESOLVED_WITHOUT_VALID_AUTH_CONTROL'
    else:
        result['classification'] = 'RESPONSE_ONLY_NOT_QUALIFIED_SCIENCE_FILE'
    return result

def run(token_file=None):
    OUT.mkdir(parents=True, exist_ok=True)
    c = json.loads((REPORTS / 'COHORT_CONTRACT.json').read_text())
    token = os.environ.get('EARTHDATA_TOKEN') or os.environ.get('EDL_TOKEN')
    if token_file:
        p = Path(token_file).resolve()
        assert not p.is_relative_to(ROOT), 'Keep credentials outside project'
        token = p.read_text().strip()
    products = {}; attempts = []
    for day in c['l2_discovery_days']:
        products[day] = {}
        for product, (collection, version) in c['products'].items():
            url = 'https://cmr.earthdata.nasa.gov/search/granules.json?' + urlencode({'collection_concept_id': collection,
                'temporal': day+'T00:00:00Z,'+day+'T23:59:59.999Z', 'bounding_box': ','.join(map(str,c['aoi_wsen'])), 'page_size': 2000})
            try:
                data, receipt = get_metadata(url, OUT / (day+'-'+product+'.json'))
                entries = data['feed']['entry']; assert len(entries) == receipt['hits'], 'Pagination incomplete'
                granules = []
                for e in entries:
                    name=e.get('producer_granule_id', e['title']); key = re.search(r'\.A(\d{7})\.(\d{4})\.',name)
                    granules.append({'id':name,'concept_id':e['id'],'start':e['time_start'],'end':e['time_end'],
                        'key':key.group(0) if key else None, 'reported_mb':float(e.get('granule_size',0)),
                        'polygons':e.get('polygons',[]), 'boxes':e.get('boxes',[]),
                        'data_urls':[l['href'] for l in e.get('links',[]) if 'data#' in l.get('rel','') and l['href'].startswith('https:') and not l.get('inherited')]})
                products[day][product]={'collection':collection,'version':version,'receipt':receipt,'granules':sorted(granules,key=lambda g:(g['start'],g['id']))}
            except (HTTPError, URLError, TimeoutError, AssertionError) as e:
                products[day][product]={'state':'DISCOVERY_BLOCKED','error_category':type(e).__name__}
        for product in ['MYD14','VNP14','MYD03']:
            gs=products[day][product].get('granules',[])
            if gs and gs[0]['data_urls']:
                url=gs[0]['data_urls'][0]
                for method in ['HEAD','GET']:
                    attempts.append({'day':day,'product':product,'granule':gs[0]['id'],**probe(url,method)})
                if token: attempts.append({'day':day,'product':product,'granule':gs[0]['id'],**probe(url,'GET',token)})
    # A documented public LAADS control tests reachability, not protected entitlement.
    attempts.append({'product':'LAADS_PUBLIC_README',**probe('https://ladsweb.modaps.eosdis.nasa.gov/archive/README','GET')})
    l3={}
    for name in ['MYD14A1','VNP14A1']:
        url='https://cmr.earthdata.nasa.gov/search/collections.json?'+urlencode({'short_name':name,'page_size':100})
        try:
            data,receipt=get_metadata(url,OUT/(name+'-collections.json'))
            l3[name]={'receipt':receipt,'collections':[{'id':e['id'],'version':e.get('version_id'),'title':e['title']} for e in data['feed']['entry']],
                      'suitability':'METADATA_ONLY; daily summary support and acquisition timing must be independently decoded; not a substitute for matched pass QA'}
        except (HTTPError,URLError,TimeoutError) as e:l3[name]={'error_category':type(e).__name__}
    result={'contract_sha256':hashlib.sha256((REPORTS/'COHORT_CONTRACT.json').read_bytes()).hexdigest(),
            'products':products,'probes':attempts,'credential_available':bool(token), 'authenticated_test_executed':bool(token),
            'science_files_downloaded':0,'pixel_support':'UNKNOWN','level3_fallback':l3,
            'auth_conclusion':'No configured EDL credential; anonymous HEAD and GET do not establish access entitlement. See per-response gateway/auth classifications. No successful authenticated control exists.' if not token else 'Authenticated range tests executed; range bytes are not qualified full science arrays.',
            'next_access_step':'Use Earthdata Login Generate Token privately, authorize relevant provider application, then run phase6_access.py --token-file PRIVATE_PATH; never commit credentials.'}
    (REPORTS/'ACCESS_AUDIT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'granules':{d:{p:len(v.get('granules',[])) for p,v in ps.items()} for d,ps in products.items()},
                      'probes':[{k:v for k,v in a.items() if k in ['day','product','method','status','classification','headers']} for a in attempts],
                      'credential_available':bool(token)}))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--token-file');args=p.parse_args();run(args.token_file)
