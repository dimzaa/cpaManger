"""
Mock data generator for testing the budget management system.

Generates realistic CSV files based on Ministry of Education format:
- invoice.csv: Summary of payments per municipality (one row per municipality per month)
- breakdown.csv: Detailed breakdown by budget topic (multiple rows per municipality per month)

Includes 3 municipalities, 3 months of data, with scenarios:
- Month 1 (Jan 2024): Balanced month - everything normal
- Month 2 (Feb 2024): Includes retro payment from January
- Month 3 (Mar 2024): Includes shortage (less than Feb) in some topics
"""

import pandas as pd
from datetime import datetime
import os

# ============ CONFIGURATION ============

MUNICIPALITIES = {
    "3000": {"name": "עיריית נצרת", "hebrew_name": "Nazareth"},
    "3100": {"name": "מועצת עראבה", "hebrew_name": "Arraba"},
    "3200": {"name": "עיריית אום אל פחם", "hebrew_name": "Um El-Fahm"},
}

BUDGET_TOPICS = {
    "101": "גני ילדים",              # Kindergartens
    "202": "חינוך מיוחד",            # Special Education
    "303": "שעות נוסף מורים",        # Teacher overtime
    "404": "ליקויי למידה",           # Learning disabilities
    "505": "נסיעות תלמידים",         # Student transport
}

MONTHS = ["2024-01", "2024-02", "2024-03"]


def generate_invoice_data():
    """
    Generate invoice (summary) data.
    
    One row per municipality per month.
    Contains: municipality_code, municipality_name, total, month, year
    """
    data = []
    
    # Month 1 (Jan 2024) - Balanced month with normal amounts
    base_amounts = {
        "3000": 450000,
        "3100": 380000,
        "3200": 420000,
    }
    
    for code, amount in base_amounts.items():
        data.append({
            "municipality_code": code,
            "municipality_name": MUNICIPALITIES[code]["name"],
            "total": amount,
            "month": "2024-01",
            "year": 2024,
        })
    
    # Month 2 (Feb 2024) - Same base + retro from January
    # Retro amounts (late payment for January): smaller amounts for specific topics
    retro_amounts = {
        "3000": 45000,   # 10% retro from January
        "3100": 38000,   # 10% retro from January
        "3200": 42000,   # 10% retro from January
    }
    
    for code, base_amount in base_amounts.items():
        retro = retro_amounts[code]
        total_feb = base_amount + retro
        data.append({
            "municipality_code": code,
            "municipality_name": MUNICIPALITIES[code]["name"],
            "total": total_feb,
            "month": "2024-02",
            "year": 2024,
        })
    
    # Month 3 (Mar 2024) - Same base but with shortages in some topics
    # Overall, amounts are similar but not identical (some topics cut partially)
    shortage_multiplier = {
        "3000": 0.92,  # 8% shortage overall
        "3100": 0.95,  # 5% shortage overall
        "3200": 0.90,  # 10% shortage overall
    }
    
    for code, base_amount in base_amounts.items():
        total_mar = int(base_amount * shortage_multiplier[code])
        data.append({
            "municipality_code": code,
            "municipality_name": MUNICIPALITIES[code]["name"],
            "total": total_mar,
            "month": "2024-03",
            "year": 2024,
        })
    
    return pd.DataFrame(data)


