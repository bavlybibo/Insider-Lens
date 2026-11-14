import hashlib
import json
from pathlib import Path
import unittest
from phase8_contract import freeze
from phase8_support import dimensions

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase8'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class Phase8Science(unittest.TestCase):
    def test_frozen_independent_event_and_no_outcome_adaptation(self):
        c=freeze();self.assertEqual(sha(OUT/'COHORT_CONTRACT.json'),'d812887c0f4cae5ca6db22561af8f19ff15596ca66506827e4055ce2791fdbb9')
        self.assertEqual(c['independent_event']['agency_record']['NFDBFIREID'],'AB-2023-SWF095');self.assertFalse(c['fit']['allowed'])
        self.assertEqual(c['view']['primary_degrees'],40);self.assertEqual(c['budget']['max_payload_bytes'],1000000000)
        d=read('DISCOVERY.json');self.assertFalse(d['outcomes_used']);self.assertEqual(len(d['queries']),42);self.assertEqual(len(d['selected']),1);self.assertEqual(d['metadata_eligible_pairs'],1)
        for receipt in d['queries']:self.assertEqual(sha(ROOT/receipt['file']),receipt['sha256'])
        selected=d['selected'][0];self.assertEqual(selected['maximum_interval_endpoint_separation_minutes'],8);self.assertEqual(selected['midpoint_offset_minutes'],2.5)

    def test_positive_result_does_not_unlock_comparison(self):
        a=read('SUPPORT_AUDIT.json');o=read('INDEPENDENT_VALIDATION.json')
        self.assertEqual(o['state'],'PASS');self.assertEqual(o['support_audit_sha256'],sha(OUT/'SUPPORT_AUDIT.json'))
        self.assertEqual([a['results'][k]['positive_mask_centers'] for k in ['MYD14','VNP14','VNP14IMG']],[0,0,16]);self.assertAlmostEqual(a['results']['VNP14IMG']['native_frp_mw_sum'],22.37004065513611)
        self.assertEqual(o['checks'][2]['positive_screens']['nominal375_within40'],16)
        self.assertIsNone(a['qualified_shared_support_m2']);self.assertIsNone(a['matched_positive_observations']);self.assertIsNone(a['valid_shared_negative_controls'])
        self.assertEqual(a['independent_fire_absence_controls'],0);self.assertFalse(a['fit']);self.assertFalse(a['improvement_demonstrated']);self.assertFalse(a['generalization']);self.assertFalse(a['holdouts_opened']);self.assertEqual(a['g4'],'ADJUSTMENT_WITHHELD')
        self.assertAlmostEqual(a['maximum_scan_bound_separation_seconds'],75.16694808,places=6)

    def test_instrument_geometry_not_center_spacing_or_exposure(self):
        a,b=dimensions(676.5);self.assertAlmostEqual(a,1000,places=3);self.assertAlmostEqual(b,1000,places=3)
        self.assertGreater(dimensions(100)[0],a)
        g=read('NOMINAL_GEOMETRY.json');self.assertEqual(g['count'],1145);self.assertFalse(g['eligible_for_B1']);self.assertIsNone(g['qualified_shared_support_m2']);self.assertIsNone(g['physical_boundary_uncertainty_m'])
        self.assertLess(read('INDEPENDENT_VALIDATION.json')['nominal_geometry']['max_relative_instrument_area_difference'],1e-6)

    def test_native_history_and_memory_retention_are_source_separated(self):
        h=read('NATIVE_HISTORY.json');self.assertEqual(h['raw_identity_checks'],857)
        self.assertEqual([(r['records'],r['occupied_cell_days']) for r in h['totals'].values()],[(63,9),(702,19),(92,11)])
        for source,v in h['totals'].items():
            self.assertEqual(sum(d['sources'][source]['records'] for d in h['calendar']),v['records'])
            self.assertTrue(all(d['sources'][source]['observation_support']=='UNKNOWN' for d in h['calendar']))
        self.assertEqual(len(read('NATIVE_RECORDS.json')),857)

    def test_new_public_evidence_checksums_and_original_pointers(self):
        pointer=json.loads((ROOT/'public/data/phase8/index.json').read_text());folder=ROOT/'public'/pointer['file'].lstrip('/');self.assertEqual(sha(folder),pointer['sha256']);b=json.loads(folder.read_text())
        for name,r in b['artifacts'].items():self.assertEqual(sha(folder.parent/name),r['sha256'])
        self.assertEqual(sha(ROOT/'public/data/release.json'),'e256a172f3c61b82f088428cc0b50554605fb0bdb4648f5410982be90a5f45ed')
        self.assertEqual(sha(ROOT/'reports/phase7/EXACT_SUPPORT_AUDIT.json'),'8ee8d0e6d8d09bf853be82efea14f193d9a4a11705dc439913a9afa859e72441')

if __name__=='__main__':unittest.main()
