"""Independent aggregation acceptance: Python counters/sets over the RAW oracle index.

No production aggregation/import. Projection and input parsing already came from
canada_oracle.py, independently from immutable ZIPs. This pass deliberately avoids
the production SQL GROUP BY and bit-shift binning; it verifies every public chunk.
"""
import collections
import hashlib
import itertools
import json
import math
from pathlib import Path
import sqlite3
import time

ROOT=Path(__file__).resolve().parents[1]

def run():
    start=time.perf_counter();pointer=json.loads((ROOT/'public/data/canada/index.json').read_text(encoding='utf8'));cat_path=ROOT/('public'+pointer['file']);catalog=json.loads(cat_path.read_text(encoding='utf8'))
    assert hashlib.sha256(cat_path.read_bytes()).hexdigest()==pointer['sha256']
    db=sqlite3.connect(f'file:{(ROOT/"data/canada/oracle.sqlite").as_posix()}?mode=ro',uri=True);db.execute('PRAGMA cache_size=-18000')
    rows=db.execute('SELECT source,pc,ym,i5,j5,day,dn FROM evidence INDEXED BY oracle_science_cover ORDER BY source,pc,ym,i5,j5,day,dn')
    h=hashlib.sha256();daily_keys=0;total=collections.defaultdict(lambda:{'records':0,'cell_days':0});scales={str(n):collections.Counter() for n in [5000,10000,20000]};checked=0;max_keys=0
    for (source,pc,ym),group in itertools.groupby(rows,key=lambda r:r[:3]):
        daily=collections.Counter();five=set();ten=set();twenty=set();n=0
        for _,_,_,i5,j5,date,dn in group:
            i,j=math.floor(i5/2),math.floor(j5/2);daily[i,j,date,dn]+=1;five.add((i5,j5,date));ten.add((i,j,date));twenty.add((math.floor(i5/4),math.floor(j5/4),date));n+=1
            if len(daily)+len(five)+len(ten)+len(twenty)>1_000_000:raise ValueError('Independent per-month memory key guard exceeded; use disk partitioning, never truncate')
        max_keys=max(max_keys,len(daily)+len(five)+len(ten)+len(twenty));key=source+'|'+pc;total[key]['records']+=n;total[key]['cell_days']+=len(ten)
        for scale,values in [('5000',five),('10000',ten),('20000',twenty)]:scales[scale][source,pc]+=len(values)
        for (i,j,date,dn),count in sorted(daily.items()):h.update((json.dumps((source,pc,ym,i,j,date,dn,count),separators=(',',':'))+'\n').encode());daily_keys+=1
        entry=next(c for c in catalog['coverage'] if (c['source'],c['pc'],c['month'])==(source,pc,ym));chunk_path=ROOT/('public'+catalog['root']+entry['file']);raw=chunk_path.read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['sha256']
        chunk=json.loads(raw);actual={}
        for i,j,days in chunk['cells']:
            for day,d,native_n in days:
                date=f'{ym}-{day:02d}'
                if d:actual[i,j,date,'D']=d
                if native_n:actual[i,j,date,'N']=native_n
        assert actual==daily,f'Independent public daily mismatch: {source}/{pc}/{ym}'
        assert entry['records']==n and entry['cell_days']==len(ten);checked+=1
    assert total==catalog['total'],'Independent source totals mismatch'
    expected=catalog['oracle']['sensitivity_cell_days']
    for scale,counts in scales.items():assert {tuple(row[:2]):row[2] for row in expected[scale]}==dict(counts),'Independent scale union mismatch'
    assert h.hexdigest()==catalog['oracle']['independent_daily_multiset']['sha256']
    result={'state':'PASS','candidate':catalog['candidate'],'catalog_sha256':pointer['sha256'],'method':'Independent raw oracle index; Python counters + mathematical floor + distinct sets. No production SQL aggregation or helpers. Every emitted source/product/month/cell/date/DN multiplicity compared. Independent parser/projection preceded this pass.',
        'public_chunks_verified':checked,'accepted_records':sum(t['records'] for t in total.values()),'daily_multiset':{'keys':daily_keys,'sha256':h.hexdigest()},'totals':dict(total),'sensitivity':{s:[[a,b,n] for (a,b),n in sorted(v.items())] for s,v in scales.items()},'maximum_per_month_keys':max_keys,'per_month_key_guard':1_000_000,'elapsed_s':time.perf_counter()-start,'human_review':'NOT_PERFORMED','adjustment':'ADJUSTMENT_WITHHELD'}
    report=ROOT/'reports/CANADA_NATIVE_ORACLE_FINAL.json';report.write_text(json.dumps(result,indent=2),encoding='utf8')
    # Append an independently hash-bound acceptance artifact. Never change sealed catalog.
    public=ROOT/('public'+catalog['root']+'native-oracle.json');data=json.dumps({k:v for k,v in result.items() if k!='elapsed_s'},separators=(',',':')).encode()
    if public.exists():assert public.read_bytes()==data
    else:public.write_bytes(data)
    op={'candidate':catalog['candidate'],'file':catalog['root']+'native-oracle.json','sha256':hashlib.sha256(data).hexdigest()};op_path=ROOT/'public/data/canada/oracle-index.json'
    if op_path.exists():assert json.loads(op_path.read_text(encoding='utf8'))==op
    else:op_path.write_text(json.dumps(op,separators=(',',':')),encoding='utf8')
    print(json.dumps(result),flush=True)

if __name__=='__main__':run()
