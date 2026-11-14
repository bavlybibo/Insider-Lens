"""Verify a real staged candidate, without promoting it or changing the release."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from acquire_history import acquire
from history_candidate import inspect_candidate,RAW,ROOT

class HistoricalCandidateTests(unittest.TestCase):
    def test_acquired_originals_match_recorded_hashes_and_whitelisted_training_sources(self):
        manifest=acquire()  # Existing acquisition is verified without network.
        self.assertEqual(manifest['candidate_month'],'2013-01')
        self.assertEqual(len(manifest['files']),4)
        for item in manifest['files']:
            self.assertTrue(item['url'].startswith('https://firms.modaps.eosdis.nasa.gov/data/country/'))
            self.assertEqual(hashlib.sha256((RAW/item['file']).read_bytes()).hexdigest(),item['sha256'])

    def test_raw_candidate_recounts_and_cannot_promote_unqualified_history(self):
        # Derived stage bytes are deterministic; scientific release stays intact.
        original=(ROOT/'public/data/release.json').read_bytes()
        report=inspect_candidate()
        self.assertEqual(report['audit'],'PASS')
        self.assertEqual(report['independent_raw_recount'],'PASS')
        self.assertEqual(report['summary']['SNPP_VIIRS']['records'],4)
        self.assertEqual(report['summary']['SNPP_VIIRS']['occupied_cell_days'],2)
        self.assertEqual(report['summary']['AQUA_MODIS']['records'],0)
        self.assertEqual(report['summary']['TERRA_MODIS']['records'],0)
        self.assertEqual(report['state'],'AUDITED_STAGED_NOT_QUALIFIED')
        self.assertEqual(report['production_vintage'],'UNVERIFIED')
        self.assertEqual(report['extract_completeness'],'UNKNOWN')
        self.assertEqual(report['observation_support'],'OBSERVATION_UNKNOWN')
        self.assertEqual(report['g4'],'ADJUSTMENT_WITHHELD')
        self.assertEqual(report['release_decision'],'DO_NOT_PROMOTE_TO_QUALIFIED_HISTORY_OR_CURRENT_CATALOG')
        self.assertEqual(len(report['qualification_blockers']),3)
        self.assertEqual(set(report['source_manifests'][0]['categories']['version']),{'6.2'})
        self.assertNotIn('6.03',report['source_manifests'][0]['collection'])
        self.assertEqual((ROOT/'public/data/release.json').read_bytes(),original)
        self.assertEqual(json.loads(original)['months'],['2017-06'])

    def test_changed_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            manifest=json.loads((RAW/'ACQUISITION_MANIFEST.json').read_text())
            for item in manifest['files']:(folder/item['file']).write_bytes((RAW/item['file']).read_bytes())
            (folder/'ACQUISITION_MANIFEST.json').write_text(json.dumps(manifest))
            with (folder/'modis_2013_Portugal.csv').open('ab') as f:f.write(b'tampered')
            with self.assertRaisesRegex(AssertionError,'Immutable acquired input changed'):
                inspect_candidate(folder,folder/'stage')

    def test_l2_metadata_is_hash_verified_and_does_not_qualify_observation(self):
        folder=ROOT/'data/acquisition/l2-inventory-2013-01'
        manifest=json.loads((folder/'MANIFEST.json').read_text())
        for item in manifest:
            content=(folder/(item['product']+'.json')).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(),item['sha256'])
            self.assertEqual(len(json.loads(content)['feed']['entry']),item['cmr_hits'])
        report=json.loads((ROOT/'reports/L2_METADATA_INVENTORY.json').read_text())
        self.assertEqual(report['state'],'METADATA_ONLY_NOT_QUALIFIED')
        self.assertEqual(report['pixel_arrays_downloaded'],0)
        self.assertEqual(report['observation_support'],'OBSERVATION_UNKNOWN')
        self.assertEqual(report['products']['MYD03']['version'],'6.1')
        self.assertEqual(report['products']['MYD14']['listed_granules'],83)
        self.assertEqual(report['products']['VNP14IMG']['listed_granules'],108)

if __name__=='__main__':unittest.main(verbosity=2)
