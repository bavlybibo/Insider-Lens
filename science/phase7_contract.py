"""A separate metadata-only development search; never changes Phase 6 rules."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/phase7'

def freeze():
    old = json.loads((ROOT / 'reports/phase6/COHORT_CONTRACT.json').read_text())
    c = {
        'id': 'ca-metadata-support-june2022-v1',
        'frozen_before': 'all Phase7 CMR queries, new science arrays and fire-outcome selection',
        'prior_knowledge': 'Phase5 national native inventories and Phase6 rejected pilot already inspected; not blind evaluation',
        'parent': 'reports/CANADA_PREREGISTRATION.json',
        'splits': {
            'development': {'aoi_wsen': [-118, 50, -117, 51], 'days': ['2022-06-15', '2022-06-16']},
            'replication': {'aoi_wsen': [-113, 53, -112, 54], 'days': ['2022-06-22', '2022-06-23']},
        },
        'independence': 'nonoverlapping development AOIs and UTC dates, >50km spatial separation and >=6 full days; no claim of independent fire episodes',
        'products': old['products'], 'grid': old['grid'],
        'time': {'primary_minutes': 10, 'sensitivity_minutes': [5, 15],
                 'screen': 'absolute granule midpoint difference <=10min; actual per-pixel time <=10min required later; interval gap reported separately'},
        'geometry': {'view_limit_degrees': 40, 'sensitivity_degrees': [30, 50],
                     'metadata_proxy': 'distance of AOI center to approximate swath centerline from CMR quadrilateral; NOT measured VZA, footprint or cloud-free area',
                     'proxy_axis': 'join midpoints of the shorter opposing GRing edges in local WGS84 LAEA; minimize center-to-line distance',
                     'rank': ['same-acquisition geolocation and both VIIRS resolutions discoverable', 'max cross-swath centerline distance in km', 'absolute midpoint offset', 'reported total bytes', 'Aqua ID', 'VIIRS ID'],
                     'intersection': 'positive projected AOI/CMR GRing area for each sensor; densified edges approximate swath extent only'},
        'lineage': 'same acquisition key is discovery only; exact named geolocation input must match file payload before qualification; no substituting an instance silently',
        'quality': 'source-specific exact-collection QA definitions, valid geolocation, no cloud/invalid/bowtie; no 375m bit policy borrowed for MODIS or 750m',
        'budgets': {'max_metadata_responses': 24, 'max_metadata_bytes_each': 4000000, 'max_payload_bytes': 900000000,
                    'max_candidates_per_split': 1, 'min_free_disk_reserve_bytes': 1200000000},
        'selection': 'freeze first ranked timing/geometry-metadata candidate per split; unresolved exact lineage/QA prevents science qualification, never re-rank by outcome',
        'support': {'denominator': 'union of actual qualified native footprints intersected in time and area; no denominator from FIRMS positives or GRing',
                    'states': ['VALID_SHARED_SUPPORT', 'VALID_SINGLE_SENSOR_SUPPORT', 'CLOUD_OR_INVALID', 'UNKNOWN_SUPPORT', 'OBSERVED_POSITIVE_DETECTION', 'QUALIFIED_OBSERVED_NONDETECTION'],
                    'unknown': None},
        'fit': {'allowed_now': False, 'minimum_qualified_passes': 30, 'minimum_7day_blocks': 5,
                'baseline': 'unchanged native observations; no adjustment identity on compatible units only',
                'metrics_if_future_eligible': 'paired FRP MW absolute bias and absolute error against identity; 50km/7day block uncertainty; positive signal required; no count factors',
                'reason': 'two-pair feasibility experiment cannot satisfy fitting floor or original G4 release conditions'},
        'holdouts': 'original Portugal/California and Canada2024 sealed; no holdout queries or outcome evaluation',
        'g4': 'ADJUSTMENT_WITHHELD', 'phase6_contract_sha256': hashlib.sha256((ROOT/'reports/phase6/COHORT_CONTRACT.json').read_bytes()).hexdigest(),
        'auth': 'revocation confirmation for every chat-exposed token; only a new private token file outside repository; no environmental or pasted-token fallback',
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT/'SEARCH_CONTRACT.json'; raw = (json.dumps(c, indent=2, sort_keys=True)+'\n').encode()
    if path.exists():
        assert path.read_bytes() == raw, 'Frozen Phase7 contract differs'
    else:
        path.write_bytes(raw)
    return c

if __name__ == '__main__':
    freeze()
    print(hashlib.sha256((OUT/'SEARCH_CONTRACT.json').read_bytes()).hexdigest())
