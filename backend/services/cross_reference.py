"""
Cross reference service for validating and analyzing budget data.

Core business logic:
- Compares invoice total vs breakdown sum
- Detects retro payments (when period_month != current_month)
- Detects shortages (when amount is less than previous months)
- Flags anomalies and differences
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
import pandas as pd


class CrossReferenceAnalysis:
    """
    Analyzes budget data for consistency and anomalies.
    
    Main responsibilities:
    1. Compare invoice total with breakdown sum
    2. Identify retro payments
    3. Identify shortages
    4. Generate analysis report
    """
    
    @staticmethod
    def cross_reference_month(
        invoice_df: pd.DataFrame,
        breakdown_df: pd.DataFrame,
        municipality_code: str,
        month: str
    ) -> Dict[str, Any]:
        """
        Cross-reference invoice vs breakdown for a specific municipality and month.
        
        Args:
            invoice_df: Invoice DataFrame
            breakdown_df: Breakdown DataFrame
            municipality_code: Municipality code to analyze
            month: Month in YYYY-MM format
            
        Returns:
            {
                "municipality_code": str,
                "month": str,
                "invoice_total": float,
                "breakdown_total": float,
                "is_balanced": bool,
                "difference": float,
                "difference_percentage": float,
                "retro_lines": List[dict],
                "shortage_lines": List[dict],
                "anomalies": List[str],
                "status": "balanced" | "unbalanced" | "error"
            }
        """
        
        # Filter data for this municipality and month
        invoice_rows = invoice_df[
            (invoice_df['municipality_code'] == municipality_code) &
            (invoice_df['month'] == month)
        ]
        
        if invoice_rows.empty:
            return {
                "municipality_code": municipality_code,
                "month": month,
                "status": "error",
                "error": f"No invoice found for {municipality_code} in {month}"
            }
        
        invoice_total = float(invoice_rows['total'].sum())  # שולם - what was actually paid

        # Use total_due if available (from CHESHBONIT), else sum breakdown amounts
        if 'total_due' in invoice_rows.columns:
            breakdown_total = float(invoice_rows['total_due'].sum())  # מגיע - what should be paid
        else:
            breakdown_rows_temp = breakdown_df[
                (breakdown_df['municipality_code'] == municipality_code) &
                (breakdown_df['current_month'] == month)
            ]
            breakdown_total = float(breakdown_rows_temp['amount'].sum()) if not breakdown_rows_temp.empty else 0.0

        # difference > 0 means Ministry still owes money (normal — current month not yet paid)
        difference = breakdown_total - invoice_total
        breakdown_rows = breakdown_df[
            (breakdown_df['municipality_code'] == municipality_code) &
            (breakdown_df['current_month'] == month)
        ]
        difference_percentage = (abs(difference) / invoice_total * 100) if invoice_total != 0 else 0

        # is_balanced: True only if the gap is less than 1 shekel
        # Note: a positive difference (Ministry owes) is NORMAL behavior, not an error
        is_balanced = abs(difference) < 1.0
        
        # Analyze lines for retro and shortage patterns
        retro_lines = []
        shortage_lines = []
        anomalies = []
        
        for _, row in breakdown_rows.iterrows():
            line_info = {
                "budget_topic": row['budget_topic'],
                "topic_code": row['topic_code'],
                "amount": row['amount'],
                "period_month": row['period_month'],
                "current_month": row['current_month'],
            }
            
            # Check if this is a retro payment
            is_retro = row['period_month'] != row['current_month']
            if is_retro:
                retro_lines.append({
                    **line_info,
                    "type": "retro",
                    "explanation": f"תשלום רטרואקטיבי לחודש {row['period_month']}"
                })
                anomalies.append(
                    f"RETRO: {row['budget_topic']} - ₪{row['amount']} for {row['period_month']}"
                )
        
        return {
            "municipality_code": municipality_code,
            "month": month,
            "invoice_total": float(invoice_total),
            "breakdown_total": float(breakdown_total),
            "is_balanced": is_balanced,
            "difference": float(difference),
            "difference_percentage": float(difference_percentage),
            "retro_lines": retro_lines,
            "shortage_lines": shortage_lines,
            "anomalies": anomalies,
            "status": "balanced" if is_balanced else "unbalanced",
        }
    
    @staticmethod
    def detect_shortages(
        previous_month_df: pd.DataFrame,
        current_month_df: pd.DataFrame,
        municipality_code: str
    ) -> List[Dict[str, Any]]:
        """
        Compare current month budget to previous month to detect shortages.
        
        A shortage = amount for a topic is less than the same topic previous month.
        
        Args:
            previous_month_df: Breakdown data for previous month
            current_month_df: Breakdown data for current month
            municipality_code: Municipality to analyze
            
        Returns:
            List of shortage records
        """
        shortages = []
        
        # Filter for this municipality
        prev_data = previous_month_df[
            previous_month_df['municipality_code'] == municipality_code
        ]
        curr_data = current_month_df[
            current_month_df['municipality_code'] == municipality_code
        ]
        
        # Compare by topic
        for prev_topic in prev_data['topic_code'].unique():
            prev_amount = prev_data[
                prev_data['topic_code'] == prev_topic
            ]['amount'].sum()
            
            curr_amount = curr_data[
                curr_data['topic_code'] == prev_topic
            ]['amount'].sum()
            
            # Check if there's a shortage
            if curr_amount < prev_amount:
                shortage_amount = prev_amount - curr_amount
                shortage_pct = (shortage_amount / prev_amount * 100) if prev_amount > 0 else 0
                
                topic_name = prev_data[
                    prev_data['topic_code'] == prev_topic
                ].iloc[0]['budget_topic']
                
                shortages.append({
                    "topic_code": prev_topic,
                    "budget_topic": topic_name,
                    "previous_month_amount": float(prev_amount),
                    "current_month_amount": float(curr_amount),
                    "shortage_amount": float(shortage_amount),
                    "shortage_percentage": float(shortage_pct),
                    "explanation": f"חוסר של ₪{shortage_amount:,.0f} ({shortage_pct:.1f}%) בהשוואה לחודש קודם"
                })
        
        return shortages
    
    @staticmethod
    def analyze_all_months(
        invoice_df: pd.DataFrame,
        breakdown_df: pd.DataFrame,
        municipalities: set
    ) -> Dict[str, Any]:
        """
        Run cross-reference analysis for all data.
        
        Args:
            invoice_df: Invoice DataFrame
            breakdown_df: Breakdown DataFrame
            municipalities: Set of municipality codes
            
        Returns:
            Comprehensive analysis report
        """
        
        analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "municipalities_analyzed": len(municipalities),
            "results_by_municipality": {}
        }
        
        # Get unique months
        months = sorted(invoice_df['month'].unique())
        
        for municipality in municipalities:
            mun_results = {
                "code": municipality,
                "months": {}
            }
            
            for month in months:
                cross_ref = CrossReferenceAnalysis.cross_reference_month(
                    invoice_df, breakdown_df, municipality, month
                )
                mun_results["months"][month] = cross_ref
            
            analysis_results["results_by_municipality"][municipality] = mun_results
        
        # Summary statistics
        total_runs = len(months) * len(municipalities)
        balanced_runs = sum(
            1 for mun_data in analysis_results["results_by_municipality"].values()
            for month_data in mun_data["months"].values()
            if month_data.get("status") == "balanced"
        )
        
        analysis_results["summary"] = {
            "total_runs": total_runs,
            "balanced_runs": balanced_runs,
            "unbalanced_runs": total_runs - balanced_runs,
            "balance_percentage": (balanced_runs / total_runs * 100) if total_runs > 0 else 0,
        }
        
        return analysis_results
