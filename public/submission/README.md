# Insider Lens — historical evidence that survives a sensor switch

Team Insider Lens · NASA Space Apps 2026 submission text draft · 14 November 2026.

## Problem and demonstrated solution

Changing from MODIS to VIIRS can discard acquired historical thermal evidence or
create misleading comparisons between instruments with different responses.
Insider Lens preserves source identity and shows exactly which positive records,
fixed spatial cells and UTC dates survive each source-selection policy. It solves
evidence retention and auditability; calibrated MODIS–VIIRS continuity is unresolved.

[Open the Evidence Retention map](/?region=canada&view=retention).
The browser uses public hash-bound scientific artifacts. No Earthdata login,
private archive, API token or local Python service is required for the demo.

## Reproducible Canada case

Southern study tract: 120–110°W, 49–55°N, June 2023, Standard Processing, all native
Day/Night flags. Membership uses centers of the existing 10 km WGS84 ellipsoidal
Lambert azimuthal equal-area grid, centered 60°N, 100°W, origin 0 m. West/south
edges are included; east/north excluded. This is a research box within the acquired
Canada extract, not an independently reconstructed country boundary.

| Retained sources | Source records | Unique positive cell-days | Positive UTC dates |
|---|---:|---:|---:|
| Aqua + Terra MODIS | 2,139 | 233 | 24 |
| S-NPP VIIRS | 8,385 | 534 | 27 |
| Both native families | 10,524 | 568 | 28 |

The exact disjoint key partition is **34 MODIS-only + 199 shared + 335 VIIRS-only
= 568**. Aqua contributes 990 records / 178 source-specific keys; Terra 1,149 / 155.
MODIS keys use an Aqua/Terra union, never an addition of overlapping keys.
All 12 independent rectangle / month / Day/Night cases were compared by exact key
and source multiplicity against the original-archive oracle index.

June 2010, full acquired Canada extract: selecting VIIRS alone excludes **12,744
MODIS records and 30 positive dates**. The S-NPP FIRMS era begins 20 January 2012.
Earlier VIIRS evidence is unavailable, not observed zero.

## Judge demonstration — about 55 seconds

1. **0–12 s:** Open the map. Identify orange squares, purple diamonds and teal
   triangles: positive cell-day groups, not physical fires. A month can contain
   different groups in the same fixed cell.
2. **12–25 s:** Switch MODIS only / VIIRS only / both. Show 2,139 / 8,385 / 10,524
   retained source records and 24 / 27 / 28 dates. On mobile open “Cells, dates &
   evidence” for source policies and the three-part journey.
3. **25–37 s:** Select a map cell, inspect its actual UTC dates and separate Aqua,
   Terra and S-NPP counts. Select a calendar date or Day/Night acquisition flag;
   export the exact same selection, including all reference keys and policy flags.
4. **37–47 s:** Select Before VIIRS. Show 12,744 acquired MODIS records excluded by
   VIIRS-only selection. The earlier VIIRS lane has no operational era.
5. **47–55 s:** Show Scientific limit: overlap is not simultaneous common support;
   no missed-fire count, calibrated trend or anomaly is claimed. G4 stays withheld.

## Scientific boundaries

Positive FIRMS detections alone cannot establish complete/cloud-free observation
opportunity, valid negative observations, fire-free dates, physical wildfire counts,
sensor-normalized trends, anomaly significance or equal detection sensitivity.
Shared keys mean same fixed cell and UTC date, not matched overpasses. Exclusive
keys are not confirmed missed fires. Drawing/panning outside the acquired extract
does not create worldwide scientific coverage. Rectangle membership never changes
to raw-point membership. SP and NRT remain separate; Aqua/Terra stay identifiable.

MODIS literal SP version code changes from 6.03 in 2022 to 61.03 in 2023; upstream
lineage remains unresolved. VIIRS row version 2 is not a monthly production-vintage
certificate. Type was not used as a vegetation-fire filter; all valid native
confidence classes and zero-FRP detections are retained by the native contract.

The supplementary 16-candidate L2 experiment remains UNKNOWN_SUPPORT. Exact
geolocation equivalence and nominal pixel centers do not qualify common physical
response or registration bounds. No correction, model fitting or new holdout
evaluation was performed for Evidence Retention. Original G4 conditions are intact.

## Architecture and reproduction

Existing React / TypeScript / Vite / MapLibre application; immutable versioned
Python artifacts, independent original-data parser/projection oracle and
SHA-256-checked browser loading. The map is a view of accepted scientific data;
the UTC calendar, selected-cell evidence and CSV use the same committed scope.

From the existing repository with its preserved source archives and accepted
native releases: install the pinned Python environment and `npm ci`, then run:

```text
.venv\Scripts\python.exe science/phase12_partition.py
.venv\Scripts\python.exe science/phase12_oracle.py
.venv\Scripts\python.exe -m unittest discover -s science -p test*.py -v
npm.cmd run build
npx.cmd playwright test
```

Run scientific replays separately from browser/GPU load on constrained machines.
The source index binds original ZIP and member hashes; never replace original
bytes or silently regenerate historical scientific releases.

[Exact partition](/data/phase12/PARTITION.json) ·
[Independent acceptance](/data/phase12/INDEPENDENT_PARTITION.json) ·
[Frozen scope and interpretation](/data/phase12/PARTITION_CONTRACT.json) ·
[AI-use disclosure](/submission/AI_DISCLOSURE.json) ·
[Software license inventory](/submission/THIRD_PARTY_SOFTWARE.json) ·
[Data attribution and rules status](/submission/SOURCES_AND_RULES.md).

This is a team-built research demonstration, not NASA endorsement, an operational
fire-warning system, an official submission receipt or proof of award eligibility.

Historical internal codename: EmberGuard. Original source IDs, scientific contracts and release hashes retain that name for reproducibility.

Public source repository: [Insider Lens on GitHub](https://github.com/bavlybibo/Insider-Lens). Public software reproduction is documented in its README and docs/REPRODUCIBILITY.md; the complete historical raw/L2 audit requires external original inputs.
