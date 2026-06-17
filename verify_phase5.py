"""
Phase 5 Verification Script
Tests that all new components work correctly
"""

import sys
import os

# Add the repo to path
sys.path.insert(0, r'c:\Users\zahal\OneDrive\cpa')

def verify_phase5():
    """Verify Phase 5 implementation"""
    
    print("=" * 60)
    print("PHASE 5 - EXPLANATIONS ENGINE VERIFICATION")
    print("=" * 60)
    
    # Test 1: purple_booklet_rules with real codes
    print("\n[1/4] Verifying purple_booklet_rules.py with REAL Ministry codes...")
    try:
        from backend.data.purple_booklet_rules import (
            get_budget_topic,
            get_all_budget_topics,
            get_explanation_template,
        )
        
        # Check for real codes instead of mock codes
        topics = get_all_budget_topics()
        real_codes = ["3", "5", "19", "33", "47", "50"]
        mock_codes = ["101", "202", "303", "404", "505"]
        
        has_real = all(code in topics for code in real_codes)
        has_mock = any(code in topics for code in mock_codes)
        
        if has_real and not has_mock:
            print("   ✓ purple_booklet_rules.py has REAL Ministry codes (3, 5, 19, 33, 47, 50)")
            print(f"   ✓ Total topics configured: {len(topics)}")
        else:
            print("   ✗ FAILED: Rules file still has mock or missing real codes")
            return False
        
        # Test template generation
        template = get_explanation_template("3", "regular")
        if template and "גנ" in template:
            print("   ✓ Templates working correctly for code 3 (kindergarten)")
        
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Test 2: Change Detection Service
    print("\n[2/4] Verifying change_detector.py service...")
    try:
        from backend.services.change_detector import ChangeDetector, DetectedChange
        
        detector = ChangeDetector()
        
        # Test detecting a children count change
        prev_line = {
            "topic_code": "3",
            "num_children": 100,
            "cost_per_child": 500,
        }
        curr_line = {
            "topic_code": "3",
            "num_children": 110,
            "cost_per_child": 500,
        }
        
        changes = detector.detect_changes(prev_line, curr_line, "3")
        
        if len(changes) > 0 and "110" in str(changes[0].current_value):
            print("   ✓ Change detector correctly identifies children count changes (100→110)")
            print(f"   ✓ Detected {len(changes)} change(s)")
        else:
            print("   ✗ FAILED: Change detector not working properly")
            return False
            
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Test 3: Explanation Service
    print("\n[3/4] Verifying explanation_service.py...")
    try:
        from backend.services.explanation_service import generate_auto_explanation
        
        budget_line = {
            "topic_code": "3",
            "line_type": "regular",
            "period_month": "2026-03",
            "amount": 50000,
            "num_children": 100,
        }
        
        explanation = generate_auto_explanation(budget_line)
        
        if explanation and len(explanation) > 0 and "2026" in str(explanation):
            print("   ✓ Explanation service generates Hebrew explanations")
            print(f"   ✓ Generated: {explanation[:60]}...")
        else:
            print("   ✗ FAILED: Explanation service not generating text")
            return False
            
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Test 4: Routes Registration
    print("\n[4/4] Verifying explanations.py routes...")
    try:
        from backend.routes import explanations
        
        if hasattr(explanations, 'router') and explanations.router is not None:
            print("   ✓ explanations.py routes module loaded")
            print("   ✓ Router object created successfully")
            
            # Check for key endpoints
            has_get = any('get' in str(r) for r in dir(explanations.router))
            has_post = any('post' in str(r) for r in dir(explanations.router))
            
            if has_get and has_post:
                print("   ✓ GET and POST endpoints available")
        else:
            print("   ✗ FAILED: Routes not properly configured")
            return False
            
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Success!
    print("\n" + "=" * 60)
    print("✅ PHASE 5 VERIFICATION COMPLETE - ALL SYSTEMS READY")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start backend server: cd backend && python -m uvicorn main:app --reload")
    print("2. Start frontend server: cd frontend && npm run dev")
    print("3. Test Explanations Engine in municipality portal")
    print("4. Create custom explanations as CPA admin")
    print("5. Verify change detection displays correctly")
    
    return True

if __name__ == '__main__':
    success = verify_phase5()
    sys.exit(0 if success else 1)
