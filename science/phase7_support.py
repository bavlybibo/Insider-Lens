"""Fail-closed support qualification and mapped, explicit native center evidence."""
from collections import Counter
import json
import time
import numpy as np
from pyproj import Transformer
from phase6_l2 import process, SD, SDC, h5py, plain
from phase7_contract import ROOT, OUT
from phase7_discovery import digest, immutable

def state(mask,geo_compatible=False,qa_qualified=False,footprint_qualified=False,temporal_qualified=False):
    if mask in [0,1,2,4]:return 'CLOUD_OR_INVALID'
    if not (geo_compatible and qa_qualified and footprint_qualified and temporal_qualified):return 'UNKNOWN_SUPPORT'
    if mask in [7,8,9]:return 'OBSERVED_POSITIVE_DETECTION'
    if mask==5:return 'QUALIFIED_OBSERVED_NONDETECTION'
    return 'UNKNOWN_SUPPORT'

def modis_qa(words):
    """Exact C6/C6.1 Table4 fields, NOT the incompatible 375m bit policy."""
    q=np.asarray(words,dtype=np.uint32)
    return {'land_water':q&3,'day':(q>>4)&1,'potential_fire':(q>>5)&1,
            'adjacent_cloud':(q>>20)&1,'adjacent_water':(q>>21)&1,'glint_level':(q>>22)&3,
            'rejection_flags':(q>>24)&31}

def read_points(fire_path,geo_path,product,bbox):
    modis=product=='MYD14'
    f=SD(str(fire_path),SDC.READ) if modis else h5py.File(fire_path,'r')
    g=SD(str(geo_path),SDC.READ) if modis else h5py.File(geo_path,'r')
    lat=g.select('Latitude') if modis else g['geolocation_data/latitude'];lon=g.select('Longitude') if modis else g['geolocation_data/longitude']
    mask=f.select('fire mask') if modis else f['fire mask'];qa=f.select('algorithm QA') if modis else f['algorithm QA']
    zen=g.select('SensorZenith') if modis else g['geolocation_data/sensor_zenith']
    shape=mask.info()[2] if modis else mask.shape;points=[];qa_counts=Counter();w,s,e,n=bbox
    for row in range(0,shape[0],64):
        sl=np.s_[row:min(shape[0],row+64),:];la=np.asarray(lat[sl]);lo=np.asarray(lon[sl]);inside=(la>=s)&(la<n)&(lo>=w)&(lo<e)
        if not inside.any():continue
        mm=np.asarray(mask[sl]);qq=np.asarray(qa[sl],dtype=np.uint32);zz=np.asarray(zen[sl],dtype=float)/100
        rr,cc=np.where(inside)
        for r,col in zip(rr,cc):
            m=int(mm[r,col]);q=int(qq[r,col]);qa_counts[q]+=1
            points.append({'line':row+int(r),'sample':int(col),'lon':float(lo[r,col]),'lat':float(la[r,col]),'mask':m,'qa':q,'view_zenith_degrees':float(zz[r,col]),
                           'native_class':'cloud' if m==4 else 'invalid' if m in [0,1,2] else 'positive' if m in [7,8,9] else 'nonfire_land' if m==5 else 'other_unknown',
                           'support_state':state(m)})
    if modis:f.end();g.end()
    else:f.close();g.close()
    return points,dict(sorted(qa_counts.items()))

