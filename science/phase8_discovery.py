"""Outcome-blind pass selection for the independently anchored incident window."""
import json
from urllib.parse import urlencode
from phase8_contract import ROOT,OUT,freeze,immutable,sha
from phase7_discovery import metadata,granule,pairs,seconds

def run():
    c=freeze();cache=ROOT/'data/acquisition/phase8/metadata';cache.mkdir(parents=True,exist_ok=True)
    products={p:[] for p in c['products']};receipts=[]
    for day in c['window_days']:
        for name,(collection,version) in c['products'].items():
            url='https://cmr.earthdata.nasa.gov/search/granules.json?'+urlencode({'collection_concept_id':collection,'temporal':day+'T00:00:00Z,'+day+'T23:59:59.999Z','bounding_box':','.join(map(str,c['aoi_wsen'])),'page_size':2000})
            path=cache/f'{day}-{name}.json';data,r=metadata(url,path);entries=data['feed']['entry'];assert len(entries)==r['hits']
            receipts.append({'day':day,'product':name,'file':path.relative_to(ROOT).as_posix(),**r});products[name].extend(granule(e,c['aoi_wsen']) for e in entries)
            print(json.dumps({'day':day,'product':name,'hits':r['hits']}),flush=True)
    ledger=pairs(products,60);eligible=[]
    for pair in ledger:
        a=pair['aqua'];v=pair['viirs750']
        bound=max(abs(seconds(a['start'])-seconds(v['end'])),abs(seconds(a['end'])-seconds(v['start'])))/60
        pair['maximum_interval_endpoint_separation_minutes']=bound
        pair['phase8_metadata_eligible']=bool(pair['same_acquisition_geo_and_375_available'] and pair['midpoint_offset_minutes']<=5 and bound<=10 and pair['max_centerline_distance_km']<=600)
        if pair['phase8_metadata_eligible']:eligible.append(pair)
    selected=[]
    for pair in eligible:
        if all(abs(seconds(pair['aqua']['start'])-seconds(x['aqua']['start']))>=86400 for x in selected):selected.append(pair)
        if len(selected)==c['selection']['maximum_candidates']:break
    assert len(receipts)<=c['budget']['max_CMR_responses']
    for i,p in enumerate(selected):immutable(OUT/f'CANDIDATE_{i+1}.json',{'contract_sha256':sha(OUT/'COHORT_CONTRACT.json'),'rank':i+1,'selected_before_science_payloads':True,'pair':p})
    result={'state':'FROZEN_METADATA_SELECTION','contract_sha256':sha(OUT/'COHORT_CONTRACT.json'),'queries':receipts,'products':products,'within60min_pair_ledger':ledger,
            'total_aqua_viirs_combinations':len(products['MYD14'])*len(products['VNP14']),'metadata_eligible_pairs':len(eligible),'selected':selected,
            'outcomes_used':False,'science_payloads_opened_at_selection':0,'holdout_evaluation':False,'g4':c['g4']}
    immutable(OUT/'DISCOVERY.json',result)
    print(json.dumps({'eligible':len(eligible),'selected':[[x['aqua']['id'],x['viirs750']['id'],x['midpoint_offset_minutes'],x['maximum_interval_endpoint_separation_minutes'],x['max_centerline_distance_km']] for x in selected]}))

if __name__=='__main__':run()
