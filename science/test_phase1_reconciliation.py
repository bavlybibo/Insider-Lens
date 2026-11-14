"""Read-only regression against the supplied diagnostic, never held-out data.

Keeps the production pipeline and existing oracle unchanged. The original ZIPs
are read directly; cells use the oracle's independent ellipsoidal equations.
"""
from collections import Counter
import contextlib
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import unittest
import tempfile
import zipfile

from independent_recount import ellipsoidal_laea, recount
from pipeline import build

ROOT = Path(__file__).resolve().parents[1]
INPUT = Path.home() / "Downloads"
EXPECTED = {"AQUA_MODIS": (238, 32, 5, 15), "TERRA_MODIS": (172, 24, 4, 14), "SNPP_VIIRS": (2041, 65, 12, 27)}


class DiagnosticArchiveRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = json.loads((ROOT / "public/data/release.json").read_text(encoding="utf-8"))
        cls.rows = []
        for manifest in cls.release["manifests"]:
            data = (INPUT / manifest["filename"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == manifest["zip_sha256"]
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                assert archive.testzip() is None
                content = archive.read(manifest["csv_name"])
            assert hashlib.sha256(content).hexdigest() == manifest["csv_sha256"]
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            seen = set()
            for number, row in enumerate(reader, 2):
                identity = tuple(row.values())
                if identity in seen:
                    continue
                seen.add(identity)
                lon, lat = float(row["longitude"]), float(row["latitude"])
                if not (-8.7 <= lon <= -7.2 and 39.3 <= lat <= 40.8):
                    continue
                x, y = ellipsoidal_laea(lon, lat)
                cls.rows.append(dict(id=f'{manifest["request_id"]}:{number}',
                    source={"Aqua": "AQUA_MODIS", "Terra": "TERRA_MODIS", "SNPP": "SNPP_VIIRS"}[row["satellite"]],
                    day=row["acq_date"], cell=f"g:{math.floor(x/10000)}:{math.floor(y/10000)}",
                    dn=row["daynight"], version=row["version"]))

    def test_raw_archives_and_every_source_day_cell_multiplicity(self):
        self.assertEqual(len(self.rows), 2451)
        counter = lambda rows: Counter((r["source"], r["day"], r["cell"]) for r in rows)
        self.assertEqual(counter(self.rows), counter(self.release["records"]))
        self.assertEqual({r["id"] for r in self.rows}, {r["id"] for r in self.release["records"]})
        for source, expected in EXPECTED.items():
            rows = [r for r in self.rows if r["source"] == source]
            actual = (len(rows), len(counter(rows)), len({r["day"] for r in rows}), len({r["cell"] for r in rows}))
            self.assertEqual(actual, expected)

    def test_reference_cell_and_utc_dates_from_raw_points(self):
        for source, expected in {"AQUA_MODIS": (57, 4), "SNPP_VIIRS": (484, 4), "TERRA_MODIS": (45, 3)}.items():
            rows = [r for r in self.rows if r["source"] == source and r["cell"] == "g:-2:-1"]
            self.assertEqual((len(rows), len({r["day"] for r in rows})), expected)
            dates = {"2017-06-18", "2017-06-19", "2017-06-20"}
            if source != "TERRA_MODIS":
                dates.add("2017-06-21")
            self.assertEqual({r["day"] for r in rows}, dates)

    def test_daynight_versions_and_withheld_science_remain_native(self):
        for source in EXPECTED:
            for dn in ("D", "N"):
                raw = {r["id"] for r in self.rows if r["source"] == source and r["dn"] == dn}
                app = {r["id"] for r in self.release["records"] if r["source"] == source and r["daynight"] == dn}
                self.assertEqual(raw, app)
            self.assertEqual({r["version"] for r in self.rows if r["source"] == source}, {"2" if source == "SNPP_VIIRS" else "6.03"})
        self.assertEqual(self.release["policy"]["observation_support"], "OBSERVATION_UNKNOWN")
        self.assertEqual(self.release["policy"]["adjustment"], "ADJUSTMENT_WITHHELD")

    def test_existing_pipeline_and_full_oracle_replay_in_temporary_directory(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            output, reports = Path(tmp) / "data", Path(tmp) / "reports"
            build(INPUT, output, reports)
            recount(INPUT, output / "release.json", reports)
            self.assertEqual((output / "release.json").read_bytes(), (ROOT / "public/data/release.json").read_bytes())
            self.assertEqual((output / "catalog.json").read_bytes(), (ROOT / "public/data/catalog.json").read_bytes())
            self.assertEqual((reports / "NATIVE_OCCUPIED_CELL_DAYS.csv").read_bytes(), (ROOT / "reports/NATIVE_OCCUPIED_CELL_DAYS.csv").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
