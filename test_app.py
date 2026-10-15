import unittest
import json
import os
import uuid
import app
import models

class WorkoutTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.test_id = uuid.uuid4().hex[:8]
        self.test_db = os.path.join(os.path.dirname(__file__), f"test_{self.test_id}.db")
        models.DB_PATH = self.test_db
        models.init_db(self.test_db)
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def tearDown(self):
        models.DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def test_homepage(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"FitPulse", res.data)

    def test_add_exercise_and_compare(self):
        # Day 1: Bench press 3 sets of 10 @ 60kg
        payload_day1 = {
            "date": "2026-10-01",
            "exercise_name": "Press de Banca",
            "muscle_group": "Pecho",
            "sets": [
                {"reps": 10, "weight": 60.0},
                {"reps": 10, "weight": 60.0},
                {"reps": 10, "weight": 60.0}
            ]
        }
        res1 = self.client.post("/api/exercise", json=payload_day1)
        self.assertEqual(res1.status_code, 200)
        data1 = json.loads(res1.data)
        ex1 = data1["workout"]["exercises"][0]
        self.assertEqual(ex1["comparison"]["status"], "nuevo")

        # Query /api/exercise/last
        res_last = self.client.get("/api/exercise/last?name=Press de Banca&before_date=2026-10-08")
        self.assertEqual(res_last.status_code, 200)
        last_data = json.loads(res_last.data)
        self.assertIsNotNone(last_data["last_session"])
        self.assertEqual(last_data["last_session"]["stats"]["total_reps"], 30)

        # Day 2: Bench press 3 sets of 10 @ 62.5kg (Improvement!)
        payload_day2 = {
            "date": "2026-10-08",
            "exercise_name": "Press de Banca",
            "muscle_group": "Pecho",
            "sets": [
                {"reps": 10, "weight": 62.5},
                {"reps": 10, "weight": 62.5},
                {"reps": 10, "weight": 62.5}
            ]
        }
        res2 = self.client.post("/api/exercise", json=payload_day2)
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        ex2 = data2["workout"]["exercises"][0]
        self.assertEqual(ex2["comparison"]["status"], "mejora")
        self.assertEqual(ex2["comparison"]["weight_diff"], 2.5)

        # Weekly summary for week containing 2026-10-08
        res_week = self.client.get("/api/weekly?date=2026-10-08")
        self.assertEqual(res_week.status_code, 200)
        week_data = json.loads(res_week.data)
        self.assertEqual(week_data["improvements_count"], 1)
        self.assertIn("Progreso", week_data["verdict"])

if __name__ == "__main__":
    unittest.main()
