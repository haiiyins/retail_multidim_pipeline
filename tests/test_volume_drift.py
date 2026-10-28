import datetime as dt
from pathlib import Path
import unittest

import duckdb


ROOT = Path(__file__).resolve().parents[1]
STATEMENT = "CREATE OR REPLACE TABLE audit.volume_drift AS"
QC5_SQL = STATEMENT + (ROOT / "sql/audit_checks.sql").read_text().split(STATEMENT, 1)[1]
START = dt.date(2024, 1, 1)


class VolumeDriftTests(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.execute("""
            CREATE SCHEMA bronze;
            CREATE SCHEMA audit;
            CREATE SCHEMA ext;
            CREATE TABLE bronze.dim_calendar AS
              SELECT CAST(d AS DATE) AS date_of_day
              FROM generate_series(DATE '2024-01-01', DATE '2024-04-30', INTERVAL 1 DAY) t(d);
            CREATE TABLE bronze.sales_detail (
              economical_businessunit_country_code VARCHAR, gmv_recorded_at TIMESTAMP,
              transaction_id VARCHAR, transaction_num_line INTEGER, transaction_version_at TIMESTAMP);
            CREATE TABLE bronze.tracking_ecom_events (country_code VARCHAR, date DATE);
            CREATE TABLE ext.public_holidays (
              country_code VARCHAR, holiday_date DATE, holiday_name VARCHAR);
        """)

    def load_series(self, *, table="sales_detail", country="VN", counts=None, days=70, copies=1):
        """Sales rows carry a unique (transaction, line, version) key; `copies` > 1 repeats each row that many times,
        the way the overlapping exports did (exact duplicates, same version)."""
        volumes = counts or {}
        rows = [(country, START + dt.timedelta(days=i), i, k)
                for i in range(days) for k in range(volumes.get(i, 100))]
        if table == "sales_detail":
            self.con.executemany(
                "INSERT INTO bronze.sales_detail VALUES (?, ?, ?, ?, ?)",
                [(c, d, f"{c}-{i}-{k}", 1, d) for c, d, i, k in rows for _ in range(copies)],
            )
        else:
            self.con.executemany(f"INSERT INTO bronze.{table} VALUES (?, ?)", [(c, d) for c, d, _, _ in rows])

    def result(self, day=35, *, table="sales_detail", country="VN"):
        self.con.execute(QC5_SQL)
        cursor = self.con.execute(
            """SELECT * FROM audit.volume_drift
               WHERE table_name = ? AND country_code = ? AND calendar_date = ?""",
            [table, country, START + dt.timedelta(days=day)],
        )
        return dict(zip([column[0] for column in cursor.description], cursor.fetchone()))

    def test_weekend_seasonality_is_not_drift(self):
        self.load_series(counts={i: 180 for i in range(70)
                                 if (START + dt.timedelta(days=i)).weekday() >= 5})
        self.result()
        self.assertEqual(self.con.execute(
            "SELECT count(*) FROM audit.volume_drift WHERE flagged"
        ).fetchone()[0], 0)

    def test_strict_threshold_and_current_day_excluded_from_baseline(self):
        for volume, flagged in [(50, False), (150, False), (49, True), (151, True)]:
            with self.subTest(volume=volume):
                self.con.execute("DELETE FROM bronze.sales_detail")
                self.load_series(counts={35: volume})
                row = self.result()
                self.assertEqual(row["mean_same_weekday_28d"], 100)
                self.assertEqual(row["flagged"], flagged)
                self.assertAlmostEqual(row["drift"], volume / 100 - 1)

    def test_requires_four_previous_weekdays(self):
        self.load_series(counts={21: 300})
        self.assertFalse(self.result(21)["flagged"])

    def test_missing_day_is_retained_and_flagged(self):
        self.load_series(counts={35: 0})
        row = self.result()
        self.assertEqual(row["rows"], 0)
        self.assertEqual(row["drift"], -1)
        self.assertTrue(row["flagged"])
        self.assertEqual(row["probable_cause"], "NO_ROWS")

    def test_restart_requires_two_nonempty_baseline_days(self):
        self.load_series(counts={i: 0 for i in range(7, 35)})
        row = self.result()
        self.assertEqual(row["baseline_days_with_rows"], 0)
        self.assertFalse(row["flagged"])

    def test_partial_gap_is_labelled_after_gap(self):
        self.load_series(counts={21: 0, 28: 0})
        row = self.result()
        self.assertEqual(row["baseline_days_with_rows"], 2)
        self.assertTrue(row["flagged"])
        self.assertEqual(row["probable_cause"], "AFTER_GAP")

    def test_last_day_drop_is_export_edge(self):
        self.load_series(counts={69: 10})
        self.assertEqual(self.result(69)["probable_cause"], "EXPORT_EDGE")

    def test_holiday_and_adjacent_day_hints(self):
        self.load_series(counts={35: 200, 36: 200})
        self.con.execute("INSERT INTO ext.public_holidays VALUES (?, ?, ?)",
                         ["VN", START + dt.timedelta(days=35), "Test holiday"])
        self.assertEqual(self.result()["probable_cause"], "PUBLIC_HOLIDAY: Test holiday")
        self.assertEqual(self.result(36)["probable_cause"],
                         "ADJACENT_TO_HOLIDAY: Test holiday")

    def test_holiday_in_baseline_hint(self):
        self.load_series(counts={35: 200})
        self.con.execute("INSERT INTO ext.public_holidays VALUES (?, ?, ?)",
                         ["VN", START + dt.timedelta(days=28), "Test holiday"])
        self.assertEqual(self.result()["probable_cause"], "HOLIDAY_IN_BASELINE")

    def test_duplicated_export_rows_are_diagnosed(self):
        self.load_series(counts={35: 0})
        self.load_series(counts={i: 0 for i in range(70) if i != 35}, copies=2)
        row = self.result()
        self.assertEqual((row["rows"], row["distinct_lines"], row["dup_factor"]), (200, 100, 2.0))
        self.assertTrue(row["flagged"])
        self.assertEqual(row["probable_cause"], "DUPLICATED_EXPORT")
        self.assertEqual(self.result(34)["dup_factor"], 1.0)

    def test_country_and_table_baselines_are_independent(self):
        self.load_series(counts={35: 200})
        self.load_series(country="SG", counts={i: 1000 for i in range(70)})
        self.load_series(table="tracking_ecom_events",
                         counts={i: 500 for i in range(70)})
        self.assertEqual(self.result()["probable_cause"], "UNEXPLAINED")
        self.assertFalse(self.result(country="SG")["flagged"])
        self.assertFalse(self.result(table="tracking_ecom_events")["flagged"])

    def test_single_day_web_sample_has_no_usable_baseline(self):
        self.load_series(table="tracking_ecom_events", days=1)
        row = self.result(0, table="tracking_ecom_events")
        self.assertIsNone(row["mean_same_weekday_28d"])
        self.assertFalse(row["flagged"])
        self.assertIsNone(row["probable_cause"])


if __name__ == "__main__":
    unittest.main()
