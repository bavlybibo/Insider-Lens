import hashlib
import json
from pathlib import Path
import unittest
from pyproj import Transformer
from phase6_science import timed_candidates, geometry, summarize, sensitivity
from phase6_access import SafeRedirect,validate_token
from urllib.request import Request

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/phase6'

class Phase6Science(unittest.TestCase):
    def test_contract_is_frozen_and_gate_is_preserved(self):
        self.assertEqual(hashlib.sha256((R/'COHORT_CONTRACT.json').read_bytes()).hexdigest(),'ab874a4a4d038e30d2835829ace7a99d7276ee4fda16e9bee51207f88a95404a')
        a=json.loads((R/'COMMON_SUPPORT_AUDIT.json').read_text());self.assertEqual(a['g4'],'ADJUSTMENT_WITHHELD');self.assertFalse(a['candidate_fit']);self.assertFalse(a['holdout_evaluation'])

    def test_timing_threshold_and_native_flag_are_not_same_day_agreement(self):
        rows=[dict(source='AQUA_MODIS',utc='2022-06-01T08:00:00Z',x=-1,y=-1,dn='N',raw_sha256='a'),dict(source='SNPP_VIIRS',utc='2022-06-01T08:32:00Z',x=-2,y=-2,dn='N',raw_sha256='v')]
        self.assertEqual(summarize(rows,10000)['positive_sets']['both_source_reported'],1)
        self.assertEqual(timed_candidates(rows,10000,30)['same_cell_day_same_flag_candidate_keys'],0)
        self.assertEqual(timed_candidates(rows,10000,60)['same_cell_day_same_flag_candidate_keys'],1)
        rows[1]['dn']='D';self.assertEqual(timed_candidates(rows,10000,60)['same_cell_day_same_flag_candidate_keys'],0)
        self.assertIsNone(timed_candidates(rows,10000,60)['qualified_opportunities'])

    def test_zero_frp_is_not_missing_or_excluded_from_native_baseline(self):
        rows=[dict(source='SNPP_VIIRS',utc='2022-06-01T08:00:00Z',x=0,y=0,native={'frp':0,'type':'2','confidence':'l'})]
        policies=sensitivity(rows);self.assertEqual(len(policies['native_all']),1)
        self.assertEqual(policies['positive_frp_research'],[]);self.assertEqual(policies['literal_type0_unverified'],[])

    def test_clipping_conserves_area_with_partial_boundary_cells(self):
        c=json.loads((R/'COHORT_CONTRACT.json').read_text());t=Transformer.from_crs('EPSG:4326',c['grid']['crs'],always_xy=True)
        result=geometry(c,t,16)
        self.assertGreater(result['partial_cells'],0);self.assertAlmostEqual(result['sum_clipped_area_m2'],result['aoi_projected_area_m2'],delta=1)
        self.assertTrue(all(0<r['cell_fraction']<=1+1e-7 for r in result['cells']))

    def test_both_independent_acceptances_bind_actual_artifacts(self):
        for report,field,artifact in [('INDEPENDENT_VALIDATION.json','audit_sha256','COMMON_SUPPORT_AUDIT.json'),('L2_INDEPENDENT_VALIDATION.json','l2_audit_sha256','L2_SUPPORT_AUDIT.json')]:
            o=json.loads((R/report).read_text());self.assertEqual(o['state'],'PASS');self.assertEqual(o[field],hashlib.sha256((R/artifact).read_bytes()).hexdigest())
        a=json.loads((R/'L2_SUPPORT_AUDIT.json').read_text());self.assertEqual(a['science_files'],10);self.assertEqual(a['primary_eligible_shared_support'],0);self.assertIsNone(a['qualified_observation_denominator'])
        self.assertEqual(a['results']['2022-06-01']['VNP14IMG']['mask_counts']['4'],133613)

    def test_redirects_do_not_leak_authorization_to_untrusted_hosts(self):
        with self.assertRaisesRegex(ValueError,'value redacted'):
            validate_token('bad\r\nheader')
        request=Request('https://data.lpdaac.earthdatacloud.nasa.gov/file',headers={'Authorization':'Bearer test-value'})
        for target in ['https://untrusted.example/file','http://urs.earthdata.nasa.gov/file']:
            redirected=SafeRedirect().redirect_request(request,None,302,'redirect',{},target)
            self.assertIsNone(redirected.get_header('Authorization'))

if __name__=='__main__':unittest.main()
