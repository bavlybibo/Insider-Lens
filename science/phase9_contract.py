"""Frozen follow-up analysis, never a replacement of the Phase8 event or outcomes."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase9'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def immutable(p,obj):
    raw=(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode();p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==raw,'Immutable mismatch: '+p.name
    else:p.write_bytes(raw)
def freeze():
    c={'id':'p9-swf095-triangular-v1','scope':'all16 Phase8 positives, same exact six inputs; known16/0/0 outcome, not blinded or a new calibration cohort',
       'parent_contract_sha256':sha(ROOT/'reports/phase8/COHORT_CONTRACT.json'),'parent_support_sha256':sha(ROOT/'reports/phase8/SUPPORT_AUDIT.json'),
       'parent_manifest_sha256':sha(ROOT/'reports/phase8/DETAIL_DOWNLOAD_MANIFEST.json'),'aoi_wsen':[-117.2,54.75,-116.4,55.0],
       'candidate_halo_degrees':.05,'association':'exhaustive nearest geodesic center within declared AOI+halo, stable row/sample tie breaks; test floor(row/2),floor(col/2) separately as unqualified array-index hypothesis',
       'no_containment_assumption':True,'time':'same scan IDs and raw scan-start/end equality between exact375/750 geolocation inputs; bounded scan times, never exact exposure time',
       'view':{'primary':40,'sensitivity':[30,50]},
       'geometry':'center distances and navigation equality are evidence, never physical pixel containment; require independently justified response boundaries and uncertainty for qualified support',
       'qa':'375 C2 guide1.2 Table2;750 exact C2 applicability must be established separately;MODIS C6/C6.1 Table4 unchanged',
       'categories':['375_POSITIVE_750_POSITIVE','375_POSITIVE_750_VALID_NONDETECTION','375_POSITIVE_750_INVALID_OR_CLOUD','375_POSITIVE_750_UNKNOWN_SUPPORT','UNMATCHED_TIME_OR_GEOMETRY'],
       'category_gate':'without qualified location support and applicable750 QA use UNKNOWN_SUPPORT, even when nearest center has native mask5; candidate association failure is UNMATCHED, not non-detection',
       'frp':'sum unique native row/sample fractions once; inspect equal M13/background radiance and FRP fractions in index candidate groups, including same-group siblings outsideAOI only. Never add a reconstructed group total to its fractions; no claim of independent375m radiometry.',
       'estimands':['native positive pixel multiplicity','reported allocated FRP MW','candidate source mask classifications','qualified shared support m2 or null'],
       'fit':False,'baseline':'unchanged source-separated native observations','adequacy':'one event/pass cannot satisfy parent30pass/5week floor; no new model or generalized coefficient',
       'uncertainty':'exact finite counts; report center-distance and40degree/scan-bound sensitivities, not fitted confidence intervals; physical boundary uncertainty remains null until justified',
       'budget':{'new_science_payload_bytes':0,'max_reference_requests':12,'max_reference_bytes':20000000},
       'holdouts':'unchanged and not evaluated','g4':'ADJUSTMENT_WITHHELD','stop':'complete all16 and independent oracle; bounded official documentation search, never select a replacement fire sample'}
    immutable(OUT/'ANALYSIS_CONTRACT.json',c);return c
if __name__=='__main__':freeze();print(sha(OUT/'ANALYSIS_CONTRACT.json'))
