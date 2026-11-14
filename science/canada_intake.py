"""Canada positive-evidence intake. Streaming JSON arrays; immutable ZIPs stay closed to writes.

Run with the repository venv. SQLite is the disk-backed raw partition/index, not a
browser payload. A committed member is resumable only under the same input hash.
"""
import argparse
import collections
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import time
import zipfile
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
CRS = '+proj=laea +lat_0=60 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs +type=crs'
GRID = 'ca-laea60n100w-wgs84-o0-v1'
INPUTS = [('DL_FIRE_M-C61_845605.zip', '845605', 'MODIS C6.1'), ('DL_FIRE_SV-C2_845606.zip', '845606', 'S-NPP VIIRS C2')]
EXPECTED = {'845605':'a77dd443e9c3a85724b3994a3500d9d129bf528bd61ce78bf6e518fd07276913', '845606':'0d15a42c9584beb691e2ed4e33e1b8ce7d744a79105b52dc21a0c55bf480daad'}
BASE = {'latitude','longitude','acq_date','acq_time','track','version','frp','confidence','scan','bright_t31','satellite','brightness','instrument','daynight'}
NUMERIC = ['latitude','longitude','frp','scan','track','brightness','bright_t31']

def dump(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf8')

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def safe_members(z):
    total = 0
    for m in z.infolist():
        p = PurePosixPath(m.filename.replace('\\','/'))
        if p.is_absolute() or '..' in p.parts or ':' in m.filename or m.flag_bits & 1:
            raise ValueError('Unsafe/encrypted ZIP member')
        total += m.file_size
        if m.file_size > 4_000_000_000 or total > 6_000_000_000 or m.file_size/max(m.compress_size,1)>100:
            raise ValueError('ZIP expansion guard')
        if m.filename not in ('Readme.txt',) and not (m.filename.startswith(('fire_archive_','fire_nrt_')) and m.filename.endswith('.json')):
            raise ValueError('Unexpected member/schema')
    return z.infolist()

def objects(binary, hash_state=None, chunk=131072):
    """Strict incremental top-level JSON array, bounded to one 64KiB record + chunk.

    Raw bytes hashed as consumed; ZipExtFile checks CRC at EOF. No read(-1).
    """
    decoder=json.JSONDecoder(); buf=''; pos=0; eof=False
    def refill():
        nonlocal buf,pos,eof
        b=binary.read(chunk)
        if hash_state is not None: hash_state.update(b)
        buf=buf[pos:]+b.decode('utf8');pos=0;eof=not b
    def whitespace():
        nonlocal pos
        while True:
            while pos<len(buf) and buf[pos].isspace():pos+=1
            if pos<len(buf) or eof:return
            refill()
    refill();whitespace()
    if pos>=len(buf) or buf[pos]!='[':raise ValueError('Expected JSON array')
    pos+=1;whitespace()
    if pos<len(buf) and buf[pos]==']':pos+=1
    else:
        while True:
            while True:
                try: value,end=decoder.raw_decode(buf,pos);break
                except json.JSONDecodeError:
                    if eof or len(buf)-pos>65536:raise ValueError('Malformed/oversized JSON object')
                    refill()
            if end-pos>65536:raise ValueError('Oversized JSON object')
            if not isinstance(value,dict):raise ValueError('Non-object JSON record')
            pos=end;yield value;whitespace()
            if pos>=len(buf):raise ValueError('Truncated JSON array')
            c=buf[pos];pos+=1
            if c==']':break
            if c!=',':raise ValueError('Invalid JSON array separator')
            whitespace()
    whitespace()
    if pos!=len(buf):raise ValueError('Trailing JSON data')

def parse(r, request):
    if not BASE.issubset(r) or set(r)-BASE-{'type'}:raise ValueError('schema')
    lon,lat=float(r['longitude']),float(r['latitude'])
    if not math.isfinite(lon+lat) or not(-180<=lon<=180 and -90<=lat<=90):raise ValueError('coordinates')
    date=dt.date.fromisoformat(str(r['acq_date']));t=str(r['acq_time']).zfill(4)
    if len(t)!=4 or not t.isdigit():raise ValueError('utc')
    instant=dt.datetime(date.year,date.month,date.day,int(t[:2]),int(t[2:]),tzinfo=dt.timezone.utc)
    if not '2010-01-01'<=date.isoformat()<='2026-11-13':raise ValueError('requested_time_bounds')
    sat,inst=str(r['satellite']),str(r['instrument'])
    if request=='845605' and inst=='MODIS' and sat in ('Aqua','Terra'):source=sat.upper()+'_MODIS'
    elif request=='845606' and sat=='SNPP' and inst in ('VIIRS','SNPP'):source='SNPP_VIIRS'
    else:raise ValueError('source_identity')
    if str(r['daynight']) not in ('D','N'):raise ValueError('daynight')
    conf=str(r['confidence'])
    if source=='SNPP_VIIRS':
        if conf not in ('l','n','h'):raise ValueError('confidence')
        if instant<dt.datetime(2012,1,20,tzinfo=dt.timezone.utc) or instant>dt.datetime(2026,11,2,15,40,tzinfo=dt.timezone.utc):raise ValueError('source_era')
    elif not (conf.isdigit() and 0<=int(conf)<=100):raise ValueError('confidence')
    for f in NUMERIC:
        v=float(r[f])
        if not math.isfinite(v) or (f in ('frp','scan','track') and v<0):raise ValueError('numeric_'+f)
    return source,instant.strftime('%Y-%m-%dT%H:%M:00Z'),lon,lat

def preregister():
    p=ROOT/'reports/CANADA_PREREGISTRATION.json'
    rule={'id':'ca-native-protocol-v1','frozen_before':'full record parsing / regional outcome inspection',
      'inputs':EXPECTED,'grid':{'id':GRID,'crs':CRS,'origin_m':[0,0],'counting_m':10000,'sensitivity_m':[5000,10000,20000]},
      'estimand':'native positive source/product-class occupied cell UTC days; no exposure denominator',
      'pilot':{'southern':[-120,49,-110,55],'northern':[-120,60,-110,66],
        'active_context':'2023-06 (Canada 2023 fire season is prior public context, not outcome-selected)',
        'comparable':'2022-06, same bounds, no seasonal anomaly inference','early_context':'2010-06'},
      'development':{'bbox':[-120,49,-110,55],'months':['2022-06','2023-06']},
      'temporal_holdout':{'bbox':[-120,49,-110,55],'months':['2024-06'],'buffer':'no fitting on intervening 11 months'},
      'geographic_holdout':{'bbox':[-120,60,-110,66],'months':['2024-06'],'buffer':'5 degree latitude gap from development'},
      'holdout_policy':'Intake aggregate inventory is not evaluation. No holdout model/outcome metrics opened; no model fitted. Original Portugal/California holds remain sealed.',
      'matching_if_data_qualified':{'maximum_offset_minutes':10,'sensitivities_minutes':[5,15],
        'required':['same-platform fire mask and QA definitions verified for exact collection','geolocation footprint intersection','valid clear pixels in shared footprint','view zenith <=40 degrees with 30/50 sensitivity','no non-nominal/bowtie/duplicate support'],
        'baseline':'no-adjustment identity on compatible measured units only','uncertainty':'space/time block bootstrap, blocks >=50km /7days, frozen before fit',
        'release':'all original G4 conditions plus independent reviewer signatures; fail closed'},
      'stop':'No masks/QA/compatible support -> no matching model or correction; G4 ADJUSTMENT_WITHHELD'}
    if p.exists():assert json.loads(p.read_text(encoding='utf8'))==rule,'Frozen protocol changed'
    else:dump(p,rule)
    return digest(p)

def run():
    start=time.perf_counter();prereg_sha=preregister()
    stage=ROOT/'data/canada';stage.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(stage/'native.sqlite');db.execute('PRAGMA cache_size=-24000');db.execute('PRAGMA temp_store=FILE');db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL')
    db.executescript('''CREATE TABLE IF NOT EXISTS members(name TEXT PRIMARY KEY, archive_hash TEXT, report TEXT);
      CREATE TABLE IF NOT EXISTS rows(member TEXT,row INTEGER,source TEXT,pc TEXT,ym TEXT,day TEXT,utc TEXT,lon REAL,lat REAL,i5 INTEGER,j5 INTEGER,dn TEXT,hash BLOB,raw TEXT);
      CREATE UNIQUE INDEX IF NOT EXISTS raw_member_identity ON rows(member,hash);''')
    transform=Transformer.from_crs('EPSG:4326',CRS,always_xy=True)
    inventory=[]
    for filename,request,collection in INPUTS:
        path=Path.home()/'Downloads'/filename;archive_hash=digest(path)
        assert archive_hash==EXPECTED[request],'Input identity mismatch'
        entry={'path':str(path),'request':request,'collection':collection,'zip_sha256':archive_hash,'zip_bytes':path.stat().st_size,'origin':'Operator-supplied FIRMS request ZIP; exact delivery URL not supplied','members':[]}
        with zipfile.ZipFile(path) as z:
            for m in safe_members(z):
                if m.filename=='Readme.txt':
                    data=z.read(m);entry['members'].append({'name':m.filename,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'crc':'PASS'});continue
                existing=db.execute('SELECT archive_hash,report FROM members WHERE name=?',(m.filename,)).fetchone()
                if existing:
                    assert existing[0]==archive_hash,'Cannot resume changed source'
                    entry['members'].append(json.loads(existing[1]));print('RESUME committed',m.filename,flush=True);continue
                # A partial member is re-streamed for complete forensic counters.
                # Its committed raw keys are reused, not deleted or ingested twice.
                pc='SP' if m.filename.startswith('fire_archive_') else 'NRT'
                report={'name':m.filename,'processing_class':pc,'bytes':m.file_size,'compressed_bytes':m.compress_size,'crc32':f'{m.CRC:08x}',
                    'rows':0,'accepted':0,'duplicates':0,'excluded':{},'missing':{},'categories':{},'numeric_ranges':{},'first_utc':None,'last_utc':None,'bbox_wsen':[180,90,-180,-90],'outside_broad_canada_envelope':0,'schemas':{}}
                categories={f:collections.Counter() for f in ['satellite','instrument','daynight','version','confidence','type']};missing=collections.Counter();excluded=collections.Counter();schemas=collections.Counter();ranges={};h=hashlib.sha256();batch=[]
                with z.open(m) as f:
                    for row,r in enumerate(objects(f,h),1):
                        report['rows']=row;schemas['|'.join(sorted(r))]+=1
                        for field in BASE|{'type'}:
                            if field not in r or r[field] is None or str(r[field]).strip()=='':missing[field]+=1
                        for field in categories:categories[field][str(r.get(field,'<ABSENT>'))]+=1
                        for field in NUMERIC:
                            try:
                                value=float(r[field])
                                if math.isfinite(value):
                                    a=ranges.setdefault(field,{'min':value,'max':value});a['min']=min(a['min'],value);a['max']=max(a['max'],value)
                            except (ValueError,TypeError,KeyError):pass
                        try:source,utc,lon,lat=parse(r,request)
                        except (ValueError,TypeError,KeyError) as e:excluded[str(e)]+=1;continue
                        report['first_utc']=min(report['first_utc'] or utc,utc);report['last_utc']=max(report['last_utc'] or utc,utc)
                        b=report['bbox_wsen'];b[0]=min(b[0],lon);b[1]=min(b[1],lat);b[2]=max(b[2],lon);b[3]=max(b[3],lat)
                        if not(-141.1<=lon<=-52 and 41.6<=lat<=83.3):report['outside_broad_canada_envelope']+=1
                        x,y=transform.transform(lon,lat);raw=json.dumps(r,sort_keys=True,separators=(',',':'));key=hashlib.sha256(raw.encode()).digest()
                        batch.append((m.filename,row,source,pc,utc[:7],utc[:10],utc,lon,lat,math.floor(x/5000),math.floor(y/5000),r['daynight'],key,raw))
                        if len(batch)>=10000:
                            before=db.total_changes;db.executemany('INSERT OR IGNORE INTO rows VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',batch);report['accepted']+=db.total_changes-before;batch.clear();db.commit()
                        if row%250000==0:print(m.filename,row,'rows',round(time.perf_counter()-start,1),'s',flush=True)
                if batch:
                    before=db.total_changes;db.executemany('INSERT OR IGNORE INTO rows VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',batch);report['accepted']+=db.total_changes-before;db.commit()
                report['accepted']=db.execute('SELECT COUNT(*) FROM rows WHERE member=?',(m.filename,)).fetchone()[0]
                report.update(sha256=h.hexdigest(),crc='PASS',duplicates=report['rows']-report['accepted']-sum(excluded.values()),excluded=dict(excluded),missing=dict(missing),schemas=dict(schemas),categories={k:dict(v) for k,v in categories.items()},numeric_ranges=ranges)
                report['distinct_acquisition_instants']=db.execute('SELECT COUNT(DISTINCT utc) FROM rows WHERE member=?',(m.filename,)).fetchone()[0]
                report['distinct_dates']=db.execute('SELECT COUNT(DISTINCT day) FROM rows WHERE member=?',(m.filename,)).fetchone()[0]
                db.execute('INSERT INTO members VALUES(?,?,?)',(m.filename,archive_hash,json.dumps(report)));db.commit();entry['members'].append(report)
                dump(stage/'progress.json',{'completed':m.filename,'report':report});print('COMMITTED',m.filename,report['accepted'],flush=True)
        inventory.append(entry)
    db.execute('CREATE INDEX IF NOT EXISTS scope ON rows(pc,ym,source,i5,j5,day)')
    db.execute('CREATE INDEX IF NOT EXISTS science_cover ON rows(source,pc,ym,i5,j5,day,dn)');db.commit()
    manifest={'schema':'canada-intake-v1','candidate_id':'ca-'+hashlib.sha256((''.join(EXPECTED.values())+GRID).encode()).hexdigest()[:24],
      'status':'ACQUIRED_NATIVE_CANDIDATE','preregistration_sha256':prereg_sha,'grid_id':GRID,'crs':CRS,'archives':inventory,
      'support':'OBSERVATION_UNKNOWN','production_vintage':'UNVERIFIED','type_policy':'no Type filter','confidence_policy':'all valid native classes','adjustment':'ADJUSTMENT_WITHHELD',
      'elapsed_s':time.perf_counter()-start,'ram_policy':'128KiB JSON chunks, <=64KiB object, 10000-row insert batches, SQLite 24MiB cache, disk temp/indexes; no country-wide Python list'}
    manifest_file=stage/'INTAKE_MANIFEST.json'
    if manifest_file.exists():
        prior=json.loads(manifest_file.read_text(encoding='utf8'))
        assert {k:v for k,v in prior.items() if k!='elapsed_s'}=={k:v for k,v in manifest.items() if k!='elapsed_s'},'Committed intake manifest changed'
        manifest=prior
    else:dump(manifest_file,manifest)
    report_file=ROOT/'reports/CANADA_RAW_INVENTORY.json'
    if report_file.exists():assert json.loads(report_file.read_text(encoding='utf8'))==manifest
    else:dump(report_file,manifest)
    db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close();print(json.dumps({'candidate':manifest['candidate_id'],'current_run_elapsed_s':time.perf_counter()-start,'original_generation_elapsed_s':manifest['elapsed_s']}),flush=True)

if __name__=='__main__':run()
