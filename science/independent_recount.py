"""Independent raw CSV + ellipsoidal LAEA recount, without importing production code.

Projection uses the EPSG 9820 authalic-latitude equations, evaluated with math;
production uses PROJ via pyproj. CSV parsing and UTC conversion are separate.
"""
import argparse
import calendar
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def ellipsoidal_laea(longitude, latitude):
    a = 6378137.0
    flattening = 1 / 298.257223563
    e2 = 2 * flattening - flattening**2
    e = math.sqrt(e2)
    def q(phi):
        s = math.sin(phi)
        return (1 - e2) * (s / (1 - e2 * s*s) - math.log((1-e*s)/(1+e*s)) / (2*e))
    qp = q(math.pi / 2)
    phi0, phi = math.radians(40.05), math.radians(latitude)
    beta0, beta = math.asin(q(phi0) / qp), math.asin(q(phi) / qp)
    rq = a * math.sqrt(qp / 2)
    m0 = math.cos(phi0) / math.sqrt(1 - e2 * math.sin(phi0)**2)
    scale = a * m0 / (rq * math.cos(beta0))
    delta = math.radians(longitude + 7.95)
    b = rq * math.sqrt(2 / (1 + math.sin(beta0)*math.sin(beta) + math.cos(beta0)*math.cos(beta)*math.cos(delta)))
    return (b * scale * math.cos(beta) * math.sin(delta),
            b / scale * (math.cos(beta0)*math.sin(beta) - math.sin(beta0)*math.cos(beta)*math.cos(delta)))


