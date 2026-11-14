"""Publish a separate hash-bound research result after both independent checks."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/phase6'
SHA=lambda b:hashlib.sha256(b).hexdigest()
def read(n):return json.loads((R/n).read_text())
def run():
    common=read('COMMON_SUPPORT_AUDIT.json');oracle=read('INDEPENDENT_VALIDATION.json');l2=read('L2_SUPPORT_AUDIT.json');lo=read('L2_INDEPENDENT_VALIDATION.json')
    assert oracle['state']==lo['state']=='PASS'
    assert oracle['audit_sha256']==SHA((R/'COMMON_SUPPORT_AUDIT.json').read_bytes())
    assert lo['l2_audit_sha256']==SHA((R/'L2_SUPPORT_AUDIT.json').read_bytes())
    rows=read('RESEARCH_ROWS.json');assert SHA((R/'RESEARCH_ROWS.json').read_bytes())==oracle['research_rows_sha256']
    c=read('COHORT_CONTRACT.json');index=json.loads((ROOT/'public/data/canada/index.json').read_text());catalog=json.loads((ROOT/('public'+index['file'])).read_text())
    chunks=[]
    for source in c['sources']:
        cells=defaultdict(lambda:defaultdict(lambda:[0,0]))
        for r in rows:
            if r['source']!=source:continue
            i,j=int(r['x']//10000),int(r['y']//10000);r['cell']=f"{c['grid']['id']}:10000:{i}:{j}"
            cells[i,j][int(r['utc'][8:10])][0 if r['dn']=='D' else 1]+=1
        chunks.append({'candidate':catalog['candidate'],'source':source,'pc':'SP','month':'2022-06','grid':c['grid']['id'],
                       'cells':[[i,j,[[d,*counts] for d,counts in sorted(days.items())]] for (i,j),days in sorted(cells.items())]})
    summary={day:{p:{k:v for k,v in a.items() if k not in ['cells','qa_word_counts','examples','mask_legend']} for p,a in ps.items()} for day,ps in l2['results'].items()}
    sources={s:next(a for a in catalog['archives'] if a['request']==('845606' if s=='SNPP_VIIRS' else '845605')) for s in c['sources']}
    release={'id':'p6-'+common['contract_sha256'][:12]+'-'+SHA((R/'L2_SUPPORT_AUDIT.json').read_bytes())[:12],
             'parent_candidate':catalog['candidate'],'classification':common['classification'],'contract':c,'contract_sha256':common['contract_sha256'],
             'common':common,'independent':oracle,'l2':{k:v for k,v in l2.items() if k!='results'},'l2_products':summary,'l2_independent':lo,
             'rows':rows,'chunks':chunks,'sources':sources,'scientific_release':'RESEARCH_ONLY; G4 ADJUSTMENT_WITHHELD',
             'evidence_sha256':{n:SHA((R/n).read_bytes()) for n in ['COHORT_CONTRACT.json','COMMON_SUPPORT_AUDIT.json','RESEARCH_ROWS.json','RESEARCH_FRP.csv','RAW_FIELD_AUDIT.json','L2_SUPPORT_AUDIT.json','L2_INDEPENDENT_VALIDATION.json','INDEPENDENT_VALIDATION.json','ACCESS_AUDIT.json','L2_DOWNLOAD_MANIFEST.json']}}
    root=ROOT/'public/data/phase6'/release['id'];root.mkdir(parents=True,exist_ok=True)
    for name in release['evidence_sha256']:
        data=(R/name).read_bytes();p=root/name
        if p.exists():assert p.read_bytes()==data,'Research asset already sealed; use new identity'
        else:p.write_bytes(data)
    data=(json.dumps(release,separators=(',',':'),sort_keys=True)+'\n').encode();p=root/'bridge.json'
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
    pointer={'id':release['id'],'file':'/data/phase6/'+release['id']+'/bridge.json','sha256':SHA(data),'bytes':len(data)}
    (root.parent/'index.json').write_text(json.dumps(pointer,indent=2)+'\n');print(json.dumps(pointer))

if __name__=='__main__':run()
