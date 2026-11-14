"""Known-answer, adversarial and independent-projection checks, all synthetic."""
import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
import zipfile

from pyproj import Transformer
import pipeline as production
import independent_recount as oracle


def fixture_row(satellite="Aqua", **updates):
    row = dict(zip(production.FIELDS, ["39.9", "-8.2", "330", "1.1", "1.1", "2017-06-06", "3", satellite,
        "MODIS" if satellite != "SNPP" else "SNPP", "50" if satellite != "SNPP" else "n", "6.03" if satellite != "SNPP" else "2", "290", "0", "N", "0"]))
    row.update(updates)
    return row


def make_archive(directory, filename, member, rows):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=production.FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(directory / filename, "w") as z:
        z.writestr(member, text.getvalue())
        z.writestr("Readme.txt", "Synthetic test input; not NASA observations.")


class ScientificContracts(unittest.TestCase):
    def test_utc_zero_padding_and_boundaries(self):
        self.assertEqual(production.utc_time("2017-06-06", "3"), "2017-06-06T00:03:00Z")
        self.assertEqual(production.utc_time("2017-06-06", "2359"), "2017-06-06T23:59:00Z")
        for invalid in ["2400", "1260", "00300", "1.5", "-1", "", " 3"]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                production.utc_time("2017-06-06", invalid)
        with self.assertRaises(ValueError):
            production.utc_time("2017-02-29", "1200")

    def test_negative_cell_indices_and_edges(self):
        for point, expected in [((0, 0), "g:0:0"), ((-0.001, -10000), "g:-1:-1"), ((10000, 9999.9), "g:1:0"), ((-10000.1, 10000), "g:-2:1")]:
            self.assertEqual(production.cell_key(*point), expected)

    def test_aoi_outer_boundary_and_invalid_points(self):
        self.assertTrue(production.in_aoi(-8.7, 39.3))
        self.assertTrue(production.in_aoi(-7.2, 40.8))
        self.assertFalse(production.in_aoi(-8.700001, 39.3))

    def test_platforms_stay_separate(self):
        self.assertEqual(production.source_id(fixture_row(), "MODIS"), "AQUA_MODIS")
        self.assertEqual(production.source_id(fixture_row("Terra"), "MODIS"), "TERRA_MODIS")
        self.assertEqual(production.source_id(fixture_row("SNPP"), "VIIRS"), "SNPP_VIIRS")
        with self.assertRaises(ValueError):
            production.source_id(fixture_row("SNPP"), "MODIS")

    def test_independent_ellipsoidal_projection(self):
        project = Transformer.from_crs("EPSG:4326", production.CRS_TEXT, always_xy=True)
        for lon in [-8.7, -8.2, -7.95, -7.2]:
            for lat in [39.3, 39.9, 40.05, 40.8]:
                x, y = project.transform(lon, lat)
                ox, oy = oracle.ellipsoidal_laea(lon, lat)
                self.assertAlmostEqual(x, ox, places=6)
                self.assertAlmostEqual(y, oy, places=6)

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("../escape.csv", "bad")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                production.read_archive(p, "escape.csv")

    def test_finite_number_required(self):
        for value in ["nan", "inf", "-inf"]:
            with self.assertRaises(ValueError):
                production.numeric({"frp": value}, "frp")

    def test_end_to_end_unknown_support_recount_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            a = fixture_row()
            make_archive(directory, production.INPUTS[0][0], production.INPUTS[0][1], [a, a, fixture_row("Terra")])
            make_archive(directory, production.INPUTS[1][0], production.INPUTS[1][1], [fixture_row("SNPP"), fixture_row("SNPP", latitude="42")])
            out, reports = directory / "public", directory / "reports"
            with contextlib.redirect_stdout(io.StringIO()):
                result = production.build(directory, out, reports)
                oracle.recount(directory, out / "release.json", reports)
            self.assertEqual(len(result["records"]), 3)
            self.assertEqual(result["manifests"][0]["exact_duplicates"], 1)
            self.assertEqual(result["manifests"][1]["excluded"], 1)
            self.assertEqual(result["policy"]["observation_support"], "OBSERVATION_UNKNOWN")
            self.assertEqual(result["policy"]["adjustment"], "ADJUSTMENT_WITHHELD")
            self.assertTrue(all(r["frp"] == 0 for r in result["records"]))
            released = json.loads((out / "release.json").read_text())
            self.assertEqual(released["verification"]["state"], "PASS")
            released["records"][0]["cell"] = "g:999:999"
            (out / "release.json").write_text(json.dumps(released))
            with self.assertRaisesRegex(AssertionError, "mismatch"):
                oracle.recount(directory, out / "release.json", reports)


if __name__ == "__main__":
    unittest.main(verbosity=2)
