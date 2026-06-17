import io

import pandas as pd

from backend.models import BudgetLineInstitution


def _mock_parse_result(with_direct_institution=True):
    invoice_df = pd.DataFrame(
        [
            {
                "municipality_code": "7000",
                "municipality_name": "עיר בדיקה",
                "month": 3,
                "year": 2026,
            }
        ]
    )

    row = {
        "municipality_code": "7000",
        "month": 3,
        "current_month": 3,
        "period_month": 3,
        "period_year": 2026,
        "topic_code": "361",
        "budget_topic": "חטיבה עליונה",
        "amount": 1000.0,
        "line_type": "regular",
        "is_retro": False,
        "children_count": 100,
        "percentage": 100.0,
        "source_file": "breakdown.csv",
    }
    if with_direct_institution:
        row["institution_code"] = "A123"
        row["institution_name"] = "תיכון אלפא"

    breakdown_df = pd.DataFrame([row])

    return {
        "temp_dir": "C:/tmp/test",
        "invoice_df": invoice_df,
        "breakdown_df": breakdown_df,
        "municipalities": ["7000"],
    }


def _mock_analysis():
    return {
        "summary": {"balanced_runs": 1, "unbalanced_runs": 0},
        "results_by_municipality": {
            "7000": {
                "months": {
                    3: {
                        "invoice_total": 1000.0,
                        "breakdown_total": 1000.0,
                        "is_balanced": True,
                        "difference": 0.0,
                    }
                }
            }
        },
    }


def test_upload_creates_direct_institution_rows(client, db, auth_headers_admin, monkeypatch):
    from backend.routes import upload as upload_route

    monkeypatch.setattr(upload_route.FileParser, "parse_zip", lambda _: _mock_parse_result(with_direct_institution=True))
    monkeypatch.setattr(upload_route.FileParser, "extract_institution_roster", lambda _: {"source_file": "SHARATIM.csv", "institutions": []})
    monkeypatch.setattr(upload_route.CrossReferenceAnalysis, "analyze_all_months", lambda *_: _mock_analysis())

    response = client.post(
        "/api/upload",
        headers=auth_headers_admin,
        files={"file": ("test.zip", io.BytesIO(b"fake zip"), "application/zip")},
    )

    assert response.status_code == 200
    rows = db.query(BudgetLineInstitution).all()
    assert len(rows) == 1
    assert rows[0].institution_code == "A123"
    assert rows[0].institution_name == "תיכון אלפא"
    assert float(rows[0].amount) == 1000.0
    assert rows[0].source_file == "breakdown.csv"
