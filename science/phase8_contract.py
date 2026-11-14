"""Freeze independently anchored event enrichment before any Phase8 fire outcomes."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def immutable(p,obj):
    raw=(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode();p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==raw,'Immutable artifact differs: '+p.name
    else:p.write_bytes(raw)

def freeze():
    witness=ROOT/'data/acquisition/canada-nrcan/points.json';receipt=json.loads((ROOT/'data/acquisition/canada-nrcan/MANIFEST.json').read_text())
    assert sha(witness)=='342a54a97a583a34adea3ac30b7346a1325fe8552e5ff68e87236c7b1b9f64de'
    agency=json.loads(witness.read_text())['features'][0]['properties'];assert agency['NFDBFIREID']=='AB-2023-SWF095'
    c={'id':'ca-swf095-positive-signal-v1','frozen_before':'all Phase8 CMR search and L2 outcome inspection',
       'independent_event':{'agency_record':agency,'raw_path':witness.relative_to(ROOT).as_posix(),'sha256':sha(witness),'provider_receipt':receipt['receipts'][1],
            'dated_map':'https://159128.fs1.hubspotusercontent-na1.net/hubfs/159128/Alberta%20Wildfire/Forest%20areas/Slave%20Lake/2023/SWF095_11x17_20230610.pdf',
            'map_evidence':'NASA web search cached Alberta Incident Command GIS public map dated2023-06-10, accessed as text; direct PDF retrieval not yet established',
            'limits':'approximate agency point and report date, >=200ha service subset; dated estimated perimeter is not instantaneous active flaming extent; satellite-derived perimeter components may not be fully independent'},
       'aoi_wsen':[-117.2,54.75,-116.4,55.0],
       'window_days':['2023-06-'+str(d).zfill(2) for d in range(7,14)],
       'event_rule':'agency report UTC date plus6 subsequent UTC days, fixed0.8deg longitude /0.25deg latitude tract around event inside parent development; north clipped at55N',
       'prior_knowledge':'Phase5 context native-month counts already visible and disclosed; this is enriched descriptive development, not blind evaluation. No agreement/ratio/FRP used to rank passes.',
       'products':json.loads((ROOT/'reports/phase7/SEARCH_CONTRACT.json').read_text())['products'],
       'grid':json.loads((ROOT/'reports/phase7/SEARCH_CONTRACT.json').read_text())['grid'],
       'selection':{'maximum_candidates':2,'separation_hours':24,'rank':['all6same-acquisition products discoverable','maximum GRing centerline-distance proxy','absolute midpoint offset','estimated transfer size','stable IDs'],
                    'time_screen':'max separation of any granule interval endpoints <=10min; midpoint <=5min; actual pixel timing or conservative bounds required',
                    'max_centerline_proxy_km':600,'no_outcome_adaptation':True,'negative_result':'stop after frozen2 candidates; never replace by observed agreement or intensity'},
       'view':{'primary_degrees':40,'sensitivities_degrees':[30,50]},
       'qa':{'MYD14':'exact C6/C6.1 mask/landwater, contextual quality and geolocation flags; known table4 fields, no375m borrowing',
             'VNP14':'require exact C2 applicability evidence; decode any historical-table sensitivity explicitly UNQUALIFIED until established',
             'VNP14IMG':'C2 guide v1.2 inputs bits0..6 nominal, bit22 residual bowtie excluded, geo flags0; validland/fire classes5/7/8/9, water/glint/cloud excluded'},
       'geometry':{'requirement':'oriented instrument/geolocation-derived footprints with justified boundary uncertainty; never GRings or center spacing as physical support',
                   'acceptance':'independent geometry agrees within1e-6 relative area and edge uncertainty is documented; otherwise qualified area null',
                   'aoi':'ellipsoidal LAEA clipped, half-open center membership only for descriptive baseline',
                   'dedup':'same source, acquisition key and native row/sample once; union overlapping physical support, never sum duplicate areas'},
       'controls':{'source_negative':'all qualified same-pass shared-support observations with both native masks5; satellite-classified non-detection controls, not independent physical fire absence',
                   'spatial_diagnostic_aoi':[-117.2,53.75,-116.4,54.0],'spatial_control_limits':'same granules, no assumption that absence of incident record means fire-free; diagnostic outcomes only',
                   'null_control':'sealed Phase7 no-positive sample re-used only as a procedural withholding control, never a qualified fire-free reference'},
       'metrics':{'B0':'source-separated raw reported positives and FRP MW, no adjustment','B1':'positive pixels and FRP within qualified shared physical support only',
                  'B2':'750m identity baseline versus interpretable candidate; no fit in this two-pass feasibility study',
                  'B3':'375m detail/QA sensitivity, distinct algorithm','B4':'no FRP correction absent sufficient qualified positive pairs and physical uncertainty',
                  'uncertainty':'finite selected-catalog counts exact, geometry/view/time/boundary sensitivities descriptive; no model CI without qualified replicated samples'},
       'fit':{'allowed':False,'minimum_qualified_passes':30,'minimum_7day_blocks':5,'reason':'two-pass enriched feasibility cannot justify model or generalization'},
       'budget':{'max_CMR_responses':42,'max_each_metadata_bytes':4000000,'max_payload_bytes':1000000000,'minimum_free_bytes':1200000000},
       'holdouts':'original Portugal/California and Canada2024 sealed; only existing southern Canada June2023 development',
       'lineage_boundary':'2023 native61.03 separate from2022 literal6.03. Exact current L2061 and C2 inputs required; no unproved join to FIRMS row production vintage.',
       'g4':'ADJUSTMENT_WITHHELD','phase7_contract_sha256':sha(ROOT/'reports/phase7/SEARCH_CONTRACT.json')}
    immutable(OUT/'COHORT_CONTRACT.json',c);return c

if __name__=='__main__':freeze();print(sha(OUT/'COHORT_CONTRACT.json'))
