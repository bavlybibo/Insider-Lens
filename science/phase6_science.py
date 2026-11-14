"""Bounded raw-field research lane, fixed geometry and positive timing experiment.

Reads verified native store read-only. Does not change/requalify native releases.
No footprint, exposure, absent-fire, or calibration result is inferred.
"""
import bisect
from collections import Counter, defaultdict
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import zipfile
from pyproj import Transformer, Geod
from canada_intake import objects

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/phase6'
SOURCES=['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS']

def digest(b): return hashlib.sha256(b).hexdigest()
def dump(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def seconds(utc): return int(dt.datetime.fromisoformat(utc.replace('Z','+00:00')).timestamp())
def key(r,width): return (math.floor(r['x']/width),math.floor(r['y']/width),r['utc'][:10])

def summarize(rows,width):
    result={}
    for s in SOURCES:
        rs=[r for r in rows if r['source']==s]
        result[s]={'records':len(rs),'cell_days':len({key(r,width) for r in rs})}
    a={key(r,width) for r in rows if r['source']=='AQUA_MODIS'}
    v={key(r,width) for r in rows if r['source']=='SNPP_VIIRS'}
    result['positive_sets']={'both_source_reported':len(a&v),'aqua_only':len(a-v),'viirs_only':len(v-a)}
    return result

def timed_candidates(rows,width,minutes):
    groups=defaultdict(lambda:defaultdict(list))
    for r in rows:
        if r['source'] in ['AQUA_MODIS','SNPP_VIIRS']:
            groups[(*key(r,width),r['dn'])][r['source']].append((seconds(r['utc']),r['raw_sha256']))
    keys=set();a_ids=set();v_ids=set();nearest=[]
    for k,s in groups.items():
        a=sorted(s['AQUA_MODIS']);v=sorted(s['SNPP_VIIRS']); vt=[t for t,h in v]
        if not a or not v: continue
        nearest.append(min(abs(t-u) for t,h in a for u,j in v)/60)
        for t,h in a:
            lo=bisect.bisect_left(vt,t-minutes*60);hi=bisect.bisect_right(vt,t+minutes*60)
            if hi>lo:
                keys.add(k[:3]);a_ids.add(h);v_ids.update(j for u,j in v[lo:hi])
    return {'minutes':minutes,'same_cell_day_same_flag_candidate_keys':len(keys),
            'aqua_records_with_candidate':len(a_ids),'viirs_records_with_candidate':len(v_ids),
            'qualified_opportunities':None,'qualified_report_frequency':None,
            'meaning':'positive-only candidate timing, not matched exposure or fire agreement'}

def clip(poly,axis,bound,greater):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ai=(a[axis]>=bound) if greater else (a[axis]<=bound)
        bi=(b[axis]>=bound) if greater else (b[axis]<=bound)
        if ai: result.append(a)
        if ai!=bi:
            t=(bound-a[axis])/(b[axis]-a[axis]);p=[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])];p[axis]=bound;result.append(tuple(p))
    return result

def area(poly): return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1])))/2 if poly else 0

def geometry(c,transform,segments):
    w,s,e,n=c['aoi_wsen'];corners=[(w,s),(e,s),(e,n),(w,n)]
    geographic=[(a[0]+(b[0]-a[0])*k/segments,a[1]+(b[1]-a[1])*k/segments) for a,b in zip(corners,corners[1:]+corners[:1]) for k in range(segments)]
    poly=[transform.transform(*p) for p in geographic];total=area(poly)
    xs,ys=zip(*poly);pieces=[]
    for i in range(math.floor(min(xs)/10000),math.floor(max(xs)/10000)+1):
        for j in range(math.floor(min(ys)/10000),math.floor(max(ys)/10000)+1):
            p=poly
            for axis,bound,greater in [(0,i*10000,True),(0,(i+1)*10000,False),(1,j*10000,True),(1,(j+1)*10000,False)]:p=clip(p,axis,bound,greater)
            a=area(p)
            if a>0.01:pieces.append({'i':i,'j':j,'area_m2':a,'cell_fraction':a/1e8})
    geod=Geod(ellps='WGS84');lons,lats=zip(*geographic);ga=abs(geod.polygon_area_perimeter(lons,lats)[0])
    return {'segments_per_edge':segments,'aoi_projected_area_m2':total,'geodesic_area_m2':ga,
            'sum_clipped_area_m2':sum(p['area_m2'] for p in pieces),'intersecting_cells':len(pieces),
            'partial_cells':sum(p['cell_fraction']<1-1e-7 for p in pieces),'cells':pieces}

