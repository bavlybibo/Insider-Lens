"""New immutable research namespace; does not replace any native/P6/P7 release."""
import json
from phase8_contract import ROOT,OUT,sha,immutable

def run():
    a=json.loads((OUT/'SUPPORT_AUDIT.json').read_text());o=json.loads((OUT/'INDEPENDENT_VALIDATION.json').read_text());c=json.loads((OUT/'COHORT_CONTRACT.json').read_text())
    assert o['state']=='PASS' and o['support_audit_sha256']==sha(OUT/'SUPPORT_AUDIT.json') and o['mapped_centers_sha256']==sha(OUT/'MASK_CENTERS.json')
    history=json.loads((OUT/'NATIVE_HISTORY.json').read_text());assert history['state']=='PASS'
    identity='p8-'+sha(OUT/'COHORT_CONTRACT.json')[:12]+'-'+sha(OUT/'SUPPORT_AUDIT.json')[:12]
    folder=ROOT/'public/data/phase8'/identity;folder.mkdir(parents=True,exist_ok=True);artifacts={}
    centers=json.loads((OUT/'MASK_CENTERS.json').read_text())
    for product,points in centers.items():
        name=f'development-{product}.json';immutable(folder/name,{'fields':['line','sample','lon','lat','mask','qa','view_zenith_degrees'],'points':[[p[k] for k in ['line','sample','lon','lat','mask','qa','view_zenith_degrees']] for p in points]})
        artifacts[name]={'sha256':sha(folder/name),'bytes':(folder/name).stat().st_size,'points':len(points)}
    for name in ['COHORT_CONTRACT.json','CANDIDATE_1.json','DETAIL_DOWNLOAD_MANIFEST.json','SUPPORT_AUDIT.json','INDEPENDENT_VALIDATION.json','NATIVE_HISTORY.json','NATIVE_RECORDS.json']:
        raw=(OUT/name).read_bytes();target=folder/name
        if target.exists():assert target.read_bytes()==raw
        else:target.write_bytes(raw)
        artifacts[name]={'sha256':sha(target),'bytes':len(raw)}
    pair=json.loads((OUT/'CANDIDATE_1.json').read_text())['pair']
    fields=['aoi_pixel_centers','mask_counts','view_zenith_min_degrees','view_zenith_max_degrees','exact_geolocation_input_identity','support_states_at_centers','positive_mask_centers','native_frp_mw_sum','scan_time_bounds']
    bundle={'id':identity,'phase':8,'contract_sha256':sha(OUT/'COHORT_CONTRACT.json'),'support_sha256':sha(OUT/'SUPPORT_AUDIT.json'),'parent_canada':'ca-92a935da01aecfa3e1d130b3',
        'g4':'ADJUSTMENT_WITHHELD','metadata_queries':42,'ranked_pairs':len(json.loads((OUT/'DISCOVERY.json').read_text())['within60min_pair_ledger']),
        'science_files':a['science_files'],'downloaded_bytes':a['downloaded_bytes'],'qualified_shared_support_m2':None,'fit':False,'generalization':False,'holdouts_opened':False,
        'maximum_scan_bound_separation_seconds':a['maximum_scan_bound_separation_seconds'],'native_history':history,'independent':o,'artifacts':artifacts,
        'splits':{'development':{'aoi_wsen':c['aoi_wsen'],'searched_days':c['window_days'],'date':pair['aqua']['start'][:10],'offset_minutes':pair['midpoint_offset_minutes'],
            'aqua_start':pair['aqua']['start'],'aqua_end':pair['aqua']['end'],'viirs_start':pair['viirs750']['start'],'viirs_end':pair['viirs750']['end'],
            'proxy_distance_km':pair['max_centerline_distance_km'],'failures':a['failures'],'products':{p:{k:v[k] for k in fields} for p,v in a['results'].items()}}},
        'meaning':'16 native375m positive pixels, zero Aqua/750m positives in a single event-anchored pass. No qualified common domain, missed-fire rate, calibration or generalization.'}
    immutable(folder/'bridge.json',bundle)
    immutable(ROOT/'public/data/phase8/index.json',{'id':identity,'file':'/data/phase8/'+identity+'/bridge.json','sha256':sha(folder/'bridge.json')})
    print(json.dumps({'id':identity,'points':sum(len(v) for v in centers.values()),'public_artifacts':len(artifacts)}))

if __name__=='__main__':run()
