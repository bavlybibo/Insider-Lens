# Insider Lens — Pages Canada production repair

Executed 14 November 2026. Production: **https://insider-lens.pages.dev/?region=canada&view=retention**. Existing Git-connected Pages project `insider-lens`; no project was created and no Worker permission or manual Worker deployment was used for this repair.

## Diagnosis and scope of the conclusion

Baseline main was `785e0ca9f9fbbba55d078b4aea302187cb249344`, Pages deployment `5b13e98b-f9fb-4311-a260-566db1238509`, entry `/assets/index-CFpmbeBm.js`.

Six fresh live Chromium contexts (three default, three SwiftShader) all rendered direct Canada entry. The operator's original spontaneous blank was **not naturally reproduced**. It would be inaccurate to identify its exact network/GPU trigger retrospectively.

Three concrete defects were established before editing:

1. **Region and URL diverged.** `Workspace.tsx` changed only React region state; no pushState or popstate synchronization existed. In all six runs, Portugal → Canada left the Portugal URL unchanged; refresh rendered Portugal. This is a deterministic routing cause, independent of scientific JSON integrity.
2. **Canada depended on Portugal's release load.** The outer component always fetched and validated Portugal before selecting Canada. Blocking `/data/catalog.json` on the live origin prevented direct Canada entry despite intact Canada receipts.
3. **An uncaught lazy-import failure could blank the root.** Deliberately aborting `CanadaWorkspace-DPm2uaRO.js` on the live origin produced `TypeError: Failed to fetch dynamically imported module` and an empty root. No workspace error boundary existed. This is a controlled reproduction of the blank-screen failure mechanism, **not proof that the original incident had that trigger**.

