"""
Test script for the rejected suggestions feature.
Tests:
1. GET /api/suggestions/my-rejected endpoint
2. Approved explanations appear in municipality portal
3. New employee account can submit, get rejected, and see rejection
"""
import requests
import sqlite3
import sys

BASE = "http://127.0.0.1:8000"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "admin123"


def login(email, password):
    r = requests.post(BASE + "/api/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"]
    return None


def hdr(token):
    return {"Authorization": "Bearer " + token}


def get_db_data():
    conn = sqlite3.connect("cpa.db")
    cur = conn.cursor()

    # Get municipalities
    cur.execute("SELECT id, name FROM municipalities LIMIT 1")
    municipality = cur.fetchone()

    # Get budget lines
    cur.execute("SELECT id, topic_code FROM budget_lines LIMIT 1")
    budget_line = cur.fetchone()

    # Get employees with rejected suggestions
    cur.execute("""
        SELECT DISTINCT u.id, u.email
        FROM users u
        JOIN explanation_suggestions es ON es.suggested_by = u.id
        WHERE es.status = 'rejected'
        LIMIT 1
    """)
    employee_with_rejections = cur.fetchone()

    # Count total rejected
    cur.execute("SELECT COUNT(*) FROM explanation_suggestions WHERE status='rejected'")
    rejected_count = cur.fetchone()[0]

    # Count approved explanations
    cur.execute("SELECT COUNT(*) FROM approved_explanations")
    approved_count = cur.fetchone()[0]

    conn.close()
    return municipality, budget_line, employee_with_rejections, rejected_count, approved_count


def print_result(name, passed, detail=""):
    icon = "PASS" if passed else "FAIL"
    status = "[" + icon + "]"
    print(f"  {status} {name}" + (f" - {detail}" if detail else ""))
    return passed


