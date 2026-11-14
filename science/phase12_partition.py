"""Exact source-positive cell-day partition from accepted immutable native chunks."""
from pathlib import Path
import hashlib,json,collections
from pyproj import Transformer
R=Path(__file__).resolve().parents[1];O=R/'reports/phase12'
S=['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS']
CASES=[('before','2010-06',None),('overlap','2023-06',[-120,49,-110,55]),('rectangle','2023-06',[-117,54,-115,55]),('empty','2023-06',[-53,80,-52.5,81])]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n').encode()
    if p.exists():assert p.read_bytes()==b,'Frozen result changed: '+str(p)
    else:p.write_bytes(b)
def run():
    ptr=json.loads((R/'public/data/canada/index.json').read_text(encoding='utf-8'));cp=R/('public'+ptr['file']);assert sha(cp)==ptr['sha256'];cat=json.loads(cp.read_text(encoding='utf-8'))
    inverse=Transformer.from_crs(cat['grid']['crs'],'EPSG:4326',always_xy=True)
    contract={'id':'native-positive-key-partition-v1','candidate':cat['candidate'],'catalog_sha256':ptr['sha256'],
      'cases':[{'id':i,'month':m,'rect':b} for i,m,b in CASES],'flags':['ALL','D','N'],'pc':'SP','grid':cat['grid']['grid_id'],
      'classification':'MODIS_ONLY if Aqua-or-Terra positive and no S-NPP positive; SHARED if both families positive; VIIRS_ONLY otherwise. Same fixed cell and UTC day, NOT simultaneous support.',
      'membership':'Unchanged native 10 km cell center; west/south inclusive, east/north exclusive; Canada extract membership not independently political-boundary certified',
      'rectangle_constraints':{'envelope':[-141.1,41.6,-52,83.3],'minimum_span_deg':0.05,'maximum_span_lon_lat_deg':[20,12]},
      'interpretation':'Positive-key retention only. Unknown observation opportunity/completeness; no calibrated agreement, missed fires, physical events or normalized trend.',
      'known_reference':[34,199,335,568],'prior_outcomes_known':True,'holdouts':'No new 2024 or original holdout query; no fit','g4':'ADJUSTMENT_WITHHELD'}
    put(O/'PARTITION_CONTRACT.json',contract)
    results=[];used={}
    for id,month,b in CASES:
      entries=[e for e in cat['coverage'] if e['pc']=='SP' and e['month']==month];chunks=[]
      for e in entries:
        p=R/('public'+cat['root']+e['file']);assert sha(p)==e['sha256'];used[e['file']]=e['sha256'];chunks.append(json.loads(p.read_text(encoding='utf-8')))
      for flag in ['ALL','D','N']:
        keys=collections.defaultdict(lambda:[0,0,0])
        for c in chunks:
          for i,j,days in c['cells']:
            if b:
              lon,lat=inverse.transform((i+.5)*10000,(j+.5)*10000)
              if not(b[0]<=lon<b[2] and b[1]<=lat<b[3]):continue
            for d,nd,nn in days:
              n=nd if flag=='D' else nn if flag=='N' else nd+nn
              if n:keys[i,j,f'{month}-{d:02}'][S.index(c['source'])]+=n
        rows=[];counts=collections.Counter()
        for (i,j,date),v in sorted(keys.items()):
          group='SHARED' if v[0]+v[1]>0 and v[2]>0 else 'MODIS_ONLY' if v[0]+v[1]>0 else 'VIIRS_ONLY'
          rows.append([i,j,date,*v,group]);counts[group]+=1
        totals={k:counts[k] for k in ['MODIS_ONLY','SHARED','VIIRS_ONLY']};totals['UNION']=len(rows)
        assert sum(totals[k] for k in ['MODIS_ONLY','SHARED','VIIRS_ONLY'])==totals['UNION']
        results.append({'id':id,'month':month,'rect':b,'flag':flag,'counts':totals,'records':[sum(v[3+k] for v in rows) for k in range(3)],'dates':sorted(set(r[2] for r in rows)),'rows':rows})
    main=next(c for c in results if c['id']=='overlap' and c['flag']=='ALL');assert list(main['counts'][k] for k in ['MODIS_ONLY','SHARED','VIIRS_ONLY','UNION'])==[34,199,335,568]
    result={'contract_sha256':sha(O/'PARTITION_CONTRACT.json'),'catalog_sha256':ptr['sha256'],'candidate':cat['candidate'],'input_chunks':used,
      'columns':['i','j','utc_day',*S,'positive_key_group'],'cases':results,'g4':'ADJUSTMENT_WITHHELD'}
    put(O/'PARTITION.json',result);print(json.dumps({'state':'PRODUCTION_RECOUNTED','cases':len(results),'primary':main['counts']}))
if __name__=='__main__':run()
