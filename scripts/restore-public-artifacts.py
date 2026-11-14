"""Restore three immutable public runtime receipts, without credentials or edits."""
from pathlib import Path
import hashlib
import json
import ssl
import urllib.request
import certifi

ROOT = Path(__file__).resolve().parents[1]


def run():
    manifest = json.loads((ROOT / 'docs/PUBLIC_ARTIFACT_RESTORE.json').read_text(encoding='utf-8'))
    for item in manifest['artifacts']:
        path = ROOT / item['file']
        assert path.resolve().is_relative_to((ROOT / 'public').resolve())
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], 'Existing artifact differs; refusing overwrite'
            continue
        request = urllib.request.Request(item['url'], headers={'User-Agent': 'Insider-Lens-public-artifact-restore/1.0'})
        # Use the pinned CA bundle; never disable TLS certificate verification.
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request, context=context, timeout=60) as response:
            raw = response.read(item['bytes'] + 1)
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], 'Public artifact integrity failed'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(raw)
    print('PASS: all three public artifacts match immutable source hashes; no credentials used.')


if __name__ == '__main__':
    run()
