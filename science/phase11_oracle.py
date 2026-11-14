"""Independent native-retention acceptance from original-archive raw oracle keys.

Does not import the production summarizer or read public chunks to calculate
expected values. The sealed oracle index was parsed independently from every
immutable ZIP record; its archive identities are checked again here.
"""
from pathlib import Path
import calendar
import hashlib
import json
import math
import sqlite3
import time

R=Path(__file__).resolve().parents[1]; O=R/'reports/phase11'
S=['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS']

def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def inverse(x,y):
    # Independent analytical ellipsoidal EPSG 9820 inverse (production uses PROJ).
    a=6378137; e2=(1/298.257223563)*(2-1/298.257223563); e=math.sqrt(e2)
    def q(phi):
        v=math.sin(phi)
        return (1-e2)*(v/(1-e2*v*v)-math.log((1-e*v)/(1+e*v))/(2*e))
    qp=q(math.pi/2); p0=math.radians(60); b0=math.asin(q(p0)/qp)
    rq=a*math.sqrt(qp/2); d=a*math.cos(p0)/math.sqrt(1-e2*math.sin(p0)**2)/(rq*math.cos(b0))
    u,v=x/d,y*d; rho=math.hypot(u,v)
    if not rho:return -100.,60.
    c=2*math.asin(rho/(2*rq)); b=math.asin(math.cos(c)*math.sin(b0)+v*math.sin(c)*math.cos(b0)/rho)
    target=qp*math.sin(b); p=b
    for _ in range(15):
        step=(q(p)-target)/(2*(1-e2)*math.cos(p)/(1-e2*math.sin(p)**2)**2);p-=step
        if abs(step)<1e-13:break
    return -100+math.degrees(math.atan2(u*math.sin(c),rho*math.cos(b0)*math.cos(c)-v*math.sin(b0)*math.sin(c))),math.degrees(p)

