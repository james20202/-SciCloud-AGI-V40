import json
import tempfile
import unittest
from core.shot_production_engine import ShotProductionEngine


class ShotProductionStatusTests(unittest.TestCase):
    def test_partial_batch_is_resumable_and_exposes_remaining_count(self):
        with tempfile.TemporaryDirectory() as root:
            engine = ShotProductionEngine()
            engine.root = root
            run = engine.create_run("EP-TEST", [{"shot_id": "S1"}, {"shot_id": "S2"}])
            data = engine.load(run["run_id"])
            data["shots"][0]["status"] = "done"
            engine._save(data)
            report = engine.status(run["run_id"])
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["done_count"], 1)
        self.assertEqual(report["remaining_count"], 1)
        self.assertEqual(report["progress"], 50.0)

    def test_blocked_shot_is_not_reported_as_completed(self):
        with tempfile.TemporaryDirectory() as root:
            engine = ShotProductionEngine()
            engine.root = root
            run = engine.create_run("EP-TEST", [{"shot_id": "S1"}])
            data = engine.load(run["run_id"])
            data["shots"][0]["status"] = "blocked"
            engine._save(data)
            report = engine.status(run["run_id"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["blocked_count"], 1)
        self.assertFalse(report["progress"] == 100.0)


if __name__ == "__main__":
    unittest.main()
