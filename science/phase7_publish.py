"""Publish a separate, immutable evidence overlay, leaving both native releases sealed."""
import csv
import hashlib
import io
import json
from phase7_contract import ROOT,OUT
from phase7_discovery import immutable,digest

def run(exact=False):
    prefix='EXACT_' if exact else ''
    support=json.loads((OUT/(prefix+'SUPPORT_AUDIT.json')).read_text());oracle=json.loads((OUT/(prefix+'INDEPENDENT_VALIDATION.json')).read_text())
    assert oracle['state']=='PASS' and oracle['support_audit_sha256']==digest(OUT/(prefix+'SUPPORT_AUDIT.json'))
    assert oracle['mapped_centers_sha256']==digest(OUT/(prefix+'MASK_CENTERS.json'))
    identity='p7-'+digest(OUT/'SEARCH_CONTRACT.json')[:12]+'-'+digest(OUT/(prefix+'SUPPORT_AUDIT.json'))[:12]
    folder=ROOT/'public/data/phase7'/identity;folder.mkdir(parents=True,exist_ok=True)
    centers=json.loads((OUT/(prefix+'MASK_CENTERS.json')).read_text());discovery=json.loads((OUT/'DISCOVERY.json').read_text());artifacts={}
    for split,products in centers.items():
        for product,points in products.items():
            name=f'{split}-{product}.json'
            immutable(folder/name,{'fields':['line','sample','lon','lat','mask','qa','view_zenith_degrees'],
                'points':[[p[k] for k in ['line','sample','lon','lat','mask','qa','view_zenith_degrees']] for p in points]})
            artifacts[name]={'sha256':digest(folder/name),'bytes':(folder/name).stat().st_size,'points':len(points)}
    proof_names=(['PROVIDER_CONTROLS.json','QUALIFICATION_SENSITIVITY.json'] if exact else [])+['SEARCH_CONTRACT.json','PRESEARCH_GEOMETRY_AMENDMENT.json','ACQUISITION_SCOPE.json','L2_DOWNLOAD_MANIFEST.json','SUPPORT_AUDIT.json','INDEPENDENT_VALIDATION.json','EXACT_GEO_ACCESS.json','DEVELOPMENT_CANDIDATE.json','REPLICATION_CANDIDATE.json']
    for name in proof_names:
        source_name=(prefix+name if name in ['SUPPORT_AUDIT.json','INDEPENDENT_VALIDATION.json'] else 'L2_EXACT_DOWNLOAD_MANIFEST.json' if exact and name=='L2_DOWNLOAD_MANIFEST.json' else name)
        raw=(OUT/source_name).read_bytes();target=folder/name
        if target.exists():assert target.read_bytes()==raw
        else:target.write_bytes(raw)
        artifacts[name]={'sha256':digest(target),'bytes':len(raw),'source_report':source_name}
    contract=json.loads((OUT/'SEARCH_CONTRACT.json').read_text());summary={}
    for split,r in support['results'].items():
        selected=discovery['splits'][split]['candidate']
        summary[split]={'aoi_wsen':contract['splits'][split]['aoi_wsen'],'searched_days':contract['splits'][split]['days'],
            'date':selected['aqua']['start'][:10],'offset_minutes':selected['midpoint_offset_minutes'],'aqua_start':selected['aqua']['start'],
            'aqua_end':selected['aqua']['end'],'viirs_start':selected['viirs750']['start'],'viirs_end':selected['viirs750']['end'],
            'proxy_distance_km':selected['max_centerline_distance_km'],'failures':r['failures'],
            'products':{p:{k:v[k] for k in ['aoi_pixel_centers','mask_counts','view_zenith_min_degrees','view_zenith_max_degrees','exact_geolocation_input_identity','support_states_at_centers']} for p,v in r['products'].items()}}
    bundle={'id':identity,'contract_sha256':digest(OUT/'SEARCH_CONTRACT.json'),'support_sha256':digest(OUT/(prefix+'SUPPORT_AUDIT.json')),
        'parent_canada':'ca-92a935da01aecfa3e1d130b3','parent_portugal':'eg-9a6ad9ccfda103bf80926db6','g4':'ADJUSTMENT_WITHHELD',
        'metadata_queries':discovery['queries'],'ranked_pairs':sum(len(s['ranked_pairs']) for s in discovery['splits'].values()),
        'science_files':support['science_files'],'downloaded_bytes':support['downloaded_bytes'],'qualified_shared_support_m2':None,
        'fit':False,'generalization':False,'holdouts_opened':False,'independent':oracle,'splits':summary,'artifacts':artifacts,
        'meaning':'native mask centers from new bounded L2 passes, not physical footprints, cloud-free area, zero-fire days or harmonization'}
    immutable(folder/'bridge.json',bundle)
    pointer=ROOT/'public/data/phase7/index.json'
    entry={'id':identity,'file':'/data/phase7/'+identity+'/bridge.json','sha256':digest(folder/'bridge.json')}
    if pointer.exists() and json.loads(pointer.read_text())!=entry:
        assert exact, 'Do not downgrade the active research pointer'
        current=json.loads(pointer.read_text())
        immutable(OUT/('PUBLIC_INDEX_'+current['id']+'.json'),current)
        pending=pointer.with_suffix('.pending.json')
        pending.write_text(json.dumps(entry,indent=2,sort_keys=True)+'\n')
        pending.replace(pointer)
    else:immutable(pointer,entry)
    print(json.dumps({'id':identity,'bundle_bytes':(folder/'bridge.json').stat().st_size,'mapped_points':sum(len(p) for s in centers.values() for p in s.values())}))

if __name__=='__main__':
    import sys
    run('--exact' in sys.argv)