A natural run also captured MapLibre's `The layer 'offline-land' does not exist in the map's style and cannot be queried for features.` `checkGeography` queried cached layer IDs while a replacement style was active. That was a console error, not evidence of an uncaught React exception.

The three corresponding baseline regression tests failed (0/3). [Condensed diagnosis](pages-repair/diagnosis.json), [controlled error events](pages-repair/before-error-events.json), [baseline science responses](pages-repair/before-science.json).

## Minimal correction

- `src/Workspace.tsx`: choose Canada before Portugal loading; isolate the unchanged Portugal loader; synchronize region navigation with history and popstate; reset the workspace at region/study transitions; catch rendering and rejected lazy modules with an accessible recovery screen. Failures explicitly withhold results and offer reload or Portugal; no evidence substitution.
- `src/CanadaMap.tsx`: query only base layers present in the current style, preventing the observed stale-layer error.
- `tests/pages-route.spec.ts`, `playwright.pages.config.ts`: five production-origin regressions covering independent Canada entry, URL/refresh/back/forward, deliberate lazy-module failure, corrupt-catalog rejection, repeated retention entry/refresh/Passport/export and unexpected errors.

`src/CanadaWorkspace.tsx`, `src/canada.ts` and `src/evidenceRetention.ts` were inspected and **not modified**. Science algorithms, assets, manifests, oracles and source identifiers were not edited.

## Git and Pages identity

- Repository: https://github.com/bavlybibo/Insider-Lens
- Old main: `785e0ca9f9fbbba55d078b4aea302187cb249344`.
- Repair source commit: **`32d66c1bd8102350d7f6dcdecfc91869bbb55c35`**, pushed normally to main.
- Successful automatic production deployment: **`0e048e32-5486-4987-b9b8-6048524f23b0`**, https://0e048e32.insider-lens.pages.dev ; completed 10:43:31 UTC.
- Live entry: `/assets/index-CXZyRKdr.js`; Canada module `/assets/CanadaWorkspace-B3dmMACj.js` and map `/assets/CanadaMap-VJ2ZxNkj.js` matched the locally verified production bytes.
- Effective build: `npm run build:cloudflare`; Node **22.23.4**; `SKIP_DEPENDENCY_INSTALL=1`; output `dist`.
- Cloudflare logs confirm all three pinned public receipts were restored and verified, all 798 output assets passed validation, and assets were published. The existing Worker configuration was skipped by Pages; it did not affect this static build.

[Pages source/deployment receipt](pages-repair/deployment-repair.json), [filtered actual build log](pages-repair/build-production.json). This report records the application repair identity. A subsequent documentation/test-synchronization commit does not change the production application bytes; its final remote SHA and deployment receipt are supplied with the release delivery.

## Actual live acceptance

Fresh anonymous Chromium contexts used the actual **Pages** origin, blocked service workers, and had no saved cookies/storage state or localhost data source.

| Live check | Executed result |
|---|---|
| Portugal June 2017 | Aqua 238; S-NPP VIIRS 2,041; navigation back remains functional |
| Direct Canada / refresh / repeated visits | Retention map rendered; URL stayed Canada; no empty root |
| Portugal → Canada / back / forward | Region URL and rendered region synchronized |
| Southern Canada June 2023 | 34 MODIS-only + 199 shared + 335 VIIRS-only = **568** positive cell-day keys |
| MODIS only | **2,139** retained source records / 233 keys |
| VIIRS only | **8,385** retained source records / 534 keys |
| Both native | **10,524** retained source records / 568 keys / 28 UTC dates |
| June 2010 before VIIRS | **12,744** MODIS records / 2,113 positive keys / 30 UTC dates; VIIRS unavailable in era, not observation zero |
| Cell/day selection | Map cell, keyboard cell, date calendar and selected exports reconcile |
| CSV | 568 overlap rows; each policy's retained-record sum checked; selected UTC day and cell subsets checked |
| Evidence Passport | Opens; 8,355,817 accepted native records and limitations visible |
| Scientific Bridge | Available; all 16 candidates remain UNKNOWN_SUPPORT; exported rows retain ADJUSTMENT_WITHHELD |
| Ordinary-route exceptions | Zero page exceptions, console errors and unhandled rejections in the repeated-route regression |
| Scientific networking | 33 same-origin science responses / 21 distinct paths hash-checked in the complete journey; no missing or mismatched science resource |

Five live P0 tests passed in **24.3 s**; six existing live acceptance tests passed in **49.0 s**. [Test receipt](pages-repair/live-tests.json), [response/performance receipt](pages-repair/screenshots/browser-evidence.json).

One initial live test attempt had 4 passes / 1 failure: its rapid Passport close intentionally triggered AbortController cleanup before optional `examples.json` finished. Traces showed two `net::ERR_ABORTED` cancellations, not missing files (the full artifact crawl verified the same file). The test now waits for that real response before closing; no production loader or integrity check was weakened. The rerun passed all five tests.

## Integrity and output verification

All **798 production resources / 38,648,744 bytes** returned expected bytes and SHA-256 from Pages. This includes every required Canada month, both retained Phase 6 bridge receipts, Phase 7–12 dependencies, JavaScript/CSS and the real HTML entry. Missing list is empty. Required JSON passed exact byte/hash matching and JSON validation; HTML SPA fallbacks cannot pass those checks.

[Per-resource PATH / PRESENT / SIZE / HASH / HTTP STATUS / REQUIRED BY](pages-repair/production-resources.tsv).

| Receipt | Bytes | SHA-256 |
|---|---:|---|
| Canada catalog | 1,568,686 | `ecebbb2614b6e60825752210cdc672a29b3e7e6ef956d59057ade4baa4cf1938` |
| Canada native oracle | 1,544 | `9ff195b400d62e3c2390636663ac23357d4bed71c76d0359be7eaefb8d75fa80` |
| Phase 12 partition | 262,748 | `e8b76d1bbe1c24e166dece3d54f22122fcc3076fe887d0eed1e65546057c7887` |
| Phase 12 independent partition | 625 | `50b186d978fa7e287218d58ed8fea198286d8b1038dabd2d31b469e2fd4ae1e2` |

Local `npm run build:cloudflare` passed; 59 existing static desktop/contracts passed in **239.4 s**; five new regressions passed locally; five deployment unit tests passed. The portable scientific verifier rehashed **771** protected files and replayed the frozen **12** partition cases successfully. The raw-data independent oracle was not rerun for this frontend-only repair. [Local test receipt](pages-repair/local-tests.json).

## Rendered desktop evidence and performance

Screenshots were captured from the live Pages origin and visually inspected: [1440 × 900 retention](pages-repair/screenshots/retention-1440.png), [1920 × 1080 retention](pages-repair/screenshots/retention-1920.png), [June 2010](pages-repair/screenshots/history-2010.png), [Scientific Bridge](pages-repair/screenshots/bridge.png). The map, retained quantities, calendar and Passport were visible. Coarse local geography appeared while the external detail basemap loaded; the detailed 1920 view loaded successfully. No new mobile work or redesign was performed.

One live journey: scientific answer **3,010 ms**, rendered geographic context **3,616 ms**; policy changes **309 / 296 / 305 ms**; final Chromium used-JS-heap snapshot **33.1 MB**. These are measured samples, not a performance guarantee or peak browser-memory measurement. Existing Vite cartography chunk-size advisory remains.

## Files and preservation

Application/test files: the four paths listed under Minimal correction. Public documentation: `README.md`, `docs/CLOUDFLARE_PAGES.md`, `docs/NASA_SUBMISSION.md`; this report and its explicitly linked receipts/screenshots. The only follow-up test edit waits for the optional Passport response before close.

No original NASA archive, HDF, SQLite database, private credential, machine token or new private runtime dependency was published. Preserved hashes, grid, UTC grouping, independent receipts, sealed holdouts and **G4 ADJUSTMENT_WITHHELD** are unchanged. The prior chatgpt.site demo was not altered. No Worker was created or deployed during this repair.

## Remaining limitations / operator action

No production-blocking Canada asset or routing defect remains in the executed acceptance tests. The exact trigger of the originally reported intermittent blank remains unproven; the verified render/lazy-failure path now has a visible fail-closed recovery state. External detailed basemap availability remains an existing dependency with local coarse fallback.

Scientific support and calibration remain unqualified; the positive-key partition is not physical fire counts or coincident cloud-free observation coverage. NASA submission materials now use the verified Pages Canada URL; the official NASA form was **not** edited or submitted.

## Exact published file list across repair and evidence commits

- `README.md`
- `docs/CLOUDFLARE_PAGES.md`
- `docs/NASA_SUBMISSION.md`
- `playwright.pages.config.ts`
- `src/CanadaMap.tsx`
- `src/Workspace.tsx`
- `tests/pages-route.spec.ts`
- `reports/PAGES_CANADA_PRODUCTION_REPAIR.md`
- `reports/pages-repair/diagnosis.json`
- `reports/pages-repair/before-science.json`
- `reports/pages-repair/before-error-events.json`
- `reports/pages-repair/local-tests.json`
- `reports/pages-repair/live-tests.json`
- `reports/pages-repair/deployment-repair.json`
- `reports/pages-repair/build-production.json`
- `reports/pages-repair/production-resources.tsv`
- `reports/pages-repair/screenshots/browser-evidence.json`
- `reports/pages-repair/screenshots/retention-1440.png`
- `reports/pages-repair/screenshots/retention-1920.png`
- `reports/pages-repair/screenshots/history-2010.png`
- `reports/pages-repair/screenshots/bridge.png`
