# Existing Insider Lens Worker

## Separate optional deployment — not the submission origin

The verified judge demonstration is **https://insider-lens.pages.dev/?region=canada&view=retention**. Pages and Workers Builds are separate Git integrations. A failed Worker check does not invalidate a separately verified Pages deployment.

On 14 November the operator confirmed that Worker Build `675fe5f7-1415-4f89-9ee0-d60f387a40dd` at `785e0ca` used dashboard build command `npm run build`, then failed the Wrangler runtime-integrity guard with `Required runtime asset missing`. That command omits the pinned receipt restoration performed by `npm run build:cloudflare`. This specific log diagnosis is **operator-confirmed**; local API access to Workers Builds settings/logs still returns HTTP403 code10000, so effective Node/deploy/environment settings have not been independently verified or changed. GitHub independently reports a failed Worker check at `7879875` while Pages succeeded for that same source commit.

Optional operator correction: existing Worker → Settings → Build: save build `npm run build:cloudflare`, deploy `npx wrangler deploy`, build variables `NODE_VERSION=22`, `SKIP_DEPENDENCY_INSTALL=1`; then retry the failed build and inspect receipt-restoration/integrity logs. Keep repository `bavlybibo/Insider-Lens`, branch `main`, root `/`. With skip enabled, the project script performs the locked JavaScript install itself; do not add a redundant installation command. These settings are requirements, **not a claim that dashboard values were saved**. No Worker settings or deployments were changed for the Pages release completion.

The current [Workers Builds configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/) separates build and deploy commands; its [build image reference](https://developers.cloudflare.com/workers/ci-cd/builds/build-image/) documents Node overrides and skipping automatic dependency installation.

## Required reproducible configuration

Use the existing Git-connected **`insider-lens` Worker**, repository `bavlybibo/Insider-Lens`, branch `main`. No replacement Worker, Pages migration, Python backend, KV, database or R2 is required.

Workers Builds settings:

- Node.js **22** (`.node-version` and optional `NODE_VERSION=22`).
- Build command **`npm run build:cloudflare`**.
- Deploy command **`npx wrangler deploy`**, using exactly pinned development dependency **Wrangler 4.162.0**.
- Build variable **`SKIP_DEPENDENCY_INSTALL=1`** is supported by Workers Builds. The existing build then installs only locked JavaScript dependencies itself; it avoids automatic research Python installation. Do not add a second explicit `npm ci` when using this setting.

`wrangler.jsonc` explicitly serves **`./dist`**, enables the existing `workers.dev` URL and disables optional preview URLs. The app navigates by query parameters at `/`; it needs no arbitrary pathname SPA fallback. `not_found_handling: "none"` returns genuine 404 responses for absent science JSON, avoiding the original Worker’s false HTTP200/index.html result. No application Worker API or bindings are introduced.

Wrangler's custom-build command is an additional **integrity guard**, `node scripts/verify-runtime.mjs dist`, not a second compilation or a substitute for the Workers Builds build command. The pinned CLI dry run demonstrated that guard executes before asset upload. Actual Workers Builds settings still own compilation/restoration.

The three pinned receipts remain Git-excluded. `PUBLIC_RUNTIME_MANIFEST.json` and `PUBLIC_ARTIFACT_RESTORE.json` retain their original scientific hashes and URLs. All 787 public files and the complete production bundle must be present; missing/corrupt receipt or dependency means deployment fails. Original NASA ZIP/HDF/SQLite files and private credentials remain unnecessary.

```sh
npm ci
npm run build:cloudflare
npx wrangler deploy --dry-run
# Authenticated operator / connected Workers Builds only:
npx wrangler deploy
node scripts/verify-runtime.mjs dist https://WORKER.ACCOUNT.workers.dev reports/worker-production/resources --strict-missing-json
```

The HTTP verification directly checks every pinned runtime file and built asset. `--strict-missing-json` additionally requires a deliberately absent `/data/` canary to return 404. Canonical HTML entry routing and percent-encoded scoped-license filenames are requested directly; data redirects and HTML substitutions are rejected.

Workers deployment version UUIDs are distinct from Git commit hashes. Record the Git source and active version separately. Workers Builds configuration/logs requires its own API permission, not merely Wrangler's deployment OAuth permission. Use the dashboard for those settings/logs when that API permission is unavailable; do not copy credentials into the repository.

Official references checked 14 November 2026: [static assets](https://developers.cloudflare.com/workers/static-assets/), [Wrangler asset routing](https://developers.cloudflare.com/workers/wrangler/configuration/#assets), [Workers Builds settings](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/), [dependency installation](https://developers.cloudflare.com/workers/ci-cd/builds/build-image/), [workers.dev](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/).
