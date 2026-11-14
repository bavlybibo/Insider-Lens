"""Bounded response-uncertainty review; no communication, decoder or fit."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1];O=R/'reports/phase11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,b):
    if p.exists():assert p.read_bytes()==b
    else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def run():
    old=R/'reports/phase10/QUALIFICATION_RESULT.json'; result=json.loads(old.read_text(encoding='utf-8'))
    assert len(result['rows'])==16 and result['became_qualified']==0
    draft='''# NASA LP DAAC technical support — DRAFT, NOT SENT

To: LP DAAC User Services <LPDAAC@usgs.gov>, for routing to the VIIRS active-fire science/production team
Subject: Exact VNP14.002 SCI QA applicability and bounded thermal-response uncertainty

Please clarify the SP granule `VNP14.A2023164.1042.002.2023164205253.nc`, SHA256 `022e9ccdc4444aba6219a577c348875977f92c9680c97ebd27c3f617daab807e`, AlgorithmVersion NPP_PR14 1.6.1 / PGE530 2.0.4. Its embedded fire-mask legend is explicit; `algorithm QA` only says bit field. Sixteen fixed native 375 m positives have candidate 750 m centers with native mask 5 and raw algorithm-QA word 2 (literal bit 1 set). We have not interpreted that bit or qualified a shared non-detection.

1. Which version-controlled QA specification and eligibility rules apply to this exact Collection 002 SCI production? Please identify bit positions, polarity, reserved/fill rules and required input-radiance/geolocation, trim/bowtie, cloud, background and rejection tests. Does the 2019 Collection 1 NPP_PR14 V1.4.3 mapping apply unchanged? A citable applicability statement or corrected specification would resolve the ambiguity; IMG and NRT mappings are not being substituted.
2. The fire input names `VNP03MOD.A2023164.1042.002.2023164194353.nc`. The exact companion `VNP03MODLL.A2023164.1042.002.2023183103833.h5` names that same input. Every stored latitude, longitude and height agrees (10,393,600 values each). Is using the named full MOD for viewing angles/quality intended when MODLL contains none of those arrays?
3. Which source-qualified spatial response and band-registration/geolocation uncertainty apply to I4/I5/M13 in this production/aggregation zone? IMG zero-based rows 877–888, columns 4534–4548; MOD rows 438–444, columns 2267–2274 are in the two-sample aggregation zone. We seek an effective response/encircled-energy definition and defensible uncertainty or confidence region, including correlations and detector/scan dependencies, rather than an artificial exact hard boundary. What validation and response-overlap eligibility rule is recommended before declaring common observation support?

Companions: `VNP14IMG.A2023164.1042.002.2024079133754.nc`, NPP_PR14IMG 3.1.6 / PGE 2.0.13; `VNP03IMG.A2023164.1042.002.2023164194353.nc`. Both fire files name `VNP02CCMOD.A2023164.1042.002.2023164204525.nc`; that radiance payload has not been acquired/verified. Scan UTC bounds match, but band exposure times and processing vintages differ. We do not infer a causal resolution effect, missed physical fires or a correction factor.

Our reproducible sixteen-candidate classification remains UNKNOWN_SUPPORT; G4 remains withheld. This requests technical clarification, not endorsement. No credentials or signed download redirects are included. Prepared for team review only; no external message has been sent.

Contact routing verified against [NASA LP DAAC Data Resources](https://nasa.github.io/LPDAAC-Data-Resources/) on 2026-11-14. The current Earthdata contact page returned HTTP 403 through the public web fetch; this is not an authenticated data-access diagnosis.
'''
    put(O/'NASA_SUPPORT_DRAFT.md',draft.encode())
    evidence={
      'state':'BOUND_NOT_QUALIFIED','parent_result_sha256':sha(old),
      'candidate_ids':[r['id'] for r in result['rows']],
      'categories':[r['category'] for r in result['rows']],
      'sampling_location':'Exact stored centers, sampling pitches and aggregation-zone membership verified in Phase 10; sampling pitch is not response extent.',
      'effective_response':'Published first-order PSF family is a research starting point, not an exact thermal-pixel response certificate.',
      'confidence_region':'Requires a justified response-energy/eligibility definition and source/version/scan-specific registration/geolocation error model, with dependency/correlation assumptions.',
      'exact_hard_edged_optical_boundary_required':False,
      'response_energy_quantile':None,'registration_confidence_bound_m':None,'qualified_shared_support':None,
      'feasible_conditional_method':'Propagate a documented source-specific response and registration uncertainty through a preregistered shared-response criterion, assess classifications over justified parameter bounds; do not fit bounds to these known outcomes.',
      'current_blockers':['Exact SP VNP14.002 algorithm-QA eligibility mapping unresolved','Applicable I4/M13 effective response and registration uncertainty not established'],
      'not_substituted':['Nominal squares','Nearest-center distances','Collection 1 QA','IMG QA','Arbitrary Gaussian errors','Unvalidated confidence percentages'],
      'literature':[{'url':'https://pmc.ncbi.nlm.nih.gov/articles/PMC7340089/','locator':'Section III; Table I; Section VII',
        'file':'data/acquisition/phase10/references/Tilton2019.html','sha256':sha(R/'data/acquisition/phase10/references/Tilton2019.html'),
        'finding':'First-order ideal detector/integration PSF model allows neighboring response overlap. Thermal examples include I5/M15, not a measured I4/M13 confidence bound for the 2023 case.'},
        {'url':'https://www.star.nesdis.noaa.gov/jpss/documents/ATBD/D0001-M01-S01-004_JPSS_ATBD_VIIRS-Geolocation_B.pdf','locator':'Revision B; printed pp49–50 / PDF pp74–75',
        'file':'data/acquisition/phase10/references/VIIRS_GEO_ATBD_B.pdf','sha256':sha(R/'data/acquisition/phase10/references/VIIRS_GEO_ATBD_B.pdf'),
        'finding':'Detector sampling, integration and aggregation distinctions; not an empirical response/error bound for these exact thermal pixels.'}],
      'requests_this_phase':'Public web metadata/reference review only; no authenticated payload acquisition or support communication',
      'newly_qualified_candidates':0,'fit':False,'g4':'ADJUSTMENT_WITHHELD'}
    put(O/'BOUNDED_UNCERTAINTY.json',(json.dumps(evidence,sort_keys=True,indent=2)+'\n').encode())
    for n in ['NASA_SUPPORT_DRAFT.md','BOUNDED_UNCERTAINTY.json']:
        put(R/'public/data/phase11'/n,(O/n).read_bytes())
    print(json.dumps({'state':evidence['state'],'fixed_candidates':16,'newly_qualified':0,'message_sent':False}))
if __name__=='__main__':run()
