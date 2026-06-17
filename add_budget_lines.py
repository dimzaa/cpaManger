#!/usr/bin/env python3
"""Add budget lines for 2026-04"""
from backend.database import SessionLocal
from backend.models.monthly_run import MonthlyRun
from backend.models.budget_line import BudgetLine

db = SessionLocal()

# Get the 2026-04 run
run = db.query(MonthlyRun).filter(
    MonthlyRun.municipality_id == 4,
    MonthlyRun.month == '2026-04'
).first()

if not run:
    print("❌ 2026-04 run not found")
    db.close()
    exit(1)

# Get reference lines from 2026-03
ref_run = db.query(MonthlyRun).filter(
    MonthlyRun.municipality_id == 4,
    MonthlyRun.month == '2026-03'
).first()

ref_lines = db.query(BudgetLine).filter(
    BudgetLine.run_id == ref_run.id
).all()

# Add budget lines to 2026-04
count = 0
for line in ref_lines:
    new_line = BudgetLine(
        run_id=run.id,
        municipality_id=4,
        budget_topic=line.budget_topic,
        topic_code=line.topic_code,
        amount=line.amount * 1.02,  # Slight variation
        line_type=line.line_type,
        period_month='2026-04',
        current_month='2026-04',  # Add current_month
        is_retro=False,
        notes='Seeded from 2026-03 data'
    )
    db.add(new_line)
    count += 1

db.commit()
print(f"✅ Added {count} budget lines to 2026-04")

# Verify
lines = db.query(BudgetLine).filter(BudgetLine.run_id == run.id).all()
print(f"✅ Verification: {len(lines)} lines now in 2026-04")

db.close()
