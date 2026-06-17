#!/usr/bin/env python3
"""Add budget data for 2026-04 to municipality 4"""
from backend.database import SessionLocal
from backend.models.monthly_run import MonthlyRun
from backend.models.budget_line import BudgetLine
from datetime import datetime

db = SessionLocal()

# Check if 2026-04 already exists
existing = db.query(MonthlyRun).filter(
    MonthlyRun.municipality_id == 4,
    MonthlyRun.month == '2026-04'
).first()

if existing:
    print("✅ 2026-04 already exists for municipality 4")
else:
    # Get reference run from 2026-03
    ref_run = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == 4,
        MonthlyRun.month == '2026-03'
    ).first()
    
    if not ref_run:
        print("❌ Reference run 2026-03 not found")
        db.close()
        exit(1)
    
    # Create new monthly run for 2026-04
    new_run = MonthlyRun(
        municipality_id=4,
        month='2026-04',
        year=2026,
        status='processed',
        uploaded_at=datetime.now()
    )
    db.add(new_run)
    db.commit()
    print(f"✅ Created MonthlyRun for 2026-04 (ID: {new_run.id})")
    
    # Copy budget lines from reference run
    ref_lines = db.query(BudgetLine).filter(
        BudgetLine.run_id == ref_run.id
    ).all()
    
    count = 0
    for line in ref_lines:
        new_line = BudgetLine(
            run_id=new_run.id,
            municipality_id=4,  # Add municipality_id
            budget_topic=line.budget_topic,
            topic_code=line.topic_code,
            amount=line.amount * 1.02,  # Slight variation
            line_type=line.line_type,
            period_month='2026-04',
            is_retro=False,
            notes=f'Seeded from 2026-03 data'
        )
        db.add(new_line)
        count += 1
    
    db.commit()
    print(f"✅ Created {count} budget lines for 2026-04")

db.close()
print("\n✅ Database updated! Try: /municipality/4?month=2026-04")
