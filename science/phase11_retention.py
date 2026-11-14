"""Native evidence retention from immutable, accepted calendar chunks. No fit.

Independent acceptance reads the original-archive oracle index, not these chunks.
All policies share one UTC window, native D/N partition and fixed 10 km AOI rule.
"""
from pathlib import Path
import calendar
import hashlib
import json
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/phase11'
SOURCES = ['AQUA_MODIS', 'TERRA_MODIS', 'SNPP_VIIRS']
POLICIES = {'MODIS_ONLY': SOURCES[:2], 'VIIRS_ONLY': SOURCES[2:], 'ALL_NATIVE': SOURCES}
AREAS = {'canada': None, 'south': [-120, 49, -110, 55], 'north': [-120, 60, -110, 66]}
MONTHS = ['2010-06', '2022-06', '2023-06']
YEARS = [2022, 2023]
CRS = '+proj=laea +lat_0=60 +lon_0=-100 +ellps=WGS84 +units=m +no_defs'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()
    if p.exists(): assert p.read_bytes() == data, 'Scientific artifact changed: '+str(p)
    else: p.write_bytes(data)

def catalog():
    pointer = json.loads((ROOT/'public/data/canada/index.json').read_text(encoding='utf-8'))
    p = ROOT/('public'+pointer['file'])
    assert sha(p) == pointer['sha256']
    return pointer, json.loads(p.read_text(encoding='utf-8'))

def measure(lanes):
    """Rows are additive source records; spatial/date evidence uses distinct sets."""
    all_keys = set().union(*(v['keys'] for v in lanes.values()))
    all_dates = set().union(*(v['dates'] for v in lanes.values()))
    total = sum(v['records'] for v in lanes.values())
    policies = {}
    for name, included in POLICIES.items():
        keys = set().union(*(lanes[s]['keys'] for s in included))
        dates = set().union(*(lanes[s]['dates'] for s in included))
        policies[name] = {
            'records': sum(lanes[s]['records'] for s in included),
            'source_cell_days': {s: len(lanes[s]['keys']) for s in included},
            'union_cell_days': len(keys), 'dates_with_records': sorted(dates),
            'excluded_records': total-sum(lanes[s]['records'] for s in included),
            'exclusive_cell_days_lost': len(all_keys-keys),
            'exclusive_dates_lost': sorted(all_dates-dates),
        }
    return policies

def run():
    pointer, cat = catalog()
    inverse = Transformer.from_crs(CRS, 'EPSG:4326', always_xy=True)
    center_cache = {}
    def inside(i, j, area):
        if area == 'canada': return True
        if (i,j) not in center_cache: center_cache[i,j] = inverse.transform((i+.5)*10000, (j+.5)*10000)
        lon, lat = center_cache[i,j]; b = AREAS[area]
        return b[0] <= lon < b[2] and b[1] <= lat < b[3]
    cases, seasonal, inputs = [], [], {}
    months = sorted(set(MONTHS+[f'{y}-{m:02}' for y in YEARS for m in range(1,13)]))
    for month in months:
        entries = [e for e in cat['coverage'] if e['pc']=='SP' and e['month']==month]
        chunks = []
        for e in entries:
            p = ROOT/('public'+cat['root']+e['file']); assert sha(p)==e['sha256']
            chunks.append(json.loads(p.read_text(encoding='utf-8'))); inputs[e['file']]=e['sha256']
        for area in AREAS:
            for flag in ['ALL', 'D', 'N']:
                for day in ([None,1,7,13] if month in MONTHS else [None]):
                    lanes = {s:{'records':0,'keys':set(),'dates':set()} for s in SOURCES}
                    for chunk in chunks:
                        lane = lanes[chunk['source']]
                        for i,j,days in chunk['cells']:
                            if not inside(i,j,area): continue
                            for d,nd,nn in days:
                                n = nd if flag=='D' else nn if flag=='N' else nd+nn
                                if not n or (day is not None and d!=day): continue
                                date=f'{month}-{d:02}'; lane['records']+=n
                                lane['keys'].add((i,j,date)); lane['dates'].add(date)
                    scope={'month':month,'area':area,'flag':flag,'day':day,'pc':'SP'}
                    if month in MONTHS: cases.append({'scope':scope,'policies':measure(lanes)})
                    if month[:4] in [str(y) for y in YEARS] and day is None:
                        for s in SOURCES:
                            entry=next((e for e in entries if e['source']==s),None)
                            seasonal.append({'scope':scope,'source':s,'records':lanes[s]['records'],
                                'cell_days':len(lanes[s]['keys']),'dates_with_records':sorted(lanes[s]['dates']),
                                'month_length':calendar.monthrange(int(month[:4]),int(month[5:]))[1],
                                'native_versions':entry.get('native_versions',[]) if entry else [],
                                'month_has_acquired_rows':entry is not None})
    contract={'id':'phase11-native-retention-v1','parent_catalog_sha256':pointer['sha256'],
        'examples':MONTHS,'seasonal_years':YEARS,'areas':AREAS,'day_filters':[None,1,7,13],
        'grid':'ca-laea60n100w-wgs84-o0-v1','cell_m':10000,'policies':POLICIES,
        'membership':'Canada extract or native 10 km cell center in half-open declared pilot box; no exact raw point polygon claim',
        'unit':'source records; source-specific cell-date keys; cross-source key/date unions are descriptive set operations',
        'opportunity':'UNKNOWN','completeness':'UNKNOWN','calibration':False,'holdout_access':'NONE; 2024 not queried',
        'interpretation':'Excluded evidence is not missed physical fires. Month length is disclosed, never an opportunity denominator.',
        'bridge_contract_sha256':sha(ROOT/'reports/phase10/QUALIFICATION_CONTRACT.json'),
        'g4_sha256':sha(ROOT/'reports/G4_DECISION.md')}
    dump(OUT/'RETENTION_CONTRACT.json',contract)
    result={'contract_sha256':sha(OUT/'RETENTION_CONTRACT.json'),'candidate':cat['candidate'],
        'catalog_sha256':pointer['sha256'],'chunk_sha256':inputs,'cases':cases,'seasonal':seasonal,
        'g4':'ADJUSTMENT_WITHHELD'}
    dump(OUT/'NATIVE_RETENTION.json',result)
    print(json.dumps({'cases':len(cases),'seasonal_lanes':len(seasonal),'chunk_checks':len(inputs),
        'sha256':sha(OUT/'NATIVE_RETENTION.json')}))

if __name__=='__main__': run()
