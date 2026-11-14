import hashlib
import json
import math
from pathlib import Path
import unittest
from phase9_contract import freeze
from phase9_analysis import decode375,classification
from phase9_oracle import vincenty
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase9'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Phase9Science(unittest.TestCase):
    def test_frozen_followup_preserves_parent_cohort(self):
        c=freeze();self.assertEqual(sha(OUT/'ANALYSIS_CONTRACT.json'),'6bf2cedaf20fd910c7d9bad539aa06029a1f0ba1a656e1a6705652d67481eecf')
        self.assertEqual(c['parent_support_sha256'],sha(ROOT/'reports/phase8/SUPPORT_AUDIT.json'));self.assertEqual(c['budget']['new_science_payload_bytes'],0);self.assertFalse(c['fit']);self.assertTrue(c['no_containment_assumption'])
    def test_every_pixel_reconciles_to_independent_raw_oracle(self):
        a=read('TRIANGULAR_ANALYSIS.json');o=read('INDEPENDENT_VALIDATION.json');self.assertEqual(o['state'],'PASS');self.assertEqual(o['analysis_sha256'],sha(OUT/'TRIANGULAR_ANALYSIS.json'));self.assertEqual(len(a['pixels']),16)
        self.assertAlmostEqual(a['allocated_frp_sum_mw'],22.37004065513611);self.assertEqual(o['allocated_frp_sum_mw'],a['allocated_frp_sum_mw']);self.assertLess(o['max_nearest_geodesic_difference_m'],.002)
        self.assertEqual(a['same_scan_interval_count'],16);self.assertEqual(a['maximum_orbit_mid_vector_difference_m'],0)
        self.assertEqual(a['nearest750_mask_counts'],{'5':16});self.assertTrue(all(r['viirs750']['qa']==2 for r in a['pixels']))
    def test_equal_frp_fractions_are_not_duplicate_detections_or_extra_totals(self):
        a=read('TRIANGULAR_ANALYSIS.json');groups=a['allocation_groups'];self.assertEqual(len(groups),12);self.assertEqual(sorted(g['selected_count'] for g in groups),[1]*8+[2]*4)
        self.assertEqual(math.fsum(g['selected_fraction_sum_mw'] for g in groups),a['allocated_frp_sum_mw']);self.assertNotEqual(math.fsum(set(r['frp_mw'] for r in a['pixels'])),a['allocated_frp_sum_mw'])
        self.assertTrue(all(g['equal_M13_radiance'] and g['equal_background_radiance'] and g['equal_allocated_frp'] and g['siblings_outside_aoi']==0 for g in groups));self.assertTrue(all(not r['duplicate_native_address'] and not r['residual_bowtie'] for r in a['pixels']))
    def test_qa_bit_semantics_are_source_specific(self):
        self.assertTrue(decode375(2)['I2_input_bad']);self.assertFalse(decode375(64)['geolocation_input_bad']);self.assertTrue(decode375(64)['M13_input_bad']);self.assertTrue(decode375(1<<22)['residual_bowtie'])
        self.assertFalse(read('TRIANGULAR_ANALYSIS.json')['source_qa750_qualified']);self.assertTrue(all(r['viirs750']['qa_qualified'] is False for r in read('TRIANGULAR_ANALYSIS.json')['pixels']))
    def test_unqualified_center_never_becomes_valid_disagreement(self):
        self.assertEqual(classification(True,True,False,False,5),'375_POSITIVE_750_UNKNOWN_SUPPORT');self.assertEqual(classification(True,False,True,True,5),'UNMATCHED_TIME_OR_GEOMETRY');self.assertEqual(classification(True,True,True,False,5),'375_POSITIVE_750_UNKNOWN_SUPPORT')
        self.assertEqual(classification(True,True,True,True,5),'375_POSITIVE_750_VALID_NONDETECTION');self.assertEqual(classification(True,True,True,True,8),'375_POSITIVE_750_POSITIVE');self.assertEqual(classification(True,True,True,True,4),'375_POSITIVE_750_INVALID_OR_CLOUD')
        a=read('TRIANGULAR_ANALYSIS.json');self.assertEqual(a['category_counts'],{'375_POSITIVE_750_UNKNOWN_SUPPORT':16});self.assertIsNone(a['qualified_shared_support_m2']);self.assertIsNone(a['qualified_disagreements']);self.assertFalse(a['fit']);self.assertFalse(a['generalization']);self.assertFalse(a['holdouts_opened']);self.assertEqual(a['g4'],'ADJUSTMENT_WITHHELD')
    def test_independent_distance_known_benchmarks(self):
        self.assertEqual(vincenty(0,0,0,0),0);self.assertAlmostEqual(vincenty(0,0,1,0),111319.490793,places=5);self.assertAlmostEqual(vincenty(-116.6,54.9,-116.61,54.91),vincenty(-116.61,54.91,-116.6,54.9),places=5)
    def test_new_namespace_all_hashes_and_no_modified_native_release(self):
        p=json.loads((ROOT/'public/data/phase9/index.json').read_text());bpath=ROOT/'public'/p['file'].lstrip('/');self.assertEqual(sha(bpath),p['sha256']);b=json.loads(bpath.read_text())
        for name,a in b['artifacts'].items():self.assertEqual(sha(bpath.parent/name),a['sha256'])
        self.assertEqual(sha(ROOT/'public/data/release.json'),'e256a172f3c61b82f088428cc0b50554605fb0bdb4648f5410982be90a5f45ed')
if __name__=='__main__':unittest.main()
