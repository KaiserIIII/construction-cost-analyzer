"""Validate public snapshot integrity and the ONS monthly-level import boundary."""

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / "scripts" / "import_ons_opi.py"
CSV_PATH = ROOT / "data" / "indices" / "ons_construction_opi.csv"
METADATA_PATH = CSV_PATH.with_suffix(".metadata.json")
FIELDS = ["period", "index_type", "series", "index_value", "base_year", "source_type", "source_ref"]
HAS_OPENPYXL = importlib.util.find_spec("openpyxl") is not None


def workbook_bytes(sheets):
    """Build small public-layout fixtures; never contact ONS during tests."""
    from openpyxl import Workbook

    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    stream = io.BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


class ImporterTests(unittest.TestCase):
    def importer(self):
        self.assertTrue(IMPORTER.is_file(), "Reproducible ONS importer is missing")
        spec = importlib.util.spec_from_file_location("ons_importer_under_test", IMPORTER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_sha_mismatch_rejected_before_reading_untrusted_workbook(self):
        module = self.importer()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            module.parse_workbook(b"changed source, not an XLSX")

    def test_cli_refuses_changed_input_without_writing_outputs(self):
        self.importer()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "changed.xlsx"
            source.write_bytes(b"not the pinned workbook")
            output = Path(directory) / "output"
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(IMPORTER), "--workbook", str(source), "--output-dir", str(output)],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256", result.stderr)
            self.assertFalse(output.exists())

    @unittest.skipUnless(HAS_OPENPYXL, "optional XLSX importer needs openpyxl")
    def test_only_monthly_index_levels_not_growth_or_aggregated_periods(self):
        module = self.importer()
        content = workbook_bytes({"All construction": [
            ["2015=100"],
            ["Time period", "All new work\nindex, (2015=100)", "All new work percentage change over 1 month"],
            ["2014 Jan", 100.5, 1.7], ["Feb", 99.4, -1.1],
            ["2014 Q1", 99.6, -0.4], ["2014", 99.3, 0.2],
            ["2015 Jan", 98.7, -0.1],
        ]})
        rows = module.parse_workbook(content, expected_sha256=hashlib.sha256(content).hexdigest())
        self.assertEqual([(r["period"], r["series"], r["index_value"]) for r in rows],
                         [("2014-01", "All new work", "100.5"),
                          ("2014-02", "All new work", "99.4"),
                          ("2015-01", "All new work", "98.7")])
        self.assertEqual(set(rows[0]), set(FIELDS))
        self.assertEqual(rows[0]["index_type"], "OPI")
        self.assertEqual(rows[0]["base_year"], "2015")

    @unittest.skipUnless(HAS_OPENPYXL, "optional XLSX importer needs openpyxl")
    def test_separate_year_column_carries_year_for_continuation_months(self):
        module = self.importer()
        content = workbook_bytes({"New work": [
            ["Year", "Time period", "Infrastructure index 2015=100"],
            [2014, "Jan", 100.2], [None, "February", 99.2],
            [2015, "Jan", 98.6], [None, "Q1", 99.5],
        ]})
        rows = module.parse_workbook(content, expected_sha256=hashlib.sha256(content).hexdigest())
        self.assertEqual([(r["period"], r["index_value"]) for r in rows],
                         [("2014-01", "100.2"), ("2014-02", "99.2"), ("2015-01", "98.6")])

    @unittest.skipUnless(HAS_OPENPYXL, "optional XLSX importer needs openpyxl")
    def test_cross_sheet_duplicate_totals_must_agree(self):
        module = self.importer()
        for second_value, conflict in [(100.5, False), (101.5, True)]:
            with self.subTest(second_value=second_value):
                content = workbook_bytes({
                    "All construction": [["Time period", "All new work index 2015=100"], ["2014 Jan", 100.5]],
                    "New work": [["Time period", "All new work index 2015=100"], ["2014 Jan", second_value]],
                })
                if conflict:
                    with self.assertRaisesRegex(ValueError, "Conflicting"):
                        module.parse_workbook(content, expected_sha256=hashlib.sha256(content).hexdigest())
                else:
                    self.assertEqual(len(module.parse_workbook(content, expected_sha256=hashlib.sha256(content).hexdigest())), 1)

    @unittest.skipUnless(HAS_OPENPYXL, "optional XLSX importer needs openpyxl")
    def test_missing_year_invalid_level_and_unknown_period_fail_closed(self):
        module = self.importer()
        for period, value in [("Jan", 100), ("2014 Jan", None), ("2014 Jan", 0),
                              ("2014 Jan", ".."), ("2014 Foo", 100)]:
            with self.subTest(period=period, value=value):
                content = workbook_bytes({"All construction": [
                    ["Time period", "All new work index 2015=100"], [period, value],
                ]})
                with self.assertRaises(ValueError):
                    module.parse_workbook(content, expected_sha256=hashlib.sha256(content).hexdigest())

    @unittest.skipUnless(HAS_OPENPYXL, "optional XLSX importer needs openpyxl")
    def test_duplicate_month_in_same_sheet_and_empty_layout_rejected(self):
        module = self.importer()
        for rows in [
            [["Time period", "All new work index 2015=100"], ["2014 Jan", 100], ["2014 Jan", 100]],
            [["Time period", "All new work percentage change"], ["2014 Jan", 1.7]],
        ]:
            content = workbook_bytes({"All construction": rows})
            with self.assertRaises(ValueError):
                module.parse_workbook(content, expected_sha256=hashlib.sha256(content).hexdigest())


