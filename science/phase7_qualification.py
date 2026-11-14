"""Independent375m input QA and measured old/exact geolocation sensitivity."""
import hashlib
import json
import os
from pathlib import Path
from collections import Counter
import numpy as np
import h5py
from pyproj import Geod

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase7'
DLL=os.add_dll_directory(str(ROOT/'.venv/phase6-hdf4')) if os.name=='nt' else None
from pyhdf.SD import SD,SDC

def run():
    m=json.loads((OUT/'L2_EXACT_DOWNLOAD_MANIFEST.json').read_text());rs={(r['split'],r['product']):r for r in m['receipts']};a=json.loads((OUT/'EXACT_SUPPORT_AUDIT.json').read_text())
    c=json.loads((OUT/'SEARCH_CONTRACT.json').read_text());w,s,e,n=c['splits']['replication']['aoi_wsen']
    selected=0;nominal=0;land=0;geobad=0;inputbad=0;bowtie=0
    with h5py.File(ROOT/rs['replication','VNP14IMG']['file']) as f,h5py.File(ROOT/rs['replication','VNP03IMG']['file']) as g:
        for row in range(0,f['fire mask'].shape[0],113):
            sl=np.s_[row:row+113,:];lat=np.asarray(g['geolocation_data/latitude'][sl]);lon=np.asarray(g['geolocation_data/longitude'][sl]);inside=(lat>=s)&(lat<n)&(lon>=w)&(lon<e)
            q=np.asarray(f['algorithm QA'][sl])[inside];gf=np.asarray(g['geolocation_data/quality_flag'][sl])[inside];mask=np.asarray(f['fire mask'][sl])[inside]
            for word,flag,cl in zip(q,gf,mask):
                word=int(word);selected+=1;gb=int(flag)!=0;ib=any((word//(2**bit))%2 for bit in range(7));bb=(word//4194304)%2!=0
                geobad+=gb;inputbad+=ib;bowtie+=bb;valid=not(gb or ib or bb);nominal+=valid;land+=valid and int(cl)==5
    p=a['results']['replication']['products']['VNP14IMG']
    assert selected==p['aoi_pixel_centers'] and nominal==p['qa_375m_nominal_no_residual_bowtie_centers']
    assert land==p['view_sensitivity']['40']['fully_QA_screened_375m_centers']
    geo_changes=[];original=json.loads((OUT/'L2_DOWNLOAD_MANIFEST.json').read_text());old={(r['split'],r['product']):r for r in original['receipts']};gd=Geod(ellps='WGS84')
    for split in c['splits']:
        box=c['splits'][split]['aoi_wsen'];v=SD(str(ROOT/old[split,'MYD03']['file']),SDC.READ);z=SD(str(ROOT/rs[split,'MYD03']['file']),SDC.READ)
        distances=[];shape=v.select('Latitude').info()[2]
        for row in range(0,shape[0],113):
            sl=np.s_[row:row+113,:];la=np.array(v.select('Latitude')[sl]);lo=np.array(v.select('Longitude')[sl]);newla=np.array(z.select('Latitude')[sl]);newlo=np.array(z.select('Longitude')[sl]);w,s,e,n=box
            choose=((la>=s)&(la<n)&(lo>=w)&(lo<e))|((newla>=s)&(newla<n)&(newlo>=w)&(newlo<e))
            if choose.any():distances.extend(gd.inv(lo[choose],la[choose],newlo[choose],newla[choose])[2].tolist())
        v.end();z.end();geo_changes.append({'split':split,'same_array_indices_in_either_aoi':len(distances),'median_center_displacement_m':float(np.median(distances)),'max_center_displacement_m':max(distances),
            'meaning':'production-instance coordinate sensitivity, not sensor footprint accuracy or uncertainty bound'})
    result={'state':'PASS','exact_support_sha256':hashlib.sha256((OUT/'EXACT_SUPPORT_AUDIT.json').read_bytes()).hexdigest(),
        'independent375':{'aoi_centers':selected,'geolocation_flags_nonzero':geobad,'input_quality_nonnominal':inputbad,'residual_bowtie':bowtie,'nominal_centers':nominal,'nominal_land_centers':land,
            'meaning':'source-specific375m QA-screened centers only, not shared exposure area or qualified non-detection count'},'geo_instance_sensitivity':geo_changes,
        'footprint_validation':'NOT_QUALIFIED','full750m_qa':'C2_APPLICABILITY_UNRESOLVED'}
    path=OUT/'QUALIFICATION_SENSITIVITY.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
