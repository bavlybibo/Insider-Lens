"""Sixteen-pixel evidence, provisional center associations and allocated FRP.

No nearest-center or index association is a physical observation footprint.
No C1 or375m QA policy is transferred to the exact750m Collection2 product.
"""
from collections import Counter,defaultdict
import csv
import datetime as dt
import io
import json
import math
import re
import numpy as np
from pyproj import Geod
from phase6_l2 import SD,SDC,h5py,plain
from phase9_contract import ROOT,OUT,freeze,immutable,sha

QA375=['I1_input_bad','I2_input_bad','I3_input_bad','I4_input_bad','I5_input_bad','geolocation_input_bad','M13_input_bad','unambiguous_fire_night','background_pixel','bright_pixel_rejection','candidate_pixel','scene_background_day','contextual_test1','contextual_test2','contextual_test3','contextual_test4_day','pixel_saturation_day','glint_day','potential_SAA','fire_over_water','persistence_test1','persistence_test2','residual_bowtie']
def decode375(q):return {name:bool(q&(1<<i)) for i,name in enumerate(QA375)}
def classification(associated,time_ok,footprint_ok,qa_ok,mask):
    if not associated or not time_ok:return 'UNMATCHED_TIME_OR_GEOMETRY'
    if not footprint_ok or not qa_ok:return '375_POSITIVE_750_UNKNOWN_SUPPORT'
    if mask in [7,8,9]:return '375_POSITIVE_750_POSITIVE'
    if mask==5:return '375_POSITIVE_750_VALID_NONDETECTION'
    if mask in [0,1,2,4,6]:return '375_POSITIVE_750_INVALID_OR_CLOUD'
    return '375_POSITIVE_750_UNKNOWN_SUPPORT'
