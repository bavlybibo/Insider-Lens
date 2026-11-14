"""Stage the predeclared January 2013 candidate; never publishes a release.

Uses the unchanged production audit/PROJ method and the existing oracle's
independent ellipsoidal equations. An independent parser recounts raw country
CSV rows. VIIRS thermal aliases are renamed verbatim, never converted.
"""
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile
from pyproj import Transformer
import pipeline
from independent_recount import ellipsoidal_laea

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/acquisition/portugal-2013'
STAGE=ROOT/'data/staging/portugal-2013-01'
sha=lambda b: hashlib.sha256(b).hexdigest()


def inspect_candidate(raw=RAW, stage=STAGE):
    acquisition=json.loads((raw/'ACQUISITION_MANIFEST.json').read_text())
    assert acquisition['candidate_month']=='2013-01'
    for item in acquisition['files']:
        assert sha((raw/item['file']).read_bytes())==item['sha256'], 'Immutable acquired input changed'
    index={r['filename']:r for r in csv.DictReader(io.StringIO((raw/'yearly_summary_files.txt').read_text()))}
    stage.mkdir(parents=True,exist_ok=True)
    transformer=Transformer.from_crs('EPSG:4326',pipeline.CRS_TEXT,always_xy=True)
    accepted=[]; all_oracle={}; manifests=[]; lineage={}; delivery=[]
    for name,family in [('modis_2013_Portugal.csv','MODIS'),('viirs-snpp_2013_Portugal.csv','VIIRS')]:
        original=(raw/name).read_bytes()
        assert len(original)==int(index[name]['size']), 'NASA index byte-size mismatch'
        reader=csv.DictReader(io.StringIO(original.decode('utf-8-sig')))
        aliases={'bright_ti4':'brightness','bright_ti5':'bright_t31'} if family=='VIIRS' else {}
        assert [aliases.get(f,f) for f in reader.fieldnames]==pipeline.FIELDS
        subset=[]
        for row_number,row in enumerate(reader,2):
            if row['acq_date'].startswith('2013-01-'): subset.append((row_number,row))
        request=f'country-{family.lower()}-2013-01'  # Derived identity, NOT a NASA request number.
        member=f'{request}.csv'
        text=io.StringIO(newline=''); writer=csv.DictWriter(text,fieldnames=pipeline.FIELDS);writer.writeheader()
        for row_number,row in subset:
            writer.writerow({aliases.get(k,k):v for k,v in row.items()})
        archive_path=stage/f'{request}.zip'
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as z:
            for filename,data in [(member,text.getvalue()),('Readme.txt',(raw/'AttributesReadme.txt').read_text())]:
                z.writestr(zipfile.ZipInfo(filename,date_time=(1980,1,1,0,0,0)),data)
        derived=buffer.getvalue()
        if archive_path.exists(): assert archive_path.read_bytes()==derived, 'Derived immutable archive mismatch'
        else: archive_path.write_bytes(derived)
        manifest,rows=pipeline.audit(archive_path,member,request,family,transformer)
        # The original audit has delivery-label text specific to the 2017 ZIPs.
        # Retain its measurement/validation rules, replace those documentary
        # labels with facts about this distinct country-file acquisition.
        manifest['collection']='Official SP country '+family+'; literal row versions '+','.join(manifest['categories']['version'])+'; upstream collection/production mapping unverified'
        manifest['delivery_processing_family']='NASA_OFFICIAL_COUNTRY_SP_DESCRIPTION'
        manifest['processing_lineage']='RAW_COUNTRY_CSV_TO_DETERMINISTIC_MONTH_SUBSET'
        accepted.extend(rows); manifests.append(manifest)
        # Independent reader over ORIGINAL CSV, not the normalized derivative.
        reader2=csv.reader(io.StringIO(original.decode('utf-8-sig')));header=next(reader2);pos={k:i for i,k in enumerate(header)}
        month_row=1;seen=set()
        for raw_number,fields in enumerate(reader2,2):
            v=lambda key:fields[pos[key]]
            if not v('acq_date').startswith('2013-01-'):continue
            month_row+=1
            identifier=f'{request}:{month_row}'
            if tuple(fields) in seen:continue
            seen.add(tuple(fields))
            lon,lat=float(v('longitude')),float(v('latitude'))
            if not(-8.7<=lon<=-7.2 and 39.3<=lat<=40.8):continue
            source={'Aqua':'AQUA_MODIS','Terra':'TERRA_MODIS','N':'SNPP_VIIRS'}[v('satellite')]
            x,y=ellipsoidal_laea(lon,lat);hh,mm=divmod(int(v('acq_time')),100)
            assert 0<=hh<24 and 0<=mm<60 and len(fields)==15
            utc=f"{v('acq_date')}T{hh:02}:{mm:02}:00Z"
            all_oracle[identifier]=(source,utc,f'g:{math.floor(x/10000)}:{math.floor(y/10000)}',lon,lat,
                v('confidence'),v('version'),float(v('frp')),v('daynight'),v('type'),float(v('scan')),float(v('track')),
                float(v('bright_ti4' if family=='VIIRS' else 'brightness')),float(v('bright_ti5' if family=='VIIRS' else 'bright_t31')),v('instrument'),v('satellite'))
            lineage[identifier]={'raw_file':name,'raw_csv_row':raw_number,'derived_csv_row':month_row}
        delivery.append({'file':name,'expected_bytes':int(index[name]['size']),'received_bytes':len(original),
            'index_updated':index[name]['updated'],'csv_sha256':sha(original),'subset_month':'2013-01','country_month_rows':len(subset),
            'canonical_thermal_aliases':aliases,'derived_zip_sha256':sha(derived),'identifier_kind':'DERIVED_COUNTRY_SUBSET_NOT_NASA_REQUEST'})
    actual={r['id']:(r['source'],r['utc'],r['cell'],r['longitude'],r['latitude'],r['confidence'],r['version'],r['frp'],r['daynight'],r['type'],r['scan'],r['track'],r['brightness'],r['brightness2'],r['nativeInstrument'],r['nativeSatellite']) for r in accepted}
    assert actual==all_oracle,'Independent raw row/UTC/projection/quality-field parity failure'
    keys=Counter((r['source'],r['day'],r['cell']) for r in accepted)
    independent_keys=Counter((values[0],values[1][:10],values[2]) for values in all_oracle.values())
    assert keys==independent_keys,'Independent source/day/cell multiplicity mismatch'
    summary=pipeline.summarize(accepted)
    for source,total in summary.items():
        group={key:n for key,n in independent_keys.items() if key[0]==source}
        assert (sum(group.values()),len(group))==(total['records'],total['occupied_cell_days'])
    report={'candidate_id':'country-pt-2013-01-'+sha(json.dumps(delivery,sort_keys=True).encode())[:16],
        'state':'AUDITED_STAGED_NOT_QUALIFIED','month':'2013-01','aoi_wsen':pipeline.BBOX,'audit':'PASS','independent_raw_recount':'PASS',
        'method':pipeline.METHOD,'adapter_sha256':sha(Path(__file__).read_bytes()),
        'production_pipeline_sha256':sha(Path(pipeline.__file__).read_bytes()),
        'oracle_sha256':sha((ROOT/'science/independent_recount.py').read_bytes()),
        'summary':summary,'deliveries':delivery,'source_manifests':manifests,'expected_source_files':2,'received_source_files':2,
        'processing_family':'NASA_OFFICIAL_COUNTRY_SP_DESCRIPTION','extract_completeness':'UNKNOWN',
        'production_vintage':'UNVERIFIED','observation_support':'OBSERVATION_UNKNOWN','g4':'ADJUSTMENT_WITHHELD',
        'qualification_blockers':['Within-collection production vintage is undocumented: row values are not a granule processing-vintage inventory.',
            'Annual country file byte sizes reconcile, but their source-linked monthly upstream delivery inventory is absent. Current CMR candidates do not establish that lineage.',
            'No compatible historic fire-mask/QA/geolocation inventory qualifies valid observation opportunity.'],
        'release_decision':'DO_NOT_PROMOTE_TO_QUALIFIED_HISTORY_OR_CURRENT_CATALOG'}
    artifact={'candidate':report,'records':accepted,'row_lineage':lineage}
    (stage/'candidate.json').write_text(json.dumps(artifact,sort_keys=True,indent=2),encoding='utf-8')
    with (stage/'occupied_cell_days.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['source','utc_day','cell_id','reported_records'])
        for key,n in sorted(keys.items()):writer.writerow([*key,n])
    with (stage/'occupied_cell_days.csv').open(newline='',encoding='utf-8') as f:
        reopened={(r['source'],r['utc_day'],r['cell_id']):int(r['reported_records']) for r in csv.DictReader(f)}
    assert reopened==dict(independent_keys),'Reopened candidate CSV parity failure'
    report['candidate_sha256']=sha((stage/'candidate.json').read_bytes())
    (ROOT/'reports/HISTORICAL_CANDIDATE_AUDIT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    status={key:report[key] for key in ['candidate_id','month','state','audit','independent_raw_recount','expected_source_files','received_source_files','qualification_blockers','g4']}
    status['report_sha256']=sha((ROOT/'reports/HISTORICAL_CANDIDATE_AUDIT.json').read_bytes())
    inventory_path=ROOT/'reports/L2_METADATA_INVENTORY.json'
    if inventory_path.exists():
        metadata=json.loads(inventory_path.read_text())
        status['l2_metadata']={'state':metadata['state'],'month':metadata['month'],
            'aqua_fire_granules':metadata['products']['MYD14']['listed_granules'],
            'snpp_375m_fire_granules':metadata['products']['VNP14IMG']['listed_granules'],
            'pixel_arrays_downloaded':metadata['pixel_arrays_downloaded'],'inventory_sha256':sha(inventory_path.read_bytes())}
    (ROOT/'src/history-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    result=inspect_candidate()
    print(json.dumps({key:result[key] for key in ['candidate_id','state','audit','independent_raw_recount','summary','qualification_blockers']},indent=2))
