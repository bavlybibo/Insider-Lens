"""Standalone field/source/version crosswalk; never supplies an inferred decoder."""
import csv,io,json
from phase10_contract import ROOT,OUT,sha
def run():
    q=json.loads((OUT/'QA_APPLICABILITY.json').read_text(encoding='utf-8'));s=json.loads((OUT/'SOURCE_QUALIFICATION.json').read_text(encoding='utf-8'));a=json.loads((ROOT/'reports/phase9/TRIANGULAR_ANALYSIS.json').read_text(encoding='utf-8'));geo=json.loads((OUT/'MODLL_DOWNLOAD.json').read_text(encoding='utf-8'))
    fire=a['input_receipts']['VNP14'];guide=next(r for r in s['sources'] if '375_User_Guide' in r['file']);instrument=[r for r in s['sources'] if 'Tilton' in r['file'] or 'GEO_ATBD' in r['file']];cmr=s['sources'][0]
    native={'url':fire['url'],'file':fire['file'],'sha256':fire['sha256'],'version':'VNP14.002 / NPP_PR14 1.6.1 / PGE530 2.0.4','authority':'NASA LandSIPS exact acquired SP file'}
    rows=[]
    for r in q['rows']:
        field=r['field'];refs=[native];locator='fire mask/legend';applies='Exact-file class meaning only; shared valid support not established'
        if field.startswith('algorithm_QA') or field in ['background_rejection','observation_processability']:
            refs+=[{'url':cmr['url'],'file':cmr['file'],'sha256':cmr['sha256'],'version':'VNP14.002 CMR links C1 V1.4.3 specification; no1.6.1 applicability statement','authority':'NASA CMR documentation links'}];locator='algorithm QA/units; missing flag_masks/flag_meanings';applies='UNRESOLVED: no decoder applied; C1/IMG/NRT not interchangeable'
        if field=='scan_trim_bowtie':refs+=instrument+[guide];locator='Exact mask legend; JPSS ATBD printed49-50; Tilton2016 TableI; IMG C2 Table2 bit22';applies='Class1 trim VERIFIED; nominal zone/deletion model INFERRED for exact response;750m QA bowtie bit UNRESOLVED'
        if field=='geolocation_input':refs+=[{'url':geo['url'],'file':geo['file'],'sha256':geo['sha256'],'version':'VNP03MODLL.002 / PGE591 2.0.1','authority':'NASA LandSIPS exact companion'}];locator='VNP14 InputFileGeo/InputPointer; MODLL InputPointer; GEOLOCATION_COMPARISON.json';applies='VERIFIED exact-pair stored coordinates/height only; no angle/quality fields in MODLL; no absolute error bound'
        if field=='radiance_input':refs+=[guide];locator='VNP14 InputFileL1B/InputPointer; IMG guide Table2 bit6';applies='Named input only; IMG own bit definition verified;750m input bits and actual M13 payload not qualified'
        normalized=[]
        for ref in refs:
            assert sha(ROOT/ref['file'])==ref['sha256'];normalized.append({'url':ref['url'],'file':ref['file'],'sha256':ref['sha256'],'version':ref.get('version',ref.get('version_authority')),'authority':ref.get('authority','NASA/NOAA official document or original NASA-authored instrument research')})
        rows.append({'field':field,'meaning':r['meaning'],'status':r['status'],'observed_bit_value_at_candidates':r.get('observed_bit_value_at_candidates','NOT_A_BIT_FIELD'),'exact_production':'VNP14.002 / NPP_PR14 1.6.1 / PGE2.0.4','locator':locator,'applicability_and_limits':applies,'versioned_authority_sources_json':json.dumps(normalized,ensure_ascii=True)})
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows);raw=stream.getvalue().encode();path=OUT/'QA_FIELD_SOURCE_MATRIX.csv';assert not path.exists() or path.read_bytes()==raw
    if not path.exists():path.write_bytes(raw)
    print(json.dumps({'fields':len(rows),'sha256':sha(path),'decoder_promoted':False}))
if __name__=='__main__':run()
