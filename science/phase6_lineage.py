"""Probe exactly named Aqua geolocation inputs using the documented LAADS path.

This is a provider-specific authentication test, not an inferred product absence.
"""
import argparse
import json
from pathlib import Path,PurePosixPath
from phase6_access import probe
from phase6_l2 import SD,SDC,ROOT,OUT

def run(token_file):
    private=Path(token_file).resolve();assert not private.is_relative_to(ROOT)
    token=private.read_text().strip();results=[]
    c=json.loads((OUT/'COHORT_CONTRACT.json').read_text())
    for day in c['l2_discovery_days']:
        path=next((ROOT/'data/acquisition/phase6/l2'/day).glob('MYD14*.hdf'));f=SD(str(path),SDC.READ)
        name=PurePosixPath(f.attributes()['MOD03 input file']).name;f.end()
        doy=name.split('.')[1][5:]
        url='https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MYD03/2022/'+doy+'/'+name
        results.append({'day':day,'expected_geo_input':name,**probe(url,'GET',token)})
    (OUT/'EXACT_GEO_INPUT_ACCESS.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k in ['day','expected_geo_input','status','classification']} for r in results]))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--token-file',required=True);a=p.parse_args();run(a.token_file)
