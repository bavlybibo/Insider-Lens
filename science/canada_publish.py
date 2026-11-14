"""Verify independent disk indexes, then publish bounded native aggregates (never raw Canada).

Public chunks are one source / SP-or-NRT / UTC month. Each cell stores exact
daily D/N multiplicities; thus all filters/exports use unions, never summed D/N K.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from pyproj import Transformer,Geod
from canada_intake import CRS,GRID,ROOT,dump,digest
from canada_oracle import project as oracle_project
from canada_runtime import memory

def keyhash(db,table,columns):
    h=hashlib.sha256();n=0
    for row in db.execute(f'SELECT {columns} FROM {table} ORDER BY {columns}'):
        h.update((json.dumps(row,separators=(',',':'))+'\n').encode());n+=1
    return {'keys':n,'sha256':h.hexdigest()}

def aggregate(db,table):
    db.execute(f'''CREATE TEMP TABLE daily AS SELECT source,pc,ym,i5>>1 AS i,j5>>1 AS j,day,dn,COUNT(*) AS n
      FROM {table} GROUP BY source,pc,ym,i,j,day,dn''')
    db.execute('CREATE INDEX daily_scope ON daily(source,pc,ym,i,j,day,dn)')
    return keyhash(db,'daily','source,pc,ym,i,j,day,dn,n')

def grid_checks():
    forward=Transformer.from_crs('EPSG:4326',CRS,always_xy=True);back=Transformer.from_crs(CRS,'EPSG:4326',always_xy=True);geod=Geod(ellps='WGS84');checks=[]
    points=[(-123,49),(-75,45),(-110,60),(-100,70),(-90,80),(-141,60),(-53,47),(-100,89.9),(179.99,75),(-179.99,75),(-100,60)]
    for lon,lat in points:
        x,y=forward.transform(lon,lat);ox,oy=oracle_project(lon,lat);error=math.hypot(x-ox,y-oy)
        # Densify projected square edges; four geodesic corners alone approximate curved edges.
        ring=[]
        for ax,ay,bx,by in [(0,0,10000,0),(10000,0,10000,10000),(10000,10000,0,10000),(0,10000,0,0)]:
            for k in range(40):ring.append(back.transform(x+ax+(bx-ax)*k/40,y+ay+(by-ay)*k/40))
        area=abs(geod.polygon_area_perimeter([p[0] for p in ring],[p[1] for p in ring])[0]);rlon,rlat=back.transform(x,y)
        assert error<0.002 and abs(area/100_000_000-1)<2e-5
        assert abs(rlat-lat)<1e-7 and abs((rlon-lon+180)%360-180)<1e-7
        checks.append({'lon':lon,'lat':lat,'x_m':x,'y_m':y,'oracle_error_m':error,'geodesic_area_m2':area,'area_relative_error':area/100_000_000-1,'cell':f'{GRID}:10000:{math.floor(x/10000)}:{math.floor(y/10000)}'})
    return {'crs':CRS,'grid_id':GRID,'origin_m':[0,0],'cell_m':10000,'checks':checks,'geodesic_edge_samples_per_side':40,'state':'PASS'}

def run():
    start=time.perf_counter();stage=ROOT/'data/canada';manifest=json.loads((stage/'INTAKE_MANIFEST.json').read_text(encoding='utf8'))
    oracle_intake=json.loads((ROOT/'reports/CANADA_ORACLE_INTAKE.json').read_text(encoding='utf8'))
    for archive in manifest['archives']:
        for member in archive['members']:
            if 'rows' not in member:continue
            check=next(r for r in oracle_intake['members'] if r['member']==member['name'])
            assert check['archive_sha256']==archive['zip_sha256'] and check['crc']=='PASS'
            assert (check['raw_rows'],check['accepted'],check['duplicates'])==(member['rows'],member['accepted'],member['duplicates']),'Raw member accounting differs'
    a=sqlite3.connect(f'file:{(stage/"native.sqlite").as_posix()}?mode=ro',uri=True);b=sqlite3.connect(f'file:{(stage/"oracle.sqlite").as_posix()}?mode=ro',uri=True)
    for db in [a,b]:db.execute('PRAGMA cache_size=-24000');db.execute('PRAGMA temp_store=FILE')
    # Compare every accepted raw identity plus independent projection/classification.
    cols='member,hex(hash),source,pc,ym,day,i5,j5,dn'
    ah=keyhash(a,'rows',cols);bh=keyhash(b,'evidence',cols);assert ah==bh,'Independent raw key mismatch'
    print('All raw identities and 5km projection bins reconcile',ah,flush=True)
    da=aggregate(a,'rows');ob=aggregate(b,'evidence');assert da==ob,'Independent daily multiset mismatch'
    sensitivity={}
    for size,shift in [(5000,0),(10000,1),(20000,2)]:
        def k(db,table):return list(db.execute(f'SELECT source,pc,COUNT(*) FROM (SELECT source,pc,i5>>{shift} AS i,j5>>{shift} AS j,day FROM {table} GROUP BY source,pc,i,j,day) GROUP BY source,pc ORDER BY source,pc'))
        production,oracle=k(a,'rows'),k(b,'evidence');assert production==oracle,'Scale sensitivity mismatch';sensitivity[str(size)]=production
    checks=grid_checks();dump(ROOT/'reports/CANADA_GRID_VALIDATION.json',checks)
    a.execute('''CREATE TEMP TABLE versions AS SELECT source,pc,ym,json_extract(raw,'$.version') AS version,COUNT(*) AS n,MIN(utc) AS first,MAX(utc) AS last FROM rows GROUP BY source,pc,ym,version''')
    version_inventory=list(a.execute('SELECT * FROM versions ORDER BY source,pc,ym,version'))
    dump(ROOT/'reports/CANADA_VERSION_LINEAGE.json',{'columns':['source','processing_class','month','literal_row_version','records','first_utc','last_utc'],'rows':version_inventory,'interpretation':'Literal codes preserved. Delivery request collection is not independently traced upstream monthly production/granule vintage. No version-based calibration or Type vegetation filter.'})
    # Independently derived pilot fixtures: oracle daily keys + PROJ inverse,
    # compared in TypeScript tests against the client inverse/filter implementation.
    inverse=Transformer.from_crs(CRS,'EPSG:4326',always_xy=True);pilots=[]
    for area,bbox in [('south',[-120,49,-110,55]),('north',[-120,60,-110,66])]:
        for ym in ['2010-06','2022-06','2023-06']:
            tally=collections.defaultdict(lambda:{'records':0,'keys':set()})
            for source,i,j,day,dn,n in b.execute('SELECT source,i,j,day,dn,n FROM daily WHERE pc=\'SP\' AND ym=?',(ym,)):
                lon,lat=inverse.transform((i+.5)*10000,(j+.5)*10000)
                if not(bbox[0]<=lon<bbox[2] and bbox[1]<=lat<bbox[3]):continue
                for flag in ['ALL',dn]:tally[source,flag]['records']+=n;tally[source,flag]['keys'].add((i,j,day))
            for source in ['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS']:
                for flag in ['ALL','D','N']:
                    t=tally[source,flag];pilots.append({'area':area,'month':ym,'source':source,'flag':flag,'records':t['records'],'cell_days':len(t['keys'])})
    dump(ROOT/'reports/CANADA_PILOT_RECONCILIATION.json',{'method':'independent raw oracle keys + PROJ inverse fixed-cell centers in half-open pilot boxes; no model or holdout metrics','cases':pilots})
    quality=list(a.execute('''SELECT member, SUM(json_extract(raw,'$.frp')=0),SUM(json_extract(raw,'$.brightness')<250),SUM(json_extract(raw,'$.scan')=0 OR json_extract(raw,'$.track')=0),SUM(json_extract(raw,'$.bright_t31')=0) FROM rows GROUP BY member'''))
    dump(ROOT/'reports/CANADA_QUALITY_FLAGS.json',{'columns':['member','zero_frp_retained','brightness_below250K_review_only','zero_scan_or_track_review_only','brightness2_zero_review_only'],'rows':quality,'policy':'No physical temperature inversion, vegetation inference or FRP fusion. Flags do not silently exclude valid native detections.'})
    out=ROOT/'public/data/canada'/manifest['candidate_id'];out.mkdir(parents=True,exist_ok=True)
    coverage=[];artifacts={};source_total=collections.defaultdict(lambda:{'records':0,'cell_days':0});max_bytes=0
    for source,pc,ym in a.execute('SELECT DISTINCT source,pc,ym FROM daily ORDER BY source,pc,ym'):
        cells=[];current=None;days=[];daily=collections.defaultdict(lambda:[0,0,0]);records=0;keys=0
        def flush():
            if current is not None:cells.append([*current,days.copy()])
        for i,j,day,dn,n in a.execute('SELECT i,j,day,dn,n FROM daily WHERE source=? AND pc=? AND ym=? ORDER BY i,j,day,dn',(source,pc,ym)):
            if current!=(i,j):flush();current=(i,j);days=[]
            daynum=int(day[-2:]);index=1 if dn=='D' else 2
            if not days or days[-1][0]!=daynum:days.append([daynum,0,0]);keys+=1
            days[-1][index]+=n;daily[daynum][index]+=n;records+=n
        flush();payload={'candidate':manifest['candidate_id'],'source':source,'pc':pc,'month':ym,'grid':GRID,'cells':cells}
        name=f'{source}-{pc}-{ym}.json';dump(out/name,payload);nbytes=(out/name).stat().st_size;max_bytes=max(max_bytes,nbytes)
        artifacts[name]={'sha256':digest(out/name),'bytes':nbytes}
        ds=[]
        for daynum,counts in sorted(daily.items()):
            dnkeys=list(a.execute('SELECT dn,COUNT(*) FROM daily WHERE source=? AND pc=? AND ym=? AND day=? GROUP BY dn',(source,pc,ym,f'{ym}-{daynum:02d}')))
            allkeys=a.execute('SELECT COUNT(*) FROM (SELECT i,j FROM daily WHERE source=? AND pc=? AND ym=? AND day=? GROUP BY i,j)',(source,pc,ym,f'{ym}-{daynum:02d}')).fetchone()[0]
            ds.append({'day':daynum,'records':counts[1]+counts[2],'D':counts[1],'N':counts[2],'cell_days':allkeys,'D_cell_days':dict(dnkeys).get('D',0),'N_cell_days':dict(dnkeys).get('N',0)})
        versions=[r[3] for r in version_inventory if r[:3]==(source,pc,ym)]
        item={'source':source,'pc':pc,'month':ym,'records':records,'cell_days':keys,'cells':len(cells),'days':ds,'native_versions':versions,'file':name,**artifacts[name]}
        coverage.append(item);source_total[source+'|'+pc]['records']+=records;source_total[source+'|'+pc]['cell_days']+=keys
    # Bounded native-row exemplars are explicitly samples, never a truncated statistical cohort.
    examples={}
    for ym in ['2010-06','2022-06','2023-06']:
        for source in ['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS']:
            # First chronological evidence, not highest-count cluster. No holdout rows.
            rows=a.execute('SELECT member,row,raw,i5>>1,j5>>1 FROM rows WHERE pc=\'SP\' AND ym=? AND source=? ORDER BY utc,member,row LIMIT 12',(ym,source))
            examples[source+'|'+ym]=[{'member':m,'row':r,'native':json.loads(raw),'cell':f'{GRID}:10000:{i}:{j}'} for m,r,raw,i,j in rows]
    # Derive a dedicated Canadian context from the existing hash-verified full Natural Earth source.
    cart=ROOT/'data/acquisition/cartography/ne_50m_admin_0_countries.geojson';assert digest(cart)=='3e458fc036ad0a66411f2c1e6cac49c5d7bfb81cb1123bc513b22511a2b7fdeb'
    countries=json.loads(cart.read_text(encoding='utf8'));features=[]
    for f in countries['features']:
        if f['properties']['ADMIN'] in ['Canada','United States of America','Greenland']:
            features.append({'type':'Feature','properties':{'name':f['properties']['ADMIN']},'geometry':f['geometry']})
    dump(out/'context.json',{'type':'FeatureCollection','features':features});artifacts['context.json']={'sha256':digest(out/'context.json'),'bytes':(out/'context.json').stat().st_size}
    dump(out/'examples.json',examples);artifacts['examples.json']={'sha256':digest(out/'examples.json'),'bytes':(out/'examples.json').stat().st_size}
    reconciliation={'state':'PASS','raw_identity_and_projected_5km_keys':ah,'independent_daily_multiset':da,'sensitivity_cell_days':sensitivity,'total_by_source_product':dict(source_total),'elapsed_s':time.perf_counter()-start,'runtime_memory':memory(),'grid_checks':'CANADA_GRID_VALIDATION.json','holdout_evaluation':'NOT_EXECUTED'}
    dump(ROOT/'reports/CANADA_RECONCILIATION.json',reconciliation)
    catalog={'schema':'ca-native-calendar-v1','candidate':manifest['candidate_id'],'status':'RECOUNT_VERIFIED_NATIVE_ONLY','root':'/data/canada/'+manifest['candidate_id']+'/',
      'grid':checks,'coverage':coverage,'total':dict(source_total),'archives':manifest['archives'],'artifacts':artifacts,'oracle':reconciliation,
      'opportunity':'OBSERVATION_UNKNOWN','completeness':'UNKNOWN','production_vintage':'UNVERIFIED','adjustment':'ADJUSTMENT_WITHHELD','native_max_chunk_bytes':max_bytes,
      'context':'Natural Earth 1:50m, public domain; whole country context, not administrative point-membership QA',
      'claims':'Positive native observations in acquired request only. No fire-free days, seasonal anomaly, sensor correction or harmonized quantity.'}
    # Runtime timing is evidence in the report, not part of immutable scientific identity.
    catalog['oracle']={k:v for k,v in reconciliation.items() if k not in ('elapsed_s','runtime_memory')}
    catalog_file=out/'catalog.json'
    if catalog_file.exists():
        assert json.loads(catalog_file.read_text(encoding='utf8'))==catalog,'Published scientific candidate changed'
    else:dump(catalog_file,catalog)
    pointer={'file':'/data/canada/'+manifest['candidate_id']+'/catalog.json','sha256':digest(out/'catalog.json'),'candidate':manifest['candidate_id']}
    pointer_path=ROOT/'public/data/canada/index.json'
    if pointer_path.exists():assert json.loads(pointer_path.read_text(encoding='utf8'))==pointer,'Candidate immutability violated'
    else:dump(pointer_path,pointer)
    dump(ROOT/'reports/CANADA_SOURCE_COVERAGE.json',{'candidate':manifest['candidate_id'],'coverage':coverage,'total':dict(source_total),'opportunity':'UNKNOWN','completeness':'UNKNOWN','catalog_sha256':pointer['sha256']})
    print(json.dumps({'state':'PASS','total':dict(source_total),'chunks':len(coverage),'max_chunk_bytes':max_bytes,'elapsed_s':time.perf_counter()-start}),flush=True)

if __name__=='__main__':run()
