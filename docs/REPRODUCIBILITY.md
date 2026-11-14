# Insider Lens — reproduction boundaries

## Public clone: application and accepted evidence

1. Install Node 22+, Python 3.12+ and Git. Clone the public repository.
2. `python scripts/restore-public-artifacts.py` restores exactly three existing public JSON receipts, bound by URL, byte size and SHA-256 in `docs/PUBLIC_ARTIFACT_RESTORE.json`. Original bytes contain acquisition-machine paths; they are ignored by Git and never rewritten. No login is needed. This network dependency is explicit: a completely offline clone cannot hydrate these receipts.
3. `npm ci`, `npm run build`, `npm run dev`. Open `/?region=canada&view=retention` at the printed localhost URL. Production deployment needs HTTPS for browser SHA-256. The existing live URL is independent of GitHub; do not enable Pages or migrate hosting.
4. `npx playwright install chromium`, then `npx playwright test --config playwright.public.config.ts`. This public profile explicitly excludes one Phase2 staged-audit binding test because its original non-runtime receipt contains personal acquisition paths and is not published. It preserves all other test assertions. The original `npm run test:e2e` profile retains that test for a complete development workspace.
5. Create/activate a Python venv; `python -m pip install -r requirements.lock.txt`; `python -m unittest discover -s science -p test_science.py -v`; `python scripts/verify-public-release.py`.

The portable Python check hashes published science files and runs the exact 12-case production partition against the frozen original-data acceptance receipt. It does **not** rebuild the original raw oracle index, rerun the full 72-test research suite or claim independent raw-data validation on a fresh clone. No local node_modules, venv, original archives or SQLite indexes are copied to the clone. Browser tests require internet for the detailed basemap; bundled Natural Earth coarse context remains available.

## Full raw-data audit and rebuild

Original scientific code, parsing rules and independent oracles are included unchanged. Raw NASA archives, L2 files, SQLite indexes and historical backup snapshots are excluded for size/privacy. A future FIRMS request may not reproduce identical original packaging, request IDs or bytes; **do not silently substitute it into this sealed release**.

Acquire the originals from NASA FIRMS Archive Download (https://firms.modaps.eosdis.nasa.gov/download/) or the team's preserved read-only archive storage. Request IDs: MODIS 844805 / VIIRS 844806 (Portugal diagnostic, June 2017), MODIS 845605 / VIIRS 845606 (Canada request 2010-01-01 through 2026-11-13). Check `docs/SOURCE_ARCHIVES.json` before processing. The Canada delivery's actual latest rows precede the request endpoint; requested coverage is not proof of acquired coverage. Requests return JSON for Canada and CSV for Portugal. Original archive/member hashes are carried in accepted runtime artifacts.

Use a separate research checkout/output location. Python source defaults to the current user's Downloads, not a published personal path:

```sh
python science/pipeline.py --input-dir INPUT_DIR --output-dir OUTPUT_DIR --reports-dir REPORT_DIR
python science/independent_recount.py --input-dir INPUT_DIR --release OUTPUT_DIR/release.json --reports-dir REPORT_DIR
```

The production `release.json` is explicitly PENDING_INDEPENDENT_RECOUNT until the oracle verifies it. Use a new OUTPUT_DIR; do not overwrite an accepted pointer. Canada full rebuild, once the exact original archives are in the current user's Downloads:

```sh
python science/canada_intake.py
python science/canada_oracle.py
python science/canada_publish.py
python science/canada_native_oracle.py
python science/phase12_partition.py
python science/phase12_oracle.py
```

This is a multi-million-record disk-backed rebuild, not the lightweight public setup. Phase6–10 L2 experiments additionally need the exact product/granule IDs, frozen contracts, source-specific QA and privately configured official Earthdata authentication recorded by the original scientific workflow. Their full local receipts and old backup snapshots are not bundled. The **entire historical 72-test suite therefore requires restoring those external research materials**; it is not claimed to pass on the public clone. Source code is provided for inspection and future qualified reproduction, with this limitation explicit.

Do not open original scientific holdouts for a new experiment, infer opportunity from positive detections, change the LAEA grid or bypass ADJUSTMENT_WITHHELD. Current branded publication introduces no scientific fit, correction or holdout evaluation.
