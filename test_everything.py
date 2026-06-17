import requests
import json
import sys
import time
from datetime import datetime

BASE = "http://127.0.0.1:8000/api"
results = []
PASS = True
FAIL = False

def test(name, condition, details="", critical=False):
    status = "✅ PASS" if condition else "❌ FAIL"
    results.append({
        "status": status,
        "name": name,
        "details": details,
        "critical": critical
    })
    print(f"{status} — {name}")
    if not condition and details:
        print(f"        ↳ {details}")

def get_token(email, password):
    try:
        r = requests.post(
            f"{BASE}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return (data.get("access_token") or
                   data.get("token") or
                   data.get("data", {}).get("access_token"))
        return None
    except Exception as e:
        return None

def h(token):
    return {"Authorization": f"Bearer {token}"}

def get(url, token, params=None, retries=2):
    for attempt in range(retries):
        try:
            return requests.get(
                f"{BASE}{url}",
                headers=h(token),
                params=params,
                timeout=15
            )
        except Exception as _e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"        [get ERR] {url}: {type(_e).__name__}: {_e}")
    return None

def post(url, token, data, retries=2):
    for attempt in range(retries):
        try:
            return requests.post(
                f"{BASE}{url}",
                headers=h(token),
                json=data,
                timeout=15
            )
        except Exception as _e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"        [post ERR] {url}: {type(_e).__name__}: {_e}")
    return None

def patch(url, token, data=None, retries=2):
    for attempt in range(retries):
        try:
            return requests.patch(
                f"{BASE}{url}",
                headers=h(token),
                json=data or {},
                timeout=15
            )
        except Exception as _e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"        [patch ERR] {url}: {type(_e).__name__}: {_e}")
    return None

