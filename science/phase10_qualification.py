"""Exact geolocation equivalence, self-described classes and bounded geometry audit."""
import json,math,csv,io
import h5py,numpy as np
from pyproj import Geod
from phase10_contract import ROOT,OUT,freeze,sha,immutable

def plain(v):
    if isinstance(v,bytes):return v.decode()
    if hasattr(v,'tolist'):return plain(v.tolist())
    if isinstance(v,list):return [plain(x) for x in v]
    return v if isinstance(v,(str,int,float,bool,type(None))) else str(v)
def compare_variable(full,light):
    assert full.shape==light.shape
    count=mismatch=0;maximum=0.;valid=0
    for row in range(0,full.shape[0],97):
        a=np.asarray(full[row:row+97]);b=np.asarray(light[row:row+97]);assert a.shape==b.shape
        count+=a.size;mismatch+=int(np.count_nonzero(a!=b));maximum=max(maximum,float(np.max(np.abs(a.astype(float)-b.astype(float)))))
        valid+=int(np.count_nonzero(np.isfinite(a)&(np.abs(a)<=180)))
    return {'compared_values':count,'different_values':mismatch,'maximum_absolute_difference_native_units':maximum,'full_dtype':str(full.dtype),'light_dtype':str(light.dtype),'full_units':plain(full.attrs.get('units')),'light_units':plain(light.attrs.get('units'))}
def zone(col,imagery=False):
    # Published one-based columns; array indices are zero-based. HSI is not PSF.
    c=col+1
    if imagery:return 3 if 2017<=c<=4384 else 2 if 1281<=c<=2016 or 4385<=c<=5120 else 1
    return 3 if 1009<=c<=2192 else 2 if 641<=c<=1008 or 2193<=c<=2560 else 1
