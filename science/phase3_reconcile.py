"""Read-only original-archive D/N oracle and PROJ visualization fixtures.

Does not modify the pipeline, independent oracle, release or counting method.
"""
from collections import Counter
import csv,hashlib,io,json,math
from pathlib import Path
import zipfile
from pyproj import Transformer
from independent_recount import ellipsoidal_laea
from pipeline import CRS_TEXT
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()

def reconcile():
    original=(ROOT/'public/data/release.json').read_bytes();release=json.loads(original);raw=[]
    for manifest in release['manifests']:
        data=(Path.home()/'Downloads'/manifest['filename']).read_bytes();assert sha(data)==manifest['zip_sha256']
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert archive.testzip() is None;content=archive.read(manifest['csv_name'])
        assert sha(content)==manifest['csv_sha256'];seen=set()
        for row_no,r in enumerate(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))),2):
            identity=tuple(r.values())
            if identity in seen:continue
            seen.add(identity);lon,lat=float(r['longitude']),float(r['latitude'])
            if not(-8.7<=lon<=-7.2 and 39.3<=lat<=40.8):continue
            x,y=ellipsoidal_laea(lon,lat);hh,mm=divmod(int(r['acq_time']),100);assert 0<=hh<24 and 0<=mm<60
            assert r['daynight'] in ['D','N'],'Unknown flag cannot be silently assigned to Day/Night'
            raw.append({'id':f"{manifest['request_id']}:{row_no}",'source':{'Aqua':'AQUA_MODIS','Terra':'TERRA_MODIS','SNPP':'SNPP_VIIRS'}[r['satellite']],
                'day':r['acq_date'],'utc':f"{r['acq_date']}T{hh:02}:{mm:02}:00Z",'daynight':r['daynight'],'cell':f'g:{math.floor(x/10000)}:{math.floor(y/10000)}'})
    fields=['id','source','day','utc','daynight','cell']
    assert {tuple(r[k] for k in fields) for r in raw}=={tuple(r[k] for k in fields) for r in release['records']}
    def summary(rows):
        return {'records':len(rows),'occupied_cell_days':len({(r['source'],r['cell'],r['day']) for r in rows}),
            'utc_dates':len({r['day'] for r in rows}),'utc_instants':sorted({r['utc'] for r in rows})}
    totals={};reference={};groups=Counter((r['source'],r['day'],r['cell'],r['daynight']) for r in raw)
    for source in release['sources']:
        rows=[r for r in raw if r['source']==source]
        totals[source]={flag:summary([r for r in rows if flag=='ALL' or r['daynight']==flag]) for flag in ['ALL','D','N']}
        reference[source]={flag:summary([r for r in rows if r['cell']=='g:-2:-1' and (flag=='ALL' or r['daynight']==flag)]) for flag in ['ALL','D','N']}
        assert totals[source]['D']['records']+totals[source]['N']['records']==totals[source]['ALL']['records']
        for day in {r['day'] for r in rows}:
            keys=lambda flag:{r['cell'] for r in rows if r['day']==day and(flag=='ALL' or r['daynight']==flag)}
            assert keys('D')|keys('N')==keys('ALL')
    report={'state':'PASS','scope':'Original raw CSV -> unchanged release -> source/day/cell/DN multiplicities; browser tests independently consume these raw-derived groups.',
        'release_id':release['releaseId'],'release_sha256':sha(original),'raw_zip_hashes':{m['filename']:m['zip_sha256'] for m in release['manifests']},
        'totals':totals,'reference_cell':reference,'groups':[{'source':s,'day':d,'cell':c,'flag':f,'records':n} for (s,d,c,f),n in sorted(groups.items())],
        'other_or_missing_flags':0,'occupancy_rule':'D/N occupied keys overlap. Their union, never their arithmetic sum, equals All.',
        'opportunity':'UNKNOWN','g4':'ADJUSTMENT_WITHHELD','independent_human_review':'NOT_PERFORMED'}
    (ROOT/'reports/DAY_NIGHT_RECONCILIATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    forward=Transformer.from_crs('EPSG:4326',CRS_TEXT,always_xy=True);inverse=Transformer.from_crs(CRS_TEXT,'EPSG:4326',always_xy=True)
    points=[[-7.95,40.05],[-8.7,39.3],[-7.2,40.8]]+[[r['longitude'],r['latitude']] for r in release['records'][::100]]
    fixtures={'crs':CRS_TEXT,'producer':'PROJ via pyproj; browser uses separate equations','forward':[{'lonlat':p,'xy':forward.transform(*p)} for p in points],
        'inverse':[{'xy':[x,y],'lonlat':inverse.transform(x,y)} for x,y in [[0,0],[-20000,-10000],[60000,80000],[-60000,-80000]]],
        'release_sha256':sha(original)}
    (ROOT/'reports/ATLAS_PROJ_FIXTURES.json').write_text(json.dumps(fixtures,indent=2),encoding='utf-8')
    assert (ROOT/'public/data/release.json').read_bytes()==original
    return report
if __name__=='__main__':
    r=reconcile();print(json.dumps({'state':r['state'],'totals':{s:{f:{k:v for k,v in d.items() if k!='utc_instants'} for f,d in v.items()} for s,v in r['totals'].items()}},indent=2))
