import io

import pandas as pd

from backend.models import BudgetLineInstitution


def _mock_parse_result_without_direct_institution():
    invoice_df = pd.DataFrame(
        [
            {
                "municipality_code": "7001",
                "municipality_name": "עיר בדיקה 2",
                "month": 3,
                "year": 2026,
            }
        ]
    )

    breakdown_df = pd.DataFrame(
        [
            {
                "municipality_code": "7001",
                "month": 3,
                "current_month": 3,
                "period_month": 3,
                "period_year": 2026,
                "topic_code": "361",
                "budget_topic": "חטיבה עליונה",
                "amount": 1000.0,
                "line_type": "regular",
                "is_retro": False,
            }
        ]
    )

    return {
        "temp_dir": "C:/tmp/test",
        "invoice_df": invoice_df,
        "breakdown_df": breakdown_df,
        "municipalities": ["7001"],
    }


def _mock_analysis():
    return {
        "summary": {"balanced_runs": 1, "unbalanced_runs": 0},
        "results_by_municipality": {
            "7001": {
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


def test_upload_fallback_allocates_by_roster_children(client, db, auth_headers_admin, monkeypatch):
    from backend.routes import upload as upload_route

    monkeypatch.setattr(upload_route.FileParser, "parse_zip", lambda _: _mock_parse_result_without_direct_institution())
    monkeypatch.setattr(
        upload_route.FileParser,
        "extract_institution_roster",
        lambda _: {
            "source_file": "SHARATIM.csv",
            "institutions": [
                {"institution_code": "X01", "institution_name": "תיכון א", "num_children": 80},
                {"institution_code": "X02", "institution_name": "תיכון ב", "num_children": 20},
            ],
        },
    )
    monkeypatch.setattr(upload_route.CrossReferenceAnalysis, "analyze_all_months", lambda *_: _mock_analysis())

    response = client.post(
        "/api/upload",
        headers=auth_headers_admin,
        files={"file": ("test.zip", io.BytesIO(b"fake zip"), "application/zip")},
    )

    assert response.status_code == 200
    rows = db.query(BudgetLineInstitution).order_by(BudgetLineInstitution.institution_code.asc()).all()
    assert len(rows) == 2

    assert rows[0].institution_code == "X01"
    assert float(rows[0].amount) == 800.0
    assert rows[0].source_file == "proportional:SHARATIM.csv"

    assert rows[1].institution_code == "X02"
    assert float(rows[1].amount) == 200.0
    assert rows[1].source_file == "proportional:SHARATIM.csv"
