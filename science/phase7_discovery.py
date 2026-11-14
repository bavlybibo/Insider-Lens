"""Bounded anonymous CMR search. Never opens fire arrays or native archives."""
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import build_opener
from pyproj import Transformer, Geod
from phase7_contract import ROOT, OUT, freeze

CACHE=ROOT/'data/acquisition/phase7/metadata'
G=Geod(ellps='WGS84')

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def immutable(p,obj):
    raw=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
    if p.exists():assert p.read_bytes()==raw, 'Immutable output differs: '+p.name
    else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)

def metadata(url,path):
    receipt=path.with_suffix('.receipt.json')
    if path.exists():
        r=json.loads(receipt.read_text());assert r['url']==url and r['sha256']==digest(path)
        return json.loads(path.read_text()),r
    with build_opener().open(url,timeout=35) as response:
        raw=response.read(4000001);assert len(raw)<=4000000
        r={'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'hits':int(response.headers.get('CMR-Hits','0')),
           'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'authentication':False}
    path.write_bytes(raw);immutable(receipt,r)
    return json.loads(raw),r

def area(p):return abs(sum(x[0]*y[1]-y[0]*x[1] for x,y in zip(p,p[1:]+p[:1])))/2 if p else 0.
def oriented_area(p):return sum(x[0]*y[1]-y[0]*x[1] for x,y in zip(p,p[1:]+p[:1]))/2
def intersect(subject,clip):
    """Convex polygon clipping; metadata approximation only, not IFOV geometry."""
    if oriented_area(clip)<0:clip=list(reversed(clip))
    for a,b in zip(clip,clip[1:]+clip[:1]):
        incoming=subject;subject=[]
        if not incoming:break
        def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        p=incoming[-1];sp=side(p)
        for q in incoming:
            sq=side(q)
            if (sq>=0)!=(sp>=0):
                fraction=sp/(sp-sq);subject.append((p[0]+fraction*(q[0]-p[0]),p[1]+fraction*(q[1]-p[1])))
            if sq>=0:subject.append(q)
            p,sp=q,sq
    return subject

def ring(e):
    # CMR JSON polygon positions are latitude longitude, not GeoJSON order.
    polygons=e.get('polygons',[])
    if len(polygons)!=1 or len(polygons[0])!=1:return None
    v=[float(x) for x in polygons[0][0].split()]
    p=list(zip(v[1::2],v[0::2]))
    if p and p[-1]==p[0]:p.pop()
    return p if len(p)==4 else None

def geometry(e,bbox):
    p=ring(e)
    if p is None:return {'state':'UNSUPPORTED_GRING','aoi_intersection_proxy_m2':None,'centerline_distance_km':None,'view_zenith_estimate_degrees':None}
    w,s,ee,n=bbox;cx=(w+ee)/2;cy=(s+n)/2
    t=Transformer.from_crs('EPSG:4326',f'+proj=laea +lat_0={cy} +lon_0={cx} +ellps=WGS84 +units=m',always_xy=True)
    pp=[t.transform(*v) for v in p]
    box=[t.transform(x,y) for x,y in [(w,s),(ee,s),(ee,n),(w,n)]]
    lengths=[G.inv(*a,*b)[2] for a,b in zip(p,p[1:]+p[:1])]
    idx=0 if lengths[0]+lengths[2]>=lengths[1]+lengths[3] else 1
    a=tuple((pp[idx][k]+pp[(idx+1)%4][k])/2 for k in [0,1]);b=tuple((pp[(idx+2)%4][k]+pp[(idx+3)%4][k])/2 for k in [0,1])
    distance=abs((b[0]-a[0])*(-a[1])-(b[1]-a[1])*(-a[0]))/math.dist(a,b)
    return {'state':'GRING_APPROXIMATION_ONLY','aoi_intersection_proxy_m2':area(intersect(pp,box)),
            'centerline_distance_km':distance/1000,'view_zenith_estimate_degrees':None,
            'view_zenith_reason':'GRing has no measured sensor zenith; a centerline-distance proxy is not a VZA estimate',
            'ring_lonlat':p,'axis_long_opposing_edge_index':idx,'edge_lengths_m':lengths}

def seconds(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def granule(e,bbox):
    name=e.get('producer_granule_id',e['title']);m=re.search(r'\.A(\d{7})\.(\d{4})\.',name)
    return {'id':name,'concept_id':e['id'],'start':e['time_start'],'end':e['time_end'],'key':m.group(0) if m else None,
            'reported_bytes':math.ceil(float(e.get('granule_size',0))*1024*1024),
            'collection':e['collection_concept_id'],'day_night_metadata':e.get('day_night_flag','UNKNOWN'),
            'updated':e.get('updated'),'geometry':geometry(e,bbox),
            'data_urls':[l['href'] for l in e.get('links',[]) if 'data#' in l.get('rel','') and l['href'].startswith('https:') and not l.get('inherited')]}

def pairs(products,limit):
    out=[]
    for a in products['MYD14']:
        for v in products['VNP14']:
            amid=(seconds(a['start'])+seconds(a['end']))/2;vmid=(seconds(v['start'])+seconds(v['end']))/2
            offset=abs(amid-vmid)/60
            if offset>limit:continue
            required={k:[g for g in products[k] if g['key']==(a['key'] if k=='MYD03' else v['key'])] for k in ['MYD03','VNP03MOD','VNP14IMG','VNP03IMG']}
            files=[a,v]+[items[0] for items in required.values() if items]
            valid=all(g['geometry']['aoi_intersection_proxy_m2'] is not None and g['geometry']['aoi_intersection_proxy_m2']>0 for g in [a,v])
            if not valid:continue
            available=all(required.values()) and all(g['data_urls'] for g in files)
            distance=max(a['geometry']['centerline_distance_km'],v['geometry']['centerline_distance_km'])
            gap=max(0,seconds(a['start'])-seconds(v['end']),seconds(v['start'])-seconds(a['end']))/60
            rank=[0 if available else 1,distance,offset,sum(g['reported_bytes'] for g in files),a['id'],v['id']]
            out.append({'aqua':a,'viirs750':v,'associated':required,'midpoint_offset_minutes':offset,'interval_gap_minutes':gap,
                        'same_acquisition_geo_and_375_available':bool(available),'max_centerline_distance_km':distance,'estimated_transfer_bytes':rank[3],
                        'exact_geo_input_identity':'UNKNOWN_UNTIL_FIRE_METADATA','qa_policy':'UNQUALIFIED_UNTIL_EXACT_COLLECTION_DOCUMENTATION_AND_ARRAY_CHECKS',
                        'qualified_shared_support_m2':None,'rank_key':rank})
    return sorted(out,key=lambda x:x['rank_key'])

def run():
    c=freeze();CACHE.mkdir(parents=True,exist_ok=True)
    # Correction made BEFORE any Phase7 query: centerline joins cross-swath
    # (longer opposing) edges. Original contract bytes remain preserved.
    immutable(OUT/'PRESEARCH_GEOMETRY_AMENDMENT.json',{'parent_sha256':digest(OUT/'SEARCH_CONTRACT.json'),
        'timing':'before first Phase7 CMR request or outcome inspection','change':'proxy axis joins midpoints of longer opposing GRing edges, not shorter',
        'reason':'cross-swath width exceeds nominal along-track granule length for these products; shorter-edge join would estimate cross-track axis instead of along-track centerline',
        'limits':'heuristic only; unknown VZA remains null. No eligibility threshold changed.'})
    splits={};queries=0
    for split,spec in c['splits'].items():
        ps={p:[] for p in c['products']};receipts=[]
        for day in spec['days']:
            for product,(collection,version) in c['products'].items():
                url='https://cmr.earthdata.nasa.gov/search/granules.json?'+urlencode({'collection_concept_id':collection,
                    'temporal':day+'T00:00:00Z,'+day+'T23:59:59.999Z','bounding_box':','.join(map(str,spec['aoi_wsen'])),'page_size':2000})
                data,r=metadata(url,CACHE/f'{split}-{day}-{product}.json');queries+=1
                entries=data['feed']['entry'];assert len(entries)==r['hits'],'Incomplete CMR pagination'
                receipts.append({'day':day,'product':product,'path':(CACHE/f'{split}-{day}-{product}.json').relative_to(ROOT).as_posix(),**r})
                ps[product].extend(granule(e,spec['aoi_wsen']) for e in entries)
                print(json.dumps({'split':split,'day':day,'product':product,'hits':r['hits']}),flush=True)
        ranked=pairs(ps,c['time']['primary_minutes']);candidate=next((r for r in ranked if r['same_acquisition_geo_and_375_available'] and r['estimated_transfer_bytes']<=c['budgets']['max_payload_bytes']),None)
        immutable(OUT/f'{split.upper()}_CANDIDATE.json',{'contract_sha256':digest(OUT/'SEARCH_CONTRACT.json'),'split':split,'aoi_wsen':spec['aoi_wsen'],
            'selected_before_payload':True,'candidate':candidate,'state':'FROZEN_METADATA_CANDIDATE' if candidate else 'NO_TIMING_METADATA_CANDIDATE'})
        splits[split]={'scope':spec,'queries':receipts,'products':ps,'ranked_pairs':ranked,'candidate':candidate}
    assert queries<=c['budgets']['max_metadata_responses']
    result={'state':'METADATA_DISCOVERY_EXECUTED','contract_sha256':digest(OUT/'SEARCH_CONTRACT.json'),'queries':queries,'splits':splits,
            'fire_outcomes_used':False,'science_payloads_acquired':0,'qualified_shared_support_m2':None,'candidate_fit':False,'holdouts_opened':False,'g4':c['g4']}
    immutable(OUT/'DISCOVERY.json',result)
    print(json.dumps({'queries':queries,'ranked':{k:len(v['ranked_pairs']) for k,v in splits.items()},'selected':{k:None if not v['candidate'] else [v['candidate']['aqua']['id'],v['candidate']['viirs750']['id'],v['candidate']['midpoint_offset_minutes'],v['candidate']['max_centerline_distance_km']] for k,v in splits.items()}}))

if __name__=='__main__':run()
