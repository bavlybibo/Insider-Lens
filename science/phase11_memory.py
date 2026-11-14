"""Measure the new native recount in one process; original artifacts stay fixed."""
import contextlib,io,json,time
from pathlib import Path
from canada_runtime import memory
import phase11_retention,phase11_oracle
results={}
for name,module in [('production',phase11_retention),('independent_oracle',phase11_oracle)]:
    start=time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):module.run()
    results[name+'_elapsed_s']=time.perf_counter()-start
results['memory']=memory();results['scope']='Warm replay of Phase11 native production and original-archive raw-index oracle; excludes browser, acquisition and system cache.'
(Path(__file__).resolve().parents[1]/'reports/phase11/RUNTIME_MEMORY.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print(json.dumps(results))
