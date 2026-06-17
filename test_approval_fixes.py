#!/usr/bin/env python3
"""
Test script to verify the three approval system fixes:
1. Field name mismatch (explanation_text → custom_text)
2. NULL validation in approve endpoint
3. Color coding and comparison display in AdminApprovalsPage
"""

import os
import sys
import sqlite3
from pathlib import Path

def print_section(title):
    print(f"\n{'='*80}")
    print(f"🔍 {title}")
    print(f"{'='*80}\n")

def check_database():
    """Check what's in the explanation_suggestions table"""
    print_section("DATABASE CONTENT CHECK")
    
    db_path = Path("./cpa.db")
    if not db_path.exists():
        print("❌ Database not found at ./cpa.db")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(explanation_suggestions);")
        columns = cursor.fetchall()
        print("📋 Table structure (explanation_suggestions):")
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"   • {col_name}: {col_type} ({nullable})")
        
        # Check data
        cursor.execute("""
            SELECT 
                id, 
                suggestion_type, 
                custom_text, 
                preset_id,
                status,
                suggested_by
            FROM explanation_suggestions
            LIMIT 5
        """)
        suggestions = cursor.fetchall()
        
        print(f"\n📊 Recent suggestions ({len(suggestions)} shown):")
        for s in suggestions:
            sid, stype, custom_text, preset_id, status, suggested_by = s
            text_status = f"✅ {len(custom_text)} chars" if custom_text else "❌ NULL"
            print(f"   • ID {sid}: type={stype}, text={text_status}, status={status}")
        
        # Check for broken suggestions (custom_text is NULL)
        cursor.execute("""
            SELECT COUNT(*) FROM explanation_suggestions 
            WHERE suggestion_type='custom' AND custom_text IS NULL
        """)
        broken = cursor.fetchone()[0]
        if broken > 0:
            print(f"\n⚠️  FOUND {broken} BROKEN CUSTOM SUGGESTIONS (NULL custom_text)")
            print("   These need to be fixed before they can be approved")
        
        # Check approved_explanations table
        cursor.execute("""
            SELECT 
                id,
                budget_line_id,
                municipality_id,
                month,
                topic_code,
                final_text,
                source,
                suggestion_id
            FROM approved_explanations
            LIMIT 3
        """)
        approved = cursor.fetchall()
        print(f"\n✅ Approved explanations ({len(approved)} shown):")
        for a in approved:
            aid, bl_id, mun_id, month, code, final_text, source, sug_id = a
            text_preview = (final_text[:30] + "...") if final_text and len(final_text) > 30 else final_text
            print(f"   • ID {aid}: source={source}, ref_suggestion={sug_id}, text={text_preview}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_backend_code():
    """Verify backend fixes are in place"""
    print_section("BACKEND CODE CHECKS")
    
    suggestions_path = Path("./backend/routes/suggestions.py")
    if not suggestions_path.exists():
        print("❌ suggestions.py not found")
        return False
    
    content = suggestions_path.read_text(encoding='utf-8')
    
    checks = [
        ("NULL Validation", "cannot approve suggestion {suggestion_id}: final_text is empty" in content or "not final_text or not final_text.strip()" in content),
        ("Error Handling", "db.rollback()" in content and "status.HTTP_500_INTERNAL_SERVER_ERROR" in content),
        ("Proper Response Enrichment", "SuggestionDetailResponse(" in content and "preset_text=preset_text" in content),
    ]
    
    print("Backend /api/suggestions/pending endpoint:")
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
    
    return all(result for _, result in checks)

def check_frontend_code():
    """Verify frontend fixes are in place"""
    print_section("FRONTEND CODE CHECKS")
    
    # Check ExplanationSuggestionModal
    modal_path = Path("./frontend/src/components/portal/ExplanationSuggestionModal.jsx")
    if not modal_path.exists():
        print("❌ ExplanationSuggestionModal.jsx not found")
        return False
    
    modal_content = modal_path.read_text(encoding='utf-8')
    modal_uses_custom_text = "custom_text:" in modal_content
    
    # Check AdminApprovalsPage  
    approvals_path = Path("./frontend/src/pages/AdminApprovalsPage.jsx")
    if not approvals_path.exists():
        print("❌ AdminApprovalsPage.jsx not found")
        return False
    
    approvals_content = approvals_path.read_text(encoding='utf-8')
    approvals_checks = [
        ("Shows both explanations", "הסבר מוצע מהעובד" in approvals_content and "suggestion.custom_text || suggestion.preset_text" in approvals_content),
        ("Color coding for edits", "previous_text" in approvals_content and "bg-amber" in approvals_content),
        ("Better error messages", "err.response?.data?.detail" in approvals_content),
        ("Null text validation", "!suggestion.custom_text && !suggestion.preset_text" in approvals_content),
    ]
    
    print("Frontend ExplanationSuggestionModal.jsx:")
    print(f"   {'✅' if modal_uses_custom_text else '❌'} Uses 'custom_text' field (not 'explanation_text')")
    
    print("\nFrontend AdminApprovalsPage.jsx:")
    for check_name, result in approvals_checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
    
    all_correct = modal_uses_custom_text and all(result for _, result in approvals_checks)
    return all_correct

def main():
    print("\n" + "="*80)
    print("🧪 APPROVAL SYSTEM FIXES VERIFICATION")
    print("="*80)
    
    print("\n⏳ Checking database...")
    db_ok = check_database()
    
    print("\n⏳ Checking backend code...")
    backend_ok = check_backend_code()
    
    print("\n⏳ Checking frontend code...")
    frontend_ok = check_frontend_code()
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    status_items = [
        ("Database Structure", db_ok),
        ("Backend Fixes", backend_ok),
        ("Frontend Fixes", frontend_ok),
    ]
    
    for name, status in status_items:
        icon = "✅" if status else "❌"
        print(f"{icon} {name}")
    
    print("\n" + "="*80)
    print("🧪 NEXT STEPS TO TEST")
    print("="*80)
    
    print("""
1. SUBMIT A NEW SUGGESTION:
   • Log in as employee (user-a@example.com)
   • Go to budget page
   • Click "제안하다" (Suggest) on a budget change
   • Select "Custom" tab or "Reasons Library"
   • Submit the suggestion
   
2. VERIFY IN APPROVALS PAGE:
   • Log in as CPA admin (admin@example.com)
   • Go to /admin/approvals
   • Select a pending suggestion
   • ✅ Should show 💡 הסבר מוצע (Suggested explanation) in BLUE
   • ❌ Should NOT show "N/A" anymore
   • ⚠️ Should show color coding if edited

3. APPROVE THE SUGGESTION:
   • Click ✅ אשר (Approve) button
   • Should show success: "ההסבר אושר בהצלחה"
   • Sidebar badge should disappear
   • Dashboard alert should disappear

4. VERIFY IN MUNICIPALITY PORTAL:
   • Log in as municipality user
   • Navigate to corresponding budget line
   • Should see the newly approved explanation

✅ If all checks pass, the fixes are working!
""")
    
    return db_ok and backend_ok and frontend_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
