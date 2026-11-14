import hashlib,json,unittest
from pathlib import Path
from phase3_reconcile import reconcile
from expand_history import expand,audit_month
ROOT=Path(__file__).resolve().parents[1]

class Phase3ScienceTests(unittest.TestCase):
    def test_original_daynight_partition_and_nonadditive_occupancy(self):
        report=reconcile()
        expected={'AQUA_MODIS':(109,129,24,17,32),'TERRA_MODIS':(75,97,16,17,24),'SNPP_VIIRS':(574,1467,43,46,65)}
        for source,(d,n,dk,nk,allk) in expected.items():
            values=report['totals'][source]
            self.assertEqual((values['D']['records'],values['N']['records']),(d,n))
            self.assertEqual((values['D']['occupied_cell_days'],values['N']['occupied_cell_days'],values['ALL']['occupied_cell_days']),(dk,nk,allk))
            self.assertEqual(d+n,values['ALL']['records']);self.assertGreater(dk+nk,allk)
        self.assertEqual(report['other_or_missing_flags'],0)

    def test_chronological_history_stays_staged_and_preserves_release_and_january(self):
        paths=[ROOT/'public/data/release.json',ROOT/'public/data/catalog.json',ROOT/'data/staging/portugal-2013-01/candidate.json']
        before=[p.read_bytes() for p in paths];report=expand()
        self.assertEqual([m['month'] for m in report['months']],['2013-02','2013-03','2013-04','2013-05','2013-06'])
        expected={'2013-02':(0,0,1),'2013-03':(0,0,0),'2013-04':(6,6,35),'2013-05':(6,7,31),'2013-06':(8,4,85)}
        for m in report['months']:
            self.assertEqual(tuple(m['summary'][s]['records'] for s in ['AQUA_MODIS','TERRA_MODIS','SNPP_VIIRS']),expected[m['month']])
            self.assertEqual(m['state'],'AUDITED_STAGED_NOT_QUALIFIED');self.assertEqual(m['production_vintage'],'UNVERIFIED');self.assertEqual(m['g4'],'ADJUSTMENT_WITHHELD')
            content=(ROOT/'data/staging'/('portugal-'+m['month'])/'candidate.json').read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(),m['candidate_sha256'])
        self.assertEqual([p.read_bytes() for p in paths],before);self.assertEqual(report['additional_qualified_released_months'],0)
        with self.assertRaisesRegex(AssertionError,'Outside declared'):audit_month('2019-06')

    def test_l2_receipts_exact_pairs_and_access_do_not_become_valid_observation(self):
        folder=ROOT/'data/acquisition/phase3-l2'
        for receipt in folder.rglob('*.receipt.json'):
            item=json.loads(receipt.read_text(encoding='utf-8'));data=receipt.with_name(receipt.name.replace('.receipt.json','.json')).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256']);self.assertEqual(len(json.loads(data)['feed']['entry']),item['cmr_hits'])
        report=json.loads((ROOT/'reports/HISTORICAL_PHASE3_L2.json').read_text(encoding='utf-8'))
        self.assertEqual(len(report['months']['2013-06']),8)
        for month in ['2013-01','2013-06']:
            self.assertIn('MOD14+MOD03',report['pairs'][month])
            for pair in report['pairs'][month].values():
                self.assertTrue(set(pair['matched_metadata_keys']).isdisjoint(pair['missing_geolocation_keys']))
        self.assertEqual(report['pixel_payload_bytes_downloaded'],0);self.assertEqual(report['observation_support'],'UNKNOWN');self.assertEqual(report['g4'],'ADJUSTMENT_WITHHELD')
        self.assertNotEqual(report['access_probe']['state'],'QUALIFIED')

if __name__=='__main__':unittest.main(verbosity=2)
