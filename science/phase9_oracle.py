"""Independent raw-mask enumeration, scalar Vincenty associations and FRP recount.

Does not import Phase9 production code or its projection/geodesic implementation.
"""
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import h5py
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase9'
HANDLE=os.add_dll_directory(str(ROOT/'.venv/phase6-hdf4')) if os.name=='nt' else None
from pyhdf.SD import SD,SDC
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def vincenty(lon1,lat1,lon2,lat2):
    if lon1==lon2 and lat1==lat2:return 0.
    f=1/298.257223563;a=6378137.;b=a*(1-f);u1=math.atan((1-f)*math.tan(math.radians(lat1)));u2=math.atan((1-f)*math.tan(math.radians(lat2)));s1,c1=math.sin(u1),math.cos(u1);s2,c2=math.sin(u2),math.cos(u2);L=math.radians(lon2-lon1);lam=L
    for _ in range(100):
        sn,cn=math.sin(lam),math.cos(lam);ss=math.hypot(c2*sn,c1*s2-s1*c2*cn)
        if ss==0:return 0.
        cs=s1*s2+c1*c2*cn;sigma=math.atan2(ss,cs);sa=c1*c2*sn/ss;ca2=1-sa*sa;c2sm=cs-2*s1*s2/ca2 if ca2 else 0.;C=f/16*ca2*(4+f*(4-3*ca2));old=lam;lam=L+(1-C)*f*sa*(sigma+C*ss*(c2sm+C*cs*(-1+2*c2sm*c2sm)))
        if abs(lam-old)<1e-13:break
    else:raise AssertionError('Vincenty did not converge; no substituted distance')
    u2s=ca2*(a*a-b*b)/(b*b);A=1+u2s/16384*(4096+u2s*(-768+u2s*(320-175*u2s)));B=u2s/1024*(256+u2s*(-128+u2s*(74-47*u2s)));ds=B*ss*(c2sm+B/4*(cs*(-1+2*c2sm*c2sm)-B/6*c2sm*(-3+4*ss*ss)*(-3+4*c2sm*c2sm)))
    return b*A*(sigma-ds)
def pool(f,g,modis,bbox):
    la=g.select('Latitude') if modis else g['geolocation_data/latitude'];lo=g.select('Longitude') if modis else g['geolocation_data/longitude'];mask=f.select('fire mask') if modis else f['fire mask'];qa=f.select('algorithm QA') if modis else f['algorithm QA'];z=g.select('SensorZenith') if modis else g['geolocation_data/sensor_zenith'];shape=mask.info()[2] if modis else mask.shape;w,s,e,n=bbox;items=[]
    for row in range(0,shape[0],107):
        sl=np.s_[row:min(row+107,shape[0]),:];lat=np.array(la[sl]);lon=np.array(lo[sl]);rr,cc=np.where((lat>=s)&(lat<n)&(lon>=w)&(lon<e))
        if not len(rr):continue
        mm=np.array(mask[sl]);qq=np.array(qa[sl]);zz=np.array(z[sl])
        for r,col in zip(rr,cc):items.append((row+int(r),int(col),float(lon[r,col]),float(lat[r,col]),int(mm[r,col]),int(qq[r,col]),int(zz[r,col])/100))
    return items