def field_summary(rows):
    result={}
    for s in SOURCES:
        rs=[r for r in rows if r['source']==s];native=[r['native'] for r in rs]
        frp=[float(r['frp']) for r in native if r.get('frp') is not None]
        result[s]={'rows':len(rs),'type':dict(Counter(str(r.get('type','MISSING')) for r in native)),
                   'confidence':dict(Counter(str(r.get('confidence','MISSING')) for r in native)),
                   'version':dict(Counter(str(r.get('version','MISSING')) for r in native)),
                   'frp':{'units':'MW, native pixel-integrated value','missing':len(native)-len(frp),'zero':sum(x==0 for x in frp),
                          'positive':sum(x>0 for x in frp),'min':min(frp,default=None),'max':max(frp,default=None)},
                   'footprints':'scan/track scalar sizes retained; oriented footprint, view zenith and clear QA unavailable'}
    return result

def sensitivity(rows):
    return {
        'native_all':rows,
        'literal_type0_unverified':[r for r in rows if str(r['native'].get('type'))=='0'],
        'confidence_screen':[r for r in rows if (r['source']=='SNPP_VIIRS' and str(r['native']['confidence']) in ['n','h']) or (r['source']!='SNPP_VIIRS' and float(r['native']['confidence'])>=30)],
        'positive_frp_research':[r for r in rows if r['native'].get('frp') is not None and float(r['native']['frp'])>0],
    }

