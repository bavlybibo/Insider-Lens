"""Independent exact key/record partition from original-ZIP oracle identities."""
from pathlib import Path
import hashlib,json,sqlite3,math,collections
from pyproj import Transformer
R=Path(__file__).resolve().parents[1];O=R/'reports/phase12'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run():
    expected=json.loads((O/'PARTITION.json').read_text(encoding='utf-8'));contract=json.loads((O/'PARTITION_CONTRACT.json').read_text(encoding='utf-8'))
    assert expected['contract_sha256']==sha(O/'PARTITION_CONTRACT.json')
    # Raw archive parsing/projection already independently qualified. Recheck bindings.
    intake=json.loads((R/'data/canada/INTAKE_MANIFEST.json').read_text(encoding='utf-8'))
    for a in intake['archives']:assert sha(Path(a['path']))==a['zip_sha256']
    db=sqlite3.connect(f'file:{(R/"data/canada/oracle.sqlite").as_posix()}?mode=ro',uri=True);db.execute('PRAGMA cache_size=-18000')
    inv=Transformer.from_crs('+proj=laea +lat_0=60 +lon_0=-100 +ellps=WGS84 +units=m','EPSG:4326',always_xy=True)
    months=sorted({c['month'] for c in contract['cases']});checked=0;raw_rows=0;max_error=0
    # Separate inverse equations are retained from the independent Phase11 oracle.
    from phase11_oracle import inverse
    for month in months:
      assert not month.startswith('2024')
      raw=list(db.execute("SELECT source,i5,j5,day,dn,COUNT(*) FROM evidence INDEXED BY aggregate_scope WHERE pc='SP' AND ym=? GROUP BY source,i5,j5,day,dn",(month,)))
      raw_rows+=sum(r[-1] for r in raw)
      for case in [c for c in contract['cases'] if c['month']==month]:
        for flag in contract['flags']:
          table={}
          for s,x,y,date,dn,n in raw:
            if flag!='ALL' and flag!=dn:continue
            i,j=math.floor(x/2),math.floor(y/2)
            if case['rect']:
              lon,lat=inverse((i+.5)*10000,(j+.5)*10000);plon,plat=inv.transform((i+.5)*10000,(j+.5)*10000);max_error=max(max_error,abs(plon-lon),abs(plat-lat));b=case['rect']
              if not(b[0]<=lon<b[2] and b[1]<=lat<b[3]):continue
            key=(i,j,date);v=table.setdefault(key,dict(AQUA_MODIS=0,TERRA_MODIS=0,SNPP_VIIRS=0));v[s]+=n
          modis={k for k,v in table.items() if v['AQUA_MODIS']+v['TERRA_MODIS']>0};viirs={k for k,v in table.items() if v['SNPP_VIIRS']>0}
          groups={'MODIS_ONLY':modis-viirs,'SHARED':modis&viirs,'VIIRS_ONLY':viirs-modis};union=modis|viirs
          assert not(groups['MODIS_ONLY']&groups['SHARED'] or groups['VIIRS_ONLY']&groups['SHARED'] or groups['MODIS_ONLY']&groups['VIIRS_ONLY'])
          actual=[]
          for k,v in sorted(table.items()):actual.append([*k,v['AQUA_MODIS'],v['TERRA_MODIS'],v['SNPP_VIIRS'],next(g for g,keys in groups.items() if k in keys)])
          e=next(c for c in expected['cases'] if c['id']==case['id'] and c['flag']==flag)
          assert actual==e['rows'],f'Exact key/source/record mismatch: {case["id"]}/{flag}'
          assert {**{g:len(ks) for g,ks in groups.items()},'UNION':len(union)}==e['counts'];checked+=1
    result={'state':'PASS','production_sha256':sha(O/'PARTITION.json'),'contract_sha256':sha(O/'PARTITION_CONTRACT.json'),
      'method':'Independent original-ZIP raw oracle index; separate difference/intersection/union sets, analytical inverse, every emitted key and source multiplicity compared',
      'raw_records_recounted':raw_rows,'cases_verified':checked,'maximum_inverse_difference_deg':max_error,
      'holdouts_queried':False,'months_read':months,'fit':False,'coincident_opportunities':None,'calibrated_agreement':None,'g4':'ADJUSTMENT_WITHHELD'}
    p=O/'INDEPENDENT_PARTITION.json';b=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode()
    if p.exists():assert p.read_bytes()==b
    else:p.write_bytes(b)
    out=R/'public/data/phase12';out.mkdir(parents=True,exist_ok=True)
    for name in ['PARTITION.json','INDEPENDENT_PARTITION.json','PARTITION_CONTRACT.json']:
      p=out/name;data=(O/name).read_bytes()
      if p.exists():assert p.read_bytes()==data
      else:p.write_bytes(data)
    pointer={'candidate':expected['candidate'],'file':'/data/phase12/PARTITION.json','sha256':sha(out/'PARTITION.json'),'oracle_file':'/data/phase12/INDEPENDENT_PARTITION.json','oracle_sha256':sha(out/'INDEPENDENT_PARTITION.json')}
    p=out/'index.json';data=(json.dumps(pointer,sort_keys=True,separators=(',',':'))+'\n').encode()
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
    print(json.dumps(result))
if __name__=='__main__':run()