class PublishedSnapshotTests(unittest.TestCase):
    def snapshot(self):
        self.assertTrue(CSV_PATH.is_file(), "Public monthly ONS CSV is missing")
        with CSV_PATH.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, FIELDS)
            rows = list(reader)
        self.assertTrue(METADATA_PATH.is_file(), "Source manifest is missing")
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        return rows, metadata

    def test_complete_unique_monthly_series_and_known_source_values(self):
        rows, metadata = self.snapshot()
        self.assertEqual(len(rows), 1500)
        self.assertEqual(len({r["period"] for r in rows}), 150)
        self.assertEqual(len({r["series"] for r in rows}), 10)
        self.assertEqual(len({(r["period"], r["series"]) for r in rows}), len(rows))
        months = [f"{year:04d}-{month:02d}" for year in range(2014, 2027)
                  for month in range(1, 13) if (year, month) <= (2026, 6)]
        for series in {r["series"] for r in rows}:
            self.assertEqual(sorted(r["period"] for r in rows if r["series"] == series), months)
        values = {(r["period"], r["series"]): r["index_value"] for r in rows}
        self.assertEqual(values[("2014-01", "All construction (new work and repair and maintenance)")], "100.4")
        self.assertEqual(values[("2026-06", "All construction (new work and repair and maintenance)")], "146.4")
        self.assertEqual(values[("2026-06", "Housing (public and private)")], "158.4")
        self.assertTrue(all(float(r["index_value"]) > 0 for r in rows))
        self.assertEqual({r["index_type"] for r in rows}, {"OPI"})
        self.assertEqual({r["base_year"] for r in rows}, {"2015"})
        self.assertEqual({r["source_type"] for r in rows}, {"official_statistics"})
        self.assertEqual({r["source_ref"] for r in rows}, {metadata["source_ref"]})

    def test_manifest_verifies_csv_and_records_workbook_provenance(self):
        rows, metadata = self.snapshot()
        self.assertEqual(metadata["csv_sha256"], hashlib.sha256(CSV_PATH.read_bytes()).hexdigest())
        self.assertEqual(metadata["workbook_sha256"], "ea0cbfe6573be52210ea0469f182ac5f03c68af39b193ab0f328feb24626edde")
        self.assertEqual(metadata["row_count"], len(rows))
        self.assertEqual(metadata["month_count"], 150)
        self.assertEqual(metadata["series_count"], 10)
        self.assertEqual(metadata["release_date"], "2026-08-13")
        self.assertEqual(metadata["licence"], "Open Government Licence v3.0")
        self.assertIn("ons.gov.uk", metadata["source_url"])
        self.assertTrue(metadata["retrieved_at_utc"].endswith("Z"))
        self.assertEqual(metadata["coverage_workbook"], "Great Britain")


if __name__ == "__main__":
    unittest.main()