def recount(input_dir, release_path, report_dir):
    release = json.loads(release_path.read_text(encoding="utf-8"))
    observed, expected_records, seen = collections.Counter(), {}, set()
    max_projection_bound_distance = math.inf
    input_hashes = []
    for zip_name, csv_name in [("DL_FIRE_M-C61_844805.zip", "fire_archive_M-C61_844805.csv"), ("DL_FIRE_SV-C2_844806.zip", "fire_archive_SV-C2_844806.csv")]:
        zipped = (input_dir / zip_name).read_bytes()
        with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
            content = archive.read(csv_name)
        input_hashes.append((hashlib.sha256(zipped).hexdigest(), hashlib.sha256(content).hexdigest()))
        reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""))
        header = next(reader)
        positions = {name: i for i, name in enumerate(header)}
        request = "844805" if "M-C61" in zip_name else "844806"
        for row_number, fields in enumerate(reader, 2):
            assert len(fields) == 15, (zip_name, row_number, "ragged row")
            if (zip_name, tuple(fields)) in seen:
                continue
            seen.add((zip_name, tuple(fields)))
            value = lambda name: fields[positions[name]]
            longitude, latitude = float(value("longitude")), float(value("latitude"))
            assert all(math.isfinite(float(value(k))) for k in ["latitude", "longitude", "frp", "scan", "track", "brightness", "bright_t31"])
            assert -180 <= longitude <= 180 and -90 <= latitude <= 90
            assert float(value("frp")) >= 0 and float(value("scan")) > 0 and float(value("track")) > 0
            assert float(value("brightness")) > 0 and float(value("bright_t31")) > 0
            if not (-8.7 <= longitude <= -7.2 and 39.3 <= latitude <= 40.8):
                continue
            year, month, day = map(int, value("acq_date").split("-"))
            assert 1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]
            original_time = value("acq_time")
            assert original_time.isdigit() and 1 <= len(original_time) <= 4
            minutes_value = int(original_time)
            hour, minute = divmod(minutes_value, 100)
            assert hour < 24 and minute < 60
            utc = f"{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:00Z"
            platform = value("satellite")
            source = {"Aqua": "AQUA_MODIS", "Terra": "TERRA_MODIS", "SNPP": "SNPP_VIIRS"}[platform]
            assert value("daynight") in ("D", "N") and value("type") in ("0", "1", "2", "3")
            if source == "SNPP_VIIRS":
                assert value("confidence") in ("l", "n", "h") and value("instrument") in ("VIIRS", "SNPP")
            else:
                assert 0 <= float(value("confidence")) <= 100 and value("instrument") == "MODIS"
            x, y = ellipsoidal_laea(longitude, latitude)
            cell = f"g:{math.floor(x/10000)}:{math.floor(y/10000)}"
            max_projection_bound_distance = min(max_projection_bound_distance, abs(x - round(x/10000)*10000), abs(y - round(y/10000)*10000))
            observed[(source, value("acq_date"), cell)] += 1
            expected_records[f"{request}:{row_number}"] = (source, utc, cell, longitude, latitude, value("confidence"), value("version"),
                float(value("frp")), value("daynight"), value("type"), float(value("scan")), float(value("track")),
                float(value("brightness")), float(value("bright_t31")), value("instrument"), value("satellite"))
    assert input_hashes == [(m["zip_sha256"], m["csv_sha256"]) for m in release["manifests"]], "input hash mismatch"
    actual_records = {r["id"]: (r["source"], r["utc"], r["cell"], r["longitude"], r["latitude"], r["confidence"], r["version"],
        r["frp"], r["daynight"], r["type"], r["scan"], r["track"], r["brightness"], r["brightness2"], r["nativeInstrument"], r["nativeSatellite"]) for r in release["records"]}
    assert actual_records == expected_records, "normalized row identity/UTC/coordinate/cell mismatch"
    actual_keys = collections.Counter((r["source"], r["day"], r["cell"]) for r in release["records"])
    assert observed == actual_keys, "occupied key set or multiplicity mismatch"
    with (report_dir / "NATIVE_OCCUPIED_CELL_DAYS.csv").open(encoding="utf-8", newline="") as f:
        exported = list(csv.DictReader(f))
    export_keys = {(r["source"], r["utc_day"], r["cell_id"]): int(r["detection_records"]) for r in exported}
    assert export_keys == dict(observed) and len(exported) == len(observed), "CSV export mismatch"
    assert all(r["release_id"] == release["releaseId"] for r in exported)
    key_digest = hashlib.sha256(json.dumps(sorted(observed), separators=(",", ":")).encode()).hexdigest()
    assert key_digest == release["verification"]["occupied_key_sha256"]
    totals = {}
    for source in ("AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS"):
        keys = [key for key in observed if key[0] == source]
        totals[source] = {"records": sum(observed[k] for k in keys), "occupied_cell_days": len(keys),
            "detection_days": len({k[1] for k in keys}), "occupied_cells": len({k[2] for k in keys})}
    assert totals == release["summary"], "source summary mismatch"
    # Only this verifier can promote an artifact; it changes no raw data or gate.
    release["verification"].update({"state": "PASS", "method": "independent CSV reader, UTC parser and ellipsoidal LAEA equations",
        "oracle_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "min_observed_grid_edge_distance_m": max_projection_bound_distance,
        "independent_human_review": "NOT_PERFORMED", "g4": "ADJUSTMENT_WITHHELD"})
    verified_bytes = json.dumps(release, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    release_path.write_bytes(verified_bytes)
    versioned = release_path.with_name(release["releaseId"] + ".json")
    if versioned.exists() and versioned.read_bytes() != verified_bytes:
        raise AssertionError("immutable release name already has different bytes")
    versioned.write_bytes(verified_bytes)
    release_path.with_name("catalog.json").write_text(json.dumps({"releaseId": release["releaseId"], "file": versioned.name,
        "sha256": hashlib.sha256(verified_bytes).hexdigest()}, sort_keys=True), encoding="utf-8")
    report = ["# Independent diagnostic recount", "", f"Release `{release['releaseId']}`: **PASS numerical reconciliation**.", "",
        "The oracle uses a separate CSV reader, manual UTC conversion and WGS84 ellipsoidal LAEA equations; it does not import the production pipeline or pyproj. Input hashes, every accepted row identity, timestamp, point, cell/day key, multiplicity, summary and reopened scientific CSV reconcile exactly.",
        "", f"Minimum source point distance to a 10-km projected bin edge: {max_projection_bound_distance:.6f} m. Units: reported detections / occupied cell-days / AOI detection days.",
        "", "```json", json.dumps(totals, indent=2), "```", "",
        "This is software-independent recomputation, not an independent human review or physical fire validation. The case is INTEGRATION_DIAGNOSTIC_2017. Complete-month M1b qualification, observation support and G4 have NOT passed. Adjustments are withheld."]
    (report_dir / "M1B_INDEPENDENT_RECOUNT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"independent_recount": "PASS", "release": release["releaseId"], "totals": totals}, indent=2))
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--release", type=Path, default=ROOT / "public" / "data" / "release.json")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    recount(args.input_dir, args.release, args.reports_dir)
