"""Continue declared chronological native audits through the existing pipeline.

Preserves January stage, original annual files, current catalog and all holdouts.
"""
from collections import Counter
import csv,hashlib,io,json,math
from pathlib import Path
import zipfile
from pyproj import Transformer
import pipeline
from independent_recount import ellipsoidal_laea
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/acquisition/portugal-2013'
sha=lambda b:hashlib.sha256(b).hexdigest()

def audit_month(month):
    rule=json.loads((ROOT/'reports/HISTORICAL_PHASE3_RULE.json').read_text(encoding='utf-8'))
    assert month in rule['months'] and month.startswith('2013-'),'Outside declared training acquisition scope'
    manifest=json.loads((RAW/'ACQUISITION_MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:assert sha((RAW/item['file']).read_bytes())==item['sha256'],'Immutable source changed'
    stage=ROOT/'data/staging'/f'portugal-{month}';stage.mkdir(parents=True,exist_ok=True)
    transformer=Transformer.from_crs('EPSG:4326',pipeline.CRS_TEXT,always_xy=True)
    rows=[];oracle={};lineage={};deliveries=[]
    for filename,family in [('modis_2013_Portugal.csv','MODIS'),('viirs-snpp_2013_Portugal.csv','VIIRS')]:
        original=(RAW/filename).read_bytes();selected=[]
        aliases={'bright_ti4':'brightness','bright_ti5':'bright_t31'} if family=='VIIRS' else {}
        reader=csv.DictReader(io.StringIO(original.decode('utf-8-sig')))
        assert [aliases.get(k,k) for k in reader.fieldnames]==pipeline.FIELDS
        for number,row in enumerate(reader,2):
            if row['acq_date'].startswith(month+'-'):selected.append((number,row))
        identifier=f'country-{family.lower()}-{month}';member=identifier+'.csv';text=io.StringIO(newline='')
        writer=csv.DictWriter(text,fieldnames=pipeline.FIELDS);writer.writeheader()
        for _,row in selected:writer.writerow({aliases.get(k,k):v for k,v in row.items()})
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_STORED) as archive:
            archive.writestr(zipfile.ZipInfo(member,(1980,1,1,0,0,0)),text.getvalue())
            archive.writestr(zipfile.ZipInfo('Readme.txt',(1980,1,1,0,0,0)),(RAW/'AttributesReadme.txt').read_bytes())
        path=stage/(identifier+'.zip');data=stream.getvalue()
        if path.exists():assert path.read_bytes()==data,'Never replace a staged source derivative'
        else:path.write_bytes(data)
        audit,accepted=pipeline.audit(path,member,identifier,family,transformer);rows.extend(accepted)
        # Independent original-country reader, before canonical aliases/subset transport.
        positions=None;seen=set();derived_row=1
        for raw_number,values in enumerate(csv.reader(io.StringIO(original.decode('utf-8-sig'))),1):
            if positions is None:positions={k:i for i,k in enumerate(values)};continue
            v=lambda key:values[positions[key]]
            if not v('acq_date').startswith(month+'-'):continue
            derived_row+=1
            if tuple(values) in seen:continue
            seen.add(tuple(values));lon,lat=float(v('longitude')),float(v('latitude'))
            if not(-8.7<=lon<=-7.2 and 39.3<=lat<=40.8):continue
            x,y=ellipsoidal_laea(lon,lat);hour,minute=divmod(int(v('acq_time')),100);assert hour<24 and minute<60
            source={'Aqua':'AQUA_MODIS','Terra':'TERRA_MODIS','N':'SNPP_VIIRS'}[v('satellite')];key=f'{identifier}:{derived_row}'
            oracle[key]=(source,f"{v('acq_date')}T{hour:02}:{minute:02}:00Z",f'g:{math.floor(x/10000)}:{math.floor(y/10000)}',lon,lat,v('daynight'),v('confidence'),v('version'),v('type'),float(v('frp')),
                float(v('bright_ti4' if family=='VIIRS' else 'brightness')),float(v('bright_ti5' if family=='VIIRS' else 'bright_t31')),float(v('scan')),float(v('track')),v('satellite'),v('instrument'))
            lineage[key]={'raw_file':filename,'raw_row':raw_number,'derived_row':derived_row}
        deliveries.append({'file':filename,'raw_sha256':sha(original),'country_month_rows':len(selected),'accepted_aoi_records':len(accepted),
            'derived_zip':path.name,'derived_sha256':sha(data),'literal_versions':audit['categories']['version'],
            'identifier_kind':'DERIVED_COUNTRY_MONTH_NOT_NASA_REQUEST','original_country_processing_family':'NASA_OFFICIAL_COUNTRY_SP_DESCRIPTION'})
    actual={r['id']:(r['source'],r['utc'],r['cell'],r['longitude'],r['latitude'],r['daynight'],r['confidence'],r['version'],r['type'],r['frp'],r['brightness'],r['brightness2'],r['scan'],r['track'],r['nativeSatellite'],r['nativeInstrument']) for r in rows}
    assert actual==oracle,'Independent original-row, UTC, quality fields or LAEA mismatch'
    keys=Counter((r['source'],r['day'],r['cell']) for r in rows)
    expected=Counter((v[0],v[1][:10],v[2]) for v in oracle.values());assert keys==expected
    with (stage/'occupied_cell_days.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['source','utc_day','cell_id','reported_records']);w.writerows([*key,n] for key,n in sorted(keys.items()))
    with (stage/'occupied_cell_days.csv').open(newline='',encoding='utf-8') as f:assert {(r['source'],r['utc_day'],r['cell_id']):int(r['reported_records']) for r in csv.DictReader(f)}==dict(expected)
    result={'month':month,'state':'AUDITED_STAGED_NOT_QUALIFIED','raw_independent_recount':'PASS','summary':pipeline.summarize(rows),'deliveries':deliveries,
        'production_vintage':'UNVERIFIED','extract_completeness':'UNKNOWN','observation_support':'OBSERVATION_UNKNOWN','g4':'ADJUSTMENT_WITHHELD',
        'blockers':['Source-linked monthly expected/received upstream inventory absent.','Within-collection production vintage undocumented; literal row versions are not sufficient.','L2 pixel QA/geolocation and comparable acquisition support not qualified.']}
    content=json.dumps({'audit':result,'records':rows,'lineage':lineage},sort_keys=True,indent=2).encode()
    path=stage/'candidate.json'
    if path.exists():assert path.read_bytes()==content,'Staged candidate identity changed'
    else:path.write_bytes(content)
    result['candidate_sha256']=sha(content);result['occupied_csv_sha256']=sha((stage/'occupied_cell_days.csv').read_bytes())
    return result

def expand():
    protected={p:sha(p.read_bytes()) for p in [ROOT/'public/data/release.json',ROOT/'public/data/catalog.json',ROOT/'data/staging/portugal-2013-01/candidate.json']}
    rule_path=ROOT/'reports/HISTORICAL_PHASE3_RULE.json';rule=json.loads(rule_path.read_text(encoding='utf-8'))
    audits=[audit_month(month) for month in rule['months']]
    report={'state':'NATIVE_AUDITS_PASS_QUALIFICATION_BLOCKED','rule_sha256':sha(rule_path.read_bytes()),'adapter_sha256':sha(Path(__file__).read_bytes()),
        'pipeline_sha256':sha((ROOT/'science/pipeline.py').read_bytes()),'oracle_sha256':sha((ROOT/'science/independent_recount.py').read_bytes()),
        'months':audits,'additional_qualified_released_months':0,'current_release_unchanged':True,'holdouts_accessed':False,'g4':'ADJUSTMENT_WITHHELD'}
    output=ROOT/'reports/HISTORICAL_PHASE3_AUDIT.json';output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    status={'state':report['state'],'months':[{'month':m['month'],'state':m['state'],'summary':m['summary']} for m in audits],
        'report_sha256':sha(output.read_bytes()),'additional_qualified_released_months':0,'blockers':audits[0]['blockers']}
    (ROOT/'src/history-expansion.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    for path,digest in protected.items():assert sha(path.read_bytes())==digest,'Protected existing artifact changed'
    return report
if __name__=='__main__':
    report=expand();print(json.dumps({'state':report['state'],'months':[{k:m[k] for k in ['month','state','summary']} for m in report['months']]},indent=2))
