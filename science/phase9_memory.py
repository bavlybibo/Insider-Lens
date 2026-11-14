"""Replay actual production and independent computations without changing evidence."""
import json
import time
from canada_runtime import memory
from phase9_contract import OUT
from phase9_analysis import run as production
from phase9_oracle import run as independent
if __name__=='__main__':
    t=time.perf_counter();production();production_seconds=time.perf_counter()-t;t=time.perf_counter();independent();independent_seconds=time.perf_counter()-t
    r={'production_seconds':production_seconds,'independent_seconds':independent_seconds,**memory(),'limits':'warm local replay of all16 and six preserved files; Python process includes HDF libraries; not acquisition/browser/GPU memory'}
    (OUT/'RUNTIME_MEMORY.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
