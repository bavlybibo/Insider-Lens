# Insider Lens — copy-ready NASA submission

Project: **Insider Lens**. Team: **Insider Lens**. Historical internal codename: EmberGuard.
Challenge: **Harmonization of MODIS and VIIRS Hot Spots**, NASA Space Apps Challenge 2026.
Repository: https://github.com/bavlybibo/Insider-Lens
Live application: https://emberguard-evidence-retention.musicalartichoke4.chatgpt.site/?region=canada&view=retention

## Short summary

Insider Lens makes historical fire evidence auditable across a satellite transition. Explore real NASA FIRMS observations on a geographic map, inspect UTC dates and original source identities, and export exactly which evidence is retained under MODIS-only, VIIRS-only or both-native policies. Calibrated harmonization remains withheld.

## Current release and demo status

The GitHub release includes new desktop query-derived scope, scientific finding and copy controls. The linked live app remains the previous independently verified deployment; this release audit does not authorize redeployment. Both use the same preserved scientific artifacts.

## Problem and challenge alignment

MODIS provides historical evidence predating S-NPP VIIRS. Different spatial responses, acquisition schedules and processing lineages make raw detection ratios scientifically unsafe. We address the continuity challenge by preserving native evidence, quantifying selection consequences and exposing the qualified-support requirements that must precede any correction.

## Scientific method

Read-only, hash-bound original archives feed a reproducible Python pipeline. A separate parser/projection/counting oracle checks native quantities. Source, SP/NRT and NASA Day/Night flags remain separate. We partition positive keys on a fixed 10 km WGS84 ellipsoidal equal-area grid and UTC day. The Southern Canada June2023 development tract yields 34 MODIS-only, 199 shared and 335 VIIRS-only keys: 568 unique positive cell-days, independently reconciled. Shared keys are not matched simultaneous clear-sky observations; exclusive keys are not confirmed missed fires.

## Original contribution and impact

An interactive Evidence Retention map ties source-policy decisions to exact cells, dates, retained/excluded source records and provenance-bearing exports. Users can demonstrate evidence lost by discarding older history without inventing unavailable observations. The before-VIIRS example retains 12,744 acquired MODIS records in June2010. This supports transparent research and responsible interpretation; it is not an operational fire-warning product.

## Architecture

React, TypeScript and Vite; MapLibre geography; static SHA-256-verified scientific artifacts; Python/PROJ native processing; independent analytical projection and original-data recounts. Map, UTC calendar, selected evidence and CSV share one committed selection. The application also includes Explore, Compare, History, Memory Loss, Heat Atlas and a bounded Scientific Bridge laboratory.

## NASA data and external acknowledgments

NASA FIRMS / University of Maryland MODIS Collection6.1 and S-NPP VIIRS375m Collection2 archive deliveries (requests844805/844806 and845605/845606), with original hashes, collection labels and native processing versions preserved. Supplementary L2 experiments use cited NASA fire mask/QA/geolocation products; they have not qualified common support. Natural Earth supplies public-domain coarse geography; OpenFreeMap, OpenMapTiles and OpenStreetMap supply credited detailed context. NRCan agency-fire context is supplementary narrative, not hotspot truth or a redistributed perimeter product. Source-specific citations, licenses and limits are in the repository's public/submission notices.

## Limitations and validation

G4 remains **ADJUSTMENT_WITHHELD**. No calibrated sensor conversion, normalized trend, seasonal anomaly, physical-fire count, complete observation denominator or validated missed-fire estimate is claimed. Processing-vintage and upstream homogeneity uncertainties remain. The original full workspace scientific suite and browser suite were rerun after branding; exact results and clean-clone scope are reported in reports/FINAL_INSIDER_LENS_RELEASE_AUDIT.md; the earlier branding/publication run remains separately archived. Portable clone checks do not independently reparse all raw records; full research replay requires separately acquired source archives, L2 inputs and historical receipts.

## AI disclosure

OpenAI Codex assisted software, separate oracle implementations, research, interface/submission text and automated testing. Original NASA observations were acquired, not AI-generated. Separate software recounts within one AI-assisted workflow do not replace independent human scientific review. No generated NASA branding or synthetic observation imagery is used. See public/submission/AI_DISCLOSURE.json.

## Target ≤30-second demo script (rehearse before recording)

“Before VIIRS, MODIS preserves history. Insider Lens keeps that evidence visible. In June 2023 Southern Canada, switch native sources: 34 MODIS-only, 199 shared and 335 VIIRS-only positive cell-days. Select a cell, inspect UTC dates, and export the exact evidence. These are reported-positive keys, not fires or matched observation opportunities. We preserve history and withhold unvalidated calibration.”

Show Before VIIRS → overlap cohort → source policies → exact cell/date/export → Scientific limit. This is a proposed short script, not an uploaded/recorded video or a certified current media limit.

## Official submission status — operator action required

No NASA form has been submitted or account edited. [GO Team submission clarification](https://github.com/nasa/spaceapps/discussions/1916) confirms Team page → Project tab → Edit and **15 November 2026 23:59 in the Team Owner's local-event timezone**. Cairo corresponds to 21:59 UTC if that is the registered owner event. Actual team-account/event assignment and local pitch cutoff remain uninspected.

The [central current guide](https://www.spaceappschallenge.org/resources/project-submission-guide) again returned HTTP502 on14November2026; current media/field limits remain unverified. Official2026 local-event pages mention a 30-second video or 7-slide presentation, but that is not a verified global-form limit. Do not rely on stale staging/previous-year guidance. [GO Team source/AI guidance](https://github.com/nasa/spaceapps/discussions/1849) and [2026 terms](https://www.spaceappschallenge.org/legal/) must be checked against the live form; match at least one used NASA source to the selected challenge Resources.

Before submitting, the operator must confirm team ownership and an appropriate original-content OSI license/default, selected challenge/source match, AI disclosure, final media/link visibility and human scientific review. Local early-start permission remains USER-ATTESTED; written global exception/reuse scope is unresolved. Publication does not certify Global Awards eligibility. The team makes the final official submission.
