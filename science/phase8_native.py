"""Bounded read-only native history, reconciled to the preserved independent store."""
from collections import Counter,defaultdict
import csv
import io
import hashlib
import json
import math
import sqlite3
from pyproj import Transformer
from canada_oracle import project
from phase8_contract import ROOT,OUT,sha,immutable

def run():
    c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());w,s,e,n=c['aoi_wsen'];days={int(d[-2:]) for d in c['window_days']}
    native=sqlite3.connect((ROOT/'data/canada/native.sqlite').as_uri()+'?mode=ro',uri=True);native.row_factory=sqlite3.Row
    oracle=sqlite3.connect((ROOT/'data/canada/oracle.sqlite').as_uri()+'?mode=ro',uri=True)
    rows=list(native.execute("select * from rows where pc='SP' and ym='2023-06' and lon>=? and lon<? and lat>=? and lat<? order by source,utc,member,row",(w,e,s,n)))
    rows=[r for r in rows if int(r['day'][-2:]) in days];t=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True)
    counts=Counter();keys=defaultdict(set);frp=defaultdict(list);checks=0;native_records=[]
    for r in rows:
        raw=json.loads(r['raw']);h=bytes(r['hash']);assert hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).digest()==h
        entry=oracle.execute('select source,pc,ym,day,i5,j5,dn from evidence where member=? and hash=?',(r['member'],h)).fetchone()
        assert entry==tuple(r[k] for k in ['source','pc','ym','day','i5','j5','dn'])
        x,y=project(r['lon'],r['lat']);xp,yp=t.transform(r['lon'],r['lat']);assert max(abs(x-xp),abs(y-yp))<1e-6
        assert (math.floor(x/5000),math.floor(y/5000))==(r['i5'],r['j5'])
        # Recount using original raw fields, not stored count aggregates.
        assert raw['acq_date']==r['day'] and raw['daynight']==r['dn']
        key=(r['source'],int(r['day'][-2:]));counts[key]+=1;keys[key].add((math.floor(x/10000),math.floor(y/10000)));frp[key].append(float(raw['frp']));checks+=1
        native_records.append({'member':r['member'],'row':r['row'],'raw_sha256':h.hex(),'source':r['source'],'utc':r['utc'],'native':raw})
    sources=['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS'];calendar=[]
    for day in sorted(days):calendar.append({'date':f'2023-06-{day:02d}','sources':{source:{'records':counts[source,day],'occupied_cell_days':len(keys[source,day]),'raw_frp_mw_sum':math.fsum(frp[source,day]),'observation_support':'UNKNOWN'} for source in sources}})
    result={'state':'PASS','contract_sha256':sha(OUT/'COHORT_CONTRACT.json'),'aoi_wsen':c['aoi_wsen'],'pc':'SP','calendar':calendar,
        'totals':{source:{'records':sum(counts[source,d] for d in days),'occupied_cell_days':sum(len(keys[source,d]) for d in days)} for source in sources},
        'raw_identity_checks':checks,'independent_store':'preserved oracle.sqlite raw identity + independent scalar EPSG9820 versus PROJ; no re-ingest or database mutation',
        'L2_ancestry':'not established; monthly delivery vintage and current L2 are not joined as the same processed observations',
        'meaning':'records and source-separated occupied10kmcell-days; missing rows are not fire-free days, no exposure normalization',
        'holdouts_opened':False,'g4':'ADJUSTMENT_WITHHELD'}
    immutable(OUT/'NATIVE_HISTORY.json',result);immutable(OUT/'NATIVE_RECORDS.json',native_records)
    native.close();oracle.close();print(json.dumps({'records':checks,'totals':result['totals']}))

if __name__=='__main__':run()
