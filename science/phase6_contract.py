"""Freeze a bounded development experiment before inspecting its outcomes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/phase6'

def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    contract = {
        'id': 'ca-common-support-2022-v1',
        'frozen_before': 'Phase6 bounded native selection and CMR discovery; Phase5 national inventory already public',
        'parent_protocol': 'reports/CANADA_PREREGISTRATION.json',
        'aoi_wsen': [-120, 49, -110, 55],
        'membership': 'raw WGS84 pixel center within west/south inclusive east/north exclusive box; not footprint coverage',
        'development': ['2022-06-01', '2022-06-02', '2022-06-03'],
        'replication': ['2022-06-08', '2022-06-09', '2022-06-10'],
        'split': 'descriptive development replication only, no fitted model; four full UTC days excluded; not guaranteed independent fire episodes',
        'l2_discovery_days': ['2022-06-01', '2022-06-08'],
        'l2_sample_policy': 'first chronological Aqua fire granule with CMR-linked data URL per day, then all same-platform geolocation / VIIRS metadata candidates; no selection by positive outcomes',
        'products': {'MYD14': ['C2278858993-LPCLOUD', '061'], 'MYD03': ['C1379841358-LAADS', '6.1'],
                     'VNP14IMG': ['C2734202914-LPCLOUD', '002'], 'VNP03IMG': ['C2105092163-LAADS', '2'],
                     'VNP14': ['C2545314536-LPCLOUD', '002'], 'VNP03MOD': ['C2105092427-LAADS', '2']},
        'grid': {'id': 'ca-laea60n100w-wgs84-o0-v1', 'crs': '+proj=laea +lat_0=60 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs +type=crs',
                 'origin_m': [0, 0], 'widths_m': [5000, 10000, 20000], 'counting_m': 10000},
        'time_convention': 'UTC, native minute precision; no exact scan-time claim',
        'offset_minutes': [15, 30, 60],
        'parent_matching_change': 'Phase5 5/10/15 min superseded ONLY for this exploratory geometry/time feasibility test, before Phase6 outcomes; no gate relaxation or model eligibility',
        'sources': ['AQUA_MODIS', 'TERRA_MODIS', 'SNPP_VIIRS'],
        'bridge_sources': ['AQUA_MODIS', 'SNPP_VIIRS'],
        'pc': 'SP', 'row_versions': {'AQUA_MODIS': ['6.03'], 'TERRA_MODIS': ['6.03'], 'SNPP_VIIRS': ['2']},
        'quality': {'native_baseline': 'all native Types and valid native confidence; zero FRP retained',
                    'sensitivity': 'literal Type 0 only (presumed vegetation, production vintage unverified); MODIS confidence >=30 / VIIRS n,h; FRP strictly >0 in separate MW research lane',
                    'opportunity': 'compatible geolocated masks and algorithm QA; clear valid pixels; no bowtie/non-nominal; view zenith <=40 with 30/50 sensitivity; actual shared footprints required'},
        'targets': {'B0': 'exact source-separated positive 10km cell UTC days',
                    'B1': 'same-cell same-native-DN acquisition-time candidate keys, not matched valid opportunity',
                    'B2': '750m VNP14 vs 375m VNP14IMG on actual qualified common support, otherwise BLOCKED',
                    'B3': 'FRP MW correction only with method-specific QA, footprints and viewing geometry, otherwise BLOCKED'},
        'minimum_for_fit': {'qualified_matched_passes': 30, 'distinct_7day_blocks': 5, 'spatial_blocks_km': 50,
                            'reason': 'feasibility floor, not statistical power guarantee; this bounded pilot cannot authorize fitting'},
        'candidate_model_family': 'none until opportunity and units qualified; no count ratio or FRP coefficient transfer',
        'uncertainty': 'enumerated finite-catalog descriptive counts exact; geolocation/Type/vintage uncertain. No CI for unidentifiable exposure or predictions; no fitted calibration.',
        'gate': 'ADJUSTMENT_WITHHELD', 'holdouts': 'original Portugal/California and Canada2024 untouched; no evaluation access',
        'max_download_bytes': 512000000,
    }
    data = (json.dumps(contract, indent=2, sort_keys=True) + '\n').encode()
    path = OUT / 'COHORT_CONTRACT.json'
    if path.exists():
        assert path.read_bytes() == data, 'Frozen contract cannot be rewritten'
    else:
        path.write_bytes(data)
    print(json.dumps({'contract': str(path), 'sha256': hashlib.sha256(data).hexdigest()}))
    return contract

if __name__ == '__main__':
    freeze()