def run():
    begin=time.perf_counter();a=json.loads((OUT/'TRIANGULAR_ANALYSIS.json').read_text());c=json.loads((OUT/'ANALYSIS_CONTRACT.json').read_text());m=json.loads((ROOT/'reports/phase8/DETAIL_DOWNLOAD_MANIFEST.json').read_text());rs={r['product']:r for r in m['receipts']}
    for r in rs.values():assert digest(ROOT/r['file'])==r['sha256']
    f=h5py.File(ROOT/rs['VNP14IMG']['file'],'r');g=h5py.File(ROOT/rs['VNP03IMG']['file'],'r');v=h5py.File(ROOT/rs['VNP14']['file'],'r');vg=h5py.File(ROOT/rs['VNP03MOD']['file'],'r');mf=SD(str(ROOT/rs['MYD14']['file']),SDC.READ);mg=SD(str(ROOT/rs['MYD03']['file']),SDC.READ)
    raw_positive=[p for p in pool(f,g,False,c['aoi_wsen']) if p[4] in [7,8,9]];assert len(raw_positive)==16
    w,s,e,n=c['aoi_wsen'];halo=[w-.05,s-.05,e+.05,n+.05];assert halo==a['candidate_pool']['bbox_wsen']
    candidates=pool(v,vg,False,halo);modis=pool(mf,mg,True,halo);assert len(candidates)==a['candidate_pool']['VIIRS750_centers'] and len(modis)==a['candidate_pool']['AQUA_centers']
    assert len({(p[2],p[3]) for p in raw_positive})==16
    named_inputs=[]
    for source in [f,v]:
        named_inputs.append(set(re.findall(r'VNP02CCMOD\.A\d{7}\.\d{4}\.002\.\d+\.nc',str(source.attrs['InputPointer']))))
    assert named_inputs[0]==named_inputs[1]=={a['same_named_M13_input']}
    supplied={(p['row'],p['col']):p for p in a['pixels']};assert len(supplied)==16 and set(supplied)=={(p[0],p[1]) for p in raw_positive}
    sparse_rows=np.array(f['FP_line']);sparse_cols=np.array(f['FP_sample']);power=np.array(f['FP_power']);radiance=np.array(f['FP_Rad13']);background=np.array(f['FP_MeanRad13']);checks=[];frp=[];groups=defaultdict(list);max_error=0.
    for r,col,lon,lat,mask,q,z in raw_positive:
        row=supplied[r,col];assert (lon,lat,mask,q,z)==(row['lon'],row['lat'],row['mask'],row['raw_qa'],row['view_degrees'])
        index=np.where((sparse_rows==r)&(sparse_cols==col))[0];assert len(index)==1;i=int(index[0]);assert float(power[i])==row['frp_mw'];frp.append(float(power[i]))
        expected375=[bool((q//(2**bit))%2) for bit in range(23)];assert list(row['qa375'][k] for k in ['I1_input_bad','I2_input_bad','I3_input_bad','I4_input_bad','I5_input_bad','geolocation_input_bad','M13_input_bad','unambiguous_fire_night','background_pixel','bright_pixel_rejection','candidate_pixel','scene_background_day','contextual_test1','contextual_test2','contextual_test3','contextual_test4_day','pixel_saturation_day','glint_day','potential_SAA','fire_over_water','persistence_test1','persistence_test2','residual_bowtie'])==expected375
        assert q%128==0 and (q//4194304)%2==0 and int(g['geolocation_data/quality_flag'][r,col])==0
        ranked=sorted(((vincenty(lon,lat,p[2],p[3]),p) for p in candidates),key=lambda x:(x[0],x[1][0],x[1][1]))
        for (distance,p),actual in zip(ranked[:4],row['viirs750']['neighbor_candidates']):
            assert p==(actual['row'],actual['col'],actual['lon'],actual['lat'],actual['mask'],actual['qa'],actual['view_degrees']);error=abs(distance-actual['distance_m']);max_error=max(max_error,error);assert error<.002
        distance,p=ranked[0];assert (p[0],p[1])==(row['viirs750']['row'],row['viirs750']['col'])
        md,mp=min(((vincenty(lon,lat,p[2],p[3]),p) for p in modis),key=lambda x:(x[0],x[1][0],x[1][1]));assert mp==(row['aqua']['row'],row['aqua']['col'],row['aqua']['lon'],row['aqua']['lat'],row['aqua']['mask'],row['aqua']['qa'],row['aqua']['view_degrees']);assert abs(md-row['aqua']['distance_m'])<.002
        scan375=r//32;scan750=p[0]//16;assert scan375==scan750
        for key in ['scan_start_time','scan_end_time','ev_mid_time','scan_quality']:assert np.array_equal(g['scan_line_attributes/'+key][scan375],vg['scan_line_attributes/'+key][scan750])
        for key,utc_key in [('scan_start_time','start_utc'),('scan_end_time','end_utc')]:
            raw_seconds=float(g['scan_line_attributes/'+key][scan375])
            utc=(datetime(1993,1,1,tzinfo=timezone.utc)+timedelta(seconds=raw_seconds-10)).isoformat().replace('+00:00','Z')
            assert utc==row['scan'][utc_key]==row['viirs750']['scan'][utc_key]
        assert np.array_equal(g['navigation_data/orb_pos_ev_mid'][scan375],vg['navigation_data/orb_pos_ev_mid'][scan750])
        assert row['category']=='375_POSITIVE_750_UNKNOWN_SUPPORT' and row['viirs750']['qa_qualified'] is False and row['qualified_shared_support_m2'] is None
        assert row['cloud_adjacency']==int(f['FP_AdjCloud'][i])==0 and row['confidence']==int(f['FP_confidence'][i])==8
        assert row['water_adjacency']==int(f['FP_AdjWater'][i])==0
        assert row['geolocation_flag']==int(g['geolocation_data/quality_flag'][r,col])==0
        assert row['viirs750']['geolocation_flag']==int(vg['geolocation_data/quality_flag'][p[0],p[1]])
        assert row['duplicate_native_address'] is False and row['duplicate_center'] is False and row['residual_bowtie'] is False
        groups[(r//2,col//2)].append(i);checks.append({'id':row['id'],'row':r,'col':col,'nearest750_row':p[0],'nearest750_col':p[1],'mask750':p[4],'raw_qa750':p[5],'distance_m':distance,'same_scan':'PASS','category':row['category'],'frp_mw':float(power[i]),'state':'PASS'})
    assert math.fsum(frp)==a['allocated_frp_sum_mw'];assert len(groups)==12
    for key,indices in groups.items():
        group=next(x for x in a['allocation_groups'] if (x['candidate_750_row'],x['candidate_750_col'])==key)
        assert len(indices)==group['selected_count'];assert len({float(radiance[i]) for i in indices})==len({float(background[i]) for i in indices})==len({float(power[i]) for i in indices})==1
        assert math.fsum(float(power[i]) for i in indices)==group['selected_fraction_sum_mw']
        siblings=set(np.where((sparse_rows//2==key[0])&(sparse_cols//2==key[1]))[0].tolist())
        assert siblings==set(indices) and len(siblings)==group['same_index_group_positive_siblings'] and group['siblings_outside_aoi']==0
    result={'state':'PASS','analysis_sha256':digest(OUT/'TRIANGULAR_ANALYSIS.json'),'contract_sha256':digest(OUT/'ANALYSIS_CONTRACT.json'),'checks':checks,'positive_count':16,'allocated_frp_sum_mw':math.fsum(frp),'allocation_consistent_groups':len(groups),'max_nearest_geodesic_difference_m':max_error,'raw_mask_enumeration':'107row blocks, independent from sparse production enumeration','nearest_method':'independent scalar WGS84 Vincenty, exhaustive finite halo pool; production uses PROJ Geod','same_platform_scan_and_navigation':'all16 PASS','qa750_qualification':'UNRESOLVED; QAword2 NOT decoded with375m policy','physical_containment':'NOT_QUALIFIED','qualified_shared_area_m2':None,'fit':False,'g4':'ADJUSTMENT_WITHHELD'}
    raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode();path=OUT/'INDEPENDENT_VALIDATION.json'
    if path.exists():assert path.read_bytes()==raw
    else:path.write_bytes(raw)
    f.close();g.close();v.close();vg.close();mf.end();mg.end();print(json.dumps({'state':'PASS','positive_count':16,'frp_mw':math.fsum(frp),'groups':12,'max_distance_difference_m':max_error,'runtime_seconds':time.perf_counter()-begin}))
if __name__=='__main__':run()
