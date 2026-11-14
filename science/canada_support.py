"""Bounded Canada development-day L2 metadata and one anonymous HEAD probe.

No credentials read, no protected access bypass, no science pixels downloaded.
CMR metadata intersections are candidates, never verified observation support.
"""
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from inventory_l2 import PRODUCTS

ROOT=Path(__file__).resolve().parents[1]
PRODUCTS={**PRODUCTS,'MOD14':('C2271754179-LPCLOUD','061'),'MOD03':('C1379767668-LAADS','6.1')}
OUT=ROOT/'data/acquisition/canada-l2-2023-06-01'

def fetch(item):
    name,(concept,version)=item
    url='https://cmr.earthdata.nasa.gov/search/granules.json?'+urlencode({'collection_concept_id':concept,'temporal':'2023-06-01T00:00:00Z,2023-06-01T23:59:59.999Z','bounding_box':'-120,49,-110,55','page_size':2000})
    path=OUT/(name+'.json');receipt=OUT/(name+'.receipt.json')
    try:
        if path.exists():
            raw=path.read_bytes();meta=json.loads(receipt.read_text(encoding='utf8'));assert hashlib.sha256(raw).hexdigest()==meta['sha256'] and meta['url']==url
        else:
            with urlopen(url,timeout=30) as response:
                raw=response.read(4_000_001);assert len(raw)<=4_000_000
                meta={'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'hits':int(response.headers['CMR-Hits']),'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            path.write_bytes(raw);receipt.write_text(json.dumps(meta,indent=2),encoding='utf8')
        entries=json.loads(raw)['feed']['entry'];assert len(entries)==meta['hits'],'CMR pagination incomplete'
        granules=[]
        for e in entries:
            label=e.get('producer_granule_id',e.get('title',''));m=re.search(r'\.(A\d{7})\.(\d{4})\.',label)
            granules.append({'id':label,'concept':e['id'],'start':e.get('time_start'),'end':e.get('time_end'),'acquisition_key':'.'.join(m.groups()) if m else None,'reported_mb':float(e.get('granule_size',0)),
                'data_urls':[l['href'] for l in e.get('links',[]) if l.get('href','').startswith('https:') and 'data#' in l.get('rel','') and not l.get('inherited')]})
        return name,{'state':'METADATA_ONLY','collection':concept,'version':version,'receipt':meta,'granules':granules}
    except (HTTPError,URLError,TimeoutError,AssertionError) as e:return name,{'state':'DISCOVERY_BLOCKED','url':url,'reason':str(e)}

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:products=dict(pool.map(fetch,PRODUCTS.items()))
    pairs={}
    for fire,geo in [('MOD14','MOD03'),('MYD14','MYD03'),('VNP14IMG','VNP03IMG'),('VNP14','VNP03MOD')]:
        a={g['acquisition_key'] for g in products[fire].get('granules',[]) if g['acquisition_key']};b={g['acquisition_key'] for g in products[geo].get('granules',[]) if g['acquisition_key']}
        pairs[fire+'+'+geo]={'matched_metadata_keys':sorted(a&b),'missing_geolocation_keys':sorted(a-b),'meaning':'same-platform nominal acquisition metadata only; not cloud-free pixel support or CSV lineage'}
    first=sorted(products['MYD14'].get('granules',[]),key=lambda g:(g['start'],g['id']))
    probe={'state':'NO_AQUA_METADATA_DATA_LINK','pixel_bytes_downloaded':0,'method':'one anonymous HEAD to first chronological development-day Aqua fire granule'}
    if first and first[0]['data_urls']:
        url=first[0]['data_urls'][0];probe.update(url=url,granule=first[0]['id'])
        try:
            with urlopen(Request(url,method='HEAD'),timeout=25) as r:
                content=r.headers.get('Content-Type','');host=urlparse(r.url).hostname
                probe.update(http_status=r.status,content_type=content,final_host=host,state='AUTH_OR_HTML_RESPONSE' if 'html' in content or host=='urs.earthdata.nasa.gov' else 'HEAD_ACCESSIBLE_NOT_PIXEL_QUALIFIED')
        except HTTPError as e:probe.update(http_status=e.code,state='HTTP_ACCESS_BLOCKED')
        except (URLError,TimeoutError) as e:probe.update(state='NETWORK_ACCESS_BLOCKED',reason=type(e).__name__)
    result={'state':'METADATA_ONLY_BRIDGE_BLOCKED','preregistered_scope':'southern development pilot; first UTC day of June2023','products':products,'pairs':pairs,'access_probe':probe,'pixel_bytes_downloaded':0,'observation_support':'OBSERVATION_UNKNOWN','g4':'ADJUSTMENT_WITHHELD','missing':['exact source-linked monthly production/delivery lineage','downloaded compatible Level-2 fire masks, algorithm QA and geolocation','geolocated shared valid footprints, view angles and per-pass time differences','independent holdout evaluation and original G4 signatures']}
    (ROOT/'reports/CANADA_L2_FEASIBILITY.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({'products':{p:len(v.get('granules',[])) for p,v in products.items()},'probe':probe,'state':result['state']},indent=2))

if __name__=='__main__':run()
