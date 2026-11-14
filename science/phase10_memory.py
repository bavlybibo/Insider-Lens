"""Warm replay and process memory; no original or frozen artifact writes."""
import json,time
from canada_runtime import memory
from phase10_contract import OUT
from phase10_qualification import run as production
from phase10_oracle import run as independent
if __name__=='__main__':
    t=time.perf_counter();production();p=time.perf_counter()-t;t=time.perf_counter();independent();i=time.perf_counter()-t
    result={'production_seconds':p,'independent_seconds':i,**memory(),'limits':'Warm local raw full-granule comparison and sixteen-pixel replay, includes HDF libraries; excludes browser/GPU, acquisition and system disk cache.'}
    (OUT/'RUNTIME_MEMORY.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