def run():
    start=time.perf_counter(); expected=json.loads((O/'NATIVE_RETENTION.json').read_text(encoding='utf-8'))
    contract=json.loads((O/'RETENTION_CONTRACT.json').read_text(encoding='utf-8'))
    assert expected['contract_sha256']==sha(O/'RETENTION_CONTRACT.json')
    intake=json.loads((R/'data/canada/INTAKE_MANIFEST.json').read_text(encoding='utf-8'))
    db=sqlite3.connect(f'file:{(R/"data/canada/oracle.sqlite").as_posix()}?mode=ro',uri=True)
    db.execute('PRAGMA cache_size=-18000'); db.execute('PRAGMA temp_store=FILE')
    bindings=[]
    for a in intake['archives']:
        assert sha(Path(a['path']))==a['zip_sha256']
        for m in a['members']:
            if 'rows' not in m:continue
            done=db.execute('SELECT archive_hash,report FROM done WHERE member=?',(m['name'],)).fetchone()
            assert done[0]==a['zip_sha256']; raw=json.loads(done[1])
            assert raw['accepted']==m['accepted']
            bindings.append({'archive_sha256':a['zip_sha256'],'member':m['name'],'accepted':m['accepted']})
    cases=0; seasonals=0; all_rows=0; scales=[]; cache={}; read_months=[]
    months=sorted(set(contract['examples']+[f'{y}-{m:02}' for y in contract['seasonal_years'] for m in range(1,13)]))
    for month in months:
        assert month[:4]!='2024'
        # Read independently parsed original row identities with multiplicity,
        # grouped at the raw index's 5 km resolution, not production 10 km chunks.
        raw=list(db.execute("SELECT source,i5,j5,day,dn,COUNT(*) FROM evidence INDEXED BY aggregate_scope WHERE pc='SP' AND ym=? GROUP BY source,i5,j5,day,dn",(month,)))
        all_rows+=sum(r[5] for r in raw);read_months.append(month)
        for area,b in contract['areas'].items():
            geo=[]
            for s,x,y,date,dn,n in raw:
                i,j=math.floor(x/2),math.floor(y/2)
                if area!='canada':
                    if (i,j) not in cache: cache[i,j]=inverse((i+.5)*10000,(j+.5)*10000)
                    lon,lat=cache[i,j]
                    if not (b[0]<=lon<b[2] and b[1]<=lat<b[3]):continue
                geo.append((s,x,y,date,dn,n))
            for flag in ['ALL','D','N']:
                for day in (contract['day_filters'] if month in contract['examples'] else [None]):
                    scope={'month':month,'area':area,'flag':flag,'day':day,'pc':'SP'}
                    lanes={s:{'n':0,'dates':set(),'keys':set()} for s in S}
                    k5={s:set() for s in S};k20={s:set() for s in S}
                    for s,x,y,date,dn,n in geo:
                        if flag!='ALL' and flag!=dn:continue
                        if day is not None and int(date[-2:])!=day:continue
                        lane=lanes[s];lane['n']+=n;lane['dates'].add(date)
                        lane['keys'].add((math.floor(x/2),math.floor(y/2),date))
                        k5[s].add((x,y,date));k20[s].add((math.floor(x/4),math.floor(y/4),date))
                    if month in contract['examples']:
                        case=next(e for e in expected['cases'] if e['scope']==scope)
                        full_keys=set().union(*(lanes[s]['keys'] for s in S));full_dates=set().union(*(lanes[s]['dates'] for s in S));full_records=sum(lanes[s]['n'] for s in S)
                        for policy, sources in [('MODIS_ONLY',S[:2]),('VIIRS_ONLY',S[2:]),('ALL_NATIVE',S)]:
                            keys=set().union(*(lanes[s]['keys'] for s in sources));dates=set().union(*(lanes[s]['dates'] for s in sources));n=sum(lanes[s]['n'] for s in sources)
                            result={'records':n,'source_cell_days':{s:len(lanes[s]['keys']) for s in sources},'union_cell_days':len(keys),'dates_with_records':sorted(dates),'excluded_records':full_records-n,'exclusive_cell_days_lost':len(full_keys-keys),'exclusive_dates_lost':sorted(full_dates-dates)}
                            assert result==case['policies'][policy],f'Independent retention mismatch: {scope}/{policy}'
                        cases+=1
                        scales.append({'scope':scope,'source_cell_days':{s:{'5000':len(k5[s]),'10000':len(lanes[s]['keys']),'20000':len(k20[s])} for s in S},'membership':'same native 10 km AOI membership at every counting scale'})
                    if month[:4] in [str(y) for y in contract['seasonal_years']] and day is None:
                        for s in S:
                            lane=next(e for e in expected['seasonal'] if e['scope']==scope and e['source']==s)
                            assert (lanes[s]['n'],len(lanes[s]['keys']),sorted(lanes[s]['dates']))==(lane['records'],lane['cell_days'],lane['dates_with_records'])
                            assert lane['month_length']==calendar.monthrange(int(month[:4]),int(month[5:]))[1]
                            seasonals+=1
    result={'state':'PASS','method':'Independent original-ZIP oracle SQLite rows; separate set arithmetic and analytical ellipsoidal inverse; no production imports or public-chunk calculation',
        'production_sha256':sha(O/'NATIVE_RETENTION.json'),'contract_sha256':sha(O/'RETENTION_CONTRACT.json'),
        'original_member_bindings':bindings,'raw_records_recounted':all_rows,'months_read':read_months,
        'retention_scopes_verified':cases,'policy_results_verified':cases*3,'seasonal_source_scopes_verified':seasonals,
        'holdouts_opened':False,'fit':False,'g4':'ADJUSTMENT_WITHHELD'}
    for name,data in [('INDEPENDENT_RETENTION.json',result),('GRID_SENSITIVITY.json',scales)]:
        encoded=(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n').encode();p=O/name
        if p.exists():assert p.read_bytes()==encoded
        else:p.write_bytes(encoded)
    print(json.dumps({**result,'elapsed_s':time.perf_counter()-start}))

if __name__=='__main__':run()
