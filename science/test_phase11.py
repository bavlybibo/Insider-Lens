import hashlib,json,subprocess,sys,unittest,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'reports/phase11'
def read(n):return json.loads((O/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class NativeDeliveryTests(unittest.TestCase):
 def test_original_archive_oracle_acceptance(self):
    a=read('INDEPENDENT_RETENTION.json');self.assertEqual(a['state'],'PASS')
    self.assertEqual((a['retention_scopes_verified'],a['policy_results_verified'],a['seasonal_source_scopes_verified']),(108,324,648))
    self.assertEqual(a['raw_records_recounted'],2296114);self.assertEqual(a['production_sha256'],sha(O/'NATIVE_RETENTION.json'))
    self.assertEqual(sum(x['accepted'] for x in a['original_member_bindings']),8355817)
 def test_actual_retention_set_units(self):
    for c in read('NATIVE_RETENTION.json')['cases']:
      m,v,a=[c['policies'][k] for k in ['MODIS_ONLY','VIIRS_ONLY','ALL_NATIVE']]
      self.assertEqual(m['records']+v['records'],a['records']);self.assertLessEqual(a['union_cell_days'],m['union_cell_days']+v['union_cell_days'])
      self.assertEqual(sorted(set(m['dates_with_records'])|set(v['dates_with_records'])),a['dates_with_records'])
      self.assertEqual(m['exclusive_cell_days_lost'],a['union_cell_days']-m['union_cell_days'])
      self.assertEqual(v['exclusive_dates_lost'],sorted(set(a['dates_with_records'])-set(v['dates_with_records'])))
 def test_grid_sensitivity_fixed_aoi_membership(self):
    changed=0
    for c in read('GRID_SENSITIVITY.json'):
      for s,k in c['source_cell_days'].items():
        self.assertGreaterEqual(k['5000'],k['10000']);self.assertGreaterEqual(k['10000'],k['20000'])
        changed+=k['5000']!=k['20000']
    self.assertGreater(changed,0)
 def test_daynight_union_and_no_holdout_evaluation(self):
    cases=read('NATIVE_RETENTION.json')['cases'];a=read('INDEPENDENT_RETENTION.json')
    self.assertFalse(a['fit']);self.assertFalse(a['holdouts_opened']);self.assertTrue(all(not m.startswith('2024') for m in a['months_read']))
    for c in cases:
      if c['scope']['flag']!='ALL':continue
      d=next(v for v in cases if v['scope']=={**c['scope'],'flag':'D'});n=next(v for v in cases if v['scope']=={**c['scope'],'flag':'N'})
      for p in c['policies']:
        self.assertEqual(c['policies'][p]['records'],d['policies'][p]['records']+n['policies'][p]['records'])
        self.assertEqual(c['policies'][p]['dates_with_records'],sorted(set(d['policies'][p]['dates_with_records'])|set(n['policies'][p]['dates_with_records'])))
 def test_bounded_response_does_not_require_artificial_hard_edges(self):
    a=read('BOUNDED_UNCERTAINTY.json');self.assertFalse(a['exact_hard_edged_optical_boundary_required'])
    self.assertIsNone(a['response_energy_quantile']);self.assertIsNone(a['registration_confidence_bound_m']);self.assertIsNone(a['qualified_shared_support'])
    self.assertEqual(a['newly_qualified_candidates'],0);self.assertEqual(a['g4'],'ADJUSTMENT_WITHHELD')
    self.assertTrue(all(v=='375_POSITIVE_750_UNKNOWN_SUPPORT' for v in a['categories']))
    for s in a['literature']:self.assertEqual(sha(R/s['file']),s['sha256'])
    self.assertIn('DRAFT, NOT SENT',(O/'NASA_SUPPORT_DRAFT.md').read_text(encoding='utf-8'))
 def test_prior_contracts_and_gate_unchanged(self):
    with zipfile.ZipFile(R/'data/backups/phase11-before.zip') as z:
      old=json.loads(z.read('SNAPSHOT_SHA256.json'))
      for name in ['reports/G4_DECISION.md','reports/phase10/QUALIFICATION_RESULT.json','reports/phase9/TRIANGULAR_ANALYSIS.json','reports/CANADA_PREREGISTRATION.json','public/data/release.json','public/data/canada/index.json','public/data/canada/oracle-index.json']:
        self.assertEqual(sha(R/name),old[name])
 def test_replay_production_and_independent_raw_index_oracle(self):
    for name in ['phase11_retention.py','phase11_oracle.py','phase11_support.py']:
      p=subprocess.run([sys.executable,str(R/'science'/name)],cwd=R,capture_output=True,text=True,timeout=90)
      self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()