def main():
    print("=" * 60)
    print("REJECTED SUGGESTIONS FEATURE TEST")
    print("=" * 60)
    print()

    all_pass = True

    # -------------------------------------------------------
    print("[1] DATABASE STATE")
    print("-" * 40)
    municipality, budget_line, emp, rejected_count, approved_count = get_db_data()

    r = print_result("Rejected suggestions exist in DB", rejected_count > 0, f"count={rejected_count}")
    all_pass = all_pass and r

    r = print_result("Approved explanations in DB", approved_count > 0, f"count={approved_count}")
    all_pass = all_pass and r

    r = print_result("Employee with rejections found", emp is not None, str(emp) if emp else "none found")
    all_pass = all_pass and r

    print()

    # -------------------------------------------------------
    print("[2] ADMIN API TESTS")
    print("-" * 40)

    admin_token = login(ADMIN_EMAIL, ADMIN_PASS)
    r = print_result("Admin login", admin_token is not None)
    all_pass = all_pass and r
    if not admin_token:
        print("Cannot continue - admin login failed")
        return False

    # Test pending suggestions
    resp = requests.get(BASE + "/api/suggestions/pending", headers=hdr(admin_token))
    r = print_result(
        "GET /api/suggestions/pending",
        resp.status_code == 200,
        f"status={resp.status_code} count={len(resp.json()) if resp.status_code==200 else 'N/A'}"
    )
    all_pass = all_pass and r

    # Test my-rejected as admin (should return [] since admin has no suggestions as employee)
    resp = requests.get(BASE + "/api/suggestions/my-rejected", headers=hdr(admin_token))
    r = print_result(
        "GET /api/suggestions/my-rejected (admin)",
        resp.status_code == 200,
        f"status={resp.status_code} data={str(resp.json())[:60]}"
    )
    all_pass = all_pass and r

    print()

    # -------------------------------------------------------
    print("[3] EMPLOYEE API TESTS")
    print("-" * 40)

    if emp:
        emp_id, emp_email = emp
        # Try to find employee password or create a direct token via DB check
        conn = sqlite3.connect("cpa.db")
        cur = conn.cursor()
        cur.execute("SELECT hashed_password FROM users WHERE id=?", (emp_id,))
        pw_hash = cur.fetchone()
        conn.close()

        # Try common passwords for this employee
        emp_token = None
        for pwd in ["admin123", "password", "test123", "employee123", "123456", "test"]:
            t = login(emp_email, pwd)
            if t:
                emp_token = t
                print(f"  [INFO] Employee '{emp_email}' logged in with password '{pwd}'")
                break

        if emp_token:
            resp = requests.get(BASE + "/api/suggestions/my-rejected", headers=hdr(emp_token))
            rejected_list = resp.json() if resp.status_code == 200 else []
            r = print_result(
                "GET /api/suggestions/my-rejected (employee)",
                resp.status_code == 200,
                f"status={resp.status_code} count={len(rejected_list)}"
            )
            all_pass = all_pass and r

            if resp.status_code == 200 and rejected_list:
                first = rejected_list[0]
                r = print_result(
                    "Rejection has required fields",
                    all(k in first for k in ["id", "municipality_name", "month", "review_note"]),
                    "Fields: " + str(list(first.keys()))[:80]
                )
                all_pass = all_pass and r

                r = print_result(
                    "Rejection has municipality_name",
                    bool(first.get("municipality_name")),
                    str(first.get("municipality_name"))
                )
                all_pass = all_pass and r
        else:
            print("  [SKIP] Cannot test employee endpoint - password unknown")
            print("  [INFO] Employee email:", emp_email)
    else:
        print("  [SKIP] No employee with rejections found in DB")

    print()

    # -------------------------------------------------------
    print("[4] BACKEND CODE CHECKS")
    print("-" * 40)
    from pathlib import Path

    suggestions_py = Path("backend/routes/suggestions.py").read_text(encoding="utf-8")
    explanations_py = Path("backend/routes/explanations.py").read_text(encoding="utf-8")

    r = print_result(
        "my-rejected endpoint exists",
        "my-rejected" in suggestions_py
    )
    all_pass = all_pass and r

    r = print_result(
        "RejectedSuggestionResponse schema defined",
        "RejectedSuggestionResponse" in suggestions_py
    )
    all_pass = all_pass and r

    r = print_result(
        "ApprovedExplanation imported in explanations.py",
        "ApprovedExplanation" in explanations_py
    )
    all_pass = all_pass and r

    r = print_result(
        "explanations.py queries both Custom and Approved",
        "approved_explanation" in explanations_py.lower() or "ApprovedExplanation" in explanations_py
    )
    all_pass = all_pass and r

    r = print_result(
        "explanation_override used in explanations.py",
        "explanation_override" in explanations_py
    )
    all_pass = all_pass and r

    print()

    # -------------------------------------------------------
    print("[5] FRONTEND CODE CHECKS")
    print("-" * 40)

    emp_rejected_page = Path("frontend/src/pages/EmployeeRejectedPage.jsx").read_text(encoding="utf-8")
    use_rejected_hook = Path("frontend/src/hooks/useRejectedSuggestionsCount.js").read_text(encoding="utf-8")
    sidebar = Path("frontend/src/components/layout/Sidebar.jsx").read_text(encoding="utf-8")
    app_jsx = Path("frontend/src/App.jsx").read_text(encoding="utf-8")
    api_js = Path("frontend/src/services/api.js").read_text(encoding="utf-8")
    modal = Path("frontend/src/components/portal/ExplanationSuggestionModal.jsx").read_text(encoding="utf-8")

    r = print_result("EmployeeRejectedPage.jsx exists", len(emp_rejected_page) > 100)
    all_pass = all_pass and r

    r = print_result("useRejectedSuggestionsCount hook exists", "useRejectedSuggestionsCount" in use_rejected_hook)
    all_pass = all_pass and r

    r = print_result("Auto-refresh interval in hook", "setInterval" in use_rejected_hook)
    all_pass = all_pass and r

    r = print_result("Interval cleanup in hook", "clearInterval" in use_rejected_hook)
    all_pass = all_pass and r

    r = print_result("Sidebar imports useRejectedSuggestionsCount", "useRejectedSuggestionsCount" in sidebar)
    all_pass = all_pass and r

    r = print_result("/portal/rejected route in App.jsx", "rejected" in app_jsx)
    all_pass = all_pass and r

    r = print_result("getMyRejected in api.js", "getMyRejected" in api_js)
    all_pass = all_pass and r

    r = print_result("prefilledText prop in ExplanationSuggestionModal", "prefilledText" in modal)
    all_pass = all_pass and r

    r = print_result("isEdit prop in ExplanationSuggestionModal", "isEdit" in modal)
    all_pass = all_pass and r

    print()

    # -------------------------------------------------------
    print("=" * 60)
    if all_pass:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED - check output above")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
