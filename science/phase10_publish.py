"""New qualification namespace, no prior release pointer changes."""
import json,shutil
from phase10_contract import ROOT,OUT,sha,immutable
def run():
    read=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    result=read('QUALIFICATION_RESULT.json');oracle=read('INDEPENDENT_VALIDATION.json');assert oracle['state']=='PASS' and oracle['qualification_sha256']==sha(OUT/'QUALIFICATION_RESULT.json')
    identity='p10-'+sha(OUT/'QUALIFICATION_CONTRACT.json')[:12]+'-'+sha(OUT/'QUALIFICATION_RESULT.json')[:12];folder=ROOT/'public/data/phase10'/identity;folder.mkdir(parents=True,exist_ok=True)
    names=['QUALIFICATION_CONTRACT.json','QUALIFICATION_RESULT.json','INDEPENDENT_VALIDATION.json','GEOLOCATION_COMPARISON.json','QA_APPLICABILITY.json','SIXTEEN_CLASSIFICATIONS.csv','SOURCE_QUALIFICATION.json','NASA_SUPPORT_QUESTION.md']
    for name in names:
        source=OUT/name;target=folder/name
        if target.exists():assert target.read_bytes()==source.read_bytes()
        else:shutil.copyfile(source,target)
    bundle={'id':identity,'phase9_analysis_sha256':result['phase9_analysis_sha256'],'qualification_sha256':sha(OUT/'QUALIFICATION_RESULT.json'),'contract_sha256':sha(OUT/'QUALIFICATION_CONTRACT.json'),'result':result,'independent':oracle,'geo':read('GEOLOCATION_COMPARISON.json'),'qa':read('QA_APPLICABILITY.json'),'artifacts':{n:{'sha256':sha(folder/n),'bytes':(folder/n).stat().st_size} for n in names},'g4':'ADJUSTMENT_WITHHELD'}
    immutable(folder/'qualification.json',bundle);immutable(ROOT/'public/data/phase10/index.json',{'id':identity,'file':'/data/phase10/'+identity+'/qualification.json','sha256':sha(folder/'qualification.json')});print(identity)
if __name__=='__main__':run()
