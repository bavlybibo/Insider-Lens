"""Measure a five-mask replay without changing scientific result artifacts."""
import json
from pathlib import Path
import time
from pyproj import Transformer
from phase6_l2 import process
from canada_runtime import memory

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/phase6'
if __name__=='__main__':
    c=json.loads((R/'COHORT_CONTRACT.json').read_text());a=json.loads((R/'L2_SUPPORT_AUDIT.json').read_text());m=json.loads((R/'L2_DOWNLOAD_MANIFEST.json').read_text())
    receipts={(r['day'],r['product']):r for r in m['receipts']};transform=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True);start=time.perf_counter();checks=[]
    for day,ps in a['results'].items():
        for product,expected in ps.items():
            geo={'MYD14':'MYD03','VNP14':'VNP03MOD','VNP14IMG':'VNP03IMG'}[product]
            result=process(ROOT/receipts[day,product]['file'],ROOT/receipts[day,geo]['file'],product,c,transform)
            assert json.loads(json.dumps(result))==expected;checks.append({'day':day,'product':product,'state':'IDENTICAL_RESULT'})
    result={'checks':checks,'elapsed_seconds':time.perf_counter()-start,**memory(),'note':'Warm local file replay of all five masks; no download, fit or result artifact rewrite. Separate from browser benchmarks.'}
    (R/'L2_RUNTIME_MEMORY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
