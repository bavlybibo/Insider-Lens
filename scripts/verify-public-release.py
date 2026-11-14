"""Portable receipt integrity and production replay; not a new raw-data oracle."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run():
    inventory = json.loads((ROOT / 'docs/PUBLIC_SCIENCE_SHA256.json').read_text(encoding='utf-8'))
    for name, digest in inventory.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'Science integrity mismatch: ' + name
    subprocess.run([sys.executable, str(ROOT / 'science/phase12_partition.py')], cwd=ROOT, check=True)
    a = json.loads((ROOT / 'public/data/phase12/INDEPENDENT_PARTITION.json').read_text(encoding='utf-8'))
    assert a['state'] == 'PASS' and a['cases_verified'] == 12 and not a['fit'] and not a['holdouts_queried']
    assert a['g4'] == 'ADJUSTMENT_WITHHELD'
    print(f'PASS: {len(inventory)} scientific files hash-verified; 12-case production replay matches frozen receipt. Original-data oracle NOT rerun by this portable check.')


if __name__ == '__main__':
    run()
