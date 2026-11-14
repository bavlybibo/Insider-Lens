import hashlib,json,subprocess,sys,unittest,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'reports/phase12'
def read(n):return json.loads((O/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class EvidenceRetentionTests(unittest.TestCase):
 def test_original_data_acceptance_and_disjoint_identity(self):
  a=read('INDEPENDENT_PARTITION.json');self.assertEqual(a['state'],'PASS');self.assertEqual(a['production_sha256'],sha(O/'PARTITION.json'));self.assertEqual(a['cases_verified'],12);self.assertEqual(a['raw_records_recounted'],391445)
  for c in read('PARTITION.json')['cases']:
   groups={g:{tuple(r[:3]) for r in c['rows'] if r[-1]==g} for g in ['MODIS_ONLY','SHARED','VIIRS_ONLY']}
   self.assertEqual(sum(map(len,groups.values())),c['counts']['UNION']);self.assertFalse(groups['MODIS_ONLY']&groups['SHARED']);self.assertFalse(groups['VIIRS_ONLY']&groups['SHARED']);self.assertFalse(groups['MODIS_ONLY']&groups['VIIRS_ONLY'])
  c=next(c for c in read('PARTITION.json')['cases'] if c['id']=='overlap' and c['flag']=='ALL');self.assertEqual(c['counts'],dict(MODIS_ONLY=34,SHARED=199,VIIRS_ONLY=335,UNION=568));self.assertEqual(c['records'],[990,1149,8385])
 def test_no_qualification_or_new_holdout_claim(self):
  a=read('INDEPENDENT_PARTITION.json');self.assertFalse(a['fit']);self.assertFalse(a['holdouts_queried']);self.assertNotIn('2024',','.join(a['months_read']));self.assertIsNone(a['coincident_opportunities']);self.assertIsNone(a['calibrated_agreement']);self.assertEqual(a['g4'],'ADJUSTMENT_WITHHELD')
 def test_era_and_daynight_union(self):
  cases=read('PARTITION.json')['cases'];before=next(c for c in cases if c['id']=='before' and c['flag']=='ALL');self.assertEqual(before['records'],[5993,6751,0]);self.assertEqual(len(before['dates']),30)
  for c in cases:
   if c['flag']!='ALL':continue
   d,n=[next(v for v in cases if v['id']==c['id'] and v['flag']==f) for f in ['D','N']];self.assertEqual(c['records'],[a+b for a,b in zip(d['records'],n['records'])]);self.assertEqual({tuple(r[:3]) for r in c['rows']},{tuple(r[:3]) for r in d['rows']+n['rows']})
 def test_inherited_science_and_original_release_preserved(self):
  with zipfile.ZipFile(R/'data/backups/phase12-before.zip') as z:
   old=json.loads(z.read('SNAPSHOT_SHA256.json'))
   for n,h in old.items():
    if n.startswith(('science/','public/','reports/phase6/','reports/phase7/','reports/phase8/','reports/phase9/','reports/phase10/','reports/phase11/')) or n in ['reports/G4_DECISION.md','reports/CANADA_PREREGISTRATION.json']:self.assertEqual(sha(R/n),h,n)
 def test_deterministic_production_and_independent_replay(self):
  for name in ['phase12_partition.py','phase12_oracle.py']:
   p=subprocess.run([sys.executable,str(R/'science'/name)],cwd=R,capture_output=True,text=True,timeout=90);self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()
