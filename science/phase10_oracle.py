"""Independent column-block equivalence and raw sixteen-pixel reconciliation."""
from pathlib import Path
import hashlib,json,math
import h5py,numpy as np
from phase9_oracle import vincenty
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase10'
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
    a=json.loads((OUT/'QUALIFICATION_RESULT.json').read_text());old=json.loads((ROOT/'reports/phase9/TRIANGULAR_ANALYSIS.json').read_text());rec=json.loads((OUT/'MODLL_DOWNLOAD.json').read_text());rs=old['input_receipts'];rows=a['rows']
    for r in [rec,*rs.values()]:assert digest(ROOT/r['file'])==r['sha256']
    assert a['phase9_analysis_sha256']==digest(ROOT/'reports/phase9/TRIANGULAR_ANALYSIS.json')
    checks={};max_pitch_error=0.;frp=[]
    with h5py.File(ROOT/rec['file'],'r') as ll,h5py.File(ROOT/rs['VNP03MOD']['file'],'r') as mod,h5py.File(ROOT/rs['VNP03IMG']['file'],'r') as img,h5py.File(ROOT/rs['VNP14']['file'],'r') as f,h5py.File(ROOT/rs['VNP14IMG']['file'],'r') as fi:
        for variable,category,light_name in [('latitude','Geolocation Fields','Latitude'),('longitude','Geolocation Fields','Longitude'),('height','Data Fields','Height')]:
            source=mod['geolocation_data/'+variable];light=ll[f'HDFEOS/SWATHS/VNP_750M_GEOLOCATION/{category}/{light_name}'];count=0;different=0
            assert source.shape==light.shape==(3248,3200)
            for col in range(0,3200,131):
                x=np.array(source[:,col:col+131]);y=np.array(light[:,col:col+131]);count+=x.size;different+=np.count_nonzero(x!=y)
            assert different==0;checks[variable]={'values':count,'different_values':int(different),'method':'131-column blocks, distinct from production97-row blocks'}
        pointer=ll.attrs['InputPointer'];pointer=pointer.decode('utf-8') if isinstance(pointer,bytes) else str(pointer)
        assert pointer==rs['VNP03MOD']['file'].split('/')[-1]
        assert pointer in str(f.attrs['InputFileGeo'])
        assert 'non-fire land' in str(f['fire mask'].attrs['legend']) and 'not processed (trim)' in str(f['fire mask'].attrs['legend'])
        assert set(f['algorithm QA'].attrs)=={'units'}
        assert set(ll['HDFEOS/SWATHS/VNP_750M_GEOLOCATION/Geolocation Fields'])=={'Latitude','Longitude'}
        # All sixteen addresses independently taken from raw sparse fire vectors.
        lat=np.array(fi['FP_latitude']);lon=np.array(fi['FP_longitude']);sel=np.where((lat>=54.75)&(lat<55)&(lon>=-117.2)&(lon<-116.4))[0];assert len(sel)==16
        identities=set()
        for i in sel:
            r=int(fi['FP_line'][i]);c=int(fi['FP_sample'][i]);p=next(x for x in rows if x['row375']==r and x['col375']==c);original=next(x for x in old['pixels'] if x['row']==r and x['col']==c)
            assert (r,c) not in identities;identities.add((r,c));power=float(fi['FP_power'][i]);frp.append(power);assert power==p['frp_mw'] and int(fi['fire mask'][r,c])==8
            rr,cc=p['row750'],p['col750'];assert (rr,cc)==(original['viirs750']['row'],original['viirs750']['col']) and int(f['fire mask'][rr,cc])==5 and int(f['algorithm QA'][rr,cc])==2
            for product,g,row,col in [('375',img,r,c),('750',mod,rr,cc)]:
                la=g['geolocation_data/latitude'];lo=g['geolocation_data/longitude']
                for axis,dr,dc in [('scan',0,1),('track',1,0)]:
                    distance=vincenty(float(lo[row,col]),float(la[row,col]),float(lo[row+dr,col+dc]),float(la[row+dr,col+dc]));error=abs(distance-p[f'{product}_{axis}_center_pitch_m']);max_pitch_error=max(max_pitch_error,error);assert error<.002
            # Different expression, published one-based boundary membership.
            assert 4385<=c+1<=5120 and 2193<=cc+1<=2560 and p['index_model_aggregation375']==p['index_model_aggregation750']==2
            assert r//32==rr//16==27
            for key in ['scan_start_time','scan_end_time','scan_quality']:assert img['scan_line_attributes/'+key][27]==mod['scan_line_attributes/'+key][27]
            assert p['physical_spatial_support_m2'] is None and p['physical_registration_bound_m'] is None and p['category']=='375_POSITIVE_750_UNKNOWN_SUPPORT'
        assert math.fsum(frp)==a['allocated_frp_sum_mw']==old['allocated_frp_sum_mw']
    result={'state':'PASS','qualification_sha256':digest(OUT/'QUALIFICATION_RESULT.json'),'contract_sha256':digest(OUT/'QUALIFICATION_CONTRACT.json'),'geolocation_sha256':digest(OUT/'GEOLOCATION_COMPARISON.json'),'qa_sha256':digest(OUT/'QA_APPLICABILITY.json'),'full_granule_variable_checks':checks,'positive_count':len(identities),'allocated_frp_sum_mw':math.fsum(frp),'max_sampling_pitch_implementation_difference_m':max_pitch_error,'same_scan_checks':16,'categories':{'375_POSITIVE_750_UNKNOWN_SUPPORT':16},'coordinate_compatibility':'VERIFIED_EXACT_PAIR_ONLY','algorithm_qa_qualified':False,'physical_footprints_qualified':False,'g4':'ADJUSTMENT_WITHHELD'}
    raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode();target=OUT/'INDEPENDENT_VALIDATION.json';assert not target.exists() or target.read_bytes()==raw
    if not target.exists():target.write_bytes(raw)
    print(json.dumps({'state':'PASS','coordinate_values_per_variable':checks['latitude']['values'],'different_values':0,'count':16,'frp_mw':math.fsum(frp),'max_pitch_difference_m':max_pitch_error}))
if __name__=='__main__':run()
