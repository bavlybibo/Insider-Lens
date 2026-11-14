"""Write the requested execution record from actual experiment/test evidence."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/phase6'
def load(n):return json.loads((R/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(rows):return '\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)

def run():
    c=load('COHORT_CONTRACT.json');a=load('COMMON_SUPPORT_AUDIT.json');o=load('INDEPENDENT_VALIDATION.json');l=load('L2_SUPPORT_AUDIT.json');lo=load('L2_INDEPENDENT_VALIDATION.json');v=load('VISUAL_AND_PERFORMANCE.json');m=load('L2_RUNTIME_MEMORY.json')
    full=load('full-browser-results.json')['stats'];follow=load('final-product-followup.json')['stats'];p=json.loads((ROOT/'public/data/phase6/index.json').read_text())
    export_follow=load('final-export-followup.json')['stats']
    assert full['expected']==89 and full['unexpected']==full['skipped']==full['flaky']==0
    assert follow['expected']==17 and follow['unexpected']==follow['skipped']==follow['flaky']==0
    assert export_follow['expected']==6 and export_follow['unexpected']==export_follow['skipped']==export_follow['flaky']==0
    assert all(not r['errors'] for r in v['captures']+v['performanceRuns'])
    baseline=[['Slice','Aqua records / K','Terra records / K','VIIRS records / K','15 / 30 / 60 min positive candidate keys'],['---']*5]
    for split in ['development','replication']:
        s=a['results'][split]['scales']['10000'];baseline.append([split,*[str(s['baseline'][source]['records'])+' / '+str(s['baseline'][source]['cell_days']) for source in c['sources']], ' / '.join(str(x['same_cell_day_same_flag_candidate_keys']) for x in s['timing'])])
    masks=[['Date / source','AOI centers','Native mask classes 3 / 4 / 5 / 1','View zenith','Exact named geo input?'],['---']*5]
    for day,ps in l['results'].items():
        for prod,x in ps.items():masks.append([day+' '+prod,f"{x['aoi_pixel_centers']:,}",' / '.join(str(x['mask_counts'].get(str(k),0)) for k in [3,4,5,1]),f"{x['view_zenith_min_degrees']:.2f}–{x['view_zenith_max_degrees']:.2f}°",x['exact_geolocation_input_identity']])
    runs=v['performanceRuns'];median=lambda key:statistics.median(r[key] for r in runs)
    warm=[x['ms'] for r in runs for x in r['warm']]
    screenshot_rows=[['Width','Map height','Estimated unobscured viewport','Basemap','Actual rendered VIIRS centers'],['---']*5]
    for x in v['captures']:
        g=x['geometry'];screenshot_rows.append([x['width'],round(g['map']['height'],1),f"{100*g['unobscured_fraction_of_viewport']:.1f}%",g['basemap'],g['rendered_centers']])
    artifacts=['COHORT_CONTRACT.json','RESEARCH_ROWS.json','RESEARCH_FRP.csv','COMMON_SUPPORT_AUDIT.json','INDEPENDENT_VALIDATION.json','L2_DOWNLOAD_MANIFEST.json','L2_SUPPORT_AUDIT.json','L2_INDEPENDENT_VALIDATION.json']
    hashes=table([['Artifact','SHA-256'],['---','---']]+[[n,sha(R/n)] for n in artifacts])
    changed_code=['src/CanadaWorkspace.tsx','src/CanadaMap.tsx','src/bridge.ts','src/BridgeLab.tsx','src/bridge.css',
      *['science/'+s for s in ['phase6_contract.py','phase6_access.py','phase6_download.py','phase6_science.py','phase6_oracle.py','phase6_l2.py','phase6_l2_oracle.py','phase6_lineage.py','phase6_publish.py','phase6_memory.py','phase6_report.py','phase6-requirements.txt','test_phase6.py']],
      'scripts/setup-phase6-hdf4.py','scripts/verify-phase6.py','scripts/phase6-review.mjs','tests/phase6.spec.ts']
    code_list='\n'.join('- `'+n+'`' for n in changed_code)
    report=f'''# Phase6 scientific execution — bounded bridge experiment

Completed 14 November 2026, Africa/Cairo. **B1_GEOMETRY_ONLY. G4 = ADJUSTMENT_WITHHELD.** The original application and native scientific releases were extended in place. This is an executed geometry/timing and L2 observation-support rejection result, not calibrated continuity. The central MODIS–VIIRS harmonization objective remains incomplete.

Open [the measured bridge laboratory](http://127.0.0.1:5174/?region=canada&lab=1). Local authorization remains USER-ATTESTED; global-award eligibility is unresolved. No independent human science/G4 signoff is claimed.

## What actually advanced

- Read the entire supplied independent-audit/Phase6 directive and the actual Phase5 execution, Python/React/MapLibre code, protocols, release artifacts and tests.
- Corrected a material review misunderstanding: Phase5 “zero FRP retained” described **retaining zero-valued rows**, not erasing FRP. Original FRP, Type, confidence, scan/track and versions remain in the original archives and canonical raw store. Four original-member first-object probes were hash-linked back to that store. Full-member quality inventories are inherited independently verified evidence, not a new full-country recount.
- Froze the contract before bounded selection or new CMR discovery: raw-center AOI [-120,49,-110,55], SP only, development June1–3 and descriptive replication June8–10, 2022 UTC. June4–7 excluded. This avoids pooling across the observed2023 literal-code boundary. The existing national inventory was already visible; this is not a blind holdout experiment.
- Actually downloaded **10 NASA L2 files / 361,645,819 bytes**, including MYD14, VNP14 750m, VNP14IMG 375m and corresponding geolocation. Five real mask/QA arrays were decoded and independently re-read. Authentication is no longer a generic blocker.
- Executed B0→B1 at5/10/20km and15/30/60 minutes, class/confidence/FRP sensitivities, area clipping and a separate non-production oracle. Both native-record and actual-mask independent checks PASS.
- Integrated the frozen77-record cohort into the existing map, UTC calendar, pixel-center inspection and selection-exact scientific export. The full native releases remain available.

## Access result, exact products and processing lineage

Anonymous HEAD returned403; anonymous GET returned401 with an Earthdata Login credential challenge. Operator-authorized authenticated GET returned206 for range controls and200 for complete HDF payloads. The previous HEAD403 **did not establish product unavailability**. Per-attempt endpoint, response category and redacted headers: `phase6/ACCESS_AUDIT_ANONYMOUS.json`, `ACCESS_AUDIT.json`. No credential, account identifier or signed redirect URL was written into the repository.

The original range diagnostic compared eight received bytes to the four-byte HDF4 magic, incorrectly marking its HDF4 signature flag false. `RANGE_SIGNATURE_CORRECTION.json` links all four relevant range payload hashes to the exact acquired files' first eight bytes and confirms HDF4. Original request logs are retained; future probe code is fixed. Full-file size/SHA/HDF decoding already passed. Invalid token-header characters are rejected with a redacted message. The private local token copy was removed;892 project text artifacts were scanned with no credential occurrence. Local deletion does not revoke the token posted in chat; operator revocation remains external.

Selection was fixed before science payload inspection: first chronological Aqua granule on each frozen discovery day, closest nominal-start VIIRS within the frozen60-minute sensitivity range; matching same-platform acquisition keys for geolocation/375m. Primary2022-06-01: MYD14.A2022152.0850.061.2022152193155, VNP14.A2022152.0830.002.2023030092949 and VNP14IMG.A2022152.0830.002.2024076112654. Replication2022-06-08: MYD14.A2022159.0855.061.2022159153921 and VNP14.A2022159.0936.002.2023030105146. Exact paths, original URLs, bytes, collections and SHA-256s for all ten files: `phase6/L2_DOWNLOAD_MANIFEST.json`; frozen selection/scope: `L2_SELECTION.json`, `L2_DOWNLOAD_SCOPE.json`.

Both complete triplets would exceed the frozen512MB transfer cap. Before reading science payloads, the retrieval scope retained the full primary triplet and a750m-only replication pair. No cohort, view or timing threshold was relaxed. No reprocessed L2 sample is assumed to be the exact source of a FIRMS archive row.

MYD14 identifies collection061, processing version6.2.3. Primary VNP14 identifies collection002, algorithm1.6.1/PGE2.0.4. VNP14IMG identifies collection002, ProcessVersionNumber3.1.9, AlgorithmVersion3.1.6, PGE2.0.13 and production2024-03-16. These are distinct metadata concepts; none establishes the monthly FIRMS Type production vintage. The2022 FIRMS MODIS literal6.03 vs current L2 collection061 linkage is unresolved. The2023 transition to literal61.03 remains stratified, not silently “fixed” or treated as a proven algorithm-change effect.

Both acquired Aqua geolocation files are newer processing instances than the exact input names embedded in MYD14. VIIRS exact geolocation input names match. Authenticated probes of the *exact named Aqua inputs* through the documented LAADS path still returned401; application/provider authorization or access to that specific instance remains unresolved. This is **not** proof the old files do not exist. See `EXACT_GEO_INPUT_ACCESS.json`. Provider-specific access and input compatibility must be resolved before using those Aqua masks to release matched support.

## Native experiment and falsifiable result

{table(baseline)}

K is the distinct source/cell/UTC-date count, D/N combined by union. Zero reported Terra/Aqua records in a slice is a finite-catalog count, never a fire-free or observed-zero conclusion. One shared Aqua–VIIRS10km cell-day has a nearest same-native-flag acquisition offset of32 minutes. It fails15/30 minutes and produces a candidate only at60. The second slice has no shared positive key. The same timing rejection occurs at5/20km. These are **both-source reported positive keys**, not agreement, sensitivity, missed fires or matched exposure.

Independent re-selection started from the separate raw-archive oracle's whole-Canada date keys: {o['country_date_rows_examined']:,} rows examined,77 eligible centers selected. It re-hashed native fields, independently projected with ellipsoidal EPSG9820 equations and exhaustively compared timestamps rather than using production matching helpers. It checked all18 scale/time cases, all quality sensitivities and the raw research CSV. It does not constitute independent human review, and replication fire-episode independence is unproven.

All77 native FRP values are present and positive: Aqua36.8–38.9MW (2 records), VIIRS0.29–18.06MW (75). VIIRS confidence:71 nominal,2 high,2 low. Literal Types:58 Type0,17 Type2; Aqua2 Type0. Type0 means *presumed* vegetation, not confirmed wildfire. A diagnostic Type0 screen gives VIIRS39 records/23K in development and19/13 in replication. A confidence screen retains46/29 and27/16. No screen replaces the unchanged all-native baseline. A positive-FRP research screen happens to retain all77; nationally24,306 zero-FRP records remain retained. No missing FRP is substituted with zero and no FRP sum is presented as a physical fire count.

AOI membership uses actual raw centers, distinct from the older pilot cell-center policy. Densified projected AOI clipping has4,744 intersecting10km cells,322 partial boundary cells; summed clipped areas conserve projected AOI area to<1m². Independent analytic WGS84 meridian/parallel area is458,279.499953km²;64-segment projected approximation differs by9.49e-7 relative. These are mathematical study-area checks, **not observed, burned, clear-sky or fire-positive area**. Arbitrary interactive polygon qualification is not delivered.

## Actual masks: why this sample cannot support a bridge

{table(masks)}

Mask3 = water,4 = cloud,5 = non-fire land. Class1 is trim/unprocessed in750m, bowtie deletion in375m and obsolete/unprocessed in MODIS; native file legends are retained rather than conflated.

All primary June1 centers exceed even the50° sensitivity threshold. Thus the predeclared30°/40°/50° view rules admit **no primary shared support**, independently of later cloud/QA/footprint decisions. Replication nominal start offset is41 minutes, outside the primary30-minute window; Aqua has no center≤40°. At50°,3,640 Aqua centers pass the view screen,3,581 of them mask-class land/fire, but those are not qualified shared opportunities. The41-minute condition, exact input-instance mismatch, source-specific QA and shared footprint tests still apply.

Each sampled AOI has zero mask fire-class7–9 centers at these particular passes. This does **not** make the AOI/day fire-free: only selected swaths were acquired, masks/clouds limit support, and the native77-record cohort covers additional passes/dates. No exposure-normalized rate, valid shared non-detection calendar, accuracy, CI or calibration coefficient is identifiable. `qualified_observation_denominator` is null, not zero.

VNP14IMG input-quality bits0–6 and residual-bowtie bit22 were decoded using the exact375mC2 guide; geolocation flags and packed view-angle scale were read from actual files. Raw MODIS/750m QA words and native mask legends are retained. Their exact source-specific algorithm-QA policy has **not** been qualified; the375m bits were not transplanted into them. Pixel centers/grid intersections are not oriented sensor footprints. No swath geometry was used as cloud-free exposure. Full per-cell mask multiplicities, QA word counts, example indices and metadata are in `L2_SUPPORT_AUDIT.json`; independent re-read/projection acceptance is `L2_INDEPENDENT_VALIDATION.json` ({lo['elapsed_seconds']:.2f}s).

|Stage|Actual decision|
|---|---|
|B0 native baseline|PASS; original native releases unchanged|
|B1 geometry/time|Executed, independently reproduced; classified B1_GEOMETRY_ONLY|
|B2 750m hypothesis|Actual files decoded; frozen support eligibility fails, hypothesis scientifically INCONCLUSIVE|
|B3 FRP correction|Not fitted; no qualified comparable footprint/QA/FRP sample|
|B4 harmonized calendar|Not released; G4 ADJUSTMENT_WITHHELD|

This rejects the frozen sample's eligibility, not the general NASA750m continuity hypothesis. Original Portugal/California and Canada2024 holdouts were not evaluated. No scalar count conversion, imputed history, anomaly score or latent-fire estimate was produced.

## Scientific sources and applicability

- [NASA FireESDR](https://viirsland.gsfc.nasa.gov/Products/NASA/FireESDR.html):750m and375m algorithms are independent; MODIS heritage motivates testing750m but does not prove numeric interchangeability.
- [NASA VIIRS375mC2 guide v1.2](https://ladsweb.modaps.eosdis.nasa.gov/archive/Document%20Archive/Science%20Data%20Product%20Documentation/VIIRS_C2_AF-375m_User_Guide_1.2.pdf), tables1–3/§3.1.3/§6.1: exact mask/QA definitions; hybrid M13 FRP; zero FRP possible; monthly Type production issue. Row literal2 is not monthly production version2 or proof of version3 correction.
- [FIRMS MODIS fields](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html), [VIIRS fields](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html), [archive README](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt):native centers/UTC, source-specific confidence, MW FRP and SP/NRT distinctions; delivered request labels are not processing-lineage certificates.
- [Official LAADS token workflow](https://ladsweb.modaps.eosdis.nasa.gov/learn/download-files-using-edl-tokens/), [Earthdata application/cookie workflow](https://urs.earthdata.nasa.gov/documentation/for_users/data_access/curl_and_wget): authenticated GET with appropriate provider authorization. Actual response controls above resolve the previous anonymous-HEAD inference.
- [Li et al.2018](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2017JD027823) evaluates FRP/view-scale behavior, including a NOAA750m product; it is not automatic validation of this NASA375m extract.
- [Zheng et al.2026](https://www.mdpi.com/2072-4292/18/10/1650), §3.1:positive valid FRP, source-specific bowtie/duplication tests, actual variable MODIS footprints,≤5-minute matching and cloud-area geometry precede correction. Native minute timestamps cannot implement its8-second duplicate criterion. No paper coefficient, random90/10 pixel split or FRP factor was reused for cell-day counts.
- [Sofiev & Kouznetsov2026](https://gmd.copernicus.org/articles/19/10123/2026/):FRP observation operators require pixel geometry and missing/cloud/glint/non-fire states; no universal hotspot-count coefficient follows.

The challenge URL returned502 during this run; no current legal/eligibility conclusion follows. Archived original protocol requirements remain binding. Relevant2024/2025 product guides are explicitly dated, not represented as2026 NASA endorsement.

## Implemented interaction and exact code changes

The existing Canada adapter now opens a compact Native/Common geometry/Matched observation laboratory; calibration remains disabled. Hash-bound independent acceptance is required before the experiment can be activated. “Inspect frozen pilot” binds the same source/DN/cell/day selection to map, calendar and CSV. Non-study dates are disabled; missing support remains unknown. Close-zoom source-colored pixel centers carry actual UTC, D/N and MW FRP; selected-cell text lists native Type/confidence. The experimental square is a faint grid cell with an outline, not a fire perimeter. Returning to the full native month removes the research scope. The CSV carries experiment ID, contract/raw-row hashes and raw-center AOI/date membership; the separately linked77-row FRP CSV is explicitly the full frozen cohort, not the current filtered selection.

{code_list}

Only two inherited application modules changed; all original scientific code/tests, `src/canada.ts`, Portugal modules, source archives, native/oracle databases, release catalogs, native artifacts and G4/protocol records are protected. Updated ancillary files: `README.md`, `reports/AI_DISCLOSURE.json`, `reports/SOURCE_AND_COMPLIANCE_LEDGER.md`, `reports/VALIDATION_LOG.md`; generated `reports/browser-test-results.json`, `dist` and test evidence refresh. No dependency or architecture replacement; optional scientific research packages are separately pinned. `phase6/PRESERVATION.json` provides exact changed/new paths and SHA-256s, including all public research assets. Snapshot:808 entries, `data/backups/phase6-before.zip`, SHA25644f610d1c85b1c15531ccd473627afa34832e9335d6af70a3bb926933ff7af52.

Current research artifact **{p['id']}**,89,336 uncompressed bytes, SHA256 `{p['sha256']}`. This is separate from unchanged Portugal `eg-9a6ad9ccfda103bf80926db6` and Canada `ca-92a935da01aecfa3e1d130b3`. Earlier hash-sealed research snapshots are retained, not overwritten. Runtime/receipt timing may differ on reproduction; scientific cohort, masks/counts and frozen thresholds must reconcile.

## Executed tests, rendered review and performance

**33/33 Python tests PASS. 89/89 full browser/contract cases PASS**,{full['duration']/1000:.2f}s, no skips/flaky/unexpected/retries. Final17/17 Canada/bridge follow-up PASS,{follow['duration']/1000:.2f}s, after selected-cell visual refinement and stronger raw-center/DN/cell/export checks. TypeScript/Vite production build PASS; the existing large MapLibre chunk warning remains. All83 inherited browser cases and27 inherited science tests retain their source bytes. Raw logs/JSON are in `phase6/`.

Final CSV follow-up6/6 PASS,{export_follow['duration']/1000:.2f}s: every experimental row, including a source with no selected positive record, carries explicit OBSERVATION_UNKNOWN and input archive/member hashes. The wrapper does not mistake whole-month source availability for the bounded cohort's observation support. Python33/33 also passes after the token-format guard.

Failures corrected: Windows pyhdf wheel lacked HDF4 DLLs (isolated Anaconda runtime, hash-verified, no system edits); empty HDF4 sparse arrays required explicit zero-length handling; independent angle checks exposed float32 scale-factor rounding (decode documented0.01° unit); the first new browser expectation mistakenly assumed31-day June (corrected to30, with six eligible dates). No scientific gate or original assertion was weakened. Raw first-run log/results remain retained. The late memory-replay equality initially compared integer dictionary keys to JSON string keys; serialization normalization fixed that diagnostic without changing measured data.

Actual screenshots were opened and inspected at1440×900,390×900,320×900: `screenshots/phase6-matched-support-{{width}}.png` and `phase6-pilot-cell-{{width}}.png`. Prior selected-fill captures are retained in `screenshots/phase6-before-selection-focus/`. Every final view has three rendered VIIRS centers in the independently reconciled selected cell, no body overflow/page errors. Keyboard method switching, Escape, mobile dialog and corrupt-result rejection pass. This is emulation, not hardware/WCAG certification.

{table(screenshot_rows)}

Unobscured estimates subtract visible DOM control/answer/legend intersections, not merely count canvas height. The70% unobscured desktop objective is **not met**, and open mobile evidence overlays materially cover the map. These measured limits remain; this phase prioritized science rather than a redesign. Coarse Natural Earth1:50m fallback is explicitly labeled, never observation QA or detailed geography.

Three fresh1440×900 Chromium SwiftShader contexts, same Windows workstation, sequential after tests: median research-result readiness **{median('resultReadyMs'):.0f}ms**, binding to pilot source data **{median('bindMs'):.0f}ms**, geography/native readiness **{median('nativePaintMs'):.0f}ms**. Warm D/N/ALL point-source update median **{statistics.median(warm):.0f}ms**, observed range{min(warm)}–{max(warm)}ms; these are source-update readiness, not a GPU frame-rate guarantee. Median page heap snapshot **{median('heap_snapshot_bytes')/1e6:.2f}MB**, excluding worker/GPU memory and not a peak. The additional research pointer+bundle encoded transfer is18,454B in the initial measured compressed responses; raw bundle89,336B. Network/provider fallback varies; this77-record cohort is a different workload from the Phase5 country-month atlas, so no direct speedup claim. Final measurements: `VISUAL_AND_PERFORMANCE.json` (initial values before the fill refinement retained separately).

Five-mask warm local replay **{m['elapsed_seconds']:.2f}s**, OS-reported Python peak working set **{m['peak_working_set_bytes']/1e6:.2f}MB**; identical scientific results, no result-artifact rewrite. Independent L2 recount {lo['elapsed_seconds']:.2f}s. These are local processing measurements, not acquisition latency or total machine/GPU memory.

## Reproduce without restarting the project

Use the existing venv. `phase6_contract.py` fails if the frozen contract is changed. Research sequence: `phase6_science.py` → `phase6_l2.py` → `phase6_oracle.py` → `phase6_l2_oracle.py` → `phase6_publish.py`. The actual L2 files/receipts must exist before decoding. Optional setup: `python -m pip install -r science/phase6-requirements.txt`, then `python scripts/setup-phase6-hdf4.py` on Windows. Authorized acquisition uses `phase6_access.py --token-file PRIVATE_PATH`, `phase6_download.py --token-file PRIVATE_PATH` and `phase6_lineage.py --token-file PRIVATE_PATH`; secrets stay outside the project and are never printed. Download files are verified/resumed from receipts, not overwritten. The budget/scope and contract remain frozen. No full-country re-ingestion is needed.

Run the existing scientific test discovery, `npm.cmd run build`, `npx.cmd playwright test`. After build/test completion, `node scripts/phase6-review.mjs`; replay memory with `phase6_memory.py`; then `scripts/verify-phase6.py` and `phase6_report.py`. Publication is a separate research namespace; original release gates remain unchanged. No external deployment/submission was performed.

## Judge demonstration (60–90 seconds)

1. Open the bridge laboratory; choose **Native**. Explain2 Aqua /75 VIIRS records on six frozen dates. These are reported pixels, not physical-fire counts; original historical source lanes remain accessible.
2. Choose **Common geometry**. One shared10km cell-day becomes zero candidates at30 minutes; only60 minutes retains a candidate. Show independent5/10/20km checks and unchanged baseline.
3. Choose **Matched observation**. Show ten actual NASA files and measured view-angle rejection, plus41-minute replication offset. Explain that authentication was solved, while this sample still cannot qualify the denominator.750m heritage remains an inconclusive hypothesis.
4. **Inspect frozen pilot on map**; select cell `ca-laea60n100w-wgs84-o0-v1:10000:-102:-73` through Area & period. Aqua2 records/1K and VIIRS3/1K reconcile; the source lens shows three actual VIIRS centers. Show UTC/DN, export the exact selection, then return to full native history.

**Next scientific milestone:** freeze a new, metadata/geometry-driven selection across candidate passes before looking at fire outcomes; obtain a genuinely near-nadir,≤30-minute Aqua/VIIRS pair with exact compatible geolocation instances, source-specific QA definitions and independently checked shared pixel footprints. Reproduce it in a separate development slice. Only then can a750m/FRP candidate be tested against the unchanged baseline. Do not repurpose the rejected sample, widen rules after outcomes, open original holdouts, or call an unsigned result harmonized.

## Key artifact receipts

{hashes}
'''
    (ROOT/'reports/PHASE6_SCIENCE_EXECUTION.md').write_text(report,encoding='utf-8')
    (R/'MATCHED_OBSERVATION_AUDIT.md').write_text('# Executed matched-observation audit\n\nClassification: B1_GEOMETRY_ONLY; G4 withheld.\n\n'+table(masks)+'\n\nPrimary view rejection holds at30/40/50deg; replication nominal41min fails30min and Aqua fails40deg. Actual QA/mask arrays are retained, but exact Aqua geo instance, MODIS/750m QA definitions and shared footprints remain unqualified. No shared opportunity denominator or valid shared negative is emitted. No750m/FRP calibration is identifiable. Full methods, receipts, independent tests and judge demonstration: `../PHASE6_SCIENCE_EXECUTION.md`.\n',encoding='utf-8')
    print(json.dumps({'report':'reports/PHASE6_SCIENCE_EXECUTION.md','words':len(report.split()),'classification':a['classification']}))

if __name__=='__main__':run()
