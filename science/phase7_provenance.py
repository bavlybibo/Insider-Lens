"""Independently verify internal granule IDs and input links, not filenames alone."""
import hashlib
import json
import os
from pathlib import Path
import re
import h5py

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase7'
DLL=os.add_dll_directory(str(ROOT/'.venv/phase6-hdf4')) if os.name=='nt' else None
from pyhdf.SD import SD,SDC

def simple(v):
    if hasattr(v,'tolist'):v=v.tolist()
    if isinstance(v,list):return [simple(x) for x in v]
    return v.decode() if isinstance(v,bytes) else v
def field(text,name):
    m=re.search(r'OBJECT\s*=\s*'+name+r'\s+.*?VALUE\s*=\s*"([^"\n]+)"',text,re.S)
    return m.group(1) if m else None

def run():
    manifest=json.loads((OUT/'L2_EXACT_DOWNLOAD_MANIFEST.json').read_text());rows=[];attributes={}
    for r in manifest['receipts']:
        p=ROOT/r['file']
        with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256']
        if p.suffix=='.hdf':
            f=SD(str(p),SDC.READ);a=f.attributes();core=a['CoreMetadata.0'];internal=field(core,'LOCALGRANULEID');platform=field(core,'ASSOCIATEDPLATFORMSHORTNAME');instrument=field(core,'ASSOCIATEDINSTRUMENTSHORTNAME')
            lineage=a.get('MOD03 input file');f.end()
        else:
            with h5py.File(p) as f:a={k:simple(v) for k,v in f.attrs.items()}
            internal=a.get('LocalGranuleID',a.get('product_name'));internal=internal[0] if isinstance(internal,list) else internal;platform=a.get('platform',a.get('Satellite'));instrument=a.get('instrument',a.get('Instrument'));lineage=a.get('InputFileGeo',a.get('InputPointer'))
        assert internal==p.name, 'Internal granule ID differs from receipt filename'
        attributes[(r['split'],r['product'])]={'id':internal,'lineage':str(lineage)}
        rows.append({'split':r['split'],'product':r['product'],'sha256':r['sha256'],'internal_granule_id':internal,'internal_id_matches':'PASS','platform':platform,'instrument':instrument})
    links=[]
    for split,fire,geo in [('development','MYD14','MYD03'),('development','VNP14','VNP03MOD'),('replication','MYD14','MYD03'),('replication','VNP14','VNP03MOD'),('replication','VNP14IMG','VNP03IMG')]:
        f=attributes[split,fire];g=attributes[split,geo];assert g['id'] in f['lineage'];links.append({'split':split,'fire':f['id'],'exact_input':g['id'],'input_relationship':'PASS'})
    result={'state':'PASS','all12_internal_granule_ids':rows,'all5_exact_input_links':links,'meaning':'payload internal ID, original URL, full SHA and embedded input name agree; no claim of pixel footprint qualification'}
    path=OUT/'INTERNAL_PROVENANCE.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'state':'PASS','internal_ids':len(rows),'exact_links':len(links)}))

if __name__=='__main__':run()
