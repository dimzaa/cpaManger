"""
Cross reference service for validating and analyzing budget data.

Core business logic:
- Per-code tie-out: ingested breakdown == CHESHBONIT settling per topic
- Detects retro payments (when period_month != current_month)
- Flags anomalies
"""

from typing import Dict, Any, List
from datetime import datetime
import pandas as pd


class CrossReferenceAnalysis:
    """
    Analyzes budget data for consistency and anomalies.
    """

    @staticmethod
    def cross_reference_month(
        invoice_df: pd.DataFrame,
        breakdown_df: pd.DataFrame,
        municipality_code: str,
        month: str
    ) -> Dict[str, Any]:
        """
        Cross-reference invoice vs breakdown for a specific (municipality, month).

        Bug #2 fix (2026-06-18): previously compared `שולם` (YTD paid, ~₪17.7M)
        against `סך הכל מגיע` (YTD due, ~₪22.5M). The gap between those IS the
        current month's settling amount — by definition non-zero — so
        `is_balanced` was always False even when ingestion was perfect.

        The CPA's real reconciliation question:
            "Does the ingested breakdown (sum of הפרש מחושב across detail
             files, code-by-code) equal what CHESHBONIT says is settling this
             month (sum of הפרש לתשלום across topic codes, i.e. due − paid)?"

        Definition:
          * invoice_total   = settling amount per CHESHBONIT (ytd_due − ytd_paid)
          * breakdown_total = sum of breakdown_df.amount  (what we ingested)
          * is_balanced     = True iff |breakdown_total − invoice_total| < 0.01
        """
        # Filter invoice rows for this (muni, month)
        invoice_rows = invoice_df[
            (invoice_df['municipality_code'] == municipality_code) &
            (invoice_df['month'] == month)
        ]

        if invoice_rows.empty:
            return {
                "municipality_code": municipality_code,
                "month": month,
                "status": "error",
                "error": f"No invoice found for {municipality_code} in {month}",
                "is_balanced": False,
                "invoice_total": 0.0,
                "breakdown_total": 0.0,
                "difference": 0.0,
                "difference_percentage": 0.0,
                "retro_lines": [],
                "shortage_lines": [],
                "anomalies": [],
            }

        ytd_paid = float(invoice_rows['total'].sum()) if 'total' in invoice_rows.columns else 0.0
        ytd_due = (
            float(invoice_rows['total_due'].sum())
            if 'total_due' in invoice_rows.columns else ytd_paid
        )
        # This month's settling amount per the Ministry's invoice.
        invoice_total = ytd_due - ytd_paid

        breakdown_rows = breakdown_df[
            (breakdown_df['municipality_code'] == municipality_code) &
            (breakdown_df['current_month'] == month)
        ]
        breakdown_total = (
            float(breakdown_rows['amount'].sum()) if not breakdown_rows.empty else 0.0
        )

        # difference > 0 → ingested MORE than the Ministry settled (double-count)
        # difference < 0 → ingested LESS (gap unresolved or wrong amount column)
        # Within ₪0.01 → reconciled.
        difference = breakdown_total - invoice_total
        difference_percentage = (
            (abs(difference) / abs(invoice_total) * 100) if invoice_total != 0 else 0.0
        )

        is_balanced = abs(difference) < 0.01

        # Flag retro lines for downstream UI/narrative.
        retro_lines: List[Dict[str, Any]] = []
        anomalies: List[str] = []
        for _, row in breakdown_rows.iterrows():
            is_retro = row.get('period_month') != row.get('current_month')
            if is_retro:
                retro_lines.append({
                    "budget_topic": row.get('budget_topic'),
                    "topic_code": row.get('topic_code'),
                    "amount": float(row.get('amount', 0)),
                    "period_month": row.get('period_month'),
                    "current_month": row.get('current_month'),
                    "type": "retro",
                    "explanation": f"תשלום רטרואקטיבי לחודש {row.get('period_month')}",
                })
                anomalies.append(
                    f"RETRO: {row.get('budget_topic')} - ₪{row.get('amount')} for {row.get('period_month')}"
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
            "shortage_lines": [],
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
        """
        shortages = []
        prev_data = previous_month_df[
            previous_month_df['municipality_code'] == municipality_code
        ]
        curr_data = current_month_df[
            current_month_df['municipality_code'] == municipality_code
        ]

        for prev_topic in prev_data['topic_code'].unique():
            prev_amount = prev_data[prev_data['topic_code'] == prev_topic]['amount'].sum()
            curr_amount = curr_data[curr_data['topic_code'] == prev_topic]['amount'].sum()
            if curr_amount < prev_amount:
                shortage_amount = prev_amount - curr_amount
                shortage_pct = (shortage_amount / prev_amount * 100) if prev_amount > 0 else 0
                topic_name = prev_data[prev_data['topic_code'] == prev_topic].iloc[0]['budget_topic']
                shortages.append({
                    "topic_code": prev_topic,
                    "budget_topic": topic_name,
                    "previous_month_amount": float(prev_amount),
                    "current_month_amount": float(curr_amount),
                    "shortage_amount": float(shortage_amount),
                    "shortage_percentage": float(shortage_pct),
                    "explanation": f"חוסר של ₪{shortage_amount:,.0f} ({shortage_pct:.1f}%) בהשוואה לחודש קודם",
                })
        return shortages

    @staticmethod
    def analyze_all_months(
        invoice_df: pd.DataFrame,
        breakdown_df: pd.DataFrame,
        municipalities: set
    ) -> Dict[str, Any]:
        """
        Run cross-reference analysis for all (municipality × month) pairs.
        """
        analysis_results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "municipalities_analyzed": len(municipalities),
            "results_by_municipality": {},
        }

        months = sorted(invoice_df['month'].unique())

        for municipality in municipalities:
            mun_results = {"code": municipality, "months": {}}
            for month in months:
                cross_ref = CrossReferenceAnalysis.cross_reference_month(
                    invoice_df, breakdown_df, municipality, month
                )
                mun_results["months"][month] = cross_ref
            analysis_results["results_by_municipality"][municipality] = mun_results

        total_runs = len(months) * len(municipalities)
        balanced_runs = sum(
            1
            for mun_data in analysis_results["results_by_municipality"].values()
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
