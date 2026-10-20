import unittest
import json
import os
import uuid

os.environ["TESTING"] = "1"
import app
import models

class WorkoutTrackerTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["TESTING"] = "1"
        self.test_id = uuid.uuid4().hex[:8]
        self.test_db = os.path.join(os.path.dirname(__file__), f"test_{self.test_id}.db")
        models.DB_PATH = self.test_db
        models.init_db(self.test_db)
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def tearDown(self):
        models.DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
        os.environ.pop("TESTING", None)
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def register_and_get_token(self, username="tester", password="password123", name="Test User"):
        res = self.client.post("/api/auth/register", json={
            "username": username,
            "password": password,
            "name": name
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        return data["token"], data["user"]

    def test_homepage(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"FitChallenge", res.data)

    def test_auth_registration_and_login(self):
        # Register user
        token, user = self.register_and_get_token("carlos", "clave123", "Carlos Fit")
        self.assertEqual(user["username"], "carlos")
        self.assertEqual(user["name"], "Carlos Fit")

        # Check me
        res_me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(json.loads(res_me.data)["user"]["username"], "carlos")

        # Duplicate username should fail
        res_dup = self.client.post("/api/auth/register", json={
            "username": "carlos",
            "password": "otraclave123",
            "name": "Carlos Otro"
        })
        self.assertEqual(res_dup.status_code, 400)

        # Login with correct password
        res_login = self.client.post("/api/auth/login", json={
            "username": "carlos",
            "password": "clave123"
        })
        self.assertEqual(res_login.status_code, 200)
        login_data = json.loads(res_login.data)
        self.assertIn("token", login_data)

        # Login with bad password
        res_bad = self.client.post("/api/auth/login", json={
            "username": "carlos",
            "password": "wrongpassword"
        })
        self.assertEqual(res_bad.status_code, 401)

    def test_unauthenticated_access_rejected(self):
        # Accessing workout without token returns 401
        res = self.client.get("/api/workout?date=2026-10-15")
        self.assertEqual(res.status_code, 401)

        # Adding exercise without token returns 401
        res2 = self.client.post("/api/exercise", json={"exercise_name": "Sentadilla"})
        self.assertEqual(res2.status_code, 401)

    def test_multi_user_data_isolation(self):
        # Register two different users
        token_a, user_a = self.register_and_get_token("usuario_a", "clave123", "Usuario A")
        token_b, user_b = self.register_and_get_token("usuario_b", "clave123", "Usuario B")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A logs Bench Press on 2026-10-01
        payload_a = {
            "date": "2026-10-01",
            "exercise_name": "Press de Banca",
            "muscle_group": "Pecho",
            "sets": [{"reps": 10, "weight": 70.0}]
        }
        res_a = self.client.post("/api/exercise", json=payload_a, headers=headers_a)
        self.assertEqual(res_a.status_code, 200)
        ex_a_id = json.loads(res_a.data)["workout"]["exercises"][0]["id"]

        # User B logs Sentadilla on the same day 2026-10-01
        payload_b = {
            "date": "2026-10-01",
            "exercise_name": "Sentadilla con Barra",
            "muscle_group": "Piernas",
            "sets": [{"reps": 8, "weight": 100.0}]
        }
        res_b = self.client.post("/api/exercise", json=payload_b, headers=headers_b)
        self.assertEqual(res_b.status_code, 200)

        # User A checks workout on 2026-10-01: must see Bench Press, NOT Sentadilla
        w_a = json.loads(self.client.get("/api/workout?date=2026-10-01", headers=headers_a).data)["workout"]
        exercises_a = [e["exercise_name"] for e in w_a["exercises"]]
        self.assertIn("Press de Banca", exercises_a)
        self.assertNotIn("Sentadilla con Barra", exercises_a)

        # User B checks workout on 2026-10-01: must see Sentadilla, NOT Bench Press
        w_b = json.loads(self.client.get("/api/workout?date=2026-10-01", headers=headers_b).data)["workout"]
        exercises_b = [e["exercise_name"] for e in w_b["exercises"]]
        self.assertIn("Sentadilla con Barra", exercises_b)
        self.assertNotIn("Press de Banca", exercises_b)

        # User B cannot delete User A's exercise!
        res_del = self.client.delete(f"/api/exercise/{ex_a_id}", headers=headers_b)
        self.assertEqual(res_del.status_code, 404)

        # User A CAN delete their own exercise
        res_del_ok = self.client.delete(f"/api/exercise/{ex_a_id}", headers=headers_a)
        self.assertEqual(res_del_ok.status_code, 200)

    def test_add_exercise_and_compare(self):
        token, _ = self.register_and_get_token("progreso_user", "clave123")
        headers = {"Authorization": f"Bearer {token}"}

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
        res1 = self.client.post("/api/exercise", json=payload_day1, headers=headers)
        self.assertEqual(res1.status_code, 200)
        data1 = json.loads(res1.data)
        ex1 = data1["workout"]["exercises"][0]
        self.assertEqual(ex1["comparison"]["status"], "nuevo")

        # Query /api/exercise/last
        res_last = self.client.get("/api/exercise/last?name=Press de Banca&before_date=2026-10-08", headers=headers)
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
        res2 = self.client.post("/api/exercise", json=payload_day2, headers=headers)
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        ex2 = data2["workout"]["exercises"][0]
        self.assertEqual(ex2["comparison"]["status"], "mejora")
        self.assertEqual(ex2["comparison"]["weight_diff"], 2.5)

        # Weekly summary for week containing 2026-10-08
        res_week = self.client.get("/api/weekly?date=2026-10-08", headers=headers)
        self.assertEqual(res_week.status_code, 200)
        week_data = json.loads(res_week.data)
        self.assertEqual(week_data["improvements_count"], 1)
        self.assertIn("Progreso", week_data["verdict"])

    def test_username_minimum_length_validation(self):
        # 3-character username should be rejected
        res = self.client.post("/api/auth/register", json={
            "username": "ana",
            "password": "password123",
            "name": "Ana Test"
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("4 letras", data["error"])

        # 4-character username should succeed
        res_ok = self.client.post("/api/auth/register", json={
            "username": "juan",
            "password": "password123",
            "name": "Juan Test"
        })
        self.assertEqual(res_ok.status_code, 200)

    def test_gmail_registration_and_login(self):
        # Register with Gmail
        res = self.client.post("/api/auth/register", json={
            "username": "pedrofit",
            "email": "pedro@gmail.com",
            "password": "mypassword123",
            "name": "Pedro Gym"
        })
        self.assertEqual(res.status_code, 200)
        reg_data = json.loads(res.data)
        self.assertEqual(reg_data["user"]["email"], "pedro@gmail.com")

        # Login using username
        res_user_login = self.client.post("/api/auth/login", json={
            "username": "pedrofit",
            "password": "mypassword123"
        })
        self.assertEqual(res_user_login.status_code, 200)

        # Login using Gmail address directly
        res_email_login = self.client.post("/api/auth/login", json={
            "username": "pedro@gmail.com",
            "password": "mypassword123"
        })
        self.assertEqual(res_email_login.status_code, 200)
        email_data = json.loads(res_email_login.data)
        self.assertEqual(email_data["user"]["username"], "pedrofit")

        # Attempt to register another account with the same Gmail address should fail
        res_dup_email = self.client.post("/api/auth/register", json={
            "username": "pedrofit2",
            "email": "pedro@gmail.com",
            "password": "anotherpassword"
        })
        self.assertEqual(res_dup_email.status_code, 400)

    def test_google_user_creation_helper(self):
        # Create Google user
        user, err = models.find_or_create_google_user("atleta@gmail.com", name="Atleta Pro", db_path=self.test_db)
        self.assertIsNone(err)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "atleta@gmail.com")
        self.assertTrue(len(user["username"]) >= 4)

        # Calling again returns same user
        user2, err2 = models.find_or_create_google_user("atleta@gmail.com", name="Atleta Pro", db_path=self.test_db)
        self.assertIsNone(err2)
        self.assertEqual(user2["id"], user["id"])

    def test_security_headers(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("max-age=31536000", res.headers.get("Strict-Transport-Security", ""))
        self.assertIn("default-src 'self'", res.headers.get("Content-Security-Policy", ""))
        self.assertEqual(res.headers.get("Server"), "FitChallenge-Protegido")

    def test_path_traversal_and_sensitive_files_blocked(self):
        # Attempting to access database.db directly
        res_db = self.client.get("/database.db")
        self.assertEqual(res_db.status_code, 403)

        # Attempting to access .env
        res_env = self.client.get("/.env")
        self.assertEqual(res_env.status_code, 403)

        # Attempting directory traversal
        res_trav = self.client.get("/static/../models.py")
        self.assertEqual(res_trav.status_code, 403)

    def test_invalid_date_and_input_sanitization(self):
        token, user = self.register_and_get_token("secureuser", "clave123", "Secure User")
        headers = {"Authorization": f"Bearer {token}"}

        # Invalid date format
        res_bad_date = self.client.post("/api/workout", json={
            "date": "2026-99-99",
            "title": "Bad Date Workout"
        }, headers=headers)
        self.assertEqual(res_bad_date.status_code, 400)

        # SQL injection attempt in date
        res_inj = self.client.post("/api/workout", json={
            "date": "2026-10-01'; DROP TABLE users;--",
            "title": "Injection attempt"
        }, headers=headers)
        self.assertEqual(res_inj.status_code, 400)

    def test_rate_limiter_logic(self):
        tracker = {}
        ip = "192.168.1.100"
        tracker[ip] = []
        for _ in range(5):
            app.record_attempt(ip, tracker)
        self.assertTrue(app.is_rate_limited(ip, tracker, limit=5, window_seconds=300))
        app.clear_failures(ip, tracker)
        self.assertFalse(app.is_rate_limited(ip, tracker, limit=5, window_seconds=300))

    def test_download_apk(self):
        res = self.client.get("/descargar-apk")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/vnd.android.package-archive")
        self.assertIn("FitChallenge.apk", res.headers.get("Content-Disposition", ""))
        res.close()

        res2 = self.client.get("/download/apk")
        self.assertEqual(res2.status_code, 200)
        res2.close()


    def test_password_recovery_with_secret_word(self):
        # Register user with recovery answer
        res_reg = self.client.post("/api/auth/register", json={
            "username": "roberto",
            "password": "oldpassword123",
            "name": "Roberto",
            "email": "roberto@gmail.com",
            "recovery_answer": "mi perro toby"
        })
        self.assertEqual(res_reg.status_code, 200)

        # Lookup user
        res_lookup = self.client.post("/api/auth/recover/lookup", json={
            "identifier": "roberto"
        })
        self.assertEqual(res_lookup.status_code, 200)
        lookup_data = json.loads(res_lookup.data)
        self.assertTrue(lookup_data["user"]["has_recovery_question"])
        self.assertTrue(lookup_data["user"]["has_email"])

        # Reset with wrong secret word
        res_wrong = self.client.post("/api/auth/recover/reset", json={
            "identifier": "roberto",
            "verification_type": "secret_word",
            "verification_value": "palabra incorrecta",
            "new_password": "newpassword123"
        })
        self.assertEqual(res_wrong.status_code, 400)

        # Reset with correct secret word (case-insensitive test)
        res_reset = self.client.post("/api/auth/recover/reset", json={
            "identifier": "roberto",
            "verification_type": "secret_word",
            "verification_value": "Mi Perro TOBY",
            "new_password": "newpassword123"
        })
        self.assertEqual(res_reset.status_code, 200)
        reset_data = json.loads(res_reset.data)
        self.assertIn("token", reset_data)

        # Old password should no longer work
        res_old = self.client.post("/api/auth/login", json={
            "username": "roberto",
            "password": "oldpassword123"
        })
        self.assertEqual(res_old.status_code, 401)

        # New password works
        res_new = self.client.post("/api/auth/login", json={
            "username": "roberto",
            "password": "newpassword123"
        })
        self.assertEqual(res_new.status_code, 200)

    def test_password_recovery_with_email_match(self):
        # Register user with email but no secret word
        res_reg = self.client.post("/api/auth/register", json={
            "username": "mariana",
            "password": "marianaold123",
            "name": "Mariana",
            "email": "mariana@gmail.com"
        })
        self.assertEqual(res_reg.status_code, 200)

        # Reset with wrong email confirmation
        res_wrong = self.client.post("/api/auth/recover/reset", json={
            "identifier": "mariana",
            "verification_type": "email_match",
            "verification_value": "otro@gmail.com",
            "new_password": "mariananew123"
        })
        self.assertEqual(res_wrong.status_code, 400)

        # Reset with correct email confirmation
        res_ok = self.client.post("/api/auth/recover/reset", json={
            "identifier": "mariana",
            "verification_type": "email_match",
            "verification_value": "mariana@gmail.com",
            "new_password": "mariananew123"
        })
        self.assertEqual(res_ok.status_code, 200)

        # Login with new password
        res_login = self.client.post("/api/auth/login", json={
            "username": "mariana",
            "password": "mariananew123"
        })
        self.assertEqual(res_login.status_code, 200)

    def test_password_recovery_with_otp_code(self):
        # Register user
        res_reg = self.client.post("/api/auth/register", json={
            "username": "lucasfit",
            "password": "lucaspwd123",
            "name": "Lucas",
            "email": "lucas@gmail.com"
        })
        self.assertEqual(res_reg.status_code, 200)
        user_id = json.loads(res_reg.data)["user"]["id"]

        # Generate reset code
        code = models.create_password_reset_code(user_id, db_path=self.test_db)

        # Reset with wrong code
        res_bad_code = self.client.post("/api/auth/recover/reset", json={
            "identifier": "lucasfit",
            "verification_type": "otp_code",
            "verification_value": "000000",
            "new_password": "lucasnewpwd123"
        })
        self.assertEqual(res_bad_code.status_code, 400)

        # Reset with correct code
        res_good_code = self.client.post("/api/auth/recover/reset", json={
            "identifier": "lucasfit",
            "verification_type": "otp_code",
            "verification_value": code,
            "new_password": "lucasnewpwd123"
        })
        self.assertEqual(res_good_code.status_code, 200)

        # Used code cannot be reused
        res_reused = self.client.post("/api/auth/recover/reset", json={
            "identifier": "lucasfit",
            "verification_type": "otp_code",
            "verification_value": code,
            "new_password": "anotherpassword123"
        })
        self.assertEqual(res_reused.status_code, 400)

    def test_database_manager_endpoints(self):
        # 1. Admin DB Page loads
        res_page = self.client.get("/admin/db")
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"FitChallenge Studio", res_page.data)

        # 2. Status endpoint returns tables
        res_status = self.client.get("/api/admin/db/status")
        self.assertEqual(res_status.status_code, 200)
        st_data = json.loads(res_status.data)
        self.assertTrue(st_data["ok"])
        self.assertIn("tables", st_data)
        self.assertGreater(st_data["tables_count"], 0)

        # 3. Tables schema endpoint
        res_schemas = self.client.get("/api/admin/db/tables")
        self.assertEqual(res_schemas.status_code, 200)
        schemas_data = json.loads(res_schemas.data)
        self.assertIn("users", schemas_data)

        # 4. Table data query
        res_table = self.client.get("/api/admin/db/table/users?page=1&per_page=10")
        self.assertEqual(res_table.status_code, 200)
        tbl_data = json.loads(res_table.data)
        self.assertEqual(tbl_data["table"], "users")
        self.assertIn("columns", tbl_data)

        # 5. Execute custom SQL query
        res_sql = self.client.post("/api/admin/db/query", json={"query": "SELECT 1 as num, 'admin' as role;"})
        self.assertEqual(res_sql.status_code, 200)
        sql_data = json.loads(res_sql.data)
        self.assertEqual(sql_data["status"], "ok")
        self.assertEqual(sql_data["row_count"], 1)
        self.assertEqual(sql_data["rows"][0]["num"], 1)

        # 6. Export table
        res_export = self.client.get("/api/admin/db/export/users?format=json")
        self.assertEqual(res_export.status_code, 200)

    def test_ai_coach_and_progressive_overload(self):
        # 1. Register and get token
        token, user = self.register_and_get_token("aiuser", "password123", "AI Tester")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Add an initial exercise log for Sentadilla Hack (Hacka)
        res_add1 = self.client.post("/api/exercise", headers=headers, json={
            "date": "2026-10-10",
            "exercise_name": "Sentadilla Hack (Hacka)",
            "muscle_group": "Piernas",
            "sets": [
                {"reps": 12, "weight": 80.0},
                {"reps": 12, "weight": 80.0},
                {"reps": 12, "weight": 80.0}
            ]
        })
        self.assertEqual(res_add1.status_code, 200)
        data1 = json.loads(res_add1.data)
        self.assertIn("feedback", data1)
        self.assertTrue(data1["feedback"]["achieved"])

        # 3. Query Progressive Overload for today
        res_po = self.client.post("/api/ai/progressive_overload", headers=headers, json={
            "exercise_name": "Sentadilla Hack (Hacka)",
            "muscle_group": "Piernas",
            "before_date": "2026-10-17"
        })
        self.assertEqual(res_po.status_code, 200)
        po_data = json.loads(res_po.data)
        self.assertEqual(po_data["status"], "ok")
        self.assertEqual(po_data["last_date"], "2026-10-10")
        # Since user hit 12 reps on all sets, target should recommend weight increase
        self.assertEqual(po_data["target"]["type"], "increase_weight")
        self.assertGreater(po_data["target"]["suggested_sets"][0]["weight"], 80.0)

        # 4. Add second session with missed reps to verify motivational feedback
        res_add2 = self.client.post("/api/exercise", headers=headers, json={
            "date": "2026-10-17",
            "exercise_name": "Sentadilla Hack (Hacka)",
            "muscle_group": "Piernas",
            "sets": [
                {"reps": 6, "weight": 70.0},
                {"reps": 6, "weight": 70.0}
            ]
        })
        self.assertEqual(res_add2.status_code, 200)
        data2 = json.loads(res_add2.data)
        self.assertIn("feedback", data2)
        # Should detect missed reps and return a motivational message
        self.assertFalse(data2["feedback"]["achieved"])
        self.assertTrue(len(data2["feedback"]["message"]) > 10)

        # 5. Test AI Coach Chat
        res_chat = self.client.post("/api/ai/coach/chat", headers=headers, json={
            "message": "¿Cómo aplico sobrecarga progresiva en sentadilla hack?"
        })
        self.assertEqual(res_chat.status_code, 200)
        chat_data = json.loads(res_chat.data)
        self.assertEqual(chat_data["status"], "ok")
        self.assertTrue(len(chat_data["reply"]) > 20)

        # 6. Test Apply Routine
        res_routine = self.client.post("/api/ai/apply_routine", headers=headers, json={
            "date": "2026-10-18",
            "exercises": [
                {"name": "Sentadilla con Barra", "muscle": "Piernas", "sets": 3, "target_reps": 10, "weight": 60.0},
                {"name": "Extensiones de Cuádriceps", "muscle": "Piernas", "sets": 3, "target_reps": 12, "weight": 40.0}
            ]
        })
        self.assertEqual(res_routine.status_code, 200)
        routine_data = json.loads(res_routine.data)
        self.assertEqual(routine_data["status"], "ok")
        self.assertEqual(len(routine_data["workout"]["exercises"]), 2)

    def test_progressive_overload_multi_weight_individual_sets(self):
        token, user = self.register_and_get_token("pyramid_user", "password123", "Pyramid Lifter")
        headers = {"Authorization": f"Bearer {token}"}

        # Log exercise with different weights per set (e.g. Set 1: 35kg, Set 2 & 3: 40kg)
        res_log = self.client.post("/api/exercise", headers=headers, json={
            "date": "2026-10-14",
            "exercise_name": "Press Inclinado con Mancuernas",
            "muscle_group": "Pecho",
            "sets": [
                {"reps": 16, "weight": 35.0},
                {"reps": 12, "weight": 40.0},
                {"reps": 8, "weight": 40.0}
            ]
        })
        self.assertEqual(res_log.status_code, 200)

        # Request progressive overload suggestion for the next session
        res_po = self.client.post("/api/ai/progressive_overload", headers=headers, json={
            "exercise_name": "Press Inclinado con Mancuernas",
            "muscle_group": "Pecho",
            "before_date": "2026-10-17"
        })
        self.assertEqual(res_po.status_code, 200)
        po_data = json.loads(res_po.data)
        self.assertEqual(po_data["status"], "ok")
        target = po_data["target"]
        
        # Verify that Set 1 preserves 35.0 kg, and Set 2 and 3 preserve 40.0 kg
        suggested_sets = target["suggested_sets"]
        self.assertEqual(len(suggested_sets), 3)
        self.assertEqual(suggested_sets[0]["weight"], 35.0)
        self.assertEqual(suggested_sets[1]["weight"], 40.0)
        self.assertEqual(suggested_sets[2]["weight"], 40.0)
        
        # Verify explanation breakdown mentions 35 kg and 40 kg explicitly
        self.assertIn("35 kg", target["explanation"])
        self.assertIn("40 kg", target["explanation"])
        self.assertIn("S1: 16 reps con 35 kg", target["explanation"])

    def test_ai_coach_routine_generation_and_apply_flow(self):
        token, user = self.register_and_get_token("routine_user", "password123", "Routine Fan")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Ask for today's routine
        res_chat = self.client.post("/api/ai/coach/chat", headers=headers, json={
            "message": "Dame una rutina para hoy de piernas"
        })
        self.assertEqual(res_chat.status_code, 200)
        chat_data = json.loads(res_chat.data)
        self.assertEqual(chat_data["status"], "ok")
        self.assertIsNotNone(chat_data["suggested_routine"])
        self.assertGreaterEqual(len(chat_data["suggested_routine"]), 3)
        
        # Verify first exercise has valid structure
        first_ex = chat_data["suggested_routine"][0]
        self.assertIn("name", first_ex)
        self.assertIn("muscle", first_ex)
        self.assertIn("sets", first_ex)
        self.assertIn("target_reps", first_ex)

        # 2. Apply this suggested routine to today's date
        res_apply = self.client.post("/api/ai/apply_routine", headers=headers, json={
            "date": "2026-10-19",
            "exercises": chat_data["suggested_routine"]
        })
        self.assertEqual(res_apply.status_code, 200)
        apply_data = json.loads(res_apply.data)
        self.assertEqual(apply_data["status"], "ok")
        self.assertEqual(len(apply_data["workout"]["exercises"]), len(chat_data["suggested_routine"]))

        # 3. Verify exercises are stored in workout
        res_workout = self.client.get("/api/workout?date=2026-10-19", headers=headers)
        self.assertEqual(res_workout.status_code, 200)
        w_data = json.loads(res_workout.data)["workout"]
        self.assertEqual(len(w_data["exercises"]), len(chat_data["suggested_routine"]))

    def test_ai_coach_nutrition_and_general_queries(self):
        token, user = self.register_and_get_token("diet_user", "password123", "Nutrition Fan")
        headers = {"Authorization": f"Bearer {token}"}

        # Test nutrition query
        res_prot = self.client.post("/api/ai/coach/chat", headers=headers, json={
            "message": "¿Cuánta proteína debo comer al día?"
        })
        self.assertEqual(res_prot.status_code, 200)
        data_prot = json.loads(res_prot.data)
        self.assertIn("1.6", data_prot["reply"])
        self.assertIn("proteína", data_prot["reply"].lower())

        # Test supplements query
        res_creat = self.client.post("/api/ai/coach/chat", headers=headers, json={
            "message": "¿Cómo tomar la creatina?"
        })
        self.assertEqual(res_creat.status_code, 200)
        data_creat = json.loads(res_creat.data)
        self.assertIn("creatina", data_creat["reply"].lower())

    def test_ai_coach_settings_and_status(self):
        token, user = self.register_and_get_token("settings_user", "password123", "Settings User")
        headers = {"Authorization": f"Bearer {token}"}

        # Status endpoint
        res_st = self.client.get("/api/ai/coach/status", headers=headers)
        self.assertEqual(res_st.status_code, 200)
        self.assertIn("provider", json.loads(res_st.data))

        # Save Gemini key
        res_save = self.client.post("/api/ai/coach/settings", headers=headers, json={
            "api_key": "AIzaSyDummyTestKeyForVerification"
        })
        self.assertEqual(res_save.status_code, 200)
        save_data = json.loads(res_save.data)
        self.assertTrue(save_data["has_key"])
        self.assertEqual(save_data["provider"], "gemini")

        # Clear key
        res_clear = self.client.post("/api/ai/coach/settings", headers=headers, json={
            "api_key": ""
        })
        self.assertEqual(res_clear.status_code, 200)
        clear_data = json.loads(res_clear.data)
        self.assertFalse(clear_data["has_key"])

if __name__ == "__main__":
    unittest.main()



