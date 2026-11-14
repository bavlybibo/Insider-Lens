import hashlib
import json
from pathlib import Path
import unittest
import numpy as np
from phase7_contract import freeze
from phase7_discovery import area,intersect,geometry,granule,pairs
from phase7_support import state,modis_qa

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/phase7'
class Phase7Science(unittest.TestCase):
    def test_frozen_contract_and_original_holdouts(self):
        c=freeze();self.assertEqual(hashlib.sha256((R/'SEARCH_CONTRACT.json').read_bytes()).hexdigest(),'eab85cbb827d4f291eba66b29bb29f9fe42c423876cf844c7daa9194730dace0')
        self.assertFalse(c['fit']['allowed_now']);self.assertEqual(c['time']['primary_minutes'],10);self.assertEqual(c['geometry']['view_limit_degrees'],40)
        self.assertTrue(all(d.startswith('2022-06-') for s in c['splits'].values() for d in s['days']))
        self.assertEqual(hashlib.sha256((ROOT/'reports/phase6/COHORT_CONTRACT.json').read_bytes()).hexdigest(),c['phase6_contract_sha256'])
        self.assertEqual(hashlib.sha256((ROOT/'public/data/release.json').read_bytes()).hexdigest(),'e256a172f3c61b82f088428cc0b50554605fb0bdb4648f5410982be90a5f45ed')

    def test_unknown_does_not_become_non_detection(self):
        self.assertEqual(state(5),'UNKNOWN_SUPPORT');self.assertEqual(state(9),'UNKNOWN_SUPPORT')
        self.assertEqual(state(5,True,True,True,False),'UNKNOWN_SUPPORT')
        self.assertEqual(state(5,True,True,True,True),'QUALIFIED_OBSERVED_NONDETECTION')
        for m in [0,1,2,4]:self.assertEqual(state(m),'CLOUD_OR_INVALID')
        self.assertEqual(state(6,True,True,True,True),'UNKNOWN_SUPPORT')

    def test_modis_land_water_is_not_375_input_error_bits(self):
        q=np.array([2,2+16+32+(1<<20)+(2<<22)+(5<<24)],dtype=np.uint32);d=modis_qa(q)
        self.assertEqual(d['land_water'].tolist(),[2,2]);self.assertEqual(d['day'].tolist(),[0,1]);self.assertEqual(d['glint_level'].tolist(),[0,2]);self.assertEqual(d['rejection_flags'].tolist(),[0,5])
        self.assertEqual(d['adjacent_cloud'].tolist(),[0,1])

    def test_polygon_boundary_area_and_orientation(self):
        a=[(0,0),(10,0),(10,10),(0,10)];b=[(5,0),(15,0),(15,10),(5,10)]
        self.assertEqual(area(intersect(a,b)),50);self.assertEqual(area(intersect(a,list(reversed(b)))),50)
        self.assertEqual(area(intersect(a,[(10,0),(20,0),(20,10),(10,10)])),0)

    def test_search_ignores_fire_and_cloud_outcomes_and_never_invents_vza(self):
        p=next((ROOT/'data/acquisition/phase7/metadata').glob('*MYD14.json'));e=json.loads(p.read_text())['feed']['entry'][0];bbox=[-118,50,-117,51]
        x=granule(e,bbox);e.update(cloud_cover='100',fire_pixels=999999,frp=999999);self.assertEqual(granule(e,bbox),x)
        self.assertIsNone(x['geometry']['view_zenith_estimate_degrees'])

    def test_independent_arrays_and_all_export_points_bound(self):
        a=json.loads((R/'SUPPORT_AUDIT.json').read_text());o=json.loads((R/'INDEPENDENT_VALIDATION.json').read_text());m=json.loads((R/'MASK_CENTERS.json').read_text())
        self.assertEqual(o['state'],'PASS');self.assertEqual(len(o['checks']),4);self.assertEqual(sum(len(p) for s in m.values() for p in s.values()),32271)
        self.assertEqual(o['support_audit_sha256'],hashlib.sha256((R/'SUPPORT_AUDIT.json').read_bytes()).hexdigest());self.assertIsNone(a['qualified_shared_support_m2'])
        self.assertEqual(a['results']['development']['products']['MYD14']['view_sensitivity']['40']['aoi_centers_within_view'],0)
        self.assertEqual(a['results']['replication']['products']['VNP14']['view_sensitivity']['40']['aoi_centers_within_view'],11663)
        self.assertFalse(a['generalization']);self.assertFalse(a['holdout_evaluation']);self.assertEqual(a['g4'],'ADJUSTMENT_WITHHELD')

    def test_exact_inputs_and_375_recount_do_not_rewrite_rejected_versions(self):
        a=json.loads((R/'EXACT_SUPPORT_AUDIT.json').read_text());o=json.loads((R/'EXACT_INDEPENDENT_VALIDATION.json').read_text());q=json.loads((R/'QUALIFICATION_SENSITIVITY.json').read_text())
        self.assertEqual(a['science_files'],12);self.assertEqual(a['downloaded_bytes'],450752516);self.assertEqual(len(o['checks']),5)
        self.assertEqual(sum(c['aoi_centers'] for c in o['checks']),78923)
        self.assertTrue(all(p['exact_geolocation_input_identity'] for r in a['results'].values() for p in r['products'].values()))
        self.assertEqual(q['independent375']['nominal_land_centers'],45039);self.assertEqual(q['independent375']['residual_bowtie'],0)
        self.assertEqual(a['results']['development']['products']['MYD14']['aoi_pixel_centers'],4368)
        self.assertEqual(json.loads((R/'SUPPORT_AUDIT.json').read_text())['results']['development']['products']['MYD14']['aoi_pixel_centers'],4369)
        self.assertIsNone(a['qualified_shared_support_m2']);self.assertEqual(o['qualified_footprint_validation'],'NOT_EXECUTED_NO_QUALIFIED_FOOTPRINTS')
        for split in a['results'].values():
            for p in split['products'].values():self.assertFalse(any(int(k)>=7 and v>0 for k,v in p['mask_counts'].items()))

if __name__=='__main__':unittest.main()
