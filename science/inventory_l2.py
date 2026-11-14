"""Bounded, metadata-only CMR discovery. Never downloads or qualifies pixel QA."""
import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/acquisition/l2-inventory-2013-01'
# Exact standard-product collections independently found in CMR on 2026-11-13.
PRODUCTS={'MYD14':('C2278858993-LPCLOUD','061'),'MYD03':('C1379841358-LAADS','6.1'),
    'VNP14IMG':('C2734202914-LPCLOUD','002'),'VNP03IMG':('C2105092163-LAADS','2'),
    'VNP14':('C2545314536-LPCLOUD','002'),'VNP03MOD':('C2105092427-LAADS','2')}

def inventory():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=[];results={}
    for product,(concept,version) in PRODUCTS.items():
        query={'collection_concept_id':concept,'temporal':'2013-01-01T00:00:00Z,2013-01-31T23:59:59.999Z',
            'bounding_box':'-8.7,39.3,-7.2,40.8','page_size':'2000'}
        url='https://cmr.earthdata.nasa.gov/search/granules.json?'+urlencode(query)
        path=OUT/f'{product}.json'
        if path.exists():
            saved=json.loads((OUT/'MANIFEST.json').read_text())
            prior=next(x for x in saved if x['product']==product)
            data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==prior['sha256']
            entry=prior
        else:
            with urlopen(url,timeout=30) as response:
                data=response.read(10_000_001)
                assert len(data)<=10_000_000,'Bounded metadata response exceeded; do not silently truncate'
                entry={'product':product,'collection_concept_id':concept,'version':version,'url':url,
                    'cmr_hits':int(response.headers['CMR-Hits']),'sha256':hashlib.sha256(data).hexdigest(),
                    'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            path.write_bytes(data)
        entries=json.loads(data)['feed']['entry']
        assert len(entries)==entry['cmr_hits'],'Incomplete listing: pagination must be explicit'
        granules=[]
        for item in entries:
            name=item.get('producer_granule_id',item.get('title',''))
            match=re.search(r'\.(A\d{7})\.(\d{4})\.',name)
            granules.append({'granule_id':name,'concept_id':item['id'],'time_start':item.get('time_start'),
                'time_end':item.get('time_end'),'metadata_updated':item.get('updated'),
                'reported_size_mb':float(item.get('granule_size',0)),
                'acquisition_key':'.'.join(match.groups()) if match else None})
        results[product]={'collection':concept,'version':version,'listed_granules':len(granules),
            'cmr_reported_total_mb':sum(g['reported_size_mb'] for g in granules),'granules':granules}
        manifest.append(entry)
    (OUT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    pairs={}
    for fire,geo in [('MYD14','MYD03'),('VNP14IMG','VNP03IMG'),('VNP14','VNP03MOD')]:
        a={g['acquisition_key'] for g in results[fire]['granules'] if g['acquisition_key']}
        b={g['acquisition_key'] for g in results[geo]['granules'] if g['acquisition_key']}
        pairs[f'{fire}+{geo}']={'same_acquisition_keys':len(a&b),'fire_only_keys':len(a-b),'geolocation_only_keys':len(b-a),
            'meaning':'Metadata overlap only. Not pixel QA, cloud-free observation, or cross-sensor matched support.'}
    report={'state':'METADATA_ONLY_NOT_QUALIFIED','month':'2013-01','aoi_wsen':[-8.7,39.3,-7.2,40.8],
        'products':results,'acquisition_key_overlap':pairs,'pixel_arrays_downloaded':0,
        'observation_support':'OBSERVATION_UNKNOWN','g4':'ADJUSTMENT_WITHHELD',
        'limitations':['CMR bbox-intersecting granules are candidate viewing metadata, not validated footprint/quality masks.',
            'CMR current collections are not proof of which production granules fed the country CSVs.',
            'Reported granule-size MB sum estimates full files; no payload transfer occurred. Authentication and compatible QA decoding remain necessary.',
            '750 m products are prospective research only; not included in the current 375 m S-NPP lane.']}
    (ROOT/'reports/L2_METADATA_INVENTORY.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'state':report['state'],'products':{key:{k:v for k,v in value.items() if k!='granules'} for key,value in results.items()},'acquisition_key_overlap':pairs},indent=2))
    return report

if __name__=='__main__':inventory()
