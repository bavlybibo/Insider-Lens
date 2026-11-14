# Insider Lens static release

Verified public application: **https://insider-lens.pages.dev/?region=canada&view=retention**. The earlier `chatgpt.site` demonstration remains unchanged. See the [executed Canada route and production report](../reports/PAGES_CANADA_PRODUCTION_REPAIR.md).

Cloudflare Pages settings: existing GitHub repository `bavlybibo/Insider-Lens`, production branch `main`, React/Vite, root `/`, **Node.js 22**, build **`npm run build:cloudflare`**, output **`dist`**. `.node-version` pins the major version. No Python, server functions, Earthdata login, environment secrets or raw science files are required.

Set **`SKIP_DEPENDENCY_INSTALL=1`** in both production and preview environments. The dedicated build then runs `npm ci --include=dev --no-audit --no-fund` itself, avoiding Pages' automatic discovery of the separately preserved research `requirements.txt`. Only JavaScript build dependencies are installed. This variable is not a secret.

## Integrity boundary

Remote main `cb221e16d968ab9409d98b243ec1471f71d71863` already contained 590 Canada files / 11,773,665 bytes, within 680 scientific runtime files / 34,027,836 bytes. Only the Canada catalog and two Phase6 bridge receipts were excluded from Git. Their immutable bytes include historical acquisition-machine path strings; these are provenance, never browser fetch paths. They were already public on the original demo. They remain Git-excluded and are neither edited nor force-added.

`PUBLIC_ARTIFACT_RESTORE.json` retains the original three URLs, lengths and hashes. The Node restore module independently restricts that exact allowlist, refuses redirects and unsafe paths, bounds downloads, verifies size/SHA-256 before writing, refuses corrupt existing files and fails on unavailable artifacts. Normal Node TLS verification is required. No fallback observations exist. The original Python restoration script remains available unchanged.

`PUBLIC_RUNTIME_MANIFEST.json` pins all 787 public files (36,390,706 bytes including restored receipts, basemap and fonts). It derives from the audited remote tree plus the three original receipts, and must agree with the existing sealed public-science hash inventory. No scientific hashes or references were rewritten. Verification follows pointer and oracle bindings, every catalog coverage chunk, explicit artifact tables, Phase6 evidence hashes, basemap derivation and the active Phase11 download. Original NASA archive/member names, L2 granules and acquisition paths are not static-resource dependencies.

The production check also verifies `index.html`, Vite assets, the entire `dist` inventory and Pages' 25 MiB per-file limit. The largest scientific asset is below that limit. All scientific JSON is served from the deployed site's own origin; only the cartographic basemap uses the pre-existing external provider/fallback. Missing or corrupted science remains withheld by the existing application.

## Reproduce release checks

```sh
npm ci
npm run build:cloudflare
npm run test:deployment
npm run preview -- --port 5187 --strictPort
# In another terminal:
node scripts/verify-runtime.mjs dist http://127.0.0.1:5187 reports/cloudflare/preview-resources
node node_modules/@playwright/test/cli.js test --config playwright.static.config.ts
```

`verify-runtime.mjs dist https://PROJECT.pages.dev reports/cloudflare/production-resources` checks every produced static resource anonymously by status, exact bytes and hash. Receipts include `PATH | PRESENT | SIZE | HASH | HTTP STATUS | REQUIRED BY`. The static browser configuration starts no development server. Set `INSIDER_LENS_TEST_ORIGIN` to the production origin to repeat desktop journeys there. Its dedicated unmocked test verifies same-origin science responses, policies, key exports, 2010 history, calendar, passport and bounded Bridge scope; other existing tests also exercise deliberate failure states.

## Research and redistribution boundary

Browser aggregates and bounded evidence receipts are deployable assets. Original FIRMS ZIPs and L2/HDF inputs remain excluded; full raw-data reproduction requires those separately obtained inputs and the research environment. Audit/oracle receipts already published with the release remain intact. Private credentials, research databases and internal acquisition files are never build inputs.

NASA FIRMS / NASA Earthdata / LANCE / UMD attribution and provenance are retained. NASA observations are not project-owned observations, and NASA does not endorse this application. The official [FIRMS download README, citation and disclaimer](https://nrt3.modaps.eosdis.nasa.gov/archive/FIRMS/README.pdf) permits open sharing and requests citation/disclaimer linkage; existing product lineage is preserved. [LAADS guidance](https://ladsweb.modaps.eosdis.nasa.gov/learn/) requests acknowledgement/citation for derived results. Third-party map/dependency notices remain in the repository. No new raw NASA or third-party bulk-data redistribution occurs. The existing unresolved original-content license decision is unchanged; `LICENSE_STATUS.md` describes it.

Scientific algorithms, fixed equal-area grid, UTC grouping, independent original-data oracles, sealed holdouts and **G4 ADJUSTMENT_WITHHELD** remain unchanged. Restoration checks integrity, not new calibration or independent human scientific validation.

References checked 14 November 2026: [Pages GitHub integration](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/), [build image and Node version](https://developers.cloudflare.com/pages/configuration/build-image/), [Pages limits](https://developers.cloudflare.com/pages/platform/limits/) and the NASA sources above. The Earthdata policy/citation landing URLs returned 403 or were inaccessible from this process; the official FIRMS README and LAADS guidance were accessible.
