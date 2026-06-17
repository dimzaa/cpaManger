"""
Explanation generator service.

Generates human-readable Hebrew explanations for budget items based on:
- Line type (regular, retro, shortage)
- Topic code and name
- Amount and dates
- Comparison to previous months
"""

from typing import Optional, Dict, Any

from backend.services.student_count_delta import StudentCountDelta
from backend.services.variance_driver_classifier import (
    build_explanation_prefix,
    classify,
)


class ExplanationGenerator:
    """
    Generates professional Hebrew explanations for budget items.
    """
    
    # Hebrew explanations for budget topics
    TOPIC_DESCRIPTIONS = {
        "101": {
            "name": "גני ילדים",
            "description": "תקציב לחינוך לפני יסודי ובתי ספר ממלכתיים"
        },
        "202": {
            "name": "חינוך מיוחד",
            "description": "תקציב לשירותי חינוך מיוחד לתלמידים בעלי צרכים מיוחדים"
        },
        "303": {
            "name": "שעות נוסף מורים",
            "description": "תקציב לשעות הוראה נוספות מעבר לשעות הקבע"
        },
        "404": {
            "name": "ליקויי למידה",
            "description": "תקציב לתוכניות ישיבה וגמישות לתלמידים עם קשיים בלימודים"
        },
        "505": {
            "name": "נסיעות תלמידים",
            "description": "תקציב לנסיעות של תלמידים מהמושב לבית הספר וחזרה"
        },
    }
    
    @staticmethod
    def generate_for_regular_line(
        topic_code: str,
        topic_name: str,
        amount: float,
        month: str,
        previous_month_amount: Optional[float] = None
    ) -> str:
        """
        Generate explanation for a regular budget line.
        
        Args:
            topic_code: Topic code (e.g., "101")
            topic_name: Hebrew topic name
            amount: Amount in shekels
            month: Month in YYYY-MM format
            previous_month_amount: Amount from previous month (for comparison)
            
        Returns:
            Hebrew explanation string
        """
        explanation = f"תקציב שוטף ל{topic_name}"
        
        if previous_month_amount and amount > previous_month_amount:
            increase = amount - previous_month_amount
            increase_pct = (increase / previous_month_amount * 100)
            explanation += f", גדול בהשוואה לחודש קודם בכ{increase_pct:.0f}%"
        elif previous_month_amount and amount < previous_month_amount:
            decrease = previous_month_amount - amount
            decrease_pct = (decrease / previous_month_amount * 100)
            explanation += f", קטן בהשוואה לחודש קודם בכ{decrease_pct:.0f}%"
        
        return explanation
    
    @staticmethod
    def generate_for_retro_line(
        topic_code: str,
        topic_name: str,
        amount: float,
        period_month: str,
        current_month: str
    ) -> str:
        """
        Generate explanation for a retro payment line.
        
        A retro payment = payment for a previous month, paid late.
        
        Args:
            topic_code: Topic code
            topic_name: Hebrew topic name
            amount: Amount of retro payment
            period_month: Month this payment was FOR (תחולה)
            current_month: Month this payment was MADE in (העלאה)
            
        Returns:
            Hebrew explanation string
        """
        return (
            f"תשלום רטרואקטיבי ל{topic_name} בגין חודש {period_month}. "
            f"התשלום בוצע בחודש {current_month} עקב עיכוב."
        )
    
    @staticmethod
    def generate_for_shortage_line(
        topic_code: str,
        topic_name: str,
        current_amount: float,
        previous_amount: float
    ) -> str:
        """
        Generate explanation for a shortage line.
        
        A shortage = amount is less than previous month.
        
        Args:
            topic_code: Topic code
            topic_name: Hebrew topic name
            current_amount: Current month amount
            previous_amount: Previous month amount
            
        Returns:
            Hebrew explanation string
        """
        shortage = previous_amount - current_amount
        shortage_pct = (shortage / previous_amount * 100)
        
        return (
            f"חוסר בתקציב ל{topic_name}: ₪{shortage:,.0f} ({shortage_pct:.1f}%) "
            f"בהשוואה לחודש הקודם. סכום החודש הנוכחי: ₪{current_amount:,.0f}."
        )
    
    @staticmethod
    def generate_for_adjustment_line(
        topic_code: str,
        topic_name: str,
        amount: float,
        reason: Optional[str] = None
    ) -> str:
        """
        Generate explanation for an adjustment line.
        
        An adjustment = correction to a previous payment.
        
        Args:
            topic_code: Topic code
            topic_name: Hebrew topic name
            amount: Adjustment amount (can be negative)
            reason: Optional reason for adjustment
            
        Returns:
            Hebrew explanation string
        """
        if amount > 0:
            return f"התאמה חיובית ל{topic_name}: ₪{amount:,.0f}. {reason or 'תיקון לתשלום קודם'}"
        else:
            return f"התאמה שלילית ל{topic_name}: ₪{abs(amount):,.0f}. {reason or 'תיקון לתשלום קודם'}"
    
    @staticmethod
    def prepend_student_count_prefix(
        base_text: str,
        delta: Optional[StudentCountDelta],
    ) -> str:
        """Prepend the Hebrew student-count sentence to an existing explanation.

        Returns ``base_text`` unchanged when there is no meaningful prefix.
        """
        if delta is None:
            return base_text
        driver = classify(delta)
        prefix = build_explanation_prefix(delta, driver)
        if not prefix:
            return base_text
        if not base_text:
            return prefix
        return f"{prefix} {base_text}"

    @staticmethod
    def generate(
        budget_line_data: Dict[str, Any],
        previous_month_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Main method: Generate explanation for a budget line.
        
        Args:
            budget_line_data: Dict with keys:
                - "budget_topic": str (Hebrew name)
                - "topic_code": str
                - "amount": float
                - "period_month": str (YYYY-MM)
                - "current_month": str (YYYY-MM)
                - "line_type": str (regular/retro/shortage/adjustment)
                
            previous_month_data: Optional dict with previous month data for comparison
            
        Returns:
            Hebrew explanation string
        """
        
        line_type = budget_line_data.get("line_type", "regular")
        topic_code = budget_line_data.get("topic_code", "")
        topic_name = budget_line_data.get("budget_topic", "")
        amount = budget_line_data.get("amount", 0)
        period_month = budget_line_data.get("period_month", "")
        current_month = budget_line_data.get("current_month", "")
        
        if line_type == "retro":
            return ExplanationGenerator.generate_for_retro_line(
                topic_code, topic_name, amount, period_month, current_month
            )
        
        elif line_type == "shortage":
            previous_amount = previous_month_data.get("amount", 0) if previous_month_data else amount
            return ExplanationGenerator.generate_for_shortage_line(
                topic_code, topic_name, amount, previous_amount
            )
        
        elif line_type == "adjustment":
            return ExplanationGenerator.generate_for_adjustment_line(
                topic_code, topic_name, amount
            )
        
        else:  # regular
            previous_amount = previous_month_data.get("amount", None) if previous_month_data else None
            return ExplanationGenerator.generate_for_regular_line(
                topic_code, topic_name, amount, period_month, previous_amount
            )
