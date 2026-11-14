"""Independent Canada raw recount: separate line-object JSON reader and EPSG9820 math.

Does NOT import the intake, use its SQLite rows, or use PROJ to project records.
Reads immutable ZIPs again, checks CRC and row acceptance, builds its own disk index.
"""
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def project(lon,lat):
    a=6378137.;f=1/298.257223563;e2=f*(2-f);e=math.sqrt(e2)
    def q(p):
        s=math.sin(p)
        return (1-e2)*(s/(1-e2*s*s)-math.log((1-e*s)/(1+e*s))/(2*e))
    qp=q(math.pi/2);p0=math.pi/3;b0=math.asin(q(p0)/qp);b=math.asin(max(-1,min(1,q(math.radians(lat))/qp)))
    rq=a*math.sqrt(qp/2);d=a*math.cos(p0)/(math.sqrt(1-e2*math.sin(p0)**2)*rq*math.cos(b0))
    dl=math.radians((lon+100+180)%360-180)
    k=rq*math.sqrt(2/(1+math.sin(b0)*math.sin(b)+math.cos(b0)*math.cos(b)*math.cos(dl)))
    return k*d*math.cos(b)*math.sin(dl),k/d*(math.cos(b0)*math.sin(b)-math.sin(b0)*math.cos(b)*math.cos(dl))

def raw_objects(f):
    """Independent reader for actual delivered pretty JSON; reject format drift."""
    active=None;opened=False;closed=False
    for binary in f:
        line=binary.decode('utf8').strip()
        if not line:continue
        if line=='[' and not opened:opened=True;continue
        if line==']' and active is None:closed=True;continue
        if closed or not opened:raise ValueError('Unexpected JSON envelope')
        if line=='{':
            if active is not None:raise ValueError('Nested/unexpected object')
            active=['{'];continue
        if active is None:raise ValueError('Unexpected line outside object')
        active.append(line.rstrip(',') if line in ('},','}') else line)
        if sum(map(len,active))>65536:raise ValueError('Oversized oracle object')
        if line in ('},','}'):
            yield json.loads('\n'.join(active));active=None
    if active is not None or not closed:raise ValueError('Truncated JSON')

def run():
    start=time.perf_counter();folder=ROOT/'data/canada';folder.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(folder/'oracle.sqlite');db.execute('PRAGMA cache_size=-18000');db.execute('PRAGMA temp_store=FILE');db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''CREATE TABLE IF NOT EXISTS done(member TEXT PRIMARY KEY, archive_hash TEXT, report TEXT);
      CREATE TABLE IF NOT EXISTS evidence(member TEXT, hash BLOB, source TEXT, pc TEXT, ym TEXT, day TEXT, i5 INTEGER,j5 INTEGER,dn TEXT,PRIMARY KEY(member,hash)) WITHOUT ROWID;''')
    reports=[]
    for request,token in [('845605','M-C61'),('845606','SV-C2')]:
        path=Path.home()/'Downloads'/f'DL_FIRE_{token}_{request}.zip'
        with path.open('rb') as f:archive_hash=hashlib.file_digest(f,'sha256').hexdigest()
        with zipfile.ZipFile(path) as z:
            for name in sorted(z.namelist()):
                if not name.endswith('.json'):continue
                previous=db.execute('SELECT archive_hash,report FROM done WHERE member=?',(name,)).fetchone()
                if previous:
                    assert previous[0]==archive_hash;reports.append(json.loads(previous[1]));continue
                db.execute('DELETE FROM evidence WHERE member=?',(name,));db.commit()
                pc='NRT' if name.startswith('fire_nrt_') else 'SP';count=0;accepted=0;errors=collections.Counter();batch=[]
                with z.open(name) as f:
                    for r in raw_objects(f):
                        count+=1
                        try:
                            lon,lat=float(r['longitude']),float(r['latitude']);assert math.isfinite(lon+lat) and abs(lon)<=180 and abs(lat)<=90
                            day=datetime.date.fromisoformat(r['acq_date']);t=str(r['acq_time']).zfill(4);assert len(t)==4 and t.isdigit()
                            instant=datetime.datetime.combine(day,datetime.time(int(t[:2]),int(t[2:])))
                            assert datetime.date(2010,1,1)<=day<=datetime.date(2026,11,13)
                            if request=='845605':
                                assert r['satellite'] in ['Aqua','Terra'] and r['instrument']=='MODIS';source=r['satellite'].upper()+'_MODIS';assert str(r['confidence']).isdigit() and 0<=int(r['confidence'])<=100
                            else:
                                assert r['satellite']=='SNPP' and r['instrument'] in ['SNPP','VIIRS'];source='SNPP_VIIRS';assert r['confidence'] in ['l','n','h']
                                assert datetime.datetime(2012,1,20)<=instant<=datetime.datetime(2026,11,2,15,40)
                            assert r['daynight'] in ['D','N']
                            for field in ['latitude','longitude','frp','scan','track','brightness','bright_t31']:
                                assert math.isfinite(float(r[field]))
                                if field in ['frp','scan','track']:assert float(r[field])>=0
                        except (AssertionError,ValueError,KeyError,TypeError):errors['invalid_record']+=1;continue
                        x,y=project(lon,lat);key=hashlib.sha256(json.dumps(r,separators=(',',':'),sort_keys=True).encode('utf8')).digest()
                        batch.append((name,key,source,pc,day.isoformat()[:7],day.isoformat(),math.floor(x/5000),math.floor(y/5000),r['daynight']))
                        if len(batch)==10000:
                            before=db.total_changes;db.executemany('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?,?)',batch);accepted+=db.total_changes-before;db.commit();batch=[]
                        if count%250000==0:print(name,count,'oracle rows',round(time.perf_counter()-start,1),'s',flush=True)
                before=db.total_changes;db.executemany('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?,?)',batch);accepted+=db.total_changes-before
                result={'member':name,'raw_rows':count,'accepted':accepted,'invalid':dict(errors),'duplicates':count-accepted-sum(errors.values()),'crc':'PASS','archive_sha256':archive_hash}
                db.execute('INSERT INTO done VALUES(?,?,?)',(name,archive_hash,json.dumps(result)));db.commit();reports.append(result);print('ORACLE COMMITTED',name,count,flush=True)
    db.execute('CREATE INDEX IF NOT EXISTS aggregate_scope ON evidence(pc,ym,source,i5,j5,day)')
    db.execute('CREATE INDEX IF NOT EXISTS oracle_science_cover ON evidence(source,pc,ym,i5,j5,day,dn)');db.commit()
    out={'method':'independent line-object raw reader + ellipsoidal EPSG9820 math, separate SQLite dedup/index','members':reports,'elapsed_s':time.perf_counter()-start,'model_evaluation':'NOT_EXECUTED; holdouts sealed'}
    (ROOT/'reports/CANADA_ORACLE_INTAKE.json').write_text(json.dumps(out,indent=2),encoding='utf8');db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close();print('ORACLE INTAKE COMPLETE',out['elapsed_s'],flush=True)

if __name__=='__main__':run()
