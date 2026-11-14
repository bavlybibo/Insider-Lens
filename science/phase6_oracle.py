"""Independent bounded re-selection and exhaustive pair oracle.

Starts from the separate Phase5 raw-archive oracle, without production AOI SQL,
selection helpers, aggregation or bisect matching. No Phase6 production imports.
"""
from collections import Counter
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from canada_oracle import project

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/phase6'
SHA=lambda b:hashlib.sha256(b).hexdigest()

def run():
    started=time.perf_counter();c=json.loads((OUT/'COHORT_CONTRACT.json').read_text());audit=json.loads((OUT/'COMMON_SUPPORT_AUDIT.json').read_text())
    raw=sqlite3.connect('file:'+str(ROOT/'data/canada/native.sqlite')+'?mode=ro',uri=True)
    oracle=sqlite3.connect('file:'+str(ROOT/'data/canada/oracle.sqlite')+'?mode=ro',uri=True)
    for db in [raw,oracle]:db.execute('PRAGMA query_only=ON');db.execute('PRAGMA cache_size=-12000')
    w,s,e,n=c['aoi_wsen'];selected=[];examined=0
    # Whole-country date cohorts from independent input, then re-read canonical
    # originals from the already hash-verified research cache and apply raw AOI.
    for source in c['sources']:
        for day in c['development']+c['replication']:
            sql='SELECT member,hash,i5,j5,dn FROM evidence WHERE source=? AND pc=? AND ym=? AND day=?'
            for member,h,i5,j5,dn in oracle.execute(sql,(source,'SP','2022-06',day)):
                examined+=1;found=raw.execute('SELECT raw FROM rows WHERE member=? AND hash=?',(member,h)).fetchone();assert found
                text=found[0];assert SHA(text.encode())==h.hex();r=json.loads(text)
                lon=float(r['longitude']);lat=float(r['latitude'])
                if not(w<=lon<e and s<=lat<n):continue
                x,y=project(lon,lat);assert (math.floor(x/5000),math.floor(y/5000))==(i5,j5)
                clock=str(r['acq_time']).zfill(4);utc=day+'T'+clock[:2]+':'+clock[2:]+':00Z'
                epoch=datetime.datetime.fromisoformat(utc.replace('Z','+00:00')).timestamp()
                assert r['daynight']==dn
                selected.append({'hash':h.hex(),'source':source,'day':day,'dn':dn,'x':x,'y':y,'epoch':epoch,'native':r})
    emitted=json.loads((OUT/'RESEARCH_ROWS.json').read_text());assert {r['hash'] for r in selected}=={r['raw_sha256'] for r in emitted}
    assert len(selected)==len(emitted)==audit['cohort_records'];checks=[]
    def k(r,width):return (math.floor(r['x']/width),math.floor(r['y']/width),r['day'])
    def summary(rs,width):
        result={source:{'records':sum(r['source']==source for r in rs),'cell_days':len({k(r,width) for r in rs if r['source']==source})} for source in c['sources']}
        a={k(r,width) for r in rs if r['source']=='AQUA_MODIS'};v={k(r,width) for r in rs if r['source']=='SNPP_VIIRS'}
        result['positive_sets']={'both_source_reported':len(a.intersection(v)),'aqua_only':len(a.difference(v)),'viirs_only':len(v.difference(a))};return result
    for split in ['development','replication']:
        rs=[r for r in selected if r['day'] in c[split]]
        for width in [5000,10000,20000]:
            expected=audit['results'][split]['scales'][str(width)];assert summary(rs,width)==expected['baseline']
            for minutes,target in zip(c['offset_minutes'],expected['timing']):
                keys=set();aid=set();vid=set();offsets=[]
                for a in [r for r in rs if r['source']=='AQUA_MODIS']:
                    for v in [r for r in rs if r['source']=='SNPP_VIIRS']:
                        if k(a,width)==k(v,width) and a['dn']==v['dn']:
                            offset=abs(a['epoch']-v['epoch'])/60
                            if width==10000:offsets.append(offset)
                            if offset<=minutes:keys.add(k(a,width));aid.add(a['hash']);vid.add(v['hash'])
                assert (len(keys),len(aid),len(vid))==(target['same_cell_day_same_flag_candidate_keys'],target['aqua_records_with_candidate'],target['viirs_records_with_candidate'])
                assert target['qualified_opportunities'] is None and target['qualified_report_frequency'] is None
                checks.append({'split':split,'width_m':width,'minutes':minutes,'candidate_keys':len(keys),
                               'min_same_flag_positive_offset_minutes':min(offsets,default=None) if width==10000 else None})
        policies={'native_all':rs,'literal_type0_unverified':[r for r in rs if str(r['native'].get('type'))=='0'],
                  'confidence_screen':[r for r in rs if (r['source']=='SNPP_VIIRS' and r['native']['confidence']!='l') or (r['source']!='SNPP_VIIRS' and int(r['native']['confidence'])>=30)],
                  'positive_frp_research':[r for r in rs if float(r['native']['frp'])>0]}
        for name,pr in policies.items():assert summary(pr,10000)==audit['results'][split]['quality_sensitivity'][name]
    csv_rows=list(csv.DictReader((OUT/'RESEARCH_FRP.csv').open(encoding='utf-8')));assert len(csv_rows)==len(selected)
    byhash={r['hash']:r for r in selected}
    for r in csv_rows:
        original=byhash[r['raw_sha256']]['native'];assert float(r['frp_MW'])==float(original['frp'])
        for a,b in [('type_literal','type'),('confidence_literal','confidence'),('version_literal','version')]:assert r[a]==str(original.get(b,''))
        assert r['opportunity']=='UNKNOWN' and r['g4']=='ADJUSTMENT_WITHHELD'
    # Independent analytic ellipsoid area of a meridian/parallel-bounded AOI.
    a=6378137.;f=1/298.257223563;ecc=math.sqrt(f*(2-f))
    def primitive(lat):
        z=math.sin(math.radians(lat));return z/(2*(1-ecc*ecc*z*z))+math.atanh(ecc*z)/(2*ecc)
    analytic=a*a*(1-ecc*ecc)*math.radians(e-w)*(primitive(n)-primitive(s))
    geometry=json.loads((OUT/'COMMON_GEOMETRY.json').read_text());errors={}
    for label in ['coarse','fine']:
        g=geometry[label];assert abs(sum(p['area_m2'] for p in g['cells'])-g['aoi_projected_area_m2'])<1
        assert all(0<p['cell_fraction']<=1+1e-7 for p in g['cells'])
        errors[label]=abs(g['aoi_projected_area_m2']-analytic)/analytic
    assert errors['fine']<errors['coarse'] and errors['fine']<2e-6
    assert audit['g4']=='ADJUSTMENT_WITHHELD' and audit['candidate_fit'] is False
    result={'state':'PASS','method':'Independent raw-oracle cohort enumeration; canonical original-field re-selection; EPSG9820 projection; exhaustive timestamp pair loops; analytic ellipsoidal AOI area',
            'country_date_rows_examined':examined,'selected_rows':len(selected),'matching_checks':checks,
            'analytic_aoi_area_m2':analytic,'clipped_area_relative_errors':errors,
            'research_rows_sha256':SHA((OUT/'RESEARCH_ROWS.json').read_bytes()),'audit_sha256':SHA((OUT/'COMMON_SUPPORT_AUDIT.json').read_bytes()),
            'elapsed_seconds':time.perf_counter()-started,'human_review':'NOT_PERFORMED','holdouts':'NOT_OPENED'}
    (OUT/'INDEPENDENT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':run()
