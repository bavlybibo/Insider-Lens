"""Bounded version-qualification follow-up; no new calibration sample."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase10';OUT.mkdir(exist_ok=True)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def immutable(path,obj):
    raw=(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
    if path.exists():assert path.read_bytes()==raw,'Immutable mismatch: '+path.name
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
def freeze():
    c={'id':'p10-swf095-qualification-v1','known_outcome':'Phase9 sixteen positives/22.37004065513611MW, all UNKNOWN_SUPPORT; disclosed follow-up, not blind',
       'phase9_contract_sha256':sha(ROOT/'reports/phase9/ANALYSIS_CONTRACT.json'),'phase9_analysis_sha256':sha(ROOT/'reports/phase9/TRIANGULAR_ANALYSIS.json'),'phase9_oracle_sha256':sha(ROOT/'reports/phase9/INDEPENDENT_VALIDATION.json'),
       'immutable_manifest_sha256':sha(ROOT/'reports/phase8/DETAIL_DOWNLOAD_MANIFEST.json'),'fixed_ids':[f'F{i:02d}' for i in range(1,17)],
       'aoi_wsen':[-117.2,54.75,-116.4,55.0],'date':'2023-06-13','no_new_outcome_selection':True,
       'questions':['Exact VNP14.002 NPP_PR14 1.6.1/PGE2.0.4 QA applicability','Exact MODLL versus MOD geolocation compatibility','Detector sampling versus effective response and registration uncertainty'],
       'budget':{'max_new_science_files':1,'product':'VNP03MODLL.002','exact_acquisition_key':'A2023164.1042.002','max_science_bytes':64000000,'max_reference_requests':18,'max_reference_bytes':30000000},
       'pair_selection':'same acquisition/collection as frozen VNP14; metadata-first, exact instance preferred; never replace original geolocation or candidate set',
       'geometry':'No nominal-resolution rectangles, no center-spacing Voronoi support. Report documented aggregation/positional bounds only within applicable scope; unknown physical response means UNKNOWN support.',
       'thresholds':'unchanged primary40degree, sensitivity30/50, parent scan bounds and30minute limit; no retrospective relaxation',
       'decision':'source-level QA fields require explicit applicability; raw values and physical support assessed separately; original sixteen candidates retained',
       'fit':False,'holdouts_opened':False,'minimum_sample':'inherited30qualified passes/fiveweeks not met','g4':'ADJUSTMENT_WITHHELD'}
    immutable(OUT/'QUALIFICATION_CONTRACT.json',c);return c
if __name__=='__main__':freeze();print('Phase10 contract frozen')