def run():
    c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());transform=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True)
    con=sqlite3.connect('file:'+str(ROOT/'data/canada/native.sqlite')+'?mode=ro',uri=True);con.execute('PRAGMA query_only=ON')
    rows=[];w,s,e,n=c['aoi_wsen'];days=c['development']+c['replication']
    for source in SOURCES:
        sql='SELECT member,row,source,utc,lon,lat,i5,j5,dn,hex(hash),raw FROM rows WHERE source=? AND pc=? AND ym=? AND day IN ('+','.join('?' for _ in days)+') AND lon>=? AND lon<? AND lat>=? AND lat<?'
        for member,num,src,utc,lon,lat,i,j,dn,h,raw in con.execute(sql,[source,c['pc'],'2022-06',*days,w,e,s,n]):
            native=json.loads(raw);assert str(native['version']) in c['row_versions'][src]
            assert digest(raw.encode())==h.lower()
            x,y=transform.transform(lon,lat);assert (math.floor(x/5000),math.floor(y/5000))==(i,j)
            rows.append({'member':member,'row':num,'source':src,'utc':utc,'lon':lon,'lat':lat,'x':x,'y':y,'dn':dn,
                         'raw_sha256':h.lower(),'native':native,'slice':'development' if utc[:10] in c['development'] else 'replication'})
    rows.sort(key=lambda r:(r['utc'],r['source'],r['raw_sha256']))
    dump(OUT/'RESEARCH_ROWS.json',rows)
    with (OUT/'RESEARCH_FRP.csv').open('w',encoding='utf-8',newline='') as f:
        fields=['member','row','source','utc','slice','raw_sha256','longitude','latitude','daynight','frp_MW','type_literal','confidence_literal','version_literal','scan_km','track_km','opportunity','g4']
        writer=csv.DictWriter(f,fields);writer.writeheader()
        for r in rows:
            q=r['native'];writer.writerow({**{k:r[k] for k in fields[:6]},'longitude':r['lon'],'latitude':r['lat'],'daynight':r['dn'],
               'frp_MW':q.get('frp',''),'type_literal':q.get('type',''),'confidence_literal':q.get('confidence',''),'version_literal':q.get('version',''),
               'scan_km':q.get('scan',''),'track_km':q.get('track',''),'opportunity':'UNKNOWN','g4':c['gate']})
    results={}
    for slice_name in ['development','replication']:
        rs=[r for r in rows if r['slice']==slice_name]
        results[slice_name]={'fields':field_summary(rs),'scales':{str(width):{'baseline':summarize(rs,width),
            'timing':[timed_candidates(rs,width,t) for t in c['offset_minutes']]} for width in c['grid']['widths_m']},
            'quality_sensitivity':{p:summarize(rr,10000) for p,rr in sensitivity(rs).items()}}
    geo=geometry(c,transform,32);geo_fine=geometry(c,transform,64)
    assert abs(geo['sum_clipped_area_m2']-geo['aoi_projected_area_m2'])<1
    assert abs(geo_fine['sum_clipped_area_m2']-geo_fine['aoi_projected_area_m2'])<1
    dump(OUT/'COMMON_GEOMETRY.json',{'coarse':geo,'fine':geo_fine,'meaning':'AOI/grid geometry only; clipped area is not observed, clear, burned or fire-positive area'})
    original=[]
    inventory=json.loads((ROOT/'reports/CANADA_RAW_INVENTORY.json').read_text())
    # Direct original-archive first-object probes, with exact canonical identity
    # linked to the previously independently verified store. Not a new full scan.
    for archive in inventory['archives']:
        with zipfile.ZipFile(archive['path']) as z:
            for member in archive['members']:
                if not member.get('processing_class'):continue
                with z.open(member['name']) as f: raw=next(objects(f))
                canonical=json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False)
                sha=digest(canonical.encode());found=con.execute('SELECT source,pc FROM rows WHERE member=? AND hash=?',(member['name'],bytes.fromhex(sha))).fetchone();assert found
                original.append({'member':member['name'],'zip_sha256':archive['zip_sha256'],'raw_sha256':sha,'source':found[0],'pc':found[1],
                    'fields':{k:raw.get(k,'MISSING') for k in ['acq_date','frp','type','confidence','version','scan','track','daynight']},
                    'field_types':{k:type(raw.get(k)).__name__ for k in ['frp','type','confidence','version']}})
    dump(OUT/'RAW_FIELD_AUDIT.json',{'direct_original_probes':original,'cohort':field_summary(rows),
        'national_counts_source':'reports/CANADA_RAW_INVENTORY.json, full original-archive independently verified Phase5 inventory; not a new Phase6 full recount',
        'national_member_fields':[{'member':m['name'],'rows':m['rows'],'types':m['categories'].get('type',{}),'confidence':m['categories'].get('confidence',{}),'versions':m['categories'].get('version',{}),'missing':m['missing'],'frp_range':m['numeric_ranges']['frp']} for a in inventory['archives'] for m in a['members'] if m.get('processing_class')],
        'review_correction':'zero FRP retained meant zero-valued FRP rows retained, NOT erased FRP. Complete raw FRP remains in immutable ZIP and native store; separate research lane exported here.',
        'type_policy':'0 presumed vegetation is a literal diagnostic, not confirmed wildfire. VIIRS monthly production vintage unverified; v1/v2 Type bug cannot be excluded; NRT missing Type stays missing.'})
    audit={'classification':'B1_GEOMETRY_ONLY','contract_sha256':digest((OUT/'COHORT_CONTRACT.json').read_bytes()),
        'research_rows_sha256':digest((OUT/'RESEARCH_ROWS.json').read_bytes()),'cohort_records':len(rows),'results':results,
        'support':{'downloaded_decoded_masks':0,'qualified_opportunities':None,'valid_non_detections':None,'viewing_geometry':'UNKNOWN','observation_support':'UNKNOWN'},
        'B2':{'state':'BLOCKED','reason':'No acquired decoded matched VNP14 750m / VNP14IMG 375m / MYD14 masks, QA and geolocation'},
        'B3':{'state':'BLOCKED','reason':'Raw MW FRP retained, but oriented footprints, viewing angles, clouds, QA and compatible matched support absent; no correction fitted'},
        'uncertainty':c['uncertainty'],'g4':c['gate'],'candidate_fit':False,'holdout_evaluation':False}
    dump(OUT/'COMMON_SUPPORT_AUDIT.json',audit)
    print(json.dumps({'records':len(rows),'results':{k:v['scales']['10000'] for k,v in results.items()},'geometry_cells':geo['intersecting_cells'],'classification':audit['classification']}))

if __name__=='__main__':run()
