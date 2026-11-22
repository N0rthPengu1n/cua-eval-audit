import unittest

from audit_labels import audit_verdict, load_adjudications, read_csv
from step4_recompute import SHEET, compute
from step4b_subset import PROFILE, build_pool, load_reviews


class AuditRegressionTest(unittest.TestCase):
    def setUp(self):
        self.decisions = load_adjudications()

    def test_reviewed_false_positive_returns_to_pool(self):
        task_id = "88fe4b2d-3040-4c70-9a70-546a47764b48"
        rows = read_csv(PROFILE)
        row = next(row for row in rows if row["task_id"] == task_id)
        self.assertGreater(int(row["defect_count"]), 0)
        reviews = load_reviews()
        self.assertEqual(reviews[task_id], ("round2", "N"))
        pool, excluded = build_pool(rows, reviews, self.decisions)
        self.assertIn(row, pool)
        self.assertNotIn(task_id, dict(excluded))
        pool_without_review, excluded_without_review = build_pool([row], {}, {})
        self.assertEqual(pool_without_review, [])
        self.assertIn(task_id, dict(excluded_without_review))

    def test_pptx_cases_use_the_same_evidence_threshold(self):
        ids = ("c82632a4-56b6-4db4-9dd1-3820ee3388e4", "bf4e9888-f10f-47af-8dba-76413038b73c")
        for task_id in ids:
            with self.subTest(task_id=task_id):
                decision = self.decisions[task_id]
                self.assertEqual(decision["evidence_kind"], "artifact_replay")
                self.assertEqual(audit_verdict("N", decision), "Y")
        bins, _ = compute(read_csv(SHEET), self.decisions)
        self.assertIn("6", bins["FN"])
        self.assertIn("25", bins["TP"])

    def test_monthly_sales_false_rejection_is_excluded(self):
        task_id = "26a8440e-c166-4c50-aef4-bfb77314b46b"
        decision = self.decisions[task_id]
        self.assertEqual(decision["a_status"], "confirmed")
        self.assertEqual(decision["evidence_kind"], "artifact_replay")
        row = next(row for row in read_csv(PROFILE) if row["task_id"] == task_id)
        pool, excluded = build_pool([row], {}, {task_id: decision})
        self.assertEqual(pool, [])
        self.assertIn(task_id, dict(excluded))


if __name__ == "__main__":
    unittest.main()
