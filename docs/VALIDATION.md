# Insider Lens — publication validation

Prior rebranding/publication run, 14 November 2026 (historical results):

- TypeScript/Vite production build PASS (existing MapLibre chunk-size advisory).
- All 72 scientific tests PASS, 94.802 seconds. All 86 scientific source files and 685 public scientific/basemap files preserved byte-identically.
- All 151 browser tests PASS, including two new public-brand/title/export-name tests, zero failures/flaky/skipped.
- Desktop 1440 and mobile 390/320 real screenshots reviewed; title/home/export names match Insider Lens. No broad UI redesign.
- NASA quantities, source IDs, archive identities, grid, separate oracles and ADJUSTMENT_WITHHELD preserved.
- Production npm dependency audit: zero reported vulnerabilities at publication time (not a guarantee of future security).

The clean public-clone reproduction boundary and one explicitly excluded historical non-runtime audit test are in REPRODUCIBILITY.md. Final remote-clone and anonymous deployment receipts are recorded in the final publication report; do not equate these workspace results with a new raw-data reparse on a clone.

Completed public remote-clone verification: dependency install and production build PASS; eight synthetic science tests PASS;771 scientific file hashes and12-case production replay PASS; public browser profile150PASS with one explicitly excluded non-runtime audit binding test. Full-workspace151PASS remains distinct. Anonymous public desktop/mobile source-policy and export smoke PASS. Initial restore TLS/user-agent failure was fixed and reverified with certificate verification enabled. See reports/FINAL_GITHUB_PUBLICATION_AND_SUBMISSION.md for exact scope and submission fields.

## Final desktop judge release audit — 14 November 2026

Production build PASS. Full scientific suite72PASS (87.624s); selected contracts/browser regressions54PASS; seven latest desktop finding/scope/copy tests PASS after the scroll-bound adjustment. Exactly one narrow-layout smoke test protects shared behavior; no mobile feature, style or showcase capture was added. The original151/150 browser counts above describe the earlier full publication runs, not this new selected regression execution. Current clone and remote results are in reports/FINAL_INSIDER_LENS_RELEASE_AUDIT.md.
