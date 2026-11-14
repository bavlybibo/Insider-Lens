"""Actual event masks, scan-time bounds and explicitly unqualified IFOV sensitivity.

The nominal MODIS model implements guide section8.4.6. It is NOT a shared
opportunity footprint: response edges, orientation error and C2 750m QA remain
unqualified. No geometric output from this sensitivity can enter B1.
"""
from collections import Counter
import datetime as dt
import json
import math
import time
import numpy as np
from pyproj import Geod, Transformer
from phase6_l2 import process, SD, SDC, h5py, plain
from phase7_support import read_points, modis_qa
from phase7_discovery import area, intersect
from phase8_contract import ROOT, OUT, immutable, sha

def dimensions(sample):
    re=6378.137;r=re+705;s=.0014184397;theta=s*(sample-676.5)
    v=math.sqrt((re/r)**2-math.sin(theta)**2)
    return 1000*re*s*(math.cos(theta)/v-1),1000*r*s*(math.cos(theta)-v)

def nominal_ring(lon,lat,azimuth,sample,transform,scale=1):
    along,cross=dimensions(sample);geod=Geod(ellps='WGS84');ring=[]
    for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]:
        dx=a*along*scale/2;dy=b*cross*scale/2
        x,y,_=geod.fwd(lon,lat,azimuth+math.degrees(math.atan2(dy,dx)),math.hypot(dx,dy))
        ring.append(transform.transform(x,y))
    return ring

