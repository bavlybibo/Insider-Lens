"""Read-only five-mask replay with actual process working-set measurement."""
import json
import time
from phase6_l2 import process
from phase7_contract import ROOT,OUT
from canada_runtime import memory
from pyproj import Transformer

if __name__=='__main__':
    c=json.loads((OUT/'SEARCH_CONTRACT.json').read_text());a=json.loads((OUT/'EXACT_SUPPORT_AUDIT.json').read_text());m=json.loads((OUT/'L2_EXACT_DOWNLOAD_MANIFEST.json').read_text());rs={(r['split'],r['product']):r for r in m['receipts']}
    t=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True);start=time.perf_counter();checks=[]
    for split,r in a['results'].items():
        for product,expected in r['products'].items():
            geo={'MYD14':'MYD03','VNP14':'VNP03MOD','VNP14IMG':'VNP03IMG'}[product]
            v=process(ROOT/rs[split,product]['file'],ROOT/rs[split,geo]['file'],product,{**c,'aoi_wsen':c['splits'][split]['aoi_wsen']},t)
            for field in ['aoi_pixel_centers','mask_counts','cells','view_sensitivity','exact_geolocation_input_identity']:
                assert json.loads(json.dumps(v[field]))==expected[field]
            checks.append({'split':split,'product':product,'state':'IDENTICAL_REPLAY'})
    result={'checks':checks,'elapsed_seconds':time.perf_counter()-start,**memory(),'limits':'warm local mask/geolocation replay, no acquisition latency; process memory includes Python and HDF libraries, excludes browser/GPU'}
    (OUT/'L2_RUNTIME_MEMORY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
