"""Reproducible native thermal-detection audit. Never fits a harmonization model."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re
import stat
import zipfile

from pyproj import CRS, Transformer, __version__ as pyproj_version, proj_version_str

ROOT = Path(__file__).resolve().parents[1]
BBOX = [-8.7, 39.3, -7.2, 40.8]
CRS_TEXT = "+proj=laea +lat_0=40.05 +lon_0=-7.95 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs +type=crs"
CELL_M = 10_000
METHOD = "native-occupancy-v1.0.0"
FIELDS = "latitude longitude brightness scan track acq_date acq_time satellite instrument confidence version bright_t31 frp daynight type".split()
INPUTS = [
    ("DL_FIRE_M-C61_844805.zip", "fire_archive_M-C61_844805.csv", "844805", "MODIS"),
    ("DL_FIRE_SV-C2_844806.zip", "fire_archive_SV-C2_844806.csv", "844806", "VIIRS"),
]
SOURCE_INFO = {
    "AQUA_MODIS": {"name": "Aqua MODIS", "color": "#c45b2b", "archive": "MODIS C6.1 delivery family", "platform": "Aqua"},
    "TERRA_MODIS": {"name": "Terra MODIS", "color": "#8b6db1", "archive": "MODIS C6.1 delivery family", "platform": "Terra"},
    "SNPP_VIIRS": {"name": "S-NPP VIIRS", "color": "#087f8c", "archive": "VIIRS S-NPP Collection 2 delivery family", "platform": "S-NPP"},
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def utc_time(date: str, time: str) -> str:
    if not re.fullmatch(r"\d{1,4}", time):
        raise ValueError("acq_time must be one to four digits, interpreted as zero-padded HHMM")
    hhmm = time.zfill(4)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("acq_date must be YYYY-MM-DD")
    parsed = dt.date.fromisoformat(date)
    hour, minute = int(hhmm[:2]), int(hhmm[2:])
    if hour > 23 or minute > 59:
        raise ValueError("invalid UTC clock time")
    return f"{parsed.isoformat()}T{hour:02}:{minute:02}:00Z"


def source_id(row: dict, family: str) -> str:
    satellite = row["satellite"].strip().upper()
    if family == "MODIS" and satellite in ("A", "AQUA") and row["instrument"].upper() == "MODIS":
        return "AQUA_MODIS"
    if family == "MODIS" and satellite in ("T", "TERRA") and row["instrument"].upper() == "MODIS":
        return "TERRA_MODIS"
    if family == "VIIRS" and satellite in ("N", "SNPP", "S-NPP") and row["instrument"].upper() in ("VIIRS", "SNPP"):
        return "SNPP_VIIRS"
    raise ValueError("unexpected satellite/instrument for archive family")


def numeric(row: dict, name: str) -> float:
    value = float(row[name])
    if not math.isfinite(value):
        raise ValueError(f"nonfinite {name}")
    return value


def cell_key(x: float, y: float) -> str:
    return f"g:{math.floor(x / CELL_M)}:{math.floor(y / CELL_M)}"


def in_aoi(lon: float, lat: float) -> bool:
    return BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]


def read_archive(path: Path, csv_name: str) -> tuple[bytes, bytes, list[dict], list[dict]]:
    raw = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if len(members) > 10 or sum(m.file_size for m in members) > 20_000_000:
            raise ValueError("unexpected archive size")
        names = set()
        for member in members:
            p = Path(member.filename.replace("\\", "/"))
            if p.is_absolute() or ".." in p.parts or ":" in member.filename or member.flag_bits & 1 or stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("unsafe ZIP member")
            if member.filename in names:
                raise ValueError("duplicate ZIP member")
            names.add(member.filename)
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP CRC failure: {bad}")
        if names != {csv_name, "Readme.txt"}:
            raise ValueError("unexpected archive membership")
        data = archive.read(csv_name)
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
        if reader.fieldnames != FIELDS:
            raise ValueError(f"schema mismatch: {reader.fieldnames}")
        rows = list(reader)
        return raw, data, rows, [{"name": m.filename, "bytes": m.file_size, "crc32": f"{m.CRC:08x}"} for m in members]


def audit(path: Path, csv_name: str, request: str, family: str, projection: Transformer):
    raw, data, rows, members = read_archive(path, csv_name)
    missing = {f: sum(r.get(f) is None or str(r.get(f, "")).strip() == "" for r in rows) for f in FIELDS}
    categories = {f: dict(sorted(collections.Counter(r.get(f, "") for r in rows).items())) for f in ("satellite", "instrument", "confidence", "version", "daynight", "type", "acq_date")}
    seen, records, exclusions, diagnostics = set(), [], [], collections.Counter()
    for number, row in enumerate(rows, 2):
        reasons = []
        row_tuple = tuple(row.get(f) for f in FIELDS)
        if row_tuple in seen:
            reasons.append("exact_duplicate")
        seen.add(row_tuple)
        try:
            if None in row or any(row.get(f) is None or row[f].strip() == "" for f in FIELDS):
                raise ValueError("missing or ragged field")
            lon, lat = numeric(row, "longitude"), numeric(row, "latitude")
            if not -180 <= lon <= 180 or not -90 <= lat <= 90:
                raise ValueError("invalid coordinate")
            acquired = utc_time(row["acq_date"], row["acq_time"])
            source = source_id(row, family)
            frp, scan, track = numeric(row, "frp"), numeric(row, "scan"), numeric(row, "track")
            brightness, background = numeric(row, "brightness"), numeric(row, "bright_t31")
            if frp < 0 or scan <= 0 or track <= 0 or brightness <= 0 or background <= 0:
                raise ValueError("invalid physical field range")
            if row["daynight"] not in ("D", "N") or row["type"] not in ("0", "1", "2", "3"):
                raise ValueError("unexpected source flag")
            if family == "MODIS" and not 0 <= numeric(row, "confidence") <= 100:
                raise ValueError("invalid MODIS confidence")
            if family == "VIIRS" and row["confidence"] not in ("l", "n", "h"):
                raise ValueError("invalid VIIRS confidence")
            if not in_aoi(lon, lat):
                reasons.append("outside_aoi")
            x, y = projection.transform(lon, lat, errcheck=True)
            if frp == 0:
                diagnostics["zero_frp_retained"] += 1
            if family == "VIIRS" and brightness < 250:
                diagnostics["brightness_below_250K_review_flag_retained"] += 1
            if not reasons:
                records.append({"id": f"{request}:{number}", "row": number, "request": request, "source": source,
                    "longitude": lon, "latitude": lat, "utc": acquired, "day": row["acq_date"],
                    "cell": cell_key(x, y), "confidence": row["confidence"], "version": row["version"],
                    "frp": frp, "daynight": row["daynight"], "type": row["type"], "scan": scan, "track": track,
                    "brightness": brightness, "brightness2": background, "nativeInstrument": row["instrument"], "nativeSatellite": row["satellite"]})
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            reasons.append(str(error))
        if reasons:
            exclusions.append({"csv_row": number, "reasons": reasons})
    finite_ranges = {}
    for f in ("latitude", "longitude", "frp", "scan", "track", "brightness", "bright_t31"):
        numbers = []
        for r in rows:
            try:
                n = numeric(r, f)
                numbers.append(n)
            except (ValueError, TypeError, KeyError):
                pass
        finite_ranges[f] = {"min": min(numbers), "max": max(numbers)} if numbers else None
    timestamps = sorted(r["utc"] for r in records)
    manifest = {"filename": path.name, "input_path": str(path.resolve()), "request_id": request,
        "zip_sha256": digest(raw), "zip_bytes": len(raw), "csv_name": csv_name, "csv_sha256": digest(data), "csv_bytes": len(data),
        "crc": "PASS", "members": members, "schema": FIELDS,
        "field_types": {f: ("finite float" if f in ("latitude", "longitude", "brightness", "scan", "track", "bright_t31", "frp") else
            "ISO UTC date" if f == "acq_date" else "zero-padded HHMM UTC minute" if f == "acq_time" else
            "native numeric 0-100" if f == "confidence" and family == "MODIS" else
            "native categorical l/n/h" if f == "confidence" else "source string / categorical") for f in FIELDS},
        "rows": len(rows), "accepted": len(records),
        "excluded": len(exclusions), "exclusions": exclusions, "missing": missing, "categories": categories,
        "numeric_ranges": finite_ranges, "exact_duplicates": len(rows) - len(seen), "diagnostics": dict(diagnostics),
        "observed_utc": {"first": timestamps[0] if timestamps else None, "last": timestamps[-1] if timestamps else None},
        "extract_completeness": "UNKNOWN", "observation_support": "OBSERVATION_UNKNOWN",
        "delivery_processing_family": "STANDARD_ARCHIVE_NAMING", "processing_lineage": "PARTIAL",
        "collection": "C6.1 delivery label; row 6.03 mapping not independently confirmed" if family == "MODIS" else "C2 delivery label and row version 2",
        "monthly_production_version": "UNVERIFIED", "state": "WARN" if not exclusions else "WARN_EXCLUSIONS"}
    if digest(path.read_bytes()) != manifest["zip_sha256"]:
        raise RuntimeError("source archive changed during processing")
    return manifest, records


def clip_to_bbox(polygon):
    """Sutherland-Hodgman clipping for the display AOI, no analytical weighting."""
    points = polygon[:-1]
    for axis, limit, greater in [(0, BBOX[0], True), (0, BBOX[2], False), (1, BBOX[1], True), (1, BBOX[3], False)]:
        if not points:
            break
        output, previous = [], points[-1]
        def inside(p):
            return p[axis] >= limit if greater else p[axis] <= limit
        for current in points:
            if inside(current) != inside(previous):
                ratio = (limit - previous[axis]) / (current[axis] - previous[axis])
                output.append([previous[k] + ratio * (current[k] - previous[k]) for k in range(2)])
            if inside(current):
                output.append(current)
            previous = current
        points = output
    return points + [points[0]] if points else []


def cell_geometry(key: str, inverse: Transformer):
    _, col, row = key.split(":")
    x, y = int(col) * CELL_M, int(row) * CELL_M
    corners = [(x, y), (x + CELL_M, y), (x + CELL_M, y + CELL_M), (x, y + CELL_M), (x, y)]
    ring = []
    for a, b in zip(corners, corners[1:]):
        for step in range(8):
            f = step / 8
            ring.append(list(inverse.transform(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)))
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [clip_to_bbox(ring)]}


def summarize(records):
    result = {}
    for source in SOURCE_INFO:
        group = [r for r in records if r["source"] == source]
        result[source] = {"records": len(group), "occupied_cell_days": len({(r["cell"], r["day"]) for r in group}),
            "detection_days": len({r["day"] for r in group}), "occupied_cells": len({r["cell"] for r in group})}
    return result


def build(input_dir: Path, output_dir: Path, reports_dir: Path):
    forward = Transformer.from_crs("EPSG:4326", CRS.from_user_input(CRS_TEXT), always_xy=True)
    inverse = Transformer.from_crs(CRS.from_user_input(CRS_TEXT), "EPSG:4326", always_xy=True)
    manifests, records = [], []
    for name, member, request, family in INPUTS:
        manifest, accepted = audit(input_dir / name, member, request, family, forward)
        manifests.append(manifest)
        records.extend(accepted)
    records.sort(key=lambda r: (r["source"], r["utc"], r["id"]))
    policy = {"id": METHOD, "aoi": BBOX, "crs": CRS_TEXT, "grid_origin_m": [0, 0], "cell_width_m": CELL_M,
        "projection_engine": {"pyproj": pyproj_version, "PROJ": proj_version_str},
        "confidence": "ALL_VALID_SOURCE_CONFIDENCE_CLASSES", "type_filter": "NONE_PRODUCTION_VINTAGE_UNVERIFIED",
        "duplicates": "EXCLUDE_EXACT_DUPLICATES_PRESERVE_SOURCE", "aoi_boundary": "inclusive outer bbox; cell west/south inclusive east/north exclusive; mathematical floor",
        "observation_support": "OBSERVATION_UNKNOWN", "adjustment": "ADJUSTMENT_WITHHELD",
        "case": "INTEGRATION_DIAGNOSTIC_2017", "extract_completeness": "UNKNOWN", "utc": "source acquisition minute; UTC day",
        "count_interpretation": "reported thermal detections and occupied cell-days in supplied extracts; not fire events or complete-month activity"}
    identity = {"policy": policy, "inputs": [{"zip": m["zip_sha256"], "csv": m["csv_sha256"]} for m in manifests],
        "pipeline_sha256": digest(Path(__file__).read_bytes()),
        "oracle_sha256": digest(Path(__file__).with_name("independent_recount.py").read_bytes()), "records": records}
    release_id = "eg-" + digest(canonical(identity))[:24]
    keys = sorted({(r["source"], r["day"], r["cell"]) for r in records})
    month_keys = sorted({r["day"][:7] for r in records})
    cells = [{"type": "Feature", "id": key, "properties": {"cell": key}, "geometry": cell_geometry(key, inverse)} for key in sorted({r["cell"] for r in records})]
    public_manifests = [{k: v for k, v in m.items() if k != "input_path"} for m in manifests]
    payload = {"schemaVersion": 1, "releaseId": release_id, "policy": policy, "sources": SOURCE_INFO,
        "manifests": public_manifests, "months": month_keys, "summary": summarize(records), "records": records,
        "cells": {"type": "FeatureCollection", "features": cells},
        "verification": {"state": "PENDING_INDEPENDENT_RECOUNT", "occupied_key_sha256": digest(canonical(keys)), "key_count": len(keys)}}
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    # Snapshot is explicitly pending until the independent oracle verifies it.
    (output_dir / "release.json").write_bytes(canonical(payload))
    manifest_doc = {"release_id": release_id, "method": policy, "inputs": manifests, "sources_unchanged": True}
    (reports_dir / "RAW_DATA_MANIFEST.json").write_text(json.dumps(manifest_doc, indent=2), encoding="utf-8")
    with (reports_dir / "NATIVE_OCCUPIED_CELL_DAYS.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["release_id", "source", "utc_day", "cell_id", "detection_records", "unit", "observation_support", "extract_completeness"])
        for source, day, cell in keys:
            count = sum(r["source"] == source and r["day"] == day and r["cell"] == cell for r in records)
            writer.writerow([release_id, source, day, cell, count, "occupied_cell_day", "OBSERVATION_UNKNOWN", "UNKNOWN"])
    lines = ["# Actual data readiness", "", f"Release `{release_id}` · diagnostic extract, NOT qualified full-month M1b.", "",
        "| Check | MODIS | S-NPP VIIRS |", "|---|---|---|"]
    for label, getter in [
        ("ZIP CRC", lambda m: m["crc"]), ("Rows", lambda m: m["rows"]),
        ("Accepted within AOI", lambda m: m["accepted"]), ("Excluded", lambda m: m["excluded"]),
        ("Exact duplicates", lambda m: m["exact_duplicates"]), ("Blank fields", lambda m: sum(m["missing"].values())),
        ("Actual first UTC", lambda m: m["observed_utc"]["first"]), ("Actual last UTC", lambda m: m["observed_utc"]["last"]),
        ("Native versions", lambda m: ", ".join(m["categories"]["version"])),
        ("Extract completeness", lambda m: m["extract_completeness"]),
        ("Observation opportunity", lambda m: m["observation_support"]),
        ("Monthly production vintage", lambda m: m["monthly_production_version"]),
    ]:
        lines.append(f"| {label} | {getter(manifests[0])} | {getter(manifests[1])} |")
    lines.extend(["", "PASS: archive integrity, schema contract and executed row-level checks. WARN: lineage/production vintage, extract completeness and opportunity are not independently established.",
        "", "VIIRS instrument=SNPP is retained verbatim; platform/archive identity maps it to the VIIRS lane. MODIS row version 6.03 is not silently relabeled 6.1. VIIRS version 2 does not prove monthly production version 2 or version 3. Type filtering is disabled. Zero FRP and flagged low brightness are retained; neither is used as a physical fire temperature or energy estimate.",
        "", "All valid native confidence classes are included in the declared diagnostic measurement. Terra is a separate lane. No raw ratio is a sensor correction. Date absence is no reported record in this extract, never verified no fire.",
        "", "## Actual source-separated native quantities", "", "| Source | Records | Occupied cell-days | Detection days | Occupied cells |", "|---|---:|---:|---:|---:|"])
    for source, summary in payload["summary"].items():
        lines.append(f"| {SOURCE_INFO[source]['name']} | {summary['records']} | {summary['occupied_cell_days']} | {summary['detection_days']} | {summary['occupied_cells']} |")
    lines.extend(["", "Full date/category distributions, coordinate/thermal ranges, flags, hashes, missingness and exclusions are in RAW_DATA_MANIFEST.json. Independent numerical verification is recorded separately; this report alone does not pass it."])
    (reports_dir / "DATA_READINESS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"release": release_id, "summary": payload["summary"], "diagnostics": [m["diagnostics"] for m in manifests]}, indent=2))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "public" / "data")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    build(args.input_dir, args.output_dir, args.reports_dir)
