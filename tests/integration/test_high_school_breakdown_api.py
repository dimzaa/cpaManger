from backend.models import MonthlyRun, BudgetLine, BudgetLineInstitution
from backend.models.user import User, UserRole
from backend.services.auth import AuthService


def _seed_run_with_breakdown(db, municipality_id):
    run = MonthlyRun(
        municipality_id=municipality_id,
        month="2026-03",
        year=2026,
        status="processed",
        invoice_total=2000,
        breakdown_total=2000,
        is_balanced=True,
        difference=0,
    )
    db.add(run)
    db.flush()

    line = BudgetLine(
        run_id=run.id,
        municipality_id=municipality_id,
        budget_topic="חטיבה עליונה",
        topic_code="361",
        amount=2000,
        period_month="2026-03",
        current_month="2026-03",
        line_type="regular",
        is_retro=False,
    )
    db.add(line)
    db.flush()

    db.add_all(
        [
            BudgetLineInstitution(
                budget_line_id=line.id,
                institution_code="S1",
                institution_name="תיכון 1",
                amount=1400,
                num_children=70,
                participation_pct=70,
                source_file="direct.csv",
            ),
            BudgetLineInstitution(
                budget_line_id=line.id,
                institution_code="S2",
                institution_name="תיכון 2",
                amount=600,
                num_children=30,
                participation_pct=30,
                source_file="direct.csv",
            ),
        ]
    )

    db.commit()
    db.refresh(run)
    return run


def test_topic_institutions_endpoint_returns_sorted_rows(client, db, auth_headers_muni, municipality_record):
    run = _seed_run_with_breakdown(db, municipality_record.id)

    response = client.get(
        f"/api/budget/runs/{run.id}/municipalities/{municipality_record.id}/institutions",
        params={"topic_code": "361"},
        headers=auth_headers_muni,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["topic_code"] == "361"
    assert len(data["institutions"]) == 2
    assert data["institutions"][0]["institution_code"] == "S1"
    assert data["institutions"][0]["amount"] == 1400


def test_high_school_breakdown_endpoint_returns_topic_map(client, db, auth_headers_muni, municipality_record):
    run = _seed_run_with_breakdown(db, municipality_record.id)

    response = client.get(
        f"/api/budget/runs/{run.id}/municipalities/{municipality_record.id}/high-school-breakdown",
        headers=auth_headers_muni,
    )

    assert response.status_code == 200
    data = response.json()
    assert "361" in data["topics"]
    assert data["topics"]["361"]["total"] == 2000


def test_high_school_breakdown_forbidden_for_other_municipality_user(client, db, municipality_record):
    run = _seed_run_with_breakdown(db, municipality_record.id)

    outsider = User(
        email="outsider@test.com",
        hashed_password=AuthService.hash_password("OutPass1"),
        first_name="Out",
        last_name="Sider",
        role=UserRole.MUNICIPALITY,
        municipality_id=municipality_record.id + 99,
        is_active=True,
    )
    db.add(outsider)
    db.commit()
    db.refresh(outsider)

    token = AuthService.create_token(
        user_id=outsider.id,
        email=outsider.email,
        role=outsider.role.value if hasattr(outsider.role, "value") else outsider.role,
        municipality_id=outsider.municipality_id,
    )

    response = client.get(
        f"/api/budget/runs/{run.id}/municipalities/{municipality_record.id}/high-school-breakdown",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
