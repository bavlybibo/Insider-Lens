"""Bounded L2 metadata/access feasibility, including previously missing Terra.

No credentials, holdout requests or observation-mask qualification. HEAD probe
does not download a science payload or turn a login page into a granule.
"""
from concurrent.futures import ThreadPoolExecutor
import datetime,hashlib,json,re
from pathlib import Path
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from inventory_l2 import PRODUCTS
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/acquisition/phase3-l2'
COLLECTIONS={**PRODUCTS,'MOD14':('C2271754179-LPCLOUD','061'),'MOD03':('C1379767668-LAADS','6.1')}
sha=lambda b:hashlib.sha256(b).hexdigest()

def retrieve(task):
    month,product=task;concept,version=COLLECTIONS[product];folder=OUT/month;folder.mkdir(parents=True,exist_ok=True)
    path=folder/(product+'.json');receipt=folder/(product+'.receipt.json')
    last='31' if month=='2013-01' else '30'
    url='https://cmr.earthdata.nasa.gov/search/granules.json?'+urlencode({'collection_concept_id':concept,'temporal':f'{month}-01T00:00:00Z,{month}-{last}T23:59:59.999Z','bounding_box':'-8.7,39.3,-7.2,40.8','page_size':2000})
    if path.exists():
        meta=json.loads(receipt.read_text(encoding='utf-8'));data=path.read_bytes();assert sha(data)==meta['sha256'] and meta['url']==url
    else:
        with urlopen(url,timeout=30) as response:
            data=response.read(10_000_001);assert len(data)<=10_000_000
            meta={'url':url,'collection':concept,'version':version,'sha256':sha(data),'bytes':len(data),'cmr_hits':int(response.headers['CMR-Hits']),
                'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        path.write_bytes(data);receipt.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    entries=json.loads(data)['feed']['entry'];assert len(entries)==meta['cmr_hits'],'Incomplete CMR listing'
    granules=[]
    for e in entries:
        name=e.get('producer_granule_id',e.get('title',''));match=re.search(r'\.(A\d{7})\.(\d{4})\.',name)
        granules.append({'id':name,'concept':e['id'],'acquisition_key':'.'.join(match.groups()) if match else None,
            'start':e.get('time_start'),'end':e.get('time_end'),'reported_mb':float(e.get('granule_size',0)),
            'data_urls':[l['href'] for l in e.get('links',[]) if l.get('href','').startswith('https:') and 'data#' in l.get('rel','') and not l.get('inherited')]})
    print(f'{month} {product}: {len(granules)} metadata entries',flush=True)
    return month,product,{'collection':concept,'version':version,'raw_metadata_sha256':meta['sha256'],'reported_total_mb':sum(g['reported_mb'] for g in granules),'granules':granules}

def inventory():
    # January products are cached in Phase2. Fetch only the missing Terra pair;
    # June has been declared in the Phase3 rule before any new detection counts.
    tasks=[('2013-01',p) for p in ['MOD14','MOD03']]+[('2013-06',p) for p in COLLECTIONS]
    months={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for month,product,value in pool.map(retrieve,tasks):months.setdefault(month,{})[product]=value
    prior=ROOT/'data/acquisition/l2-inventory-2013-01';receipts=json.loads((prior/'MANIFEST.json').read_text(encoding='utf-8'))
    for item in receipts:
        data=(prior/(item['product']+'.json')).read_bytes();assert sha(data)==item['sha256']
    # Reuse the previously verified full January granule inventory unchanged.
    previous=json.loads((ROOT/'reports/L2_METADATA_INVENTORY.json').read_text(encoding='utf-8'))
    for product,value in previous['products'].items():
        months['2013-01'][product]={'collection':value['collection'],'version':value['version'],'reported_total_mb':value['cmr_reported_total_mb'],
            'granules':[{'id':g['granule_id'],'acquisition_key':g['acquisition_key'],'start':g['time_start'],'end':g['time_end'],'reported_mb':g['reported_size_mb']} for g in value['granules']],
            'origin':'Prior immutable Phase2 metadata; raw response hashes verified again'}
    pairs={}
    for month,products in months.items():
        pairs[month]={}
        for fire,geo in [('MOD14','MOD03'),('MYD14','MYD03'),('VNP14IMG','VNP03IMG'),('VNP14','VNP03MOD')]:
            a={g['acquisition_key'] for g in products[fire]['granules'] if g['acquisition_key']};b={g['acquisition_key'] for g in products[geo]['granules'] if g['acquisition_key']}
            pairs[month][fire+'+'+geo]={'matched_metadata_keys':sorted(a&b),'missing_geolocation_keys':sorted(a-b),'unpaired_geolocation_keys':sorted(b-a),
                'meaning':'Same-platform metadata keys, not pixel QA, CSV production lineage or matched cross-sensor observation support'}
    # One declared first chronological Aqua fire-granule access probe only.
    first=sorted(months['2013-06']['MYD14']['granules'],key=lambda g:(g['start'],g['id']))[0]
    probe={'granule':first['id'],'method':'HEAD only; no pixel payload read','state':'NO_DIRECT_HTTPS_DATA_LINK'}
    urls=first.get('data_urls',[])
    if urls:
        url=urls[0];probe['requested_url']=url
        try:
            with urlopen(Request(url,method='HEAD'),timeout=25) as response:
                content_type=response.headers.get('Content-Type','');host=urlparse(response.url).hostname
                probe.update({'http_status':response.status,'final_host':host,'content_type':content_type,'content_length':response.headers.get('Content-Length'),
                    'state':'AUTHENTICATION_OR_HTML_RESPONSE' if host=='urs.earthdata.nasa.gov' or 'text/html' in content_type else 'HEAD_ACCESSIBLE_PAYLOAD_NOT_QUALIFIED'})
        except HTTPError as e:probe.update({'state':'HTTP_ACCESS_BLOCKED','http_status':e.code})
        except (URLError,TimeoutError) as e:probe.update({'state':'NETWORK_ACCESS_BLOCKED','reason':type(e).__name__})
    report={'state':'METADATA_AND_ACCESS_FEASIBILITY_ONLY','months':months,'pairs':pairs,'access_probe':probe,'pixel_payload_bytes_downloaded':0,
        'source_linked_country_production_lineage':'UNVERIFIED','observation_support':'UNKNOWN','g4':'ADJUSTMENT_WITHHELD',
        'size_scope':'CMR full-file reported MB, not actual transfer, AOI subset size or valid cloud-free observation'}
    (ROOT/'reports/HISTORICAL_PHASE3_L2.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
if __name__=='__main__':
    r=inventory();print(json.dumps({'state':r['state'],'access_probe':r['access_probe'],'months':{m:{p:len(v['granules']) for p,v in products.items()} for m,products in r['months'].items()}},indent=2))