def scan_bounds(path,product,points):
    # NASA SDP Toolkit secTAI93 epoch is UTC midnight1993-01-01, not TAI midnight.
    # 10 leap seconds were inserted between that epoch and this June2023 cohort.
    epoch=dt.datetime(1993,1,1,tzinfo=dt.timezone.utc)
    def utc(t):return (epoch+dt.timedelta(seconds=float(t)-10)).isoformat().replace('+00:00','Z')
    if product=='MYD14':
        f=SD(str(path),SDC.READ);starts=np.array(f.select('EV start time')[:]);scans=sorted({p['line']//10 for p in points})
        assert all(i+1<len(starts) for i in scans)
        low=min(starts[i] for i in scans);high=max(starts[i+1] for i in scans);width=max(starts[i+1]-starts[i] for i in scans);flags=None;f.end()
    else:
        with h5py.File(path,'r') as g:
            scans=sorted({p['line']//(32 if product=='VNP14IMG' else 16) for p in points})
            starts=np.array(g['scan_line_attributes/scan_start_time']);ends=np.array(g['scan_line_attributes/scan_end_time'])
            low=min(starts[i] for i in scans);high=max(ends[i] for i in scans);width=max(ends[i]-starts[i] for i in scans)
            flags=dict(Counter(int(g['scan_line_attributes/scan_quality'][i]) for i in scans))
    return {'tai93_min':float(low),'tai93_max':float(high),'utc_start':utc(low),'utc_end':utc(high),'scan_ids':scans,
            'max_scan_bound_seconds':float(width),'scan_quality_counts':flags,
            'meaning':'conservative complete scan bounds, not exact pixel times; no paired footprint assignment'}

def run():
    start=time.perf_counter();c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());m=json.loads((OUT/'DETAIL_DOWNLOAD_MANIFEST.json').read_text())
    rs={r['product']:r for r in m['receipts']};t=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True)
    for r in rs.values():assert sha(ROOT/r['file'])==r['sha256']
    results={};mapped={};controls={};times={}
    for product,geo in [('MYD14','MYD03'),('VNP14','VNP03MOD'),('VNP14IMG','VNP03IMG')]:
        fp=ROOT/rs[product]['file'];gp=ROOT/rs[geo]['file']
        p=process(fp,gp,product,c,t);points,qcounts=read_points(fp,gp,product,c['aoi_wsen']);assert len(points)==p['aoi_pixel_centers']
        assert {str(k):v for k,v in qcounts.items()}=={str(k):v for k,v in p['qa_word_counts'].items()}
        assert p['exact_geolocation_input_identity']
        p['support_states_at_centers']=dict(Counter(r['support_state'] for r in points))
        p['positive_mask_centers']=sum(p['mask_counts'].get(k,0) for k in [7,8,9])
        p['native_frp_mw_sum']=sum(x['FP_power'] for x in p['aoi_sparse_fire_pixels'])
        if product=='MYD14':
            p['modis_table4_fields']={k:dict(Counter(map(int,v))) for k,v in modis_qa([r['qa'] for r in points]).items()}
        p['qa_qualified_for_shared_support']=False
        p['qa_interpretation']='C6/C6.1 Table4 decoded; complete response boundaries unqualified' if product=='MYD14' else 'C2 375m guide v1.2 decoded; distinct from750m' if product=='VNP14IMG' else 'Exact C2 750m bit applicability unresolved; historical C1 bits never promoted'
        times[product]=scan_bounds(gp,product,points);p['scan_time_bounds']=times[product]
        results[product]=p;mapped[product]=points
        controls[product]=process(fp,gp,product,{**c,'aoi_wsen':c['controls']['spatial_diagnostic_aoi']},t)
    bound=max(abs(times['MYD14'][a]-times['VNP14'][b]) for a in ['tai93_min','tai93_max'] for b in ['tai93_min','tai93_max'])
    assert bound<=600,'Measured scan timing exceeds frozen conservative limit'
    # Approximate instrument-derived MODIS IFOV geometry, never inferred from center spacing.
    # Intentionally do not build a VIIRS rectangle from a nominal resolution label.
    w,s,e,n=c['aoi_wsen'];clip=[t.transform(w+(e-w)*i/20,s) for i in range(20)]+[t.transform(e,s+(n-s)*i/20) for i in range(20)]+[t.transform(e-(e-w)*i/20,n) for i in range(20)]+[t.transform(w,n-(n-s)*i/20) for i in range(20)]
    f=SD(str(ROOT/rs['MYD03']['file']),SDC.READ);az=f.select('SensorAzimuth');shapes=[]
    totals={str(v):0. for v in [.9,1.,1.1]}
    for p in mapped['MYD14']:
        if p['mask'] not in [5,7,8,9] or p['view_zenith_degrees']>40:continue
        bearing=float(az[p['line'],p['sample']])*.01
        ring=nominal_ring(p['lon'],p['lat'],bearing,p['sample'],t)
        for scale in [.9,1.,1.1]:totals[str(scale)]+=area(intersect(nominal_ring(p['lon'],p['lat'],bearing,p['sample'],t,scale),clip))
        shapes.append({'line':p['line'],'sample':p['sample'],'azimuth':bearing,'xy':ring,'clipped_nominal_m2':area(intersect(ring,clip))})
    f.end()
    geometry={'state':'UNQUALIFIED_NOMINAL_IFOV_SENSITIVITY','source':'MODIS C6/C6.1 guide section8.4.6 equations11–13',
        'model':'spherical705km nominal altitude dimensions, geodesic WGS84 corners centered at exact input geolocation; sensor-azimuth orientation approximation',
        'count':len(shapes),'polygons':shapes,'clipped_sum_m2_by_linear_scale':totals,
        'limits':'sums are NOT unions or shared areas; overlap is not removed. +/-10% is a stress test, not a measured uncertainty bound. Sensor azimuth alone does not validate IFOV orientation/response edges. VIIRS aggregation and response geometry not reconstructed.',
        'qualified_shared_support_m2':None,'physical_boundary_uncertainty_m':None,'eligible_for_B1':False}
    immutable(OUT/'NOMINAL_GEOMETRY.json',geometry)
    a={'state':'B1_SUPPORT_WITHHELD','contract_sha256':sha(OUT/'COHORT_CONTRACT.json'),'manifest_sha256':sha(OUT/'DETAIL_DOWNLOAD_MANIFEST.json'),
       'results':results,'spatial_diagnostic':controls,'maximum_scan_bound_separation_seconds':bound,'metadata_endpoint_bound_seconds':480,
       'qualified_shared_support_m2':None,'matched_positive_observations':None,'valid_shared_negative_controls':None,'independent_fire_absence_controls':0,
       'B0':'actual source-separated native detections; independently recounted','B1':'WITHHELD_NO_QUALIFIED_DOMAIN','B2':'INCONCLUSIVE_NO_QUALIFIED_POSITIVE_SAMPLE',
       'B3':'distinct375m mask decoded, not merged','B4':'NOT_FITTED','fit':False,'improvement_demonstrated':False,'generalization':False,'holdouts_opened':False,
       'failures':['No independently qualified physical shared footprint boundary/uncertainty','C2 VNP14 750m QA applicability not established','One selected pass cannot meet30-pass/5-week fitting floor'],
       'g4':'ADJUSTMENT_WITHHELD','science_files':m['science_files'],'downloaded_bytes':m['total_bytes'],'elapsed_seconds':time.perf_counter()-start}
    replay_elapsed=a['elapsed_seconds']
    if (OUT/'SUPPORT_AUDIT.json').exists():
        # Immutable receipt keeps its first-generation runtime. All scientific
        # content is recomputed and byte-compared; replay time is logged separately.
        a['elapsed_seconds']=json.loads((OUT/'SUPPORT_AUDIT.json').read_text())['elapsed_seconds']
    immutable(OUT/'MASK_CENTERS.json',mapped);immutable(OUT/'SUPPORT_AUDIT.json',a)
    print(json.dumps({'products':{k:{f:v[f] for f in ['aoi_pixel_centers','mask_counts','positive_mask_centers','native_frp_mw_sum']} for k,v in results.items()},'max_time_separation_seconds':bound,'shared_area':None,'replay_elapsed_seconds':replay_elapsed,'first_generation_elapsed_seconds':a['elapsed_seconds']}))

if __name__=='__main__':run()
