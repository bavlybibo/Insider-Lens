"""Independent raw-array recount; no Phase7 production or Phase6 L2 imports."""
from collections import Counter
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import numpy as np
import h5py
from canada_oracle import project

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase7'
HANDLE=os.add_dll_directory(str(ROOT/'.venv/phase6-hdf4')) if os.name=='nt' else None
from pyhdf.SD import SD,SDC
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def utc(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00'))

def run(exact=False):
    prefix='EXACT_' if exact else ''
    start=time.perf_counter();c=json.loads((OUT/'SEARCH_CONTRACT.json').read_text());a=json.loads((OUT/(prefix+'SUPPORT_AUDIT.json')).read_text())
    m=json.loads((OUT/('L2_EXACT_DOWNLOAD_MANIFEST.json' if exact else 'L2_DOWNLOAD_MANIFEST.json')).read_text());mapped=json.loads((OUT/(prefix+'MASK_CENTERS.json')).read_text());discovery=json.loads((OUT/'DISCOVERY.json').read_text())
    rs={(r['split'],r['product']):r for r in m['receipts']};checks=[];metadata=[]
    for split,spec in c['splits'].items():
        # Independently rebuild pair identity/timing membership from cached CMR,
        # not the production shortlist. No cloud_cover or fire statistics used.
        prod={}
        for name in ['MYD14','VNP14']:
            entries=[]
            for day in spec['days']:
                p=ROOT/f'data/acquisition/phase7/metadata/{split}-{day}-{name}.json';r=json.loads(p.with_suffix('.receipt.json').read_text())
                assert sha(p)==r['sha256'];entries+=json.loads(p.read_text())['feed']['entry']
            prod[name]=entries
        pairs=set()
        for aa in prod['MYD14']:
            am=utc(aa['time_start'])+(utc(aa['time_end'])-utc(aa['time_start']))/2
            for vv in prod['VNP14']:
                vm=utc(vv['time_start'])+(utc(vv['time_end'])-utc(vv['time_start']))/2
                if abs((vm-am).total_seconds())<=600:
                    pairs.add((aa['producer_granule_id'],vv['producer_granule_id']))
        expected={(p['aqua']['id'],p['viirs750']['id']) for p in discovery['splits'][split]['ranked_pairs']}
        assert pairs==expected
        metadata.append({'split':split,'utc_candidate_pairs':len(pairs),'membership':'PASS','ranking':'not independently requalified as measured geometry; proxy is not VZA'})
        w,s,e,n=spec['aoi_wsen']
        for name,gname in [('MYD14','MYD03'),('VNP14','VNP03MOD')]+([('VNP14IMG','VNP03IMG')] if exact and split=='replication' else []):
            fp=ROOT/rs[split,name]['file'];gp=ROOT/rs[split,gname]['file'];assert sha(fp)==rs[split,name]['sha256'] and sha(gp)==rs[split,gname]['sha256']
            modis=name=='MYD14';f=SD(str(fp),SDC.READ) if modis else h5py.File(fp,'r');g=SD(str(gp),SDC.READ) if modis else h5py.File(gp,'r')
            mask=f.select('fire mask') if modis else f['fire mask'];qa=f.select('algorithm QA') if modis else f['algorithm QA']
            lat=g.select('Latitude') if modis else g['geolocation_data/latitude'];lon=g.select('Longitude') if modis else g['geolocation_data/longitude'];zen=g.select('SensorZenith') if modis else g['geolocation_data/sensor_zenith']
            shape=mask.info()[2] if modis else mask.shape;hist=Counter();qhist=Counter();views={v:0 for v in [30,40,50]};cells={v:Counter() for v in [5000,10000,20000]};points=[];fields={k:Counter() for k in ['land_water','day','potential_fire','adjacent_cloud','adjacent_water','glint_level','rejection_flags']}
            for row in range(0,shape[0],113):
                sl=np.s_[row:min(row+113,shape[0]),:];la=np.array(lat[sl]);lo=np.array(lon[sl]);mm=np.array(mask[sl]);qq=np.array(qa[sl]);zz=np.array(zen[sl])
                rr,cc=np.where((la>=s)&(la<n)&(lo>=w)&(lo<e))
                for r,col in zip(rr,cc):
                    cl=int(mm[r,col]);q=int(qq[r,col]);z=int(zz[r,col])/100;longitude=float(lo[r,col]);latitude=float(la[r,col]);hist[cl]+=1;qhist[q]+=1
                    for limit in views:views[limit]+=int(0<=z<=limit)
                    x,y=project(longitude,latitude)
                    for width in cells:cells[width][(math.floor(x/width),math.floor(y/width),cl)]+=1
                    points.append((row+int(r),int(col),longitude,latitude,cl,q,z))
                    if modis:
                        # Arithmetic extraction, not production bit-shift helper.
                        for k,base,mod in [('land_water',1,4),('day',16,2),('potential_fire',32,2),('adjacent_cloud',1048576,2),('adjacent_water',2097152,2),('glint_level',4194304,4),('rejection_flags',16777216,32)]:fields[k][(q//base)%mod]+=1
            expected=a['results'][split]['products'][name]
            assert dict(hist)=={int(k):v for k,v in expected['mask_counts'].items()};assert dict(qhist)=={int(k):v for k,v in expected['qa_word_counts'].items()}
            assert all(views[k]==expected['view_sensitivity'][str(k)]['aoi_centers_within_view'] for k in views)
            wanted=[(p['line'],p['sample'],p['lon'],p['lat'],p['mask'],p['qa'],p['view_zenith_degrees']) for p in mapped[split][name]]
            assert points==wanted, 'Every mapped native center must reconcile to arrays'
            cc=Counter({(x['i'],x['j'],int(k)):v for x in expected['cells'] for k,v in x['mask_counts'].items()});assert cells[10000]==cc
            from pyproj import Transformer
            transformer=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True)
            for width,counts in cells.items():
                other=Counter()
                for point in wanted:
                    x,y=transformer.transform(point[2],point[3]);other[(math.floor(x/width),math.floor(y/width),point[4])]+=1
                assert other==counts
            if modis:assert {k:{str(i):j for i,j in v.items()} for k,v in fields.items()}==expected['phase7_modis_qa_fields']
            checks.append({'split':split,'product':name,'aoi_centers':len(points),'mask_qa_view_all_points':'PASS','ellipsoidal_5_10_20km_bins':'PASS',
                'occupied_center_bins':{str(width):len({(i,j) for i,j,cl in counts}) for width,counts in cells.items()},
                'actual_footprint_intersection':'NOT_QUALIFIED','full_source_specific_qa':'PARTIAL_MODIS_TABLE4' if modis else 'C2_375M_GUIDE' if name=='VNP14IMG' else 'C2_APPLICABILITY_UNRESOLVED'})
            if modis:f.end();g.end()
            else:f.close();g.close()
    assert a['qualified_shared_support_m2'] is None and a['g4']=='ADJUSTMENT_WITHHELD' and not a['holdout_evaluation']
    result={'state':'PASS','support_audit_sha256':sha(OUT/(prefix+'SUPPORT_AUDIT.json')),'mapped_centers_sha256':sha(OUT/(prefix+'MASK_CENTERS.json')),'discovery_sha256':sha(OUT/'DISCOVERY.json'),
            'checks':checks,'metadata_checks':metadata,'method':'separate113row raw reads; scalarCounter QA; independent EPSG9820 vs PROJ5/10/20km; every mapped center tuple checked',
            'qualified_footprint_validation':'NOT_EXECUTED_NO_QUALIFIED_FOOTPRINTS','candidate_fit':False,'human_review':False,'elapsed_seconds':time.perf_counter()-start}
    path=OUT/(prefix+'INDEPENDENT_VALIDATION.json');assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':
    import sys
    run('--exact' in sys.argv)