def run(exact=False):
    started=time.perf_counter();c=json.loads((OUT/'SEARCH_CONTRACT.json').read_text());m=json.loads((OUT/('L2_EXACT_DOWNLOAD_MANIFEST.json' if exact else 'L2_DOWNLOAD_MANIFEST.json')).read_text())
    rs={(r['split'],r['product']):r for r in m['receipts']};t=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True)
    result={};mapped={}
    for split,spec in c['splits'].items():
        ps={};mapped[split]={}
        for product,geo in [('MYD14','MYD03'),('VNP14','VNP03MOD')]+([('VNP14IMG','VNP03IMG')] if exact else []):
            if (split,product) not in rs or (split,geo) not in rs:continue
            fire=ROOT/rs[split,product]['file'];geopath=ROOT/rs[split,geo]['file']
            assert digest(fire)==rs[split,product]['sha256'] and digest(geopath)==rs[split,geo]['sha256']
            p=process(fire,geopath,product,{**c,'aoi_wsen':spec['aoi_wsen']},t)
            points,qcounts=read_points(fire,geopath,product,spec['aoi_wsen'])
            assert len(points)==p['aoi_pixel_centers'] and {str(k):v for k,v in qcounts.items()}=={str(k):v for k,v in p['qa_word_counts'].items()}
            if product=='MYD14':
                counts={}
                for field,values in modis_qa([r['qa'] for r in points]).items():
                    vals,nums=np.unique(values,return_counts=True);counts[field]={str(int(k)):int(v) for k,v in zip(vals,nums)}
                p['phase7_modis_qa_fields']=counts;p['qa_interpretation']='C6/C6.1 user guide Table4 decoded independently of 375m; not full footprint/lineage qualification'
            elif product=='VNP14':p['qa_interpretation']='C2 750m exact bit policy unresolved; linked CMR guide/filespec describe C1, not assumed transferable'
            p['support_states_at_centers']=dict(Counter(r['support_state'] for r in points))
            ps[product]=p;mapped[split][product]=points
        selected=json.loads((OUT/f'{split.upper()}_CANDIDATE.json').read_text())['candidate']
        failures=[]
        for product,p in ps.items():
            if not p['exact_geolocation_input_identity']:failures.append(product+': geolocation production instance differs from exact named fire input')
            if p['view_sensitivity']['40']['aoi_centers_within_view']==0:failures.append(product+': zero centers satisfy frozen <=40deg view limit')
        failures.extend(['exact C2 750m algorithm-QA applicability not confirmed','actual oriented pixel-footprint intersections and per-pixel temporal support not qualified'])
        result[split]={'products':ps,'midpoint_offset_minutes':selected['midpoint_offset_minutes'] if selected else None,'failures':failures,
                       'state':'SUPPORT_NOT_QUALIFIED','qualified_shared_support_m2':None,'qualified_observation_opportunities':None,'fit':False}
    audit={'state':'B1_SUPPORT_WITHHELD','contract_sha256':digest(OUT/'SEARCH_CONTRACT.json'),'manifest_sha256':digest(OUT/('L2_EXACT_DOWNLOAD_MANIFEST.json' if exact else 'L2_DOWNLOAD_MANIFEST.json')),
           'results':result,'science_files':m['science_files'],'downloaded_bytes':m['total_bytes'],'qualified_shared_support_m2':None,
           'baseline':'unchanged source-separated native releases','B2':'INCONCLUSIVE_UNQUALIFIED_SUPPORT','B3':'NOT_FITTED','generalization':False,
           'g4':'ADJUSTMENT_WITHHELD','holdout_evaluation':False,'elapsed_seconds':time.perf_counter()-started,
           'mapping':'native pixel centers only; cloud/invalid codes actual, unqualified land/positive support unknown; no pixel polygons fabricated'}
    prefix='EXACT_' if exact else '';immutable(OUT/(prefix+'SUPPORT_AUDIT.json'),audit);immutable(OUT/(prefix+'MASK_CENTERS.json'),mapped)
    print(json.dumps({'science_files':m['science_files'],'results':{s:{p:{k:v[k] for k in ['aoi_pixel_centers','mask_counts','view_zenith_min_degrees','view_zenith_max_degrees','exact_geolocation_input_identity']} for p,v in r['products'].items()} for s,r in result.items()},'elapsed_seconds':audit['elapsed_seconds']}))

if __name__=='__main__':
    import sys
    run('--exact' in sys.argv)
