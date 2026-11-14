import json,unittest,hashlib,zipfile,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/phase10'
def read(n):return json.loads((R/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class QualificationTests(unittest.TestCase):
 def test_exact_pair_full_granule_equivalence_and_scope(self):
    g=read('GEOLOCATION_COMPARISON.json');self.assertEqual(sum(x['compared_values'] for x in g['comparisons'].values()),31180800)
    for x in g['comparisons'].values():self.assertEqual((x['different_values'],x['maximum_absolute_difference_native_units']),(0,0))
    self.assertIn('NOT_PRESENT',g['light_angles_and_quality']);self.assertFalse(g['physical_containment_qualified']);self.assertEqual(g['light_input_pointer'],g['full_file'])
 def test_qa_applicability_cannot_borrow_IMG_bits(self):
    q=read('QA_APPLICABILITY.json');self.assertTrue(q['fire_mask_qualified']);self.assertFalse(q['algorithm_qa_qualified']);self.assertEqual(q['fire_mask_semantics']['3'],'non-fire water');self.assertEqual(q['fire_mask_semantics']['5'],'non-fire land')
    bits=[r for r in q['rows'] if r['field'].startswith('algorithm_QA_bit_')];self.assertEqual(len(bits),32);self.assertTrue(all(r['status']=='UNRESOLVED' for r in bits));self.assertTrue(bits[1]['observed_bit_value_at_candidates']);self.assertIn('1.6.1',q['exact_product']['algorithm'])
 def test_frozen_baseline_and_no_qualified_promotion(self):
    a=read('QUALIFICATION_RESULT.json');old=json.loads((ROOT/'reports/phase9/TRIANGULAR_ANALYSIS.json').read_text());self.assertEqual(a['allocated_frp_sum_mw'],old['allocated_frp_sum_mw']);self.assertEqual([r['id'] for r in a['rows']],[p['id'] for p in old['pixels']]);self.assertEqual(a['became_qualified'],0);self.assertIsNone(a['qualified_valid_nondetections']);self.assertFalse(a['fit']);self.assertFalse(a['holdouts_opened']);self.assertEqual(a['g4'],'ADJUSTMENT_WITHHELD')
    for r in a['rows']:self.assertIsNone(r['physical_registration_bound_m']);self.assertEqual(r['category'],'375_POSITIVE_750_UNKNOWN_SUPPORT');self.assertTrue(r['same_scan_interval'])
 def test_independent_column_blocks_and_geodesic_recount(self):
    o=read('INDEPENDENT_VALIDATION.json');self.assertEqual(o['state'],'PASS');self.assertEqual(o['qualification_sha256'],sha(R/'QUALIFICATION_RESULT.json'));self.assertLess(o['max_sampling_pitch_implementation_difference_m'],.002);self.assertTrue(all(x['different_values']==0 for x in o['full_granule_variable_checks'].values()))
 def test_aggregation_boundaries_and_sampling_not_footprints(self):
    from phase10_qualification import zone
    for c,z in [(639,1),(640,2),(1007,2),(1008,3),(2191,3),(2192,2),(2559,2),(2560,1)]:self.assertEqual(zone(c),z)
    for r in read('QUALIFICATION_RESULT.json')['rows']:self.assertEqual(r['index_model_aggregation750'],2);self.assertGreater(r['750_scan_center_pitch_m'],r['375_scan_center_pitch_m']);self.assertIsNone(r['physical_spatial_support_m2'])
 def test_single_payload_and_documentation_receipts(self):
    r=read('MODLL_DOWNLOAD.json');self.assertEqual(r['bytes'],73370707);self.assertEqual(sha(ROOT/r['file']),r['sha256']);self.assertLess(r['bytes'],read('ACQUISITION_SCOPE.json')['max_science_bytes']);self.assertEqual(len(list((ROOT/'data/acquisition/phase10').glob('*.h5'))),1)
    for r in read('SOURCE_QUALIFICATION.json')['sources']:self.assertEqual(sha(ROOT/r['file']),r['sha256'])
    self.assertIn('DRAFT, NOT SENT',(R/'NASA_SUPPORT_QUESTION.md').read_text(encoding='utf-8'))
 def test_new_public_namespace_and_preserved_old_pointers(self):
    pointer=json.loads((ROOT/'public/data/phase10/index.json').read_text());p=ROOT/'public'/pointer['file'].lstrip('/');self.assertEqual(sha(p),pointer['sha256']);b=json.loads(p.read_text());self.assertEqual(b['result']['g4'],'ADJUSTMENT_WITHHELD')
    for n,r in b['artifacts'].items():self.assertEqual(sha(p.parent/n),r['sha256'])
    with zipfile.ZipFile(ROOT/'data/backups/phase10-before.zip') as z:
      before=json.loads(z.read('SNAPSHOT_SHA256.json'))
      for name in ['public/data/release.json','public/data/phase9/index.json','public/data/phase8/index.json']:self.assertEqual(sha(ROOT/name),before[name])
 def test_reproducible_science_and_oracle_replay(self):
    for name in ['phase10_qualification.py','phase10_oracle.py']:
      result=subprocess.run([sys.executable,str(ROOT/'science'/name)],cwd=ROOT,capture_output=True,text=True,timeout=45);self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
