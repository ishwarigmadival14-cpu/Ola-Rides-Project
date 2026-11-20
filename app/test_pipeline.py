"""Pipeline tests: python -m unittest discover -s tests -v"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import build_database, clean_data, generate_sample_data, sql_utils  # noqa: E402


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        raw = cls.tmp / "raw.csv"
        generate_sample_data.generate(3000, seed=7).to_csv(raw, index=False, na_rep="null")
        cls.df, cls.report = clean_data.clean(clean_data.load_raw(raw))
        cls.csv = cls.tmp / "clean.csv"
        cls.df.to_csv(cls.csv, index=False)
        cls.db = Path(build_database.build(cls.csv, db_path=cls.tmp / "t.db"))

    def test_no_duplicates_and_keys_present(self):
        self.assertTrue(self.df["booking_id"].is_unique)
        self.assertEqual(self.df[["booking_id", "booking_date", "booking_status"]].isna().sum().sum(), 0)
        self.assertGreater(self.report["duplicates_removed"], 0)

    def test_categories_standardised(self):
        self.assertFalse(self.df["vehicle_type"].str.contains(r"^\s|\s$").any())
        self.assertNotIn("upi", set(self.df["payment_method"]))
        self.assertFalse(self.df["booking_id"].str.contains('"').any())

    def test_validity_rules(self):
        self.assertTrue(self.df["driver_rating"].dropna().between(1, 5).all())
        self.assertTrue((self.df["ride_distance"].dropna() > 0).all())

    def test_success_rides_complete(self):
        ok = self.df[self.df["booking_status"] == "Success"]
        self.assertEqual(ok[["booking_value", "ride_distance"]].isna().sum().sum(), 0)

    def test_cancelled_rides_not_zero_filled(self):
        bad = self.df[self.df["booking_status"] == "Driver Not Found"]
        self.assertTrue(bad["booking_value"].isna().all())

    def test_all_queries_run_and_match_pandas(self):
        queries = {q["id"]: q["sql"] for q in sql_utils.load_queries()}
        self.assertEqual(len(queries), 20)
        for qid, sql in queries.items():
            sql_utils.run_sql(sql, self.db)
        q3 = sql_utils.run_sql(queries["Q3"], self.db).iloc[0, 0]
        self.assertEqual(q3, (self.df["booking_status"] == "Canceled by Customer").sum())
        q9 = sql_utils.run_sql(queries["Q9"], self.db).iloc[0, 0]
        self.assertAlmostEqual(q9, self.df.loc[self.df["booking_status"] == "Success", "booking_value"].sum(), 2)

    def test_run_sql_is_read_only(self):
        with self.assertRaises(ValueError):
            sql_utils.run_sql("DELETE FROM ola_rides", self.db)
        with self.assertRaises(ValueError):
            sql_utils.run_sql("SELECT 1; DROP TABLE ola_rides", self.db)


if __name__ == "__main__":
    unittest.main()
