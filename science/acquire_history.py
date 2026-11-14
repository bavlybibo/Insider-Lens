"""Bounded official SP acquisition for the prespecified Portugal January 2013 audit.

Public yearly country CSVs are source bytes, not qualified complete-month or
observation-support products. Re-running verifies existing bytes, never replaces
them with a changed provider version. No credentials or holdout data requested.
"""
import datetime
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'data/acquisition/portugal-2013'
FILES=['yearly_summary_files.txt','AttributesReadme.txt','modis_2013_Portugal.csv','viirs-snpp_2013_Portugal.csv']

def acquire(target=TARGET):
    rule=json.loads((ROOT/'reports/HISTORICAL_ACQUISITION_RULE.json').read_text())
    assert rule['first_candidate_month']=='2013-01' and rule['declared_before_new_detection_counts']
    manifest_path=target/'ACQUISITION_MANIFEST.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        assert {item['file'] for item in manifest['files']}==set(FILES)
        for item in manifest['files']:
            assert hashlib.sha256((target/item['file']).read_bytes()).hexdigest()==item['sha256'], 'Existing original changed'
        return manifest
    target.mkdir(parents=True,exist_ok=True)
    assert not any((target/name).exists() for name in FILES), 'Partial acquisition: inspect rather than overwrite'
    manifest={'candidate_month':'2013-01','rule':'reports/HISTORICAL_ACQUISITION_RULE.json',
        'scope':'Portugal country files; only fixed AOI January2013 processing is permitted by this candidate','files':[]}
    for name in FILES:
        url='https://firms.modaps.eosdis.nasa.gov/data/country/'+name
        with urlopen(url,timeout=25) as response:
            data=response.read(2_000_001)
            assert len(data)<=2_000_000 and response.status==200,'Unexpected source response'
            headers={key:response.headers.get(key) for key in ['Content-Type','Content-Length','Last-Modified','ETag']}
            assert not headers['Content-Length'] or int(headers['Content-Length'])==len(data)
        (target/name).write_bytes(data)
        manifest['files'].append({'file':name,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'http_headers':headers,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    result=acquire()
    print(json.dumps({'state':'ACQUIRED_OR_VERIFIED','candidate_month':result['candidate_month'],
        'files':[{'file':item['file'],'sha256':item['sha256']} for item in result['files']]},indent=2))