def generate_breakdown_data():
    """
    Generate breakdown (detail) data.
    
    Multiple rows per municipality per month.
    One row = one budget topic with amount, period, and line type.
    
    Contains: municipality_code, municipality_name, budget_topic, topic_code,
              amount, period_month, current_month, line_type
    """
    data = []
    
    # Base amounts per topic per municipality (for January)
    # These will be modified for retro and shortage scenarios
    base_distribution = {
        "3000": {  # Nazareth
            "101": 120000,  # Kindergartens
            "202": 95000,   # Special Ed
            "303": 85000,   # Teacher overtime
            "404": 100000,  # Learning disabilities
            "505": 50000,   # Student transport
        },
        "3100": {  # Arraba
            "101": 100000,
            "202": 80000,
            "303": 70000,
            "404": 85000,
            "505": 45000,
        },
        "3200": {  # Um El-Fahm
            "101": 110000,
            "202": 88000,
            "303": 75000,
            "404": 95000,
            "505": 52000,
        },
    }
    
    # ========== MONTH 1: January 2024 (Balanced) ==========
    for mun_code, topics in base_distribution.items():
        for topic_code, amount in topics.items():
            data.append({
                "municipality_code": mun_code,
                "municipality_name": MUNICIPALITIES[mun_code]["name"],
                "budget_topic": BUDGET_TOPICS[topic_code],
                "topic_code": topic_code,
                "amount": amount,
                "period_month": "2024-01",              # חודש תחולה
                "current_month": "2024-01",             # חודש העלאה
                "line_type": "regular",
                "is_retro": False,
            })
    
    # ========== MONTH 2: February 2024 (Current month normal + Retro from January) ==========
    
    # Regular February payments (same as January for now)
    for mun_code, topics in base_distribution.items():
        for topic_code, amount in topics.items():
            data.append({
                "municipality_code": mun_code,
                "municipality_name": MUNICIPALITIES[mun_code]["name"],
                "budget_topic": BUDGET_TOPICS[topic_code],
                "topic_code": topic_code,
                "amount": amount,
                "period_month": "2024-02",              # This is for February
                "current_month": "2024-02",             # Paid in February
                "line_type": "regular",
                "is_retro": False,
            })
    
    # Retro payments from January (paid late in February)
    # Only for specific topics to make it realistic
    for mun_code, topics in base_distribution.items():
        # Retro only for topics 101 and 202
        for topic_code in ["101", "202"]:
            amount = int(topics[topic_code] * 0.3)  # 30% retro payment
            data.append({
                "municipality_code": mun_code,
                "municipality_name": MUNICIPALITIES[mun_code]["name"],
                "budget_topic": BUDGET_TOPICS[topic_code],
                "topic_code": topic_code,
                "amount": amount,
                "period_month": "2024-01",              # This is for January! (retro)
                "current_month": "2024-02",             # But paid in February
                "line_type": "retro",
                "is_retro": True,
            })
    
    # ========== MONTH 3: March 2024 (Shortages in some topics) ==========
    
    # March has shortages - some topics reduced compared to February
    shortage_rates = {
        "101": 0.85,  # Kindergartens: 15% cut
        "202": 0.90,  # Special Ed: 10% cut
        "303": 1.0,   # Teacher overtime: normal
        "404": 0.88,  # Learning disabilities: 12% cut
        "505": 1.0,   # Student transport: normal
    }
    
    for mun_code, topics in base_distribution.items():
        for topic_code, base_amount in topics.items():
            shortage_amount = int(base_amount * shortage_rates[topic_code])
            data.append({
                "municipality_code": mun_code,
                "municipality_name": MUNICIPALITIES[mun_code]["name"],
                "budget_topic": BUDGET_TOPICS[topic_code],
                "topic_code": topic_code,
                "amount": shortage_amount,
                "period_month": "2024-03",
                "current_month": "2024-03",
                "line_type": "shortage" if shortage_rates[topic_code] < 1.0 else "regular",
                "is_retro": False,
            })
    
    return pd.DataFrame(data)


def save_csv_files(output_dir="./"):
    """
    Generate mock data and save as CSV files.
    Uses UTF-8-sig encoding for proper Hebrew character support.
    
    Args:
        output_dir: Directory to save CSV files to
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating mock data...")
    
    # Generate data
    invoice_df = generate_invoice_data()
    breakdown_df = generate_breakdown_data()
    
    # Save with UTF-8-sig encoding (required for Hebrew)
    invoice_path = os.path.join(output_dir, "invoice.csv")
    breakdown_path = os.path.join(output_dir, "breakdown.csv")
    
    invoice_df.to_csv(invoice_path, index=False, encoding='utf-8-sig')
    breakdown_df.to_csv(breakdown_path, index=False, encoding='utf-8-sig')
    
    print(f"✅ Invoice file saved: {invoice_path}")
    print(f"   Rows: {len(invoice_df)}")
    print(f"\n✅ Breakdown file saved: {breakdown_path}")
    print(f"   Rows: {len(breakdown_df)}")
    
    print("\n📊 MOCK DATA SUMMARY:")
    print(f"   Municipalities: 3 (codes: 3000, 3100, 3200)")
    print(f"   Months: 3 (January, February, March 2024)")
    print(f"   Budget topics per municipality: 5")
    print(f"   Total data rows:")
    print(f"     - Invoice: {len(invoice_df)} (3 mun × 3 months)")
    print(f"     - Breakdown: {len(breakdown_df)} (details with retro)")
    print(f"\n📌 SCENARIOS INCLUDED:")
    print(f"   ✓ January 2024: Balanced month (all normal)")
    print(f"   ✓ February 2024: Retro payments from January (~30% for topics 101, 202)")
    print(f"   ✓ March 2024: Shortages in some topics (10-15% cuts)")
    
    return invoice_df, breakdown_df


def preview_data():
    """Print preview of generated data."""
    invoice_df, breakdown_df = generate_invoice_data(), generate_breakdown_data()
    
    print("\n" + "="*80)
    print("INVOICE DATA PREVIEW (first 6 rows)")
    print("="*80)
    print(invoice_df.head(6).to_string(index=False))
    
    print("\n" + "="*80)
    print("BREAKDOWN DATA PREVIEW (first 10 rows)")
    print("="*80)
    print(breakdown_df.head(10).to_string(index=False))
    
    print("\n" + "="*80)
    print("RETRO PAYMENTS (rows where is_retro=True)")
    print("="*80)
    retro_rows = breakdown_df[breakdown_df['is_retro'] == True]
    print(retro_rows.to_string(index=False))
    
    print("\n" + "="*80)
    print("SHORTAGES (rows where line_type='shortage')")
    print("="*80)
    shortage_rows = breakdown_df[breakdown_df['line_type'] == 'shortage']
    print(shortage_rows.to_string(index=False))


if __name__ == "__main__":
    # Generate and save CSV files
    output_dir = "./"
    save_csv_files(output_dir)
    
    # Print preview
    print("\n")
    preview_data()
