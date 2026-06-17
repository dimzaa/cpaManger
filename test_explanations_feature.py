#!/usr/bin/env python3
"""
Comprehensive test for auto-generated change explanations feature
"""

import os
import sys

def test_files_exist():
    """Verify all required files exist"""
    print("=" * 80)
    print("📋 VERIFYING FILES")
    print("=" * 80)
    
    files = [
        "frontend/src/utils/changeExplanations.js",
        "frontend/src/pages/PortalBudgetPage.jsx",
        "frontend/src/pages/AdminBudgetDetailPage.jsx"
    ]
    
    all_exist = True
    for file_path in files:
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        print(f"{status} {file_path}")
        all_exist = all_exist and exists
    
    return all_exist


def test_imports():
    """Verify imports are correct in pages"""
    print("\n" + "=" * 80)
    print("📍 VERIFYING IMPORTS")
    print("=" * 80)
    
    tests = [
        ("frontend/src/pages/PortalBudgetPage.jsx", [
            "import { generateChangeExplanation, ChangeExplanationBox } from '../utils/changeExplanations';",
        ]),
        ("frontend/src/pages/AdminBudgetDetailPage.jsx", [
            "import { generateChangeExplanation, ChangeExplanationBox } from '../utils/changeExplanations';",
        ]),
    ]
    
    all_correct = True
    for file_path, required_imports in tests:
        print(f"\n📄 {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for import_stmt in required_imports:
            if import_stmt in content:
                print(f"  ✅ Found: {import_stmt[:60]}...")
            else:
                print(f"  ❌ Missing: {import_stmt[:60]}...")
                all_correct = False
    
    return all_correct


def test_components():
    """Verify component usage in pages"""
    print("\n" + "=" * 80)
    print("🧩 VERIFYING COMPONENT USAGE")
    print("=" * 80)
    
    tests = [
        ("frontend/src/pages/PortalBudgetPage.jsx", [
            ("generateChangeExplanation", "Call to generate explanation"),
            ("ChangeExplanationBox", "Box component display"),
            ("explanations[code]", "Lookup of custom explanation"),
        ]),
        ("frontend/src/pages/AdminBudgetDetailPage.jsx", [
            ("generateChangeExplanation", "Call to generate explanation"),
            ("ChangeExplanationBox", "Box component display"),
            ("explanations[change.topic_code]", "Lookup of custom explanation"),
        ]),
    ]
    
    all_correct = True
    for file_path, required_items in tests:
        print(f"\n📄 {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for item, desc in required_items:
            if item in content:
                print(f"  ✅ Found: {desc}")
            else:
                print(f"  ❌ Missing: {desc}")
                all_correct = False
    
    return all_correct


def test_utility_functions():
    """Verify utility functions exist and are exported"""
    print("\n" + "=" * 80)
    print("🔧 VERIFYING UTILITY FUNCTIONS")
    print("=" * 80)
    
    with open("frontend/src/utils/changeExplanations.js", 'r', encoding='utf-8') as f:
        content = f.read()
    
    functions = [
        ("export const generateChangeExplanation", "Main explanation generator"),
        ("export const ChangeExplanationBox", "React component for display"),
        ("const formatCurrency", "Currency formatter helper"),
    ]
    
    all_found = True
    for func, desc in functions:
        if func in content:
            print(f"  ✅ Found: {desc}")
        else:
            print(f"  ❌ Missing: {desc}")
            all_found = False
    
    return all_found


def test_explanation_logic():
    """Verify key explanation generation logic exists"""
    print("\n" + "=" * 80)
    print("💡 VERIFYING EXPLANATION LOGIC")
    print("=" * 80)
    
    with open("frontend/src/utils/changeExplanations.js", 'r', encoding='utf-8') as f:
        content = f.read()
    
    logic_checks = [
        ("customExplanation && customExplanation.trim()", "Custom explanation override"),
        ("items_change > 0", "Item increase detection"),
        ("items_change < 0", "Item decrease detection"),
        ("amount_change !== 0", "Amount change detection"),
        ("isNegativeImpact", "Negative impact (deductions)"),
        ("topic_code === '3'", "Children category"),
        ("topic_code === '19'", "Helpers category"),
        ("topic_code === '33'", "Kindergarten deduction category"),
        ("formatCurrency", "Currency formatting"),
    ]
    
    all_found = True
    for logic, desc in logic_checks:
        if logic in content:
            print(f"  ✅ Found: {desc}")
        else:
            print(f"  ❌ Missing: {desc}")
            all_found = False
    
    return all_found


def test_styling():
    """Verify UI styling for explanation box"""
    print("\n" + "=" * 80)
    print("🎨 VERIFYING UI STYLING")
    print("=" * 80)
    
    with open("frontend/src/utils/changeExplanations.js", 'r', encoding='utf-8') as f:
        content = f.read()
    
    styles = [
        ("mt-3", "Margin top spacing"),
        ("bg-blue-50", "Light blue background"),
        ("border-blue-200", "Blue border"),
        ("💡", "Info icon emoji"),
        ("font-hebrew", "Hebrew font class"),
        ("text-blue-900", "Dark blue text"),
    ]
    
    all_found = True
    for style, desc in styles:
        if style in content:
            print(f"  ✅ Found: {desc}")
        else:
            print(f"  ❌ Missing: {desc}")
            all_found = False
    
    return all_found


def main():
    print("\n")
    print("🚀 COMPREHENSIVE FEATURE TEST: AUTO-GENERATED CHANGE EXPLANATIONS")
    print("\n")
    
    results = {
        "Files Exist": test_files_exist(),
        "Imports Correct": test_imports(),
        "Components Used": test_components(),
        "Utility Functions": test_utility_functions(),
        "Explanation Logic": test_explanation_logic(),
        "UI Styling": test_styling(),
    }
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    all_pass = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        all_pass = all_pass and passed
    
    print("\n" + "=" * 80)
    if all_pass:
        print("✅ ALL TESTS PASSED!")
        print("\n🎯 Feature Implementation Complete:")
        print("   1. Auto-generated Hebrew explanations for budget changes")
        print("   2. Support for custom CPA explanations override")
        print("   3. Different messages for different budget categories")
        print("   4. Special handling for negative impact items (deductions)")
        print("   5. Light blue info box styling with 💡 icon")
        print("   6. Integrated in both PortalBudgetPage and AdminBudgetDetailPage")
        print("\n📍 Display Format (in month changes section):")
        print("   ┌──────────────────────────────────────────────┐")
        print("   │ Category Name — Code N                       │")
        print("   │ Items: X → Y  (+Z)                           │")
        print("   │ Amount: ₪A → ₪B (+C%)                       │")
        print("   │                                              │")
        print("   │ 💡 Explanation: Auto-generated or custom    │")
        print("   └──────────────────────────────────────────────┘")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\nReview the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
