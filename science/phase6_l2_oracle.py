"""Recount source HDF arrays independently of the L2 processing implementation."""
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import time
import h5py
import numpy as np
from canada_oracle import project

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase6'
DLL_HANDLE=os.add_dll_directory(str(ROOT/'.venv/phase6-hdf4')) if os.name=='nt' else None
from pyhdf.SD import SD,SDC

def run():
    start=time.perf_counter();manifest=json.loads((OUT/'L2_DOWNLOAD_MANIFEST.json').read_text());audit=json.loads((OUT/'L2_SUPPORT_AUDIT.json').read_text());contract=json.loads((OUT/'COHORT_CONTRACT.json').read_text())
    receipts={(r['day'],r['product']):r for r in manifest['receipts']};checks=[]
    for day,products in audit['results'].items():
        for product,expected in products.items():
            geo_product={'MYD14':'MYD03','VNP14':'VNP03MOD','VNP14IMG':'VNP03IMG'}[product]
            fp=ROOT/receipts[day,product]['file'];gp=ROOT/receipts[day,geo_product]['file'];modis=product=='MYD14'
            for p,rec in [(fp,receipts[day,product]),(gp,receipts[day,geo_product])]:
                with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==rec['sha256']
            if modis:
                f=SD(str(fp),SDC.READ);g=SD(str(gp),SDC.READ)
                m=f.select('fire mask');q=f.select('algorithm QA');lat=g.select('Latitude');lon=g.select('Longitude');zen=g.select('SensorZenith');height,width=m.info()[2]
            else:
                f=h5py.File(fp,'r');g=h5py.File(gp,'r');m=f['fire mask'];q=f['algorithm QA'];lat=g['geolocation_data/latitude'];lon=g['geolocation_data/longitude'];zen=g['geolocation_data/sensor_zenith'];height,width=m.shape
            hist=Counter();qh=Counter();cells=Counter();view={v:[0,0,0] for v in [30,40,50]};total=0;zmin=999.;zmax=-999.;geobad=0
            # Different block size and independent interval arithmetic/aggregation.
            for y in range(0,height,113):
                sl=np.s_[y:min(height,y+113),:];la=np.array(lat[sl]);lo=np.array(lon[sl]);mask=np.array(m[sl]);qa=np.array(q[sl],dtype='uint32');z=np.array(zen[sl],dtype='float64')/100
                selected=(lo>=-120)&(lo<-110)&(la>=49)&(la<55);total+=int(np.count_nonzero(selected))
                mm=mask[selected];qq=qa[selected];zz=z[selected];hist.update(map(int,mm));qh.update(map(int,qq))
                if len(zz):zmin=min(zmin,min(zz));zmax=max(zmax,max(zz))
                gf=np.zeros_like(mask) if modis else np.array(g['geolocation_data/quality_flag'][sl]);geobad+=int(np.count_nonzero(selected&(gf!=0)))
                valid375=(gf[selected]==0)
                if product=='VNP14IMG':
                    for bit in [0,1,2,3,4,5,6,22]:valid375 &= (qq&(2**bit))==0
                for v in [30,40,50]:
                    a=(zz>=0)&(zz<=v);b=a&((mm==5)|((mm>=7)&(mm<=9)))
                    view[v][0]+=int(np.count_nonzero(a));view[v][1]+=int(np.count_nonzero(b));view[v][2]+=int(np.count_nonzero(b&valid375)) if product=='VNP14IMG' else 0
                for longitude,latitude,cl in zip(lo[selected],la[selected],mm):
                    x0,y0=project(float(longitude),float(latitude));cells[(math.floor(x0/10000),math.floor(y0/10000),int(cl))]+=1
            assert total==expected['aoi_pixel_centers'];assert dict(sorted(hist.items()))=={int(k):v for k,v in expected['mask_counts'].items()};assert dict(qh)=={int(k):v for k,v in expected['qa_word_counts'].items()}
            assert abs(zmin-expected['view_zenith_min_degrees'])<1e-8 and abs(zmax-expected['view_zenith_max_degrees'])<1e-8, (day,product,float(zmin),float(zmax),expected['view_zenith_min_degrees'],expected['view_zenith_max_degrees'])
            wanted={(c['i'],c['j'],int(k)):v for c in expected['cells'] for k,v in c['mask_counts'].items()};assert cells==wanted
            for v,nums in view.items():
                if product!='VNP14IMG':nums[2]=None
                assert nums==[expected['view_sensitivity'][str(v)][k] for k in ['aoi_centers_within_view','mask_land_or_fire_centers_within_view','fully_QA_screened_375m_centers']]
            assert expected['nonzero_geolocation_quality_centers']==(None if modis else geobad)
            checks.append({'day':day,'product':product,'aoi_centers':total,'mask_histogram':'PASS','all_grid_class_multiplicities':'PASS','view_30_40_50':'PASS'})
            if modis:f.end();g.end()
            else:f.close();g.close()
    assert len(checks)==5
    assert all(audit['results']['2022-06-01'][p]['view_sensitivity']['50']['aoi_centers_within_view']==0 for p in ['MYD14','VNP14','VNP14IMG'])
    assert audit['nominal_offsets_minutes']['2022-06-08']>30
    assert audit['qualified_observation_denominator'] is None and audit['g4']=='ADJUSTMENT_WITHHELD'
    result={'state':'PASS','checks':checks,'method':'source HDF arrays re-read at113-row blocks; Python Counter and independent EPSG9820 cell projection; exhaustive class/QA/view counts; no production L2 imports',
        'l2_audit_sha256':hashlib.sha256((OUT/'L2_SUPPORT_AUDIT.json').read_bytes()).hexdigest(),'elapsed_seconds':time.perf_counter()-start,
        'primary_shared_support_rejection':'REPRODUCED','human_review':'NOT_PERFORMED'}
    (OUT/'L2_INDEPENDENT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