def utc93(value):return (dt.datetime(1993,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(seconds=float(value)-10)).isoformat().replace('+00:00','Z')
def scan(g,row,product):
    if product=='MYD14':
        i=row//10;starts=g.select('EV start time');lo=float(starts[i]);hi=float(starts[i+1]);flag=None
    else:
        i=row//(32 if product=='VNP14IMG' else 16);lo=float(g['scan_line_attributes/scan_start_time'][i]);hi=float(g['scan_line_attributes/scan_end_time'][i]);flag=int(g['scan_line_attributes/scan_quality'][i])
    return {'id':i,'start_tai93':lo,'end_tai93':hi,'start_utc':utc93(lo),'end_utc':utc93(hi),'scan_quality':flag,'meaning':'full scan interval, not exact pixel exposure time'}
def centers(f,g,modis,bbox):
    lat=g.select('Latitude') if modis else g['geolocation_data/latitude'];lon=g.select('Longitude') if modis else g['geolocation_data/longitude'];mask=f.select('fire mask') if modis else f['fire mask'];qa=f.select('algorithm QA') if modis else f['algorithm QA'];zen=g.select('SensorZenith') if modis else g['geolocation_data/sensor_zenith'];shape=mask.info()[2] if modis else mask.shape
    w,s,e,n=bbox;out=[]
    for row in range(0,shape[0],61):
        sl=np.s_[row:min(row+61,shape[0]),:];la=np.asarray(lat[sl]);lo=np.asarray(lon[sl]);rr,cc=np.where((la>=s)&(la<n)&(lo>=w)&(lo<e))
        if not len(rr):continue
        mm=np.asarray(mask[sl]);qq=np.asarray(qa[sl]);zz=np.asarray(zen[sl])
        for r,col in zip(rr,cc):out.append({'row':row+int(r),'col':int(col),'lon':float(lo[r,col]),'lat':float(la[r,col]),'mask':int(mm[r,col]),'qa':int(qq[r,col]),'view_degrees':int(zz[r,col])/100})
    return out
def nearest(points,lon,lat):
    geod=Geod(ellps='WGS84');n=len(points);_,_,distance=geod.inv(np.full(n,lon),np.full(n,lat),[p['lon'] for p in points],[p['lat'] for p in points]);order=sorted(range(n),key=lambda i:(float(distance[i]),points[i]['row'],points[i]['col']))
    return [{**points[i],'distance_m':float(distance[i])} for i in order[:4]]
def run():
    c=freeze();manifest=json.loads((ROOT/'reports/phase8/DETAIL_DOWNLOAD_MANIFEST.json').read_text());rs={r['product']:r for r in manifest['receipts']}
    for r in rs.values():assert sha(ROOT/r['file'])==r['sha256']
    f=h5py.File(ROOT/rs['VNP14IMG']['file'],'r');g=h5py.File(ROOT/rs['VNP03IMG']['file'],'r');v=h5py.File(ROOT/rs['VNP14']['file'],'r');vg=h5py.File(ROOT/rs['VNP03MOD']['file'],'r');a=SD(str(ROOT/rs['MYD14']['file']),SDC.READ);ag=SD(str(ROOT/rs['MYD03']['file']),SDC.READ)
    aoi=c['aoi_wsen'];halo=[aoi[0]-.05,aoi[1]-.05,aoi[2]+.05,aoi[3]+.05];vc=centers(v,vg,False,halo);ac=centers(a,ag,True,halo)
    vectors={name:np.asarray(f[name][:]) for name in f if name.startswith('FP_')};indices=np.where((vectors['FP_longitude']>=aoi[0])&(vectors['FP_longitude']<aoi[2])&(vectors['FP_latitude']>=aoi[1])&(vectors['FP_latitude']<aoi[3]))[0];assert len(indices)==16
    m13_pattern=r'VNP02CCMOD\.A\d{7}\.\d{4}\.002\.\d+\.nc'
    m13_img=set(re.findall(m13_pattern,str(plain(f.attrs['InputPointer']))));m13_mod=set(re.findall(m13_pattern,str(plain(v.attrs['InputPointer']))));assert m13_img==m13_mod and len(m13_img)==1
    rows=[];groups=defaultdict(list);seen=set();positions=set();nav=[]
    for ordinal,index in enumerate(indices):
        r=int(vectors['FP_line'][index]);col=int(vectors['FP_sample'][index]);lon=float(vectors['FP_longitude'][index]);lat=float(vectors['FP_latitude'][index]);q=int(f['algorithm QA'][r,col]);mask=int(f['fire mask'][r,col]);flags=decode375(q)
        assert mask==int(vectors['FP_confidence'][index])==8;assert float(g['geolocation_data/longitude'][r,col])==lon and float(g['geolocation_data/latitude'][r,col])==lat
        duplicate=(r,col) in seen;seen.add((r,col));geoduplicate=(lon,lat) in positions;positions.add((lon,lat))
        fp=float(vectors['FP_power'][index]);assert math.isfinite(fp) and fp>0
        n=nearest(vc,lon,lat);near=n[0];am=nearest(ac,lon,lat)[0];t=scan(g,r,'VNP14IMG');vt=scan(vg,near['row'],'VNP14');at=scan(ag,am['row'],'MYD14')
        time_equal=t['id']==vt['id'] and t['start_tai93']==vt['start_tai93'] and t['end_tai93']==vt['end_tai93'];assert time_equal
        orbit_difference=float(np.max(np.abs(np.asarray(g['navigation_data/orb_pos_ev_mid'][t['id']])-np.asarray(vg['navigation_data/orb_pos_ev_mid'][vt['id']]))));nav.append(orbit_difference)
        geo_flag=int(g['geolocation_data/quality_flag'][r,col]);vflag=int(vg['geolocation_data/quality_flag'][near['row'],near['col']]);modis_bound=max(abs(at[k]-t[j]) for k in ['start_tai93','end_tai93'] for j in ['start_tai93','end_tai93'])
        index_candidate=(r//2,col//2);key=f'{index_candidate[0]}:{index_candidate[1]}'
        raw={k:plain(value[index]) for k,value in vectors.items()}
        row={'id':f'F{ordinal+1:02d}','granule':PathName(rs['VNP14IMG']['file']),'row':r,'col':col,'lon':lon,'lat':lat,'mask':mask,'confidence':int(vectors['FP_confidence'][index]),'raw_qa':q,'qa375':flags,'geolocation_flag':geo_flag,'view_degrees':int(g['geolocation_data/sensor_zenith'][r,col])/100,'cloud_adjacency':int(vectors['FP_AdjCloud'][index]),'water_adjacency':int(vectors['FP_AdjWater'][index]),'frp_mw':fp,'frp_state':'POSITIVE_REPORTED_ALLOCATED_MW','scan_track_dimensions_m':None,'duplicate_native_address':duplicate,'duplicate_center':geoduplicate,'residual_bowtie':flags['residual_bowtie'],'scan':t,'raw_sparse_fields':raw,
            'allocation_group_candidate':key,'index_candidate_matches_nearest_center':index_candidate==(near['row'],near['col']),
            'viirs750':{**near,'granule':PathName(rs['VNP14']['file']),'geolocation_flag':vflag,'scan':vt,'same_scan_interval':time_equal,'qa_qualified':False,'footprint_qualified':False,'location_support':'UNKNOWN','neighbor_candidates':n,'native_mask_meaning':'native land-class code5; qualified non-detection NOT established' if near['mask']==5 else 'raw class only'},
            'aqua':{**am,'granule':PathName(rs['MYD14']['file']),'scan':at,'max_scan_separation_seconds':modis_bound,'qa_table4':{'land_water':am['qa']&3,'day':(am['qa']>>4)&1,'adjacent_cloud':(am['qa']>>20)&1,'adjacent_water':(am['qa']>>21)&1,'glint':(am['qa']>>22)&3},'location_support':'UNKNOWN','footprint_qualified':False},
            'category':classification(True,time_equal,False,False,near['mask']),'qualified_shared_support_m2':None,
            'source_hashes':{product:receipt['sha256'] for product,receipt in rs.items()}}
        rows.append(row);groups[key].append(row['id'])
    allocation=[]
    for key,ids in sorted(groups.items()):
        rr,cc=map(int,key.split(':'));siblings=[i for i in range(len(vectors['FP_line'])) if int(vectors['FP_line'][i])//2==rr and int(vectors['FP_sample'][i])//2==cc];selected=[row for row in rows if row['id'] in ids]
        radiance=set(float(vectors['FP_Rad13'][i]) for i in siblings);background=set(float(vectors['FP_MeanRad13'][i]) for i in siblings);power=set(float(vectors['FP_power'][i]) for i in siblings)
        allocation.append({'candidate_750_row':rr,'candidate_750_col':cc,'selected_ids':ids,'selected_count':len(ids),'same_index_group_positive_siblings':len(siblings),'siblings_outside_aoi':len(siblings)-len(ids),'equal_M13_radiance':len(radiance)==1,'equal_background_radiance':len(background)==1,'equal_allocated_frp':len(power)==1,'allocated_frp_each_mw':next(iter(power)) if len(power)==1 else None,'selected_fraction_sum_mw':math.fsum(row['frp_mw'] for row in selected),'all_sibling_fraction_sum_mw':math.fsum(float(vectors['FP_power'][i]) for i in siblings),'interpretation':'allocation-consistent index/radiance group, NOT independently qualified physical footprint or VNP14 fire retrieval'})
    result={'id':c['id'],'state':'COMPUTED_SUPPORT_WITHHELD','contract_sha256':sha(OUT/'ANALYSIS_CONTRACT.json'),'parent_support_sha256':c['parent_support_sha256'],'parent_manifest_sha256':c['parent_manifest_sha256'],'input_receipts':rs,'pixels':rows,'category_counts':dict(Counter(row['category'] for row in rows)),'allocated_frp_sum_mw':math.fsum(row['frp_mw'] for row in rows),'allocation_groups':allocation,'same_named_M13_input':next(iter(m13_img)),
        'same_scan_interval_count':sum(row['viirs750']['same_scan_interval'] for row in rows),'maximum_orbit_mid_vector_difference_m':max(nav),'nearest750_mask_counts':dict(Counter(row['viirs750']['mask'] for row in rows)),
        'candidate_pool':{'bbox_wsen':halo,'VIIRS750_centers':len(vc),'AQUA_centers':len(ac),'meaning':'finite nearest-center search, not a support-area denominator'},'qualified_shared_support_m2':None,'qualified_disagreements':None,'fit':False,'improvement_demonstrated':False,'generalization':False,'holdouts_opened':False,'g4':'ADJUSTMENT_WITHHELD','source_qa750_qualified':False,'physical_footprints_qualified':False,
        'raw_frp_zero_semantics':'guide3.1.3: zero/null can represent unavailable retrieval (e.g.M13 saturation/background failure), never proof of no fire','meanings':'native allocated MW summed once per unique row/sample, not burned area, total energy, biomass loss, independent retrieval count or physical fires',
        'controls':'Phase8 negative controls remain unqualified; this all-positive follow-up does not create independent fire-absence controls'}
    immutable(OUT/'TRIANGULAR_ANALYSIS.json',result)
    a.end();ag.end();f.close();g.close();v.close();vg.close()
    fields=['id','granule','row','col','lon','lat','mask','confidence','raw_qa','view_degrees','cloud_adjacency','geolocation_flag','frp_mw','frp_state','residual_bowtie','duplicate_native_address','scan_track_dimensions_m','category','qualified_shared_support_m2']
    stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(fields+['viirs750_row','viirs750_col','viirs750_native_mask','viirs750_raw_qa','viirs750_center_distance_m','same_scan_interval','aqua_row','aqua_col','aqua_native_mask','aqua_center_distance_m','maximum_aqua_time_offset_seconds','fire375_sha256','fire750_sha256','aqua_sha256','contract_sha256','g4'])
    for row in rows:writer.writerow([row[k] if row[k] is not None else 'UNKNOWN' for k in fields]+[row['viirs750'][k] for k in ['row','col','mask','qa','distance_m']]+[row['viirs750']['same_scan_interval']]+[row['aqua'][k] for k in ['row','col','mask','distance_m','max_scan_separation_seconds']]+[rs[k]['sha256'] for k in ['VNP14IMG','VNP14','MYD14']]+[result['contract_sha256'],result['g4']])
    target=OUT/'POSITIVE_EVIDENCE.csv';raw=stream.getvalue().encode()
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    print(json.dumps({'pixels':len(rows),'frp_sum_mw':result['allocated_frp_sum_mw'],'allocation_groups':len(allocation),'group_sizes':dict(Counter(x['selected_count'] for x in allocation)),'categories':result['category_counts'],'nearest750_masks':result['nearest750_mask_counts'],'same_scan_intervals':result['same_scan_interval_count'],'orbit_vector_difference_m':max(nav)}))
def PathName(value):return value.split('/')[-1]
if __name__=='__main__':run()