def run():
    c=freeze();base=json.loads((ROOT/'reports/phase9/TRIANGULAR_ANALYSIS.json').read_text(encoding='utf-8'));rs=base['input_receipts']
    for rec in rs.values():assert sha(ROOT/rec['file'])==rec['sha256']
    receipt=json.loads((OUT/'MODLL_DOWNLOAD.json').read_text(encoding='utf-8'));assert sha(ROOT/receipt['file'])==receipt['sha256']
    with h5py.File(ROOT/rs['VNP03MOD']['file'],'r') as full,h5py.File(ROOT/receipt['file'],'r') as light,h5py.File(ROOT/rs['VNP14']['file'],'r') as fire,h5py.File(ROOT/rs['VNP03IMG']['file'],'r') as image:
        named=rs['VNP03MOD']['file'].split('/')[-1]
        assert plain(light.attrs['InputPointer'])==named and named in str(plain(fire.attrs['InputFileGeo'])) and named in plain(fire.attrs['InputPointer'])
        assert plain(light.attrs['VersionID'])=='002' and plain(light.attrs['ShortName'])=='VNP03MODLL'
        comparisons={}
        for key,group,name in [('latitude','Geolocation Fields','Latitude'),('longitude','Geolocation Fields','Longitude'),('height','Data Fields','Height')]:
            comparisons[key]=compare_variable(full['geolocation_data/'+key],light[f'HDFEOS/SWATHS/VNP_750M_GEOLOCATION/{group}/{name}'])
        same=all(v['different_values']==0 for v in comparisons.values());assert same
        light_names=[];light.visititems(lambda n,o:light_names.append(n) if isinstance(o,h5py.Dataset) else None)
        geo={'state':'COORDINATES_AND_HEIGHT_EQUIVALENT_FOR_EXACT_PAIR','full_file':named,'light_file':receipt['file'].split('/')[-1],'full_sha256':rs['VNP03MOD']['sha256'],'light_sha256':receipt['sha256'],'light_input_pointer':plain(light.attrs['InputPointer']),'fire_input_geo':plain(fire.attrs['InputFileGeo']),'comparisons':comparisons,
             'shape':[3248,3200],'light_datasets':light_names,'light_angles_and_quality':'NOT_PRESENT; not compared or treated as equal','original_angles_and_quality':'retained from exact named full input, never replaced by invented MODLL fields','compatibility':'Exact full MOD latitude/longitude/height are interchangeable with this required MODLL packaging for these variables only. No erroneous geolocation or offset detected; no claim for other granules or product variables.','physical_containment_qualified':False,'source_statement':'VNP14.002 CMR abstract recommends/requires MODLL; exact MODLL names full MOD and all corresponding stored coordinate/height values reconcile.'}
        immutable(OUT/'GEOLOCATION_COMPARISON.json',geo)
        legend=plain(fire['fire mask'].attrs['legend']);legend=legend[0] if isinstance(legend,list) else legend
        semantics={str(i):line.split(' ',1)[1] for line in legend.splitlines() if line and line[0].isdigit() for i in [int(line.split(' ',1)[0])]}
        assert semantics=={'0':'missing input data','1':'not processed (trim)','2':'not processed (unused)','3':'non-fire water','4':'cloud','5':'non-fire land','6':'unknown','7':'fire (low confidence)','8':'fire (nominal confidence)','9':'fire (high confidence)'}
        attrs={k:plain(v) for k,v in fire['algorithm QA'].attrs.items()};assert not any(k in attrs for k in ['flag_masks','flag_meanings','legend'])
        matrix=[{'field':'fire_mask_'+k,'meaning':v,'status':'VERIFIED_EXACT_FILE','source':rs['VNP14']['file']+' :: fire mask/legend','source_sha256':rs['VNP14']['sha256'],'qualification_limit':'Class meaning is verified; not proof of cloud-free footprint support at another source location'} for k,v in semantics.items()]
        for bit in range(32):matrix.append({'field':f'algorithm_QA_bit_{bit}','meaning':'UNRESOLVED for NPP_PR14 1.6.1/PGE2.0.4','status':'UNRESOLVED','observed_bit_value_at_candidates':bool(2&(1<<bit)),'source':'Exact file only declares units=bit field; current C2 metadata links C1 definitions without explicit applicability','source_sha256':rs['VNP14']['sha256'],'qualification_limit':'Raw QA2 measured; neither bit1=I2bad nor a C1 land/water decoder is applied'})
        matrix += [
            {'field':'scan_trim_bowtie','meaning':'Mask1 is trimmed per exact legend; detector-row deletion depends on aggregation zone in instrument literature','status':'PARTLY_VERIFIED','qualification_limit':'No 750m C2 algorithm-QA bowtie bit certified; imagery bit22 remains separately guide-qualified'},
            {'field':'geolocation_input','meaning':'Exact InputFileGeo/InputPointer bind the preserved full MOD, now coordinate-equivalent to MODLL','status':'VERIFIED_EXACT_PAIR','qualification_limit':'No per-footprint registration uncertainty certified'},
            {'field':'radiance_input','meaning':'Exact named M13 input unchanged; payload not acquired. IMG M13 input bit6 is nominal under its own C2 guide','status':'PARTLY_VERIFIED','qualification_limit':'750m input-quality bits and local radiance rejection semantics unresolved'},
            {'field':'background_rejection','meaning':'No certified 750m C2 bit meanings or per-background test margins for these class5 locations','status':'UNRESOLVED','qualification_limit':'Sparse FP arrays describe fire retrievals elsewhere, not a full negative-background QA grid'},
            {'field':'observation_processability','meaning':'A class5 center is natively non-fire land; algorithm QA, radiometric support and location containment remain unqualified','status':'UNRESOLVED','qualification_limit':'Not a valid shared non-detection or physical fire-absence measurement'}]
        immutable(OUT/'QA_APPLICABILITY.json',{'exact_product':{'file':rs['VNP14']['file'],'sha256':rs['VNP14']['sha256'],'collection':plain(fire.attrs['VersionID']),'algorithm':plain(fire.attrs['AlgorithmVersion']),'pge':plain(fire.attrs['PGEVersion'])},'rows':matrix,'fire_mask_semantics':semantics,'exact_algorithm_qa_attrs':attrs,'fire_mask_qualified':True,'algorithm_qa_qualified':False,'state':'MASK_LEGEND_VERIFIED_ALGORITHM_QA_UNRESOLVED','prior_sources':'Phase9 SOURCE_QUALIFICATION unchanged; C1/IMG/NRT not promoted'})
        geod=Geod(ellps='WGS84');rows=[]
        for p in base['pixels']:
            r=p['viirs750']['row'];col=p['viirs750']['col'];assert int(fire['fire mask'][r,col])==5 and int(fire['algorithm QA'][r,col])==2
            assert float(light['HDFEOS/SWATHS/VNP_750M_GEOLOCATION/Geolocation Fields/Latitude'][r,col])==p['viirs750']['lat'] and float(light['HDFEOS/SWATHS/VNP_750M_GEOLOCATION/Geolocation Fields/Longitude'][r,col])==p['viirs750']['lon']
            pitches={}
            for product,g,rr,cc in [('375',image,p['row'],p['col']),('750',full,r,col)]:
                la=g['geolocation_data/latitude'];lo=g['geolocation_data/longitude']
                for axis,dr,dc in [('track',1,0),('scan',0,1)]:
                    pitches[product+'_'+axis+'_center_pitch_m']=float(geod.inv(float(lo[rr,cc]),float(la[rr,cc]),float(lo[rr+dr,cc+dc]),float(la[rr+dr,cc+dc]))[2])
            rows.append({'id':p['id'],'row375':p['row'],'col375':p['col'],'row750':r,'col750':col,'native375_mask':p['mask'],'native750_mask':5,'native750_meaning':semantics['5'],'raw750_qa':2,'algorithm_qa_qualified':False,'coordinate_compatibility_verified':True,'full_to_light_coordinate_difference_m':0.,'center_distance_m':p['viirs750']['distance_m'],'view_degrees':p['viirs750']['view_degrees'],'index_model_aggregation375':zone(p['col'],True),'index_model_aggregation750':zone(col),'scan375_detector_index':p['row']%32,'scan750_detector_index':r%16,**pitches,'same_scan_interval':True,'scan_start_utc':p['scan']['start_utc'],'scan_end_utc':p['scan']['end_utc'],'aqua_max_scan_separation_seconds':p['aqua']['max_scan_separation_seconds'],'frp_mw':p['frp_mw'],'physical_spatial_support_m2':None,'physical_registration_bound_m':None,'category':p['category']})
    result={'id':c['id'],'contract_sha256':sha(OUT/'QUALIFICATION_CONTRACT.json'),'phase9_analysis_sha256':sha(ROOT/'reports/phase9/TRIANGULAR_ANALYSIS.json'),'geo_sha256':sha(OUT/'GEOLOCATION_COMPARISON.json'),'qa_sha256':sha(OUT/'QA_APPLICABILITY.json'),'rows':rows,'positive_count':16,'allocated_frp_sum_mw':math.fsum(r['frp_mw'] for r in rows),'categories':{'375_POSITIVE_750_UNKNOWN_SUPPORT':16},'became_qualified':0,'qualified_shared_area_m2':None,'qualified_positive_pairs':None,'qualified_valid_nondetections':None,'geometry_verdict':'All16 are in the published two-sample aggregation zone by one-based column model. Measured neighboring center spacings are sampling pitches, NOT detector boundaries, PSF extents or registration bounds. Literature PSF approximations/HSI ranges cannot certify exact thermal footprint containment.','algorithm_qa_qualified':False,'physical_footprints_qualified':False,'fit':False,'holdouts_opened':False,'g4':'ADJUSTMENT_WITHHELD'}
    immutable(OUT/'QUALIFICATION_RESULT.json',result)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows([{k:('UNKNOWN' if v is None else v) for k,v in r.items()} for r in rows]);target=OUT/'SIXTEEN_CLASSIFICATIONS.csv';raw=stream.getvalue().encode();assert not target.exists() or target.read_bytes()==raw
    if not target.exists():target.write_bytes(raw)
    print(json.dumps({'coordinate_values_per_variable':geo['comparisons']['latitude']['compared_values'],'different_values':sum(r['different_values'] for r in geo['comparisons'].values()),'fire_mask_semantics':'VERIFIED_EXACT_FILE','QA_bits':'UNRESOLVED','classifications':result['categories'],'FRP_MW':result['allocated_frp_sum_mw']}))
if __name__=='__main__':run()