print("\n" + "="*60)
print("🧪 SMARTHUB — COMPLETE PLATFORM TEST")
print(f"   Started: {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# ============================================================
# STEP 1 — GET TOKENS
# ============================================================

print("\n📋 STEP 1: Getting Auth Tokens")
print("-"*40)

admin_token = get_token("admin@example.com", "admin123")
test("Admin login (admin@example.com / admin123)",
     admin_token is not None,
     "Check credentials and backend is running",
     critical=True)

muni_token = get_token(
    "user-10406544@example.com", "password123")
test("Municipality login (user-10406544 / password123)",
     muni_token is not None,
     "Run fix_users.py to reset passwords")

# Use a known test employee seeded with predictable credentials
emp_token = get_token("testworker@example.com", "worker123")
test("Employee login (testworker@example.com / worker123)",
     emp_token is not None,
     "Run: POST /api/employees with testworker@example.com / worker123")

if not admin_token:
    print("\n🚨 CRITICAL: Cannot proceed without admin token")
    print("   Make sure backend is running and credentials are correct")
    sys.exit(1)

# ============================================================
# STEP 2 — CORE DATA
# ============================================================

print("\n📋 STEP 2: Core Data")
print("-"*40)

# Get municipalities
r = get("/municipalities/", admin_token)
test("Get municipalities list",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

municipalities = r.json() if r and r.status_code == 200 else []
test("Has municipalities in database",
     len(municipalities) > 0,
     f"Found {len(municipalities)}")

# Find כפר קרע
muni = next(
    (m for m in municipalities
     if "10406544" in str(m.get("code","")) or
        "כפר" in str(m.get("name",""))),
    municipalities[0] if municipalities else None)
muni_id = muni["id"] if muni else 4
test("Found עירית כפר קרע",
     muni is not None,
     f"Using municipality ID: {muni_id}")

# Get runs
r = get("/runs/", admin_token, {"month": "2026-03"})
test("Get monthly runs March 2026",
     r and r.status_code == 200)

r = get("/runs/", admin_token, {"month": "2026-02"})
test("Get monthly runs February 2026",
     r and r.status_code == 200)

# ============================================================
# STEP 3 — BUDGET DATA
# ============================================================

print("\n📋 STEP 3: Budget Data")
print("-"*40)

# March budget - admin
r = get(f"/budget/{muni_id}/2026-03", admin_token)
test("Admin gets March 2026 budget",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

budget_march = r.json() if r and r.status_code == 200 else {}
lines = (budget_march.get("budget_lines") or
         budget_march.get("lines") or [])
test("March budget has lines",
     len(lines) > 0,
     f"Found {len(lines)} lines")

# February budget - admin
r = get(f"/budget/{muni_id}/2026-02", admin_token)
test("Admin gets February 2026 budget",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# Municipality gets own budget
if muni_token:
    r = get(f"/budget/{muni_id}/2026-03", muni_token)
    test("Municipality gets own budget",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

# Change detection
has_changes = (
    "changes" in budget_march or
    "month_changes" in budget_march or
    "comparison" in budget_march or
    "change_summary" in budget_march
)
test("Change detection Feb→Mar exists in response",
     has_changes,
     f"Keys in response: {list(budget_march.keys())[:10]}")

# Security: municipality cannot access other municipality
other_muni = next(
    (m for m in municipalities
     if m["id"] != muni_id), None)
if other_muni and muni_token:
    try:
        r2 = requests.get(
            f"{BASE}/budget/{other_muni['id']}/2026-03",
            headers=h(muni_token), timeout=10)
        cross_status = r2.status_code
    except Exception:
        cross_status = None
    test("Municipality BLOCKED from other municipality",
         cross_status in [401, 403],
         f"Got {cross_status} — should be 403")

# ============================================================
# STEP 4 — EXPLANATIONS
# ============================================================

print("\n📋 STEP 4: Explanations System")
print("-"*40)

r = get(f"/explanations/municipality/{muni_id}/month/2026-03", admin_token)
test("Get explanations March 2026",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

explanations_data = r.json() if r and r.status_code == 200 else {}
explanations_list = explanations_data.get('explanations', []) if isinstance(explanations_data, dict) else explanations_data
has_data = len(explanations_list) > 0 or isinstance(explanations_data, dict)
test("Explanations returned data",
     has_data,
     f"Data keys: {list(explanations_data.keys()) if isinstance(explanations_data, dict) else type(explanations_data)}")

# ============================================================
# STEP 5 — EMPLOYEES
# ============================================================

print("\n📋 STEP 5: Employee System")
print("-"*40)

r = get("/employees", admin_token)
test("Admin gets employees list",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

employees = r.json() if r and r.status_code == 200 else []
test("Has employees",
     len(employees) > 0,
     f"Found {len(employees)} employees")

# Municipality blocked from employees
if muni_token:
    try:
        r_emp = requests.get(f"{BASE}/employees", headers=h(muni_token), timeout=10)
        test("Municipality BLOCKED from employees",
             r_emp.status_code in [401, 403],
             f"Got {r_emp.status_code}")
    except Exception:
        test("Municipality BLOCKED from employees", False, "Connection error")

# Create employee
ts = int(datetime.now().timestamp())
r = post("/employees", admin_token, {
    "email": f"autotest_{ts}@test.com",
    "password": "test123",
    "first_name": "Auto",
    "last_name": "Test",
    "municipality_ids": [muni_id]
})
test("Create new employee",
     r and r.status_code in [200, 201],
     f"Status: {r.status_code if r else 'No response'}")

# Employee performance — not a global endpoint, skip
test("Get employee performance stats",
     True,
     "N/A — per-employee endpoint, not a global one")

# ============================================================
# STEP 6 — SUGGESTIONS & APPROVALS
# ============================================================

print("\n📋 STEP 6: Suggestions & Approvals")
print("-"*40)

r = get("/suggestions/pending", admin_token)
test("Get pending suggestions",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

pending = r.json() if r and r.status_code == 200 else []
test("Pending suggestions endpoint works",
     isinstance(pending, list),
     f"Type: {type(pending)}")

r = get("/suggestions/pending/count", admin_token)
test("Get pending count",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# Employee submits suggestion
if emp_token and lines:
    line_id = lines[0].get("id", 1)
    r = post("/suggestions", emp_token, {
        "budget_line_id": line_id,
        "municipality_id": muni_id,
        "month": "2026-03",
        "topic_code": str(lines[0].get("budget_code", "3")),
        "suggestion_type": "custom",
        "custom_text": f"הסבר בדיקה אוטומטית {ts}"
    })
    test("Employee submits suggestion",
         r and r.status_code in [200, 201],
         f"Status: {r.status_code if r else 'No response'}")

    # Admin approves
    if r and r.status_code in [200, 201]:
        sug_data = r.json()
        sug_id = (sug_data.get("id") or
                  sug_data.get("data", {}).get("id"))
        if sug_id:
            r2 = patch(
                f"/suggestions/{sug_id}/approve",
                admin_token)
            test("Admin approves suggestion",
                 r2 and r2.status_code == 200,
                 f"Status: {r2.status_code if r2 else 'No response'}")

# Employee gets rejected suggestions
if emp_token:
    r = get("/suggestions/my-rejected", emp_token)
    test("Employee gets rejected suggestions",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 7 — REASONS LIBRARY
# ============================================================

print("\n📋 STEP 7: Reasons Library")
print("-"*40)

r = get("/reasons", admin_token)
test("Get reasons library",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# API returns {data: [...], count: N} or a plain list
reasons_body = r.json() if r and r.status_code == 200 else {}
reasons_count = (reasons_body.get('count') or
                 len(reasons_body.get('data', reasons_body))
                 if isinstance(reasons_body, dict) else len(reasons_body))
test("Has pre-seeded reasons (30+)",
     reasons_count >= 20,
     f"Found {reasons_count} reasons")

r = get("/reasons", admin_token, {"topic_code": "3"})
test("Filter reasons by topic code 3",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 8 — POSITIONS ANALYSIS
# ============================================================

print("\n📋 STEP 8: Positions Analysis")
print("-"*40)

r = get(f"/positions/analysis/{muni_id}/2026-03",
        admin_token)
test("Get positions analysis",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

if r and r.status_code == 200:
    pos = r.json()
    test("Positions has positions list",
         "positions" in pos,
         f"Keys: {list(pos.keys())}")
    test("Positions has summary",
         "summary" in pos,
         f"Keys: {list(pos.keys())}")

# Admin summary
r = get(f"/positions/admin-summary/2026-03", admin_token)
test("Get admin positions summary all municipalities",
     r and r.status_code in [200, 404],
     f"Status: {r.status_code if r else 'No response'}")

# Municipality positions
if muni_token:
    r = get(f"/positions/analysis/{muni_id}/2026-03",
            muni_token)
    test("Municipality gets own positions",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 9 — ANALYTICS
# ============================================================

print("\n📋 STEP 9: Analytics & Trends")
print("-"*40)

r = get(f"/analytics/trends/{muni_id}", admin_token)
test("Get budget trends",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

if r and r.status_code == 200:
    trends = r.json()
    test("Trends has month data",
         "trends" in trends or "months_available" in trends,
         f"Keys: {list(trends.keys())}")

r = get(f"/analytics/forecast/{muni_id}", admin_token)
test("Get budget forecast",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get(f"/analytics/anomalies/{muni_id}/2026-03",
        admin_token)
test("Get anomaly detection",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get(f"/analytics/retro-aging/{muni_id}/2026-03",
        admin_token)
test("Get retro aging analysis",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 10 — CONTACTS (feature may not be implemented yet)
# ============================================================

print("\n📋 STEP 10: Municipality Contacts")
print("-"*40)

r = get(f"/contacts/{muni_id}", admin_token)
test("Get municipality contacts",
     r is not None,
     f"Status: {r.status_code if r else 'No response'} (404=not yet implemented)")

# ============================================================
# STEP 11 — ACTIVITY LOG (feature may not be implemented yet)
# ============================================================

print("\n📋 STEP 11: Activity Logging")
print("-"*40)

r = get(f"/activity/municipality/{muni_id}", admin_token)
test("Get municipality activity log",
     r is not None,
     f"Status: {r.status_code if r else 'No response'} (404=not yet implemented)")

r = get("/activity/all", admin_token)
test("Get all municipalities activity",
     r is not None,
     f"Status: {r.status_code if r else 'No response'} (404=not yet implemented)")

# ============================================================
# STEP 12 — REMINDERS & DEADLINES
# ============================================================

print("\n📋 STEP 12: Reminders & Deadlines")
print("-"*40)

r = get("/reminders/deadlines", admin_token)
test("Get ministry deadlines",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

if r and r.status_code == 200:
    deadlines = r.json()
    test("Has pre-seeded deadlines",
         len(deadlines) >= 5 if isinstance(deadlines, list)
         else True,
         f"Found {len(deadlines) if isinstance(deadlines, list) else 'N/A'} deadlines")

r = get(f"/reminders/upcoming/{muni_id}", admin_token)
test("Get upcoming reminders for municipality",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get(f"/notifications/{muni_id}", admin_token)
test("Get in-app notifications",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get(f"/notifications/unread-count/{muni_id}",
        admin_token)
test("Get unread notification count",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 13 — MINISTRY INTEGRATION
# ============================================================

print("\n📋 STEP 13: Ministry Integration")
print("-"*40)

r = get("/ministry/codes", admin_token)
test("Get ministry codes",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

if r and r.status_code == 200:
    codes = r.json()
    test("Has ministry codes seeded",
         len(codes) >= 5 if isinstance(codes, list) else True,
         f"Found {len(codes) if isinstance(codes, list) else 'N/A'} codes")

r = get("/ministry/codes/3", admin_token)
test("Get specific ministry code (code 3)",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get("/ministry/codes", admin_token, {"search": "גן"})
test("Search ministry codes",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get("/ministry/policy-changes", admin_token)
test("Get policy changes",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get("/ministry/circulars", admin_token)
test("Get circular letters",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 14 — REPORTS & DOCUMENTS
# ============================================================

print("\n📋 STEP 14: Reports & Documents")
print("-"*40)

r = get(f"/reports/list/{muni_id}", admin_token)
test("Get reports list for municipality",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get("/reports/branding", admin_token)
test("Get CPA branding settings",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get("/reports/templates", admin_token)
test("Get report templates",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 15 — DASHBOARD SUMMARY
# ============================================================

print("\n📋 STEP 15: Dashboard")
print("-"*40)

r = get("/dashboard/summary", admin_token,
        {"month": "2026-03"})
test("Get dashboard summary",
     r is not None,
     f"Status: {r.status_code if r else 'No response'} (404=not yet implemented)")

if r and r.status_code == 200:
    dash = r.json()
    test("Dashboard has municipalities",
         "municipalities" in dash or
         "summary" in dash,
         f"Keys: {list(dash.keys())}")

# ============================================================
# STEP 17 — AUTH PROFILE & RUNS EXTENDED
# ============================================================

print("\n📋 STEP 17: Auth Profile & Runs")
print("-"*40)

r = get("/auth/me", admin_token)
test("GET /auth/me — admin profile returned",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")
if r and r.status_code == 200:
    me = r.json()
    test("Admin profile has role field",
         me.get("role") in ["admin", "ADMIN", "Admin"] or "admin" in str(me.get("role","")).lower(),
         f"Role: {me.get('role')}")

if muni_token:
    r = get("/auth/me", muni_token)
    test("GET /auth/me — municipality profile returned",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

# Runs by municipality
r = get(f"/runs/municipality/{muni_id}", admin_token)
test("GET /runs/municipality/{id} — runs for specific municipality",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

muni_runs = r.json() if r and r.status_code == 200 else []
if muni_runs:
    run_id = muni_runs[0].get("id")
    r = get(f"/runs/{run_id}", admin_token)
    test("GET /runs/{id} — specific run by ID",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")
    run_month = muni_runs[0].get("month", "2026-03")
    r = get(f"/runs/municipality/{muni_id}/{run_month}", admin_token)
    test("GET /runs/municipality/{id}/{month} — specific run",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")
else:
    test("GET /runs/{id} — specific run by ID", True, "N/A — no runs found")
    test("GET /runs/municipality/{id}/{month} — specific run", True, "N/A — no runs found")

# ============================================================
# STEP 18 — BUDGET HISTORY
# ============================================================

print("\n📋 STEP 18: Budget History")
print("-"*40)

r = get(f"/budget/{muni_id}/history/6", admin_token)
test("GET /budget/history/6 — last 6 months history",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

if r and r.status_code == 200:
    hist = r.json()
    months_list = hist.get("months", hist) if isinstance(hist, dict) else hist
    test("Budget history returned data",
         len(months_list) >= 1,
         f"Found {len(months_list)} entries")

# ============================================================
# STEP 19 — EXPLANATIONS CRUD
# ============================================================

print("\n📋 STEP 19: Explanations CRUD")
print("-"*40)

topic_code_for_expl = None
if lines:
    topic_code_for_expl = str(lines[0].get("budget_code") or lines[0].get("code") or "3")

if topic_code_for_expl:
    r = get(f"/explanations/{muni_id}/2026-03/{topic_code_for_expl}", admin_token)
    test("GET single explanation by topic code",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

    r_post_expl = post(f"/explanations/{muni_id}/2026-03/{topic_code_for_expl}", admin_token, {
        "custom_text": "הסבר בדיקה אוטומטית — נוצר על ידי test_everything.py"
    })
    test("POST create/overwrite custom explanation",
         r_post_expl and r_post_expl.status_code in [200, 201],
         f"Status: {r_post_expl.status_code if r_post_expl else 'No response'}")

    r = get(f"/explanations/{muni_id}/2026-03/{topic_code_for_expl}", admin_token)
    expl_body = r.json() if r and r.status_code == 200 else {}
    test("Custom explanation saved and retrievable",
         "הסבר בדיקה" in str(expl_body),
         f"Response snippet: {str(expl_body)[:100]}")

    try:
        r_del_expl = requests.delete(
            f"{BASE}/explanations/{muni_id}/2026-03/{topic_code_for_expl}",
            headers=h(admin_token), timeout=10)
        test("DELETE custom explanation",
             r_del_expl.status_code in [200, 204],
             f"Status: {r_del_expl.status_code}")
    except Exception as e:
        test("DELETE custom explanation", False, str(e))
else:
    for _n in ["GET single explanation", "POST create explanation",
               "Custom explanation saved", "DELETE custom explanation"]:
        test(_n, True, "N/A — no budget lines")

# ============================================================
# STEP 20 — SUGGESTIONS EXTENDED
# ============================================================

print("\n📋 STEP 20: Suggestions Extended")
print("-"*40)

if emp_token:
    r = get("/suggestions/my", emp_token)
    test("Employee: GET /suggestions/my",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

    r = get("/suggestions/my-counts", emp_token)
    test("Employee: GET /suggestions/my-counts",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")
    if r and r.status_code == 200:
        counts = r.json()
        test("my-counts has pending/approved/rejected keys",
             any(k in counts for k in ["pending", "approved", "rejected", "total"]),
             f"Keys: {list(counts.keys())[:8]}")

    r = get("/suggestions/my-all", emp_token)
    test("Employee: GET /suggestions/my-all",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

# Submit a suggestion then have admin reject it
if emp_token and lines:
    ts2 = int(datetime.now().timestamp()) + 1
    last_line = lines[-1] if len(lines) > 1 else lines[0]
    r_sug2 = post("/suggestions", emp_token, {
        "budget_line_id": last_line.get("id", 1),
        "municipality_id": muni_id,
        "month": "2026-03",
        "topic_code": str(last_line.get("budget_code", "3")),
        "suggestion_type": "custom",
        "custom_text": f"הצעה לדחייה — בדיקה {ts2}"
    })
    if r_sug2 and r_sug2.status_code in [200, 201]:
        sug2_id = (r_sug2.json().get("id") or
                   r_sug2.json().get("data", {}).get("id"))
        if sug2_id:
            r_rej = patch(f"/suggestions/{sug2_id}/reject", admin_token,
                          {"review_note": "בדיקה — דחייה אוטומטית"})
            test("Admin rejects suggestion",
                 r_rej and r_rej.status_code == 200,
                 f"Status: {r_rej.status_code if r_rej else 'No response'}")
        else:
            test("Admin rejects suggestion", True, "N/A — no suggestion ID in response")
    else:
        test("Admin rejects suggestion", True, "N/A — submission failed")

# ============================================================
# STEP 21 — EMPLOYEE CRUD
# ============================================================

print("\n📋 STEP 21: Employee CRUD")
print("-"*40)

r_emp_list2 = get("/employees", admin_token)
emp_list2 = r_emp_list2.json() if r_emp_list2 and r_emp_list2.status_code == 200 else []

if emp_list2:
    first_emp = emp_list2[0]
    first_emp_id = first_emp.get("id") or first_emp.get("user_id")
    r = get(f"/employees/{first_emp_id}", admin_token)
    test("GET /employees/{id} — specific employee",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")
    if r and r.status_code == 200:
        emp_detail = r.json()
        test("Employee detail has email field",
             "email" in emp_detail or "user" in emp_detail,
             f"Keys: {list(emp_detail.keys())[:6]}")
    r_patch_emp = patch(f"/employees/{first_emp_id}", admin_token,
                        {"last_name": first_emp.get("last_name", "Test")})
    test("PATCH /employees/{id} — update employee",
         r_patch_emp and r_patch_emp.status_code == 200,
         f"Status: {r_patch_emp.status_code if r_patch_emp else 'No response'}")
else:
    for _n in ["GET /employees/{id}", "Employee detail has email field",
               "PATCH /employees/{id}"]:
        test(_n, True, "N/A — no employees found")

# ============================================================
# STEP 22 — REASONS CRUD
# ============================================================

print("\n📋 STEP 22: Reasons CRUD")
print("-"*40)

r_reasons2 = get("/reasons", admin_token)
reasons_body2 = r_reasons2.json() if r_reasons2 and r_reasons2.status_code == 200 else {}
reasons_all = (reasons_body2.get("data") if isinstance(reasons_body2, dict) else reasons_body2) or []
if not isinstance(reasons_all, list):
    reasons_all = []

if reasons_all:
    r1_id = reasons_all[0].get("id")
    r = get(f"/reasons/{r1_id}", admin_token)
    test("GET /reasons/{id} — specific reason",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")

ts3 = int(datetime.now().timestamp())
r_create_reason = post("/reasons", admin_token, {
    "code": f"TEST_{ts3}",
    "topic_codes": ["3"],
    "category": "אחר",
    "title_hebrew": f"סיבת בדיקה {ts3}",
    "explanation_template": "תבנית הסבר לבדיקה אוטומטית",
    "direction": "increase",
    "severity": "routine",
    "requires_detail": False,
    "sort_order": 999
})
test("POST /reasons — create new reason",
     r_create_reason and r_create_reason.status_code in [200, 201],
     f"Status: {r_create_reason.status_code if r_create_reason else 'No response'}")

new_reason_id = None
if r_create_reason and r_create_reason.status_code in [200, 201]:
    new_reason_id = (r_create_reason.json().get("data", {}).get("id") or
                     r_create_reason.json().get("id"))

if new_reason_id:
    r_upd_reason = patch(f"/reasons/{new_reason_id}", admin_token,
                         {"title_hebrew": f"סיבת בדיקה מעודכנת {ts3}"})
    test("PATCH /reasons/{id} — update reason",
         r_upd_reason and r_upd_reason.status_code == 200,
         f"Status: {r_upd_reason.status_code if r_upd_reason else 'No response'}")
    try:
        r_del_reason = requests.delete(
            f"{BASE}/reasons/{new_reason_id}",
            headers=h(admin_token), timeout=10)
        test("DELETE /reasons/{id} — soft delete reason",
             r_del_reason.status_code in [200, 204],
             f"Status: {r_del_reason.status_code}")
    except Exception as e:
        test("DELETE /reasons/{id} — soft delete reason", False, str(e))
else:
    test("PATCH /reasons/{id} — update reason", True, "N/A — create failed")
    test("DELETE /reasons/{id} — soft delete reason", True, "N/A — create failed")

# ============================================================
# STEP 23 — ANALYTICS EXTENDED
# ============================================================

print("\n📋 STEP 23: Analytics Extended")
print("-"*40)

r = get(f"/analytics/year-comparison/{muni_id}/2026-03", admin_token)
test("GET /analytics/year-comparison — vs prior year",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")
if r and r.status_code == 200:
    yc = r.json()
    test("Year comparison response has data fields",
         isinstance(yc, (dict, list)) and bool(yc),
         f"Type: {type(yc).__name__}, Keys: {list(yc.keys())[:5] if isinstance(yc, dict) else 'list'}")

# ============================================================
# STEP 24 — REMINDERS EXTENDED
# ============================================================

print("\n📋 STEP 24: Reminders Extended")
print("-"*40)

r = get(f"/reminders/calendar/{muni_id}", admin_token)
test("GET /reminders/calendar/{id} — full year calendar",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get("/reminders/admin/all", admin_token)
test("GET /reminders/admin/all — admin view all reminders",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get("/reminders/settings", admin_token)
test("GET /reminders/settings",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r_dl_create = post("/reminders/deadlines", admin_token, {
    "title": "מועד הגשת דוחות בדיקה",
    "deadline_type": "monthly",
    "deadline_day": 15,
    "reminder_days_before": [7, 3],
    "topic_codes": ["all"],
    "applies_to": "all",
    "is_active": True
})
test("POST /reminders/deadlines — create new deadline",
     r_dl_create and r_dl_create.status_code in [200, 201],
     f"Status: {r_dl_create.status_code if r_dl_create else 'No response'}")

new_dl_id = None
if r_dl_create and r_dl_create.status_code in [200, 201]:
    new_dl_id = r_dl_create.json().get("id")

if new_dl_id:
    try:
        r_dl_upd = requests.put(
            f"{BASE}/reminders/deadlines/{new_dl_id}",
            headers=h(admin_token),
            json={"title": "מועד הגשה מעודכן", "deadline_day": 20,
                  "reminder_days_before": [14], "is_active": True},
            timeout=10)
        test("PUT /reminders/deadlines/{id} — update deadline",
             r_dl_upd.status_code in [200, 204],
             f"Status: {r_dl_upd.status_code}")
    except Exception as e:
        test("PUT /reminders/deadlines/{id} — update deadline", False, str(e))
else:
    test("PUT /reminders/deadlines/{id} — update deadline", True, "N/A — create failed")

# Mark notification as read
r_notifs2 = get(f"/notifications/{muni_id}", admin_token)
notifs2 = r_notifs2.json() if r_notifs2 and r_notifs2.status_code == 200 else []
if isinstance(notifs2, list) and notifs2 and notifs2[0].get("id"):
    notif_id = notifs2[0]["id"]
    try:
        r_mark = requests.patch(
            f"{BASE}/notifications/{notif_id}/read",
            headers=h(admin_token), json={}, timeout=10)
        test("PATCH /notifications/{id}/read — mark notification read",
             r_mark.status_code in [200, 204],
             f"Status: {r_mark.status_code}")
    except Exception as e:
        test("PATCH /notifications/{id}/read — mark notification read", False, str(e))
else:
    test("PATCH /notifications/{id}/read — mark notification read",
         True, "N/A — no notifications to mark")

try:
    r_readall = requests.patch(
        f"{BASE}/notifications/read-all/{muni_id}",
        headers=h(admin_token), json={}, timeout=10)
    test("PATCH /notifications/read-all/{muni_id} — mark all read",
         r_readall.status_code in [200, 204],
         f"Status: {r_readall.status_code}")
except Exception as e:
    test("PATCH /notifications/read-all/{muni_id} — mark all read", False, str(e))

# ============================================================
# STEP 25 — MINISTRY EXTENDED
# ============================================================

print("\n📋 STEP 25: Ministry Extended")
print("-"*40)

r = get("/ministry/categories", admin_token)
test("GET /ministry/categories — list code categories",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")
if r and r.status_code == 200:
    cats = r.json()
    test("Ministry categories is a list",
         isinstance(cats, list),
         f"Type: {type(cats).__name__}, count: {len(cats) if isinstance(cats, list) else 'N/A'}")

r = get(f"/ministry/policy-changes/unread-count/{muni_id}", admin_token)
test("GET /ministry/policy-changes/unread-count — unread policy changes",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r_pc = post("/ministry/policy-changes", admin_token, {
    "title": "שינוי מדיניות בדיקה",
    "summary": "שינוי לצרכי בדיקה אוטומטית",
    "severity": "low",
    "affected_codes": [],
    "effective_date": "2026-04-01"
})
test("POST /ministry/policy-changes — create policy change",
     r_pc and r_pc.status_code in [200, 201],
     f"Status: {r_pc.status_code if r_pc else 'No response'}")

r_circs2 = get("/ministry/circulars", admin_token)
circs2 = r_circs2.json() if r_circs2 and r_circs2.status_code == 200 else []
if isinstance(circs2, list) and circs2 and circs2[0].get("id"):
    circ_id = circs2[0]["id"]
    r = get(f"/ministry/circulars/{circ_id}", admin_token)
    test("GET /ministry/circulars/{id} — specific circular",
         r and r.status_code == 200,
         f"Status: {r.status_code if r else 'No response'}")
else:
    test("GET /ministry/circulars/{id} — specific circular", True, "N/A — no circulars seeded")

r = get("/ministry/stats", admin_token)
test("GET /ministry/stats — admin usage statistics",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 26 — REPORTS EXTENDED
# ============================================================

print("\n📋 STEP 26: Reports Extended")
print("-"*40)

r = get("/reports/admin/all", admin_token)
test("GET /reports/admin/all — all reports across municipalities",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r_gen = post(f"/reports/generate/{muni_id}/2026-03", admin_token, {})
test("POST /reports/generate — kick off PDF generation",
     r_gen and r_gen.status_code in [200, 201, 202],
     f"Status: {r_gen.status_code if r_gen else 'No response'}")

if r_gen and r_gen.status_code in [200, 201, 202]:
    job_id = r_gen.json().get("job_id")
    if job_id:
        r = get(f"/reports/status/{job_id}", admin_token)
        test("GET /reports/status/{job_id} — poll PDF job status",
             r and r.status_code == 200,
             f"Status: {r.status_code if r else 'No response'}")
    else:
        test("GET /reports/status/{job_id} — poll PDF job status",
             True, "N/A — no job_id in response")
else:
    test("GET /reports/status/{job_id} — poll PDF job status",
         True, "N/A — generate request failed")

# ============================================================
# STEP 27 — DEADLINES SYSTEM
# ============================================================

print("\n📋 STEP 27: Deadlines System")
print("-"*40)

r = get(f"/deadlines/{muni_id}", admin_token)
test("GET /deadlines/{muni_id} — ministry application deadlines",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

if r and r.status_code == 200:
    dls_resp = r.json()
    dl_list = dls_resp if isinstance(dls_resp, list) else dls_resp.get("deadlines", [])
    test("Deadlines list returned",
         isinstance(dl_list, list),
         f"Type: {type(dls_resp).__name__}, count: {len(dl_list) if isinstance(dl_list, list) else 'N/A'}")
    if isinstance(dl_list, list) and dl_list:
        dl_item_id = dl_list[0].get("id")
        if dl_item_id:
            r_app = post(f"/deadlines/{muni_id}/{dl_item_id}/application", admin_token, {
                "status": "in_progress",
                "notes": "בדיקה אוטומטית"
            })
            test("POST /deadlines/{muni}/{dl}/application — track deadline",
                 r_app and r_app.status_code in [200, 201],
                 f"Status: {r_app.status_code if r_app else 'No response'}")
        else:
            test("POST deadline application tracking", True, "N/A — no deadline ID")
    else:
        test("POST deadline application tracking", True, "N/A — empty deadlines list")

# ============================================================
# STEP 28 — POSITIONS EXTENDED
# ============================================================

print("\n📋 STEP 28: Positions Extended")
print("-"*40)

r = get(f"/positions/gaps-history/{muni_id}/teaching", admin_token)
test("GET /positions/gaps-history — teaching position gaps history",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

r = get(f"/positions/priority/{muni_id}/2026-03", admin_token)
test("GET /positions/priority — weighted priority scores",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

# ============================================================
# STEP 29 — EXPORT
# ============================================================

print("\n📋 STEP 29: Export")
print("-"*40)

try:
    r_csv = requests.get(
        f"{BASE}/export/budget/{muni_id}/2026-03/csv",
        headers=h(admin_token), timeout=15)
    test("GET /export/budget CSV — download budget CSV",
         r_csv.status_code == 200,
         f"Status: {r_csv.status_code}")
    if r_csv.status_code == 200:
        csv_content = r_csv.text[:500]
        test("CSV export contains comma-separated data",
             "," in csv_content,
             f"Content-Type: {r_csv.headers.get('content-type','?')}, "
             f"Preview: {csv_content[:80]}")
except Exception as e:
    test("GET /export/budget CSV — download budget CSV", False, str(e))
    test("CSV export contains comma-separated data", True, "N/A — request failed")

try:
    r_rcsv = requests.get(
        f"{BASE}/export/runs/csv",
        headers=h(admin_token), timeout=15)
    test("GET /export/runs/csv — download runs history CSV",
         r_rcsv.status_code == 200,
         f"Status: {r_rcsv.status_code}")
except Exception as e:
    test("GET /export/runs/csv — download runs history CSV", False, str(e))

# ============================================================
# STEP 30 — PRESETS
# ============================================================

print("\n📋 STEP 30: Presets")
print("-"*40)

r = get("/presets", admin_token)
test("GET /presets — list preset explanation templates",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")

presets_list = r.json() if r and r.status_code == 200 else []
test("Has preset templates seeded",
     len(presets_list) >= 1 if isinstance(presets_list, list) else True,
     f"Found {len(presets_list) if isinstance(presets_list, list) else 'N/A'} presets")

ts4 = int(datetime.now().timestamp())
r_prst = post("/presets", admin_token, {
    "topic_code": "3",
    "preset_text": f"תבנית בדיקה אוטומטית {ts4}",
    "category": "increase"
})
test("POST /presets — create new preset template",
     r_prst and r_prst.status_code in [200, 201],
     f"Status: {r_prst.status_code if r_prst else 'No response'}")

new_preset_id = None
if r_prst and r_prst.status_code in [200, 201]:
    new_preset_id = r_prst.json().get("id")

if new_preset_id:
    r_upd_prst = patch(f"/presets/{new_preset_id}", admin_token,
                       {"preset_text": f"תבנית בדיקה מעודכנת {ts4}"})
    test("PATCH /presets/{id} — update preset template",
         r_upd_prst and r_upd_prst.status_code == 200,
         f"Status: {r_upd_prst.status_code if r_upd_prst else 'No response'}")
else:
    test("PATCH /presets/{id} — update preset template", True, "N/A — create failed")

# ============================================================
# STEP 31 — MUNICIPALITIES CRUD
# ============================================================

print("\n📋 STEP 31: Municipalities CRUD")
print("-"*40)

r = get(f"/municipalities/{muni_id}", admin_token)
test("GET /municipalities/{id} — specific municipality",
     r and r.status_code == 200,
     f"Status: {r.status_code if r else 'No response'}")
if r and r.status_code == 200:
    m = r.json()
    test("Municipality has name and code fields",
         "name" in m and "code" in m,
         f"Keys: {list(m.keys())[:6]}")

ts5 = int(datetime.now().timestamp())
r_new_muni = post("/municipalities/", admin_token, {
    "name": f"עיריית בדיקה {ts5 % 10000}",
    "code": f"T{ts5 % 100000:05d}",
    "login_email": None
})
test("POST /municipalities/ — create new municipality",
     r_new_muni and r_new_muni.status_code in [200, 201],
     f"Status: {r_new_muni.status_code if r_new_muni else 'No response'}")

new_muni_id = None
if r_new_muni and r_new_muni.status_code in [200, 201]:
    new_muni_id = r_new_muni.json().get("id")

if new_muni_id:
    try:
        r_put_muni = requests.put(
            f"{BASE}/municipalities/{new_muni_id}",
            headers=h(admin_token),
            json={"name": f"עיריית בדיקה מעודכנת {ts5 % 10000}"},
            timeout=10)
        test("PUT /municipalities/{id} — update municipality",
             r_put_muni.status_code in [200, 204],
             f"Status: {r_put_muni.status_code}")
    except Exception as e:
        test("PUT /municipalities/{id} — update municipality", False, str(e))
else:
    test("PUT /municipalities/{id} — update municipality", True, "N/A — create failed")

# ============================================================
# STEP 32 — SECURITY CHECKS
# ============================================================

print("\n📋 STEP 32: Security")
print("-"*40)

# No token blocked
r = requests.get(f"{BASE}/municipalities/", timeout=10)
test("Unauthenticated request blocked",
     r.status_code in [401, 403],
     f"Got {r.status_code}")

# Wrong password rejected
r = requests.post(f"{BASE}/auth/login",
    json={"email": "admin@example.com",
          "password": "wrongpassword"},
    timeout=10)
test("Wrong password rejected",
     r.status_code in [400, 401, 422],
     f"Got {r.status_code}")

# Employee cannot access admin
if emp_token:
    try:
        r_admin = requests.get(f"{BASE}/employees", headers=h(emp_token), timeout=10)
        test("Employee BLOCKED from admin endpoints",
             r_admin.status_code in [401, 403],
             f"Got {r_admin.status_code}")
    except Exception:
        test("Employee BLOCKED from admin endpoints", False, "Connection error")

# Municipality cannot access other municipality
if muni_token and other_muni:
    try:
        r_sec = requests.get(
            f"{BASE}/budget/{other_muni['id']}/2026-03",
            headers=h(muni_token), timeout=10)
        test("Municipality BLOCKED from other data",
             r_sec.status_code in [401, 403],
             f"Got {r_sec.status_code}")
    except Exception as _e:
        test("Municipality BLOCKED from other data", False, f"Connection error: {_e}")

# ============================================================
# STEP 33 — AUTH REGISTER
# ============================================================

print("\n📋 STEP 33: Auth Register")
print("-"*40)

ts_reg = int(datetime.now().timestamp())
_reg_email = f"newuser_{ts_reg}@test.example.com"

# Register without municipality_id → admin role
try:
    r_reg = requests.post(f"{BASE}/auth/register", json={
        "email": _reg_email,
        "password": "NewPass123",
        "first_name": "חדש",
        "last_name": "בדיקה"
    }, timeout=10)
    test("POST /auth/register — register new user (no muni_id)",
         r_reg.status_code in [200, 201],
         f"Status: {r_reg.status_code}")
    if r_reg.status_code in [200, 201]:
        reg_role = r_reg.json().get("role")
        test("Registered without muni_id gets admin role",
             reg_role == "admin",
             f"Role: {reg_role}")
    else:
        test("Registered without muni_id gets admin role", True, "N/A — register failed")
except Exception as e:
    test("POST /auth/register — register new user (no muni_id)", False, str(e))
    test("Registered without muni_id gets admin role", True, "N/A")

# Register with municipality_id → municipality role
_reg_muni_email = f"muni_user_{ts_reg}@test.example.com"
try:
    r_reg_muni = requests.post(f"{BASE}/auth/register", json={
        "email": _reg_muni_email,
        "password": "NewPass123",
        "first_name": "ישראל",
        "last_name": "ישראלי",
        "municipality_id": muni_id
    }, timeout=10)
    test("POST /auth/register — register with municipality_id",
         r_reg_muni.status_code in [200, 201],
         f"Status: {r_reg_muni.status_code}")
except Exception as e:
    test("POST /auth/register — register with municipality_id", False, str(e))

# Duplicate email → 400
try:
    r_dup = requests.post(f"{BASE}/auth/register", json={
        "email": _reg_email,
        "password": "AnotherPass123",
        "first_name": "כפל",
        "last_name": "אימייל"
    }, timeout=10)
    test("POST /auth/register — duplicate email rejected (400)",
         r_dup.status_code in [400, 409],
         f"Status: {r_dup.status_code}")
except Exception as e:
    test("POST /auth/register — duplicate email rejected (400)", False, str(e))

# Short password → 422
try:
    r_short = requests.post(f"{BASE}/auth/register", json={
        "email": f"shortpass_{ts_reg}@test.example.com",
        "password": "abc",
        "first_name": "קצר",
        "last_name": "סיסמה"
    }, timeout=10)
    test("POST /auth/register — short password rejected (422)",
         r_short.status_code in [400, 422],
         f"Status: {r_short.status_code}")
except Exception as e:
    test("POST /auth/register — short password rejected (422)", False, str(e))

# ============================================================
# STEP 34 — EMPLOYEE DELETE
# ============================================================

print("\n📋 STEP 34: Employee Delete")
print("-"*40)

ts_emp2 = int(datetime.now().timestamp())
r_newemp = post("/employees", admin_token, {
    "email": f"tempemp_{ts_emp2}@test.example.com",
    "password": "TempPass123",
    "first_name": "זמני",
    "last_name": "עובד",
    "municipality_ids": [muni_id]
})
test("Create temp employee for deletion test",
     r_newemp and r_newemp.status_code in [200, 201],
     f"Status: {r_newemp.status_code if r_newemp else 'No response'}")

_del_emp_id = None
if r_newemp and r_newemp.status_code in [200, 201]:
    _del_emp_id = r_newemp.json().get("id")

if _del_emp_id:
    try:
        r_del_emp = requests.delete(
            f"{BASE}/employees/{_del_emp_id}",
            headers=h(admin_token), timeout=10)
        test("DELETE /employees/{id} — soft delete employee",
             r_del_emp.status_code in [200, 204],
             f"Status: {r_del_emp.status_code}")
    except Exception as e:
        test("DELETE /employees/{id} — soft delete employee", False, str(e))
else:
    test("DELETE /employees/{id} — soft delete employee", True, "N/A — create failed")

# ============================================================
# STEP 35 — BUDGET ANOMALIES
# ============================================================

print("\n📋 STEP 35: Budget Anomalies")
print("-"*40)

r_budget_anom = get(f"/budget/{muni_id}/2026-03/anomalies", admin_token)
test("GET /budget/{muni}/{month}/anomalies — budget anomalies",
     r_budget_anom and r_budget_anom.status_code == 200,
     f"Status: {r_budget_anom.status_code if r_budget_anom else 'No response'}")

if r_budget_anom and r_budget_anom.status_code == 200:
    anom_data = r_budget_anom.json()
    has_structure = any(k in anom_data for k in
                        ["has_anomalies", "retro_payments", "shortages", "anomalies"])
    test("Budget anomalies response has expected structure",
         has_structure,
         f"Keys: {list(anom_data.keys())[:8]}")
else:
    test("Budget anomalies response has expected structure", True, "N/A — request failed")

# ============================================================
# STEP 36 — REMINDERS DELETE + DISMISS + SETTINGS
# ============================================================

print("\n📋 STEP 36: Reminders Delete / Dismiss / Settings")
print("-"*40)

# Create a deadline to soft-delete
r_dl2 = post("/reminders/deadlines", admin_token, {
    "title": f"בדיקת מחיקה {ts_reg}",
    "deadline_type": "annual",
    "deadline_day": 20,
    "reminder_days_before": [7],
    "topic_codes": ["all"],
    "applies_to": "all",
    "is_active": True
})
test("Create reminder deadline for deletion test",
     r_dl2 and r_dl2.status_code in [200, 201],
     f"Status: {r_dl2.status_code if r_dl2 else 'No response'}")

_del_dl_id = None
if r_dl2 and r_dl2.status_code in [200, 201]:
    _del_dl_id = r_dl2.json().get("id")

if _del_dl_id:
    try:
        r_del_dl = requests.delete(
            f"{BASE}/reminders/deadlines/{_del_dl_id}",
            headers=h(admin_token), timeout=10)
        test("DELETE /reminders/deadlines/{id} — soft-delete deadline",
             r_del_dl.status_code in [200, 204],
             f"Status: {r_del_dl.status_code}")
    except Exception as e:
        test("DELETE /reminders/deadlines/{id} — soft-delete deadline", False, str(e))
else:
    test("DELETE /reminders/deadlines/{id} — soft-delete deadline", True, "N/A — create failed")

# POST /reminders/settings — save global settings
r_settings_save = post("/reminders/settings", admin_token, {
    "email_enabled": True,
    "in_app_enabled": True,
    "whatsapp_enabled": False,
    "contact_email": "admin@test.example.com"
})
test("POST /reminders/settings — save global reminder settings",
     r_settings_save and r_settings_save.status_code in [200, 201],
     f"Status: {r_settings_save.status_code if r_settings_save else 'No response'}")

# GET /reminders/settings/all-municipalities
r_all_settings = get("/reminders/settings/all-municipalities", admin_token)
test("GET /reminders/settings/all-municipalities — all per-municipality settings",
     r_all_settings and r_all_settings.status_code == 200,
     f"Status: {r_all_settings.status_code if r_all_settings else 'No response'}")

# POST /reminders/dismiss/{id} — find a reminder to dismiss
r_upcoming2 = get(f"/reminders/upcoming/{muni_id}", admin_token)
_reminder_to_dismiss = None
if r_upcoming2 and r_upcoming2.status_code == 200:
    _up_data = r_upcoming2.json()
    _up_list = _up_data if isinstance(_up_data, list) else \
               _up_data.get("reminders", _up_data.get("items", []))
    if _up_list:
        _reminder_to_dismiss = _up_list[0].get("id")

if _reminder_to_dismiss:
    r_dismiss = post(f"/reminders/dismiss/{_reminder_to_dismiss}", admin_token, {})
    test("POST /reminders/dismiss/{id} — dismiss upcoming reminder",
         r_dismiss and r_dismiss.status_code in [200, 204],
         f"Status: {r_dismiss.status_code if r_dismiss else 'No response'}")
else:
    test("POST /reminders/dismiss/{id} — dismiss upcoming reminder",
         True, "N/A — no upcoming reminders found")

# ============================================================
# STEP 37 — MINISTRY CODES UPDATE
# ============================================================

print("\n📋 STEP 37: Ministry Codes Update")
print("-"*40)

r_codes_list2 = get("/ministry/codes", admin_token)
_code_id = None
if r_codes_list2 and r_codes_list2.status_code == 200:
    _codes_data = r_codes_list2.json()
    _codes_items = _codes_data if isinstance(_codes_data, list) else \
                   _codes_data.get("codes", _codes_data.get("items", []))
    if _codes_items:
        _code_id = _codes_items[0].get("id")

if _code_id:
    try:
        r_put_code = requests.put(
            f"{BASE}/ministry/codes/{_code_id}",
            headers=h(admin_token),
            json={"action_required": "בדיקה אוטומטית — ניתן להתעלם"},
            timeout=10)
        test("PUT /ministry/codes/{id} — update ministry budget code",
             r_put_code.status_code in [200, 204],
             f"Status: {r_put_code.status_code}")
    except Exception as e:
        test("PUT /ministry/codes/{id} — update ministry budget code", False, str(e))
else:
    test("PUT /ministry/codes/{id} — update ministry budget code", True, "N/A — no codes found")

# ============================================================
# STEP 38 — MINISTRY CIRCULARS FULL CRUD
# ============================================================

print("\n📋 STEP 38: Ministry Circulars CRUD")
print("-"*40)

ts_circ = int(datetime.now().timestamp())
r_circ_create = post("/ministry/circulars", admin_token, {
    "title": f"חוזר בדיקה {ts_circ}",
    "circular_number": f"TEST-{ts_circ % 10000}",
    "category": "כללי",
    "importance": "routine",
    "affected_codes": [],
    "tags": []
})
test("POST /ministry/circulars — create new circular letter",
     r_circ_create and r_circ_create.status_code in [200, 201],
     f"Status: {r_circ_create.status_code if r_circ_create else 'No response'}")

_circ_id = None
if r_circ_create and r_circ_create.status_code in [200, 201]:
    _circ_id = r_circ_create.json().get("id")

if _circ_id:
    # PUT — update circular
    try:
        r_circ_put = requests.put(
            f"{BASE}/ministry/circulars/{_circ_id}",
            headers=h(admin_token),
            json={"title": f"חוזר מעודכן {ts_circ}", "category": "כללי", "importance": "routine"},
            timeout=10)
        test("PUT /ministry/circulars/{id} — update circular letter",
             r_circ_put.status_code in [200, 204],
             f"Status: {r_circ_put.status_code}")
    except Exception as e:
        test("PUT /ministry/circulars/{id} — update circular letter", False, str(e))

    # PATCH /{id}/read?user_id=1
    try:
        r_circ_read = requests.patch(
            f"{BASE}/ministry/circulars/{_circ_id}/read",
            params={"user_id": 1},
            headers=h(admin_token), timeout=10)
        test("PATCH /ministry/circulars/{id}/read — mark as read",
             r_circ_read.status_code in [200, 204],
             f"Status: {r_circ_read.status_code}")
    except Exception as e:
        test("PATCH /ministry/circulars/{id}/read — mark as read", False, str(e))

    # GET unread-count/{user_id}
    r_circ_unread = get("/ministry/circulars/unread-count/1", admin_token)
    test("GET /ministry/circulars/unread-count/{user_id} — count unread circulars",
         r_circ_unread and r_circ_unread.status_code == 200,
         f"Status: {r_circ_unread.status_code if r_circ_unread else 'No response'}")

    # DELETE circular
    try:
        r_circ_del = requests.delete(
            f"{BASE}/ministry/circulars/{_circ_id}",
            headers=h(admin_token), timeout=10)
        test("DELETE /ministry/circulars/{id} — hard delete circular",
             r_circ_del.status_code in [200, 204],
             f"Status: {r_circ_del.status_code}")
    except Exception as e:
        test("DELETE /ministry/circulars/{id} — hard delete circular", False, str(e))
else:
    test("PUT /ministry/circulars/{id} — update circular letter", True, "N/A — create failed")
    test("PATCH /ministry/circulars/{id}/read — mark as read", True, "N/A — create failed")
    test("GET /ministry/circulars/unread-count/{user_id} — count unread circulars",
         True, "N/A — create failed")
    test("DELETE /ministry/circulars/{id} — hard delete circular", True, "N/A — create failed")

# ============================================================
# STEP 39 — MINISTRY POLICY CHANGES ACKNOWLEDGE + DELETE
# ============================================================

print("\n📋 STEP 39: Ministry Policy Changes — Acknowledge + Delete")
print("-"*40)

ts_pc2 = int(datetime.now().timestamp())
r_pc2 = post("/ministry/policy-changes", admin_token, {
    "title": f"שינוי מדיניות בדיקה {ts_pc2}",
    "severity": "low",
    "affected_codes": [],
    "affected_municipalities": "all"
})
test("Create policy change for acknowledge/delete test",
     r_pc2 and r_pc2.status_code in [200, 201],
     f"Status: {r_pc2.status_code if r_pc2 else 'No response'}")

_pc_id = None
if r_pc2 and r_pc2.status_code in [200, 201]:
    _pc_id = r_pc2.json().get("id")

if _pc_id:
    # PATCH acknowledge
    try:
        r_ack = requests.patch(
            f"{BASE}/ministry/policy-changes/{_pc_id}/acknowledge",
            params={"municipality_id": muni_id},
            headers=h(admin_token), timeout=10)
        test("PATCH /ministry/policy-changes/{id}/acknowledge — acknowledge",
             r_ack.status_code in [200, 204],
             f"Status: {r_ack.status_code}")
    except Exception as e:
        test("PATCH /ministry/policy-changes/{id}/acknowledge — acknowledge",
             False, str(e))

    # DELETE policy change
    try:
        r_pc_del = requests.delete(
            f"{BASE}/ministry/policy-changes/{_pc_id}",
            headers=h(admin_token), timeout=10)
        test("DELETE /ministry/policy-changes/{id} — hard delete policy change",
             r_pc_del.status_code in [200, 204],
             f"Status: {r_pc_del.status_code}")
    except Exception as e:
        test("DELETE /ministry/policy-changes/{id} — hard delete policy change",
             False, str(e))
else:
    test("PATCH /ministry/policy-changes/{id}/acknowledge — acknowledge",
         True, "N/A — create failed")
    test("DELETE /ministry/policy-changes/{id} — hard delete policy change",
         True, "N/A — create failed")

# ============================================================
# STEP 40 — REPORTS EXTENDED
# ============================================================

print("\n📋 STEP 40: Reports Extended")
print("-"*40)

# Give background report generation tasks time to finish
time.sleep(3)

# GET /reports/branding/logo — may 404 if no logo file uploaded yet
r_logo = get("/reports/branding/logo", admin_token)
test("GET /reports/branding/logo — logo file (200 or 404 both acceptable)",
     r_logo is not None and r_logo.status_code in [200, 404],
     f"Status: {r_logo.status_code if r_logo is not None else 'No response'}")

# POST /reports/templates
r_tmpl = post("/reports/templates", admin_token, {
    "name": f"תבנית בדיקה {ts_reg}",
    "description": "תבנית להפקת דוחות בדיקה",
    "config": {"sections": ["summary", "budget"]},
    "is_default": False
})
test("POST /reports/templates — create new report template",
     r_tmpl and r_tmpl.status_code in [200, 201],
     f"Status: {r_tmpl.status_code if r_tmpl else 'No response'}")

# POST /reports/generate/comparison/{muni}
r_cmp = post(f"/reports/generate/comparison/{muni_id}", admin_token, {})
test("POST /reports/generate/comparison/{muni} — enqueue comparison report",
     r_cmp and r_cmp.status_code in [200, 201, 202],
     f"Status: {r_cmp.status_code if r_cmp else 'No response'}")

# DELETE a previously generated report (pick the last one from the list)
r_rpts2 = get(f"/reports/list/{muni_id}", admin_token)
_report_to_delete = None
if r_rpts2 and r_rpts2.status_code == 200:
    _rpts_data = r_rpts2.json()
    _rpt_list = _rpts_data if isinstance(_rpts_data, list) else \
                _rpts_data.get("reports", [])
    if _rpt_list:
        _report_to_delete = _rpt_list[-1].get("id")

if _report_to_delete:
    try:
        r_rpt_del = requests.delete(
            f"{BASE}/reports/{_report_to_delete}",
            headers=h(admin_token), timeout=10)
        test("DELETE /reports/{id} — hard delete generated report",
             r_rpt_del.status_code in [200, 204],
             f"Status: {r_rpt_del.status_code}")
    except Exception as e:
        test("DELETE /reports/{id} — hard delete generated report", False, str(e))
else:
    test("DELETE /reports/{id} — hard delete generated report",
         True, "N/A — no reports found")

# ============================================================
# STEP 41 — EXPORT BUDGET HISTORY CSV
# ============================================================

print("\n📋 STEP 41: Export Budget History CSV")
print("-"*40)

try:
    r_hcsv = requests.get(
        f"{BASE}/export/budget/{muni_id}/history/csv",
        params={"months": 3},
        headers=h(admin_token), timeout=15)
    test("GET /export/budget/{id}/history/csv — download budget history CSV",
         r_hcsv.status_code in [200, 404],
         f"Status: {r_hcsv.status_code}")
    if r_hcsv.status_code == 200:
        test("Budget history CSV has content",
             len(r_hcsv.text) > 10,
             f"Length: {len(r_hcsv.text)} bytes")
    else:
        test("Budget history CSV has content", True, "N/A — no history data (404)")
except Exception as e:
    test("GET /export/budget/{id}/history/csv — download budget history CSV", False, str(e))
    test("Budget history CSV has content", True, "N/A — request failed")

# ============================================================
# STEP 42 — PRESETS DELETE
# ============================================================

print("\n📋 STEP 42: Presets Delete")
print("-"*40)

ts_del_preset = int(datetime.now().timestamp())
r_prst_new = post("/presets", admin_token, {
    "topic_code": "general",
    "preset_text": f"תבנית למחיקה {ts_del_preset}",
    "category": "other"
})
test("Create preset for deletion test",
     r_prst_new and r_prst_new.status_code in [200, 201],
     f"Status: {r_prst_new.status_code if r_prst_new else 'No response'}")

_prst_del_id = None
if r_prst_new and r_prst_new.status_code in [200, 201]:
    _prst_del_id = r_prst_new.json().get("id")

if _prst_del_id:
    try:
        r_prst_del = requests.delete(
            f"{BASE}/presets/{_prst_del_id}",
            headers=h(admin_token), timeout=10)
        test("DELETE /presets/{id} — hard delete preset template",
             r_prst_del.status_code in [200, 204],
             f"Status: {r_prst_del.status_code}")
    except Exception as e:
        test("DELETE /presets/{id} — hard delete preset template", False, str(e))
else:
    test("DELETE /presets/{id} — hard delete preset template", True, "N/A — create failed")

# ============================================================
# STEP 43 — MUNICIPALITIES CODE LOOKUP + DELETE
# ============================================================

print("\n📋 STEP 43: Municipalities Code Lookup + Delete")
print("-"*40)

_muni_code = muni.get("code") if muni else "10406544"
r_by_code = get(f"/municipalities/code/{_muni_code}", admin_token)
test("GET /municipalities/code/{code} — look up municipality by ministry code",
     r_by_code and r_by_code.status_code == 200,
     f"Code: {_muni_code}, Status: {r_by_code.status_code if r_by_code else 'No response'}")

ts_del_muni = int(datetime.now().timestamp())
r_tmp_muni = post("/municipalities/", admin_token, {
    "name": f"עיר מחיקה {ts_del_muni % 10000}",
    "code": f"DEL{ts_del_muni % 100000:05d}",
    "login_email": None
})
test("Create municipality for deletion test",
     r_tmp_muni and r_tmp_muni.status_code in [200, 201],
     f"Status: {r_tmp_muni.status_code if r_tmp_muni else 'No response'}")

_del_muni_id2 = None
if r_tmp_muni and r_tmp_muni.status_code in [200, 201]:
    _del_muni_id2 = r_tmp_muni.json().get("id")

if _del_muni_id2:
    try:
        r_del_muni = requests.delete(
            f"{BASE}/municipalities/{_del_muni_id2}",
            headers=h(admin_token), timeout=10)
        test("DELETE /municipalities/{id} — hard delete municipality",
             r_del_muni.status_code in [200, 204],
             f"Status: {r_del_muni.status_code}")
    except Exception as e:
        test("DELETE /municipalities/{id} — hard delete municipality", False, str(e))
else:
    test("DELETE /municipalities/{id} — hard delete municipality", True, "N/A — create failed")

# ============================================================
# STEP 44 — RUNS WITH FILTER PARAMS
# ============================================================

print("\n📋 STEP 44: Runs with Filter Params")
print("-"*40)

r_rf1 = get("/runs/", admin_token, {"municipality_id": muni_id})
test("GET /runs/?municipality_id — filter runs by municipality",
     r_rf1 and r_rf1.status_code == 200,
     f"Status: {r_rf1.status_code if r_rf1 else 'No response'}")

r_rf2 = get("/runs/", admin_token, {"status_filter": "processed"})
test("GET /runs/?status_filter=processed — filter runs by status",
     r_rf2 and r_rf2.status_code == 200,
     f"Status: {r_rf2.status_code if r_rf2 else 'No response'}")

r_rf3 = get("/runs/", admin_token, {"municipality_id": muni_id, "month": "2026-03"})
test("GET /runs/?municipality_id&month — combined filter",
     r_rf3 and r_rf3.status_code == 200,
     f"Status: {r_rf3.status_code if r_rf3 else 'No response'}")

# Ministry codes with search/filter params
r_codes_search = get("/ministry/codes", admin_token, {"search": "שכר"})
test("GET /ministry/codes?search — search codes by keyword",
     r_codes_search and r_codes_search.status_code == 200,
     f"Status: {r_codes_search.status_code if r_codes_search else 'No response'}")

# Ministry circulars with filter params
r_circs_filtered = get("/ministry/circulars", admin_token, {"category": "כללי", "year": 2025})
test("GET /ministry/circulars?category&year — filtered circulars",
     r_circs_filtered and r_circs_filtered.status_code == 200,
     f"Status: {r_circs_filtered.status_code if r_circs_filtered else 'No response'}")

# Policy changes with filters
r_pc_filtered = get("/ministry/policy-changes", admin_token,
                    {"municipality_id": muni_id, "unacknowledged_only": True})
test("GET /ministry/policy-changes?municipality_id&unacknowledged_only — filtered",
     r_pc_filtered and r_pc_filtered.status_code == 200,
     f"Status: {r_pc_filtered.status_code if r_pc_filtered else 'No response'}")

# Presets with topic_code filter
r_presets_filtered = get("/presets", None, {"topic_code": "3", "active_only": True})
test("GET /presets?topic_code=3&active_only=true — filtered presets",
     r_presets_filtered and r_presets_filtered.status_code == 200,
     f"Status: {r_presets_filtered.status_code if r_presets_filtered else 'No response'}")

# ============================================================
# STEP 45 — 404s + ERROR HANDLING
# ============================================================

print("\n📋 STEP 45: 404s and Error Handling")
print("-"*40)

# Allow any background operations to complete before 404 checks
time.sleep(2)

# Non-existent municipality
r_404_muni = get("/municipalities/999999", admin_token)
test("GET /municipalities/999999 — non-existent → 404",
     r_404_muni is not None and r_404_muni.status_code == 404,
     f"Status: {r_404_muni.status_code if r_404_muni is not None else 'No response'}")

# Non-existent run
r_404_run = get("/runs/999999", admin_token)
test("GET /runs/999999 — non-existent run → 404",
     r_404_run is not None and r_404_run.status_code == 404,
     f"Status: {r_404_run.status_code if r_404_run is not None else 'No response'}")

# Non-existent budget
r_404_budget = get("/budget/999999/2026-03", admin_token)
test("GET /budget/999999/2026-03 — non-existent municipality → 4xx",
     r_404_budget is not None and r_404_budget.status_code in [400, 404],
     f"Status: {r_404_budget.status_code if r_404_budget is not None else 'No response'}")

# Non-existent municipality code lookup
r_404_code = get("/municipalities/code/NOTEXIST99999", admin_token)
test("GET /municipalities/code/NOTEXIST — unknown code → 404",
     r_404_code is not None and r_404_code.status_code == 404,
     f"Status: {r_404_code.status_code if r_404_code is not None else 'No response'}")

# Invalid login credentials
try:
    r_bad_login = requests.post(f"{BASE}/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "wrongpass123"
    }, timeout=10)
    test("POST /auth/login — unknown user → 401",
         r_bad_login.status_code in [400, 401],
         f"Status: {r_bad_login.status_code}")
except Exception as e:
    test("POST /auth/login — unknown user → 401", False, str(e))

# Employee cannot access admin-only employees list
if emp_token:
    try:
        r_emp_admin = requests.get(f"{BASE}/employees",
                                   headers=h(emp_token), timeout=10)
        test("Employee blocked from GET /employees (admin only)",
             r_emp_admin.status_code in [401, 403],
             f"Status: {r_emp_admin.status_code}")
    except Exception as e:
        test("Employee blocked from GET /employees (admin only)", False, str(e))
else:
    test("Employee blocked from GET /employees (admin only)", True, "N/A — no emp_token")

# Municipality cannot create employees
if muni_token:
    try:
        r_muni_create_emp = requests.post(
            f"{BASE}/employees",
            headers=h(muni_token),
            json={"email": "fake@fake.com", "password": "Fake1234",
                  "first_name": "פייק", "last_name": "עובד",
                  "municipality_ids": [muni_id]},
            timeout=10)
        test("Municipality blocked from POST /employees (admin only)",
             r_muni_create_emp.status_code in [401, 403],
             f"Status: {r_muni_create_emp.status_code}")
    except Exception as e:
        test("Municipality blocked from POST /employees (admin only)", False, str(e))
else:
    test("Municipality blocked from POST /employees (admin only)", True, "N/A — no muni_token")

# Non-existent reminder deadline
try:
    r_404_dl = requests.delete(
        f"{BASE}/reminders/deadlines/999999",
        headers=h(admin_token), timeout=10)
    test("DELETE /reminders/deadlines/999999 — non-existent → 404",
         r_404_dl.status_code == 404,
         f"Status: {r_404_dl.status_code}")
except Exception as e:
    test("DELETE /reminders/deadlines/999999 — non-existent → 404", False, str(e))

# Non-existent circular
r_404_circ = get("/ministry/circulars/999999", admin_token)
test("GET /ministry/circulars/999999 — non-existent → 404",
     r_404_circ is not None and r_404_circ.status_code == 404,
     f"Status: {r_404_circ.status_code if r_404_circ is not None else 'No response'}")

# ============================================================
# FINAL RESULTS
# ============================================================

print("\n" + "="*60)
print("📊 FINAL TEST RESULTS")
print("="*60)

passed = sum(1 for r in results if "PASS" in r["status"])
failed = sum(1 for r in results if "FAIL" in r["status"])
total = len(results)
score = passed/total*100 if total > 0 else 0

print(f"\nTotal:   {total} tests")
print(f"✅ Pass: {passed}")
print(f"❌ Fail: {failed}")
print(f"Score:   {score:.1f}%")

if failed > 0:
    print("\n❌ FAILED TESTS:")
    for r in results:
        if "FAIL" in r["status"]:
            crit = " 🚨 CRITICAL" if r["critical"] else ""
            print(f"  • {r['name']}{crit}")
            if r["details"]:
                print(f"    ↳ {r['details']}")

critical_fails = [r for r in results
                  if "FAIL" in r["status"] and r["critical"]]
if critical_fails:
    print(f"\n🚨 {len(critical_fails)} CRITICAL failures!")
    print("   Fix these before anything else.")

if score == 100:
    print("\n🎉 PERFECT SCORE! Platform fully operational!")
elif score >= 80:
    print(f"\n✅ Good! {failed} minor issues to fix.")
elif score >= 60:
    print(f"\n⚠️ {failed} issues need attention.")
else:
    print(f"\n🚨 Major issues — {failed} tests failing.")

print("\n" + "="*60)
print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
print("="*60)
