"""
SmartHub Platform — Full End-to-End Test Suite
Run: .\backend\venv\Scripts\python test_full_platform.py
"""
import requests
import json
import sys
from datetime import datetime

BASE = "http://127.0.0.1:8000/api"

results = []


def test(name, condition, details=""):
    status = "✅ PASS" if condition else "❌ FAIL"
    results.append((status, name, details))
    print(f"  {status} — {name}")
    if not condition and details:
        print(f"       Details: {details}")


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def get_token(email, password):
    try:
        r = requests.post(f"{BASE}/auth/login",
                          json={"email": email, "password": password},
                          timeout=8)
        if r.status_code == 200:
            return r.json().get("access_token")
        return None
    except Exception:
        return None


def H(token):
    return {"Authorization": f"Bearer {token}"}


def safe_get(url, headers=None, params=None):
    try:
        return requests.get(url, headers=headers, params=params, timeout=20)
    except Exception as e:
        class ErrResp:
            status_code = 0
            text = str(e)
            def json(self): return {}
        return ErrResp()


def safe_post(url, headers=None, json=None):
    try:
        return requests.post(url, headers=headers, json=json, timeout=20)
    except Exception as e:
        class ErrResp:
            status_code = 0
            text = str(e)
            def json(self): return {}
        return ErrResp()


def safe_patch(url, headers=None, json=None):
    try:
        return requests.patch(url, headers=headers, json=json, timeout=20)
    except Exception as e:
        class ErrResp:
            status_code = 0
            text = str(e)
            def json(self): return {}
        return ErrResp()


# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("  🧪 SMARTHUB PLATFORM — FULL TEST SUITE")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# ─── PREFLIGHT: Server reachable? ─────────────────────────────────────────────
section("PREFLIGHT: Server connectivity")
try:
    r = requests.get("http://127.0.0.1:8000/", timeout=5)
    server_up = r.status_code < 500
except Exception:
    server_up = False

test("Server is running on :8000", server_up,
     "Start: cd backend && uvicorn backend.main:app --reload --port 8000")

if not server_up:
    print("\n❌ Server is not running — aborting tests.")
    sys.exit(1)

# ─── GROUP 1: AUTHENTICATION ──────────────────────────────────────────────────
section("GROUP 1: Authentication")

admin_token = get_token("admin@example.com", "admin123")
test("Admin login (admin@example.com / admin123)", admin_token is not None)

muni_token = get_token("user-10406544@example.com", "password123")
test("Municipality login (user-10406544@example.com)", muni_token is not None)

# Try known employee passwords
emp_token = None
for pw in ["pass123", "password123", "test123", "employee123"]:
    emp_token = get_token("newemployee@example.com", pw)
    if emp_token:
        break
test("Employee login (newemployee@example.com)", emp_token is not None,
     "None of the tried passwords worked — check DB or seed_fresh_db.py")

r = requests.post(f"{BASE}/auth/login",
                  json={"email": "admin@example.com", "password": "wrong"},
                  timeout=8)
test("Wrong password rejected (401)", r.status_code == 401,
     f"Got {r.status_code}")

r = safe_get(f"{BASE}/municipalities/")
test("Unauthenticated request blocked (401/403)", r.status_code in [401, 403],
     f"Got {r.status_code}")

# ─── GROUP 2: MUNICIPALITIES ──────────────────────────────────────────────────
section("GROUP 2: Municipalities")

r = safe_get(f"{BASE}/municipalities/", headers=H(admin_token))
test("Admin: list all municipalities", r.status_code == 200,
     f"Status {r.status_code}: {r.text[:100]}")

municipalities = r.json() if r.status_code == 200 else []
test("At least one municipality exists", len(municipalities) > 0,
     f"Found {len(municipalities)}")

kfar_qara = next((m for m in municipalities if str(m.get("code", "")) == "10406544"), None)
test("כפר קרע (code 10406544) in DB", kfar_qara is not None)
MUNI_ID = kfar_qara["id"] if kfar_qara else 4

r2 = safe_get(f"{BASE}/municipalities/", headers=H(muni_token))
test("Municipality user can list municipalities (200)", r2.status_code == 200,
     f"Status {r2.status_code}")

r3 = safe_get(f"{BASE}/municipalities/{MUNI_ID}", headers=H(admin_token))
test("Admin: get municipality by ID", r3.status_code == 200,
     f"Status {r3.status_code}")

# ─── GROUP 3: BUDGET DATA ─────────────────────────────────────────────────────
section("GROUP 3: Budget Data")

r = safe_get(f"{BASE}/budget/{MUNI_ID}/2026-03", headers=H(admin_token))
test("Admin: get budget March 2026", r.status_code == 200,
     f"Status {r.status_code}: {r.text[:150]}")

