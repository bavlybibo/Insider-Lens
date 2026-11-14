"""Read-only warm replay; actual Python process working set, not browser memory."""
import json
import time
from pyproj import Transformer
from phase6_l2 import process
from canada_runtime import memory
from phase8_contract import ROOT,OUT
if __name__=='__main__':
    c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());a=json.loads((OUT/'SUPPORT_AUDIT.json').read_text());m=json.loads((OUT/'DETAIL_DOWNLOAD_MANIFEST.json').read_text());rs={r['product']:r for r in m['receipts']}
    t=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True);start=time.perf_counter();checks=[]
    for product,geo in [('MYD14','MYD03'),('VNP14','VNP03MOD'),('VNP14IMG','VNP03IMG')]:
        got=process(ROOT/rs[product]['file'],ROOT/rs[geo]['file'],product,c,t)
        for field in ['aoi_pixel_centers','mask_counts','cells','view_sensitivity','exact_geolocation_input_identity']:
            assert json.loads(json.dumps(got[field]))==a['results'][product][field]
        checks.append({'product':product,'state':'IDENTICAL_REPLAY'})
    r={'checks':checks,'elapsed_seconds':time.perf_counter()-start,**memory(),'limits':'warm local three-mask replay; memory includes Python/HDF libraries, excludes browser, GPU and payload acquisition'}
    (OUT/'L2_RUNTIME_MEMORY.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
