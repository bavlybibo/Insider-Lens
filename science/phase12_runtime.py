"""Actual process-local replay timings/memory for the new deterministic partition."""
from pathlib import Path
import contextlib,io,json,time
from canada_runtime import memory
import phase12_partition,phase12_oracle
r={}
for name,module in [('production',phase12_partition),('independent_oracle',phase12_oracle)]:
 start=time.perf_counter()
 with contextlib.redirect_stdout(io.StringIO()):module.run()
 r[name+'_elapsed_s']=time.perf_counter()-start
r['memory']=memory();r['scope']='Warm deterministic Phase12 production and original-archive oracle-index replay; no acquisition, holdout fitting, browser or GPU included.'
(Path(__file__).resolve().parents[1]/'reports/phase12/RUNTIME_MEMORY.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))