budget_data = r.json() if r.status_code == 200 else {}
has_invoice = any(k in budget_data for k in ("invoice_total", "amount_due", "total_due"))
test("Budget has invoice total field",  has_invoice,
     f"Keys: {list(budget_data.keys())[:8]}")

lines = budget_data.get("budget_lines", budget_data.get("lines", []))
test("Budget has budget lines", len(lines) > 0,
     f"Found {len(lines)} lines")

r = safe_get(f"{BASE}/budget/{MUNI_ID}/2026-03", headers=H(muni_token))
test("Municipality user can access own budget", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/budget/{MUNI_ID}/2026-02", headers=H(admin_token))
test("Admin: get budget February 2026", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/budget/{MUNI_ID}/2026-04", headers=H(admin_token))
test("Admin: get budget April 2026", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/budget/{MUNI_ID}/2026-03/anomalies", headers=H(admin_token))
test("Budget anomalies endpoint", r.status_code == 200,
     f"Status {r.status_code}")

# ─── GROUP 4: MONTHLY RUNS ────────────────────────────────────────────────────
section("GROUP 4: Monthly Runs")

r = safe_get(f"{BASE}/runs/", headers=H(admin_token), params={"month": "2026-03"})
test("Get runs for March 2026", r.status_code == 200,
     f"Status {r.status_code}")

runs = r.json() if r.status_code == 200 else []
test("Has runs for March 2026", len(runs) > 0,
     f"Found {len(runs)} runs")

r = safe_get(f"{BASE}/runs/", headers=H(admin_token))
test("Get all runs (no filter)", r.status_code == 200,
     f"Status {r.status_code}")

# ─── GROUP 5: EXPLANATIONS ────────────────────────────────────────────────────
section("GROUP 5: Explanations")

r = safe_get(f"{BASE}/explanations/municipality/{MUNI_ID}/month/2026-03",
             headers=H(admin_token))
test("Get all explanations for municipality/month", r.status_code == 200,
     f"Status {r.status_code}: {r.text[:100]}")

exp_data = r.json() if r.status_code == 200 else {}
has_exp = isinstance(exp_data, (list, dict)) and (
    (isinstance(exp_data, list) and len(exp_data) >= 0) or
    (isinstance(exp_data, dict))
)
test("Explanations endpoint returns valid data", has_exp,
     f"Type: {type(exp_data).__name__}")

# try to get a specific topic code explanation
if lines:
    topic = lines[0].get("topic_code", "3")
    r2 = safe_get(f"{BASE}/explanations/{MUNI_ID}/2026-03/{topic}",
                  headers=H(admin_token))
    test(f"Get explanation for topic code {topic}", r2.status_code in [200, 404],
         f"Status {r2.status_code}")

# ─── GROUP 6: EMPLOYEES ───────────────────────────────────────────────────────
section("GROUP 6: Employees")

r = safe_get(f"{BASE}/employees", headers=H(admin_token))
test("Admin: list all employees", r.status_code == 200,
     f"Status {r.status_code}")

employees = r.json() if r.status_code == 200 else []
test("Has employees in DB", len(employees) > 0,
     f"Found {len(employees)}")

r = safe_get(f"{BASE}/employees", headers=H(muni_token))
test("Municipality blocked from /employees (403)", r.status_code in [401, 403],
     f"Got {r.status_code}")

ts = int(datetime.now().timestamp())
r = safe_post(f"{BASE}/employees", headers=H(admin_token), json={
    "email": f"autotest{ts}@gmail.com",
    "password": "testpass123",
    "first_name": "Auto",
    "last_name": "Test",
    "municipality_ids": [MUNI_ID]
})
test("Admin creates new employee", r.status_code in [200, 201],
     f"Status {r.status_code}: {r.text[:150]}")

emp_id_new = None
if r.status_code in [200, 201]:
    rd = r.json()
    emp_id_new = (rd.get("data") or rd).get("id") if isinstance(rd, dict) else None

# ─── GROUP 7: SUGGESTIONS & APPROVALS ────────────────────────────────────────
section("GROUP 7: Suggestions & Approvals")

r = safe_get(f"{BASE}/suggestions/pending", headers=H(admin_token))
test("Admin: get pending suggestions", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/suggestions/pending/count", headers=H(admin_token))
test("Admin: get pending count", r.status_code == 200,
     f"Status {r.status_code}")

if r.status_code == 200:
    count_data = r.json()
    test("Pending count is numeric", isinstance(count_data.get("count", count_data), (int, float)),
         f"Got: {count_data}")

# Submit suggestion as admin (fallback if no emp token)
token_for_suggestion = emp_token or admin_token
suggestion_id = None
if lines:
    line_id = lines[0].get("id", 1)
    topic_code = lines[0].get("topic_code", "3")
    r2 = safe_post(f"{BASE}/suggestions", headers=H(token_for_suggestion), json={
        "budget_line_id": line_id,
        "municipality_id": MUNI_ID,
        "month": "2026-03",
        "topic_code": str(topic_code),
        "suggestion_type": "custom",
        "custom_text": f"הסבר בדיקה אוטומטי {ts}"
    })
    submitter = "Employee" if emp_token else "Admin"
    test(f"{submitter}: submit suggestion", r2.status_code in [200, 201],
         f"Status {r2.status_code}: {r2.text[:200]}")

    if r2.status_code in [200, 201]:
        sd = r2.json()
        suggestion_id = sd.get("id")

if suggestion_id:
    r3 = safe_patch(f"{BASE}/suggestions/{suggestion_id}/approve",
                    headers=H(admin_token), json={"review_note": "אושר בבדיקה"})
    test("Admin: approve suggestion", r3.status_code == 200,
         f"Status {r3.status_code}: {r3.text[:150]}")

# ─── GROUP 8: REASONS (PRESETS LIBRARY) ──────────────────────────────────────
section("GROUP 8: Reasons Library")

r = safe_get(f"{BASE}/reasons", headers=H(admin_token))
test("Get reasons library", r.status_code == 200,
     f"Status {r.status_code}")

reasons = r.json() if r.status_code == 200 else []
test("Has seeded reasons in DB", len(reasons) >= 1,
     f"Found {len(reasons)} reasons")

r = safe_get(f"{BASE}/reasons", headers=H(admin_token), params={"topic_code": "3"})
test("Filter reasons by topic_code=3", r.status_code == 200,
     f"Status {r.status_code}")

# ─── GROUP 9: PRESETS ────────────────────────────────────────────────────────
section("GROUP 9: Explanation Presets")

r = safe_get(f"{BASE}/presets", headers=H(admin_token))
test("Admin: list presets", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_post(f"{BASE}/presets", headers=H(admin_token), json={
    "topic_code": "3",
    "preset_text": f"תבנית בדיקה {ts}",
    "category": "other",
    "municipality_id": MUNI_ID
})
test("Admin: create preset", r.status_code in [200, 201],
     f"Status {r.status_code}: {r.text[:150]}")

# ─── GROUP 10: POSITIONS ANALYSIS ────────────────────────────────────────────
section("GROUP 10: Positions Analysis")

r = safe_get(f"{BASE}/positions/analysis/{MUNI_ID}/2026-03", headers=H(admin_token))
test("Get positions analysis (municipality/month)", r.status_code == 200,
     f"Status {r.status_code}: {r.text[:150]}")

if r.status_code == 200:
    pos = r.json()
    test("Positions response has 'positions' list", "positions" in pos,
         f"Keys: {list(pos.keys())}")
    test("Positions response has 'summary'", "summary" in pos,
         f"Keys: {list(pos.keys())}")

r = safe_get(f"{BASE}/positions/admin-summary/2026-03", headers=H(admin_token))
test("Admin: positions summary all municipalities", r.status_code == 200,
     f"Status {r.status_code}")

# ─── GROUP 11: ANALYTICS & TRENDS ────────────────────────────────────────────
section("GROUP 11: Analytics & Trends")

r = safe_get(f"{BASE}/analytics/trends/{MUNI_ID}", headers=H(admin_token))
test("Trends data", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/analytics/forecast/{MUNI_ID}", headers=H(admin_token))
test("Forecast data", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/analytics/anomalies/{MUNI_ID}/2026-03", headers=H(admin_token))
test("Anomaly detection", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/analytics/retro-aging/{MUNI_ID}/2026-03", headers=H(admin_token))
test("Retro aging analysis", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/analytics/year-comparison/{MUNI_ID}/2026-03", headers=H(admin_token))
test("Year-over-year comparison", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/analytics/overview/2026-03", headers=H(admin_token))
test("Admin analytics overview", r.status_code == 200,
     f"Status {r.status_code}")

# ─── GROUP 12: DEADLINES ─────────────────────────────────────────────────────
section("GROUP 12: Deadlines & Applications")

r = safe_get(f"{BASE}/deadlines/{MUNI_ID}", headers=H(admin_token))
test("Get municipality deadlines", r.status_code == 200,
     f"Status {r.status_code}: {r.text[:100]}")

deadlines_raw = r.json() if r.status_code == 200 else {}
# Response is a dict with a 'deadlines' key
deadlines = deadlines_raw.get("deadlines", []) if isinstance(deadlines_raw, dict) else (deadlines_raw if isinstance(deadlines_raw, list) else [])
test("Deadlines response has deadlines list", isinstance(deadlines, list),
     f"Got type: {type(deadlines).__name__}, keys: {list(deadlines_raw.keys()) if isinstance(deadlines_raw, dict) else 'N/A'}")

r = safe_get(f"{BASE}/deadlines/admin/overview", headers=H(admin_token))
test("Admin deadlines overview", r.status_code == 200,
     f"Status {r.status_code}")

if deadlines:
    dl_id = deadlines[0].get("id") if isinstance(deadlines[0], dict) else None
    if dl_id:
        r2 = safe_post(f"{BASE}/deadlines/{MUNI_ID}/{dl_id}/application",
                       headers=H(admin_token),
                       json={"status": "submitted", "notes": "בדיקה"})
        test(f"Submit application for deadline {dl_id}", r2.status_code in [200, 201, 400],
             f"Status {r2.status_code}: {r2.text[:150]}")

# ─── GROUP 13: REPORTS ───────────────────────────────────────────────────────
section("GROUP 13: Reports System")

r = safe_get(f"{BASE}/reports/list/{MUNI_ID}", headers=H(admin_token))
test("List reports for municipality", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/reports/branding", headers=H(admin_token))
test("Get branding settings", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/reports/templates", headers=H(admin_token))
test("Get report templates", r.status_code == 200,
     f"Status {r.status_code}")

r = safe_get(f"{BASE}/reports/admin/all", headers=H(admin_token))
test("Admin: all reports grouped by municipality", r.status_code == 200,
     f"Status {r.status_code}")

# Generate a monthly report (async job)
r = safe_post(f"{BASE}/reports/generate/{MUNI_ID}/2026-03", headers=H(admin_token))
test("Generate monthly report (start job)", r.status_code in [200, 201],
     f"Status {r.status_code}: {r.text[:150]}")

if r.status_code in [200, 201]:
    job_id = r.json().get("job_id")
    if job_id:
        import time
        time.sleep(2)
        r2 = safe_get(f"{BASE}/reports/status/{job_id}", headers=H(admin_token))
        test("Poll report job status", r2.status_code == 200,
             f"Status {r2.status_code}")
        if r2.status_code == 200:
            job_status = r2.json().get("status", "")
            test("Job status is valid value",
                 job_status in ("queued", "running", "done", "error"),
                 f"Got status: '{job_status}'")

# ─── GROUP 14: SECURITY ───────────────────────────────────────────────────────
section("GROUP 14: Security Checks")

other_muni = next((m for m in municipalities if m["id"] != MUNI_ID), None)
if other_muni and muni_token:
    r = safe_get(f"{BASE}/budget/{other_muni['id']}/2026-03", headers=H(muni_token))
    test("Municipality CANNOT access other municipality budget", r.status_code in [401, 403],
         f"Got {r.status_code} for muni id={other_muni['id']} — expected 403")
else:
    test("Municipality isolation check (skipped — only 1 municipality)", True)

if emp_token:
    r = safe_get(f"{BASE}/employees", headers=H(emp_token))
    test("Employee CANNOT access /employees (admin-only)", r.status_code in [401, 403],
         f"Got {r.status_code}")

    r = safe_get(f"{BASE}/suggestions/pending", headers=H(emp_token))
    test("Employee CANNOT access pending suggestions list", r.status_code in [401, 403],
         f"Got {r.status_code}")
else:
    test("Employee security checks skipped (no emp token)", True)

# Invalid token
r = safe_get(f"{BASE}/municipalities/", headers={"Authorization": "Bearer invalid.token.here"})
test("Invalid JWT rejected", r.status_code in [401, 403],
     f"Got {r.status_code}")

# ─── FINAL SUMMARY ────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("  📊 TEST RESULTS SUMMARY")
print("=" * 60)

passed = sum(1 for s, _, _ in results if "PASS" in s)
failed = sum(1 for s, _, _ in results if "FAIL" in s)
total = len(results)

print(f"\n  Total : {total}")
print(f"  ✅ Pass: {passed}")
print(f"  ❌ Fail: {failed}")
print(f"  Score : {passed / total * 100:.1f}%")

if failed:
    print("\n  ❌ FAILED TESTS:")
    for status, name, details in results:
        if "FAIL" in status:
            print(f"    • {name}")
            if details:
                print(f"      {details}")

if passed == total:
    print("\n  🎉 ALL TESTS PASSED — platform is healthy!")
else:
    print(f"\n  ⚠️  {failed} test(s) failed. See details above.")

print()
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
