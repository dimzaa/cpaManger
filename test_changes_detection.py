#!/usr/bin/env python3
"""
Test script to verify change detection is working between Feb and March 2026
"""
import sys
import json
from datetime import datetime
sys.path.insert(0, '.')

from backend.database import SessionLocal, engine, Base
from backend.models import Municipality, MonthlyRun, BudgetLine
from backend.routes.budget import calculate_month_changes
from backend.utils.serializers import bytes_to_string

# Initialize database
Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    # Get municipality
    mun = db.query(Municipality).filter(Municipality.code == '10406544').first()
    if not mun:
        print("❌ Municipality 10406544 not found")
        sys.exit(1)
    
    print(f"✅ Found municipality: {bytes_to_string(mun.name)} (ID: {mun.id})")
    
    # Get both months
    feb_run = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == mun.id,
        MonthlyRun.month == "2026-02"
    ).first()
    
    mar_run = db.query(MonthlyRun).filter(
        MonthlyRun.municipality_id == mun.id,
        MonthlyRun.month == "2026-03"
    ).first()
    
    if not feb_run:
        print("❌ February 2026 data not found")
    else:
        print(f"✅ February 2026 run found (ID: {feb_run.id})")
        feb_lines = db.query(BudgetLine).filter(BudgetLine.run_id == feb_run.id).all()
        print(f"   - Total budget lines: {len(feb_lines)}")
        
        # Group by topic code
        feb_by_topic = {}
        for line in feb_lines:
            code = bytes_to_string(line.topic_code)
            if code not in feb_by_topic:
                feb_by_topic[code] = {"name": "", "count": 0, "total": 0}
            feb_by_topic[code]["name"] = bytes_to_string(line.budget_topic)
            feb_by_topic[code]["count"] += 1
            feb_by_topic[code]["total"] += float(line.amount)
        
        print(f"   - Groups: {len(feb_by_topic)}")
        for code in sorted(feb_by_topic.keys()):
            data = feb_by_topic[code]
            print(f"      קוד {code} ({data['name']}): {data['count']} items, ₪{data['total']:,.2f}")
    
    if not mar_run:
        print("❌ March 2026 data not found")
    else:
        print(f"✅ March 2026 run found (ID: {mar_run.id})")
        mar_lines = db.query(BudgetLine).filter(BudgetLine.run_id == mar_run.id).all()
        print(f"   - Total budget lines: {len(mar_lines)}")
        
        # Group by topic code
        mar_by_topic = {}
        for line in mar_lines:
            code = bytes_to_string(line.topic_code)
            if code not in mar_by_topic:
                mar_by_topic[code] = {"name": "", "count": 0, "total": 0}
            mar_by_topic[code]["name"] = bytes_to_string(line.budget_topic)
            mar_by_topic[code]["count"] += 1
            mar_by_topic[code]["total"] += float(line.amount)
        
        print(f"   - Groups: {len(mar_by_topic)}")
        for code in sorted(mar_by_topic.keys()):
            data = mar_by_topic[code]
            print(f"      קוד {code} ({data['name']}): {data['count']} items, ₪{data['total']:,.2f}")
    
    # Test change detection
    print("\n📊 CHANGE DETECTION TEST:")
    changes = calculate_month_changes(db, mun.id, "2026-03")
    
    if changes:
        print(f"✅ Changes detected!")
        print(f"   Previous month: {changes['previous_month']}")
        print(f"   Has changes: {changes['has_changes']}")
        print(f"\n   Changes by topic:")
        for code, change in sorted(changes['changes_by_topic'].items()):
            print(f"\n      קוד {code} - {change['topic_name']}:")
            print(f"         Items: {change['prev_lines_count']} → {change['curr_lines_count']} ({change['items_change']:+d})")
            print(f"         Amount: ₪{change['prev_total']:,.2f} → ₪{change['curr_total']:,.2f}")
            print(f"         Change: ₪{change['amount_change']:+,.2f} ({change['amount_change_pct']:+.1f}%)")
    else:
        print("⚠️ No changes detected (or function returned None)")
    
    print("\n✅ Test completed successfully!")

except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    db.close()
