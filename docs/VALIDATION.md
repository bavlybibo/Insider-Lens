# Insider Lens — publication validation

14 November 2026. Existing full development workspace after public rebranding:

- TypeScript/Vite production build PASS (existing MapLibre chunk-size advisory).
- All 72 scientific tests PASS, 94.802 seconds. All 86 scientific source files and 685 public scientific/basemap files preserved byte-identically.
- All 151 browser tests PASS, including two new public-brand/title/export-name tests, zero failures/flaky/skipped.
- Desktop 1440 and mobile 390/320 real screenshots reviewed; title/home/export names match Insider Lens. No broad UI redesign.
- NASA quantities, source IDs, archive identities, grid, separate oracles and ADJUSTMENT_WITHHELD preserved.
- Production npm dependency audit: zero reported vulnerabilities at publication time (not a guarantee of future security).

The clean public-clone reproduction boundary and one explicitly excluded historical non-runtime audit test are in REPRODUCIBILITY.md. Final remote-clone and anonymous deployment receipts are recorded in the final publication report; do not equate these workspace results with a new raw-data reparse on a clone.
