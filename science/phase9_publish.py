"""Separately versioned triangular evidence, bound to original Phase8 release."""
import json
from phase9_contract import ROOT,OUT,sha,immutable
def run():
    a=json.loads((OUT/'TRIANGULAR_ANALYSIS.json').read_text());o=json.loads((OUT/'INDEPENDENT_VALIDATION.json').read_text())
    assert o['state']=='PASS' and o['analysis_sha256']==sha(OUT/'TRIANGULAR_ANALYSIS.json') and o['contract_sha256']==a['contract_sha256']
    identity='p9-'+a['contract_sha256'][:12]+'-'+o['analysis_sha256'][:12];folder=ROOT/'public/data/phase9'/identity;folder.mkdir(parents=True,exist_ok=True);artifacts={}
    for name in ['ANALYSIS_CONTRACT.json','TRIANGULAR_ANALYSIS.json','INDEPENDENT_VALIDATION.json','POSITIVE_EVIDENCE.csv']:
        target=folder/name;raw=(OUT/name).read_bytes()
        if target.exists():assert target.read_bytes()==raw
        else:target.write_bytes(raw)
        artifacts[name]={'sha256':sha(target),'bytes':len(raw)}
    bundle={'id':identity,'parent_canada':'ca-92a935da01aecfa3e1d130b3','parent_support_sha256':a['parent_support_sha256'],'analysis_sha256':o['analysis_sha256'],'contract_sha256':a['contract_sha256'],'analysis':a,'independent':o,'artifacts':artifacts,'g4':'ADJUSTMENT_WITHHELD','fit':False,'qualified_shared_support_m2':None}
    immutable(folder/'triangle.json',bundle);immutable(ROOT/'public/data/phase9/index.json',{'id':identity,'file':'/data/phase9/'+identity+'/triangle.json','sha256':sha(folder/'triangle.json')})
    print(json.dumps({'id':identity,'bytes':(folder/'triangle.json').stat().st_size,'pixels':len(a['pixels'])}))
if __name__=='__main__':run()
