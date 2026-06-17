"""
Explanation Service — Auto-generates Hebrew explanations for budget lines.

Provides two levels of explanations:
1. Auto-generated from purple_booklet_rules.py templates (using change detection)
2. Manual override from custom_explanations database
"""

from typing import Dict, List, Optional
from backend.data.purple_booklet_rules import (
    get_explanation_template,
    get_budget_topic,
    get_hebrew_month,
)
from backend.services.change_detector import ChangeDetector


def format_hebrew_month(month_str):
    """
    Convert YYYY-MM format to Hebrew month name.
    Uses the shared function from purple_booklet_rules.
    
    Args:
        month_str: e.g., "2024-03" or "2024-03-15"
    
    Returns:
        str: e.g., "מרץ 2024"
    """
    return get_hebrew_month(month_str)


def generate_auto_explanation(budget_line, previous_line=None):
    """
    Generate an auto explanation for a budget line with change detection.
    
    Works with REAL Ministry topic codes: 3, 19, 33, 50, 47, 5
    
    Args:
        budget_line: BudgetLine object or dict with attributes:
            - topic_code: e.g., "3", "19", "50"
            - line_type or determined from context: "regular", "retro", "shortage", "adjustment"
            - period_month: YYYY-MM (month this payment is FOR)
            - amount: amount in shekels
            - num_children: if applicable
            - cost_per_child: if applicable
            - other attributes depending on topic
        
        previous_line: Previous month's BudgetLine (optional, for change detection)
    
    Returns:
        str: Hebrew explanation text with change details
    """
    
    # Convert to dict if it's an object
    if hasattr(budget_line, "__dict__"):
        line_dict = budget_line.__dict__
    else:
        line_dict = budget_line
    
    topic_code = str(line_dict.get("topic_code", ""))
    line_type = str(line_dict.get("line_type", "regular")).lower()
    period_month = line_dict.get("period_month", "")
    amount = line_dict.get("amount", 0)
    
    # Get base template from new real codes
    base_template = get_explanation_template(topic_code, line_type)
    
    # Build core explanation
    if line_type == "retro":
        month_hebrew = format_hebrew_month(period_month)
        explanation = f"{base_template} — עבור {month_hebrew}"
    
    elif line_type == "shortage":
        abs_diff = abs(float(amount)) if amount else 0
        if abs_diff > 0:
            explanation = f"{base_template} — הפרש של ₪{abs_diff:,.0f}"
        else:
            explanation = base_template
    
    elif line_type == "adjustment":
        explanation = f"{base_template}"
    
    else:  # "regular" or default
        month_hebrew = format_hebrew_month(period_month) if period_month else ""
        if month_hebrew:
            explanation = f"{base_template} — חודש {month_hebrew}"
        else:
            explanation = base_template
    
    # Add detected changes if previous line provided
    if previous_line:
        detector = ChangeDetector()
        prev_dict = previous_line.__dict__ if hasattr(previous_line, "__dict__") else previous_line
        
        changes = detector.detect_changes(prev_dict, line_dict, topic_code)
        
        if changes:
            explanation += "\n\nשינויים בשורה זו:"
            for i, change in enumerate(changes, 1):
                if change.hebrew_description:
                    explanation += f"\n{i}. {change.hebrew_description}"
                    if change.impact_amount and change.impact_amount != 0:
                        impact_str = f"₪{change.impact_amount:,.2f}"
                        explanation += f" (השפעה: {impact_str})"
    
    return explanation


def get_explanation(budget_line, previous_line=None, custom_explanation=None):
    """
    Get the final explanation for a budget line.
    
    Priority:
    1. Custom explanation (if provided by admin)
    2. Auto-generated explanation (with change detection)
    
    Args:
        budget_line: BudgetLine object or dict
        previous_line: Previous month's budget line (for change detection)
        custom_explanation: CustomExplanation object (or None)
    
    Returns:
        dict with:
            - text: the explanation text (Hebrew)
            - is_custom: boolean, True if custom explanation was used
            - is_retro: boolean, True if retro payment
            - has_changes: boolean, True if changes detected
    """
    
    # Convert to dict if needed
    if hasattr(budget_line, "__dict__"):
        line_dict = budget_line.__dict__
    else:
        line_dict = budget_line
    
    # Determine if this is a retro payment
    is_retro = False
    if line_dict.get("line_type") == "retro":
        is_retro = True
    elif "period_month" in line_dict and "current_month" in line_dict:
        is_retro = line_dict.get("period_month") != line_dict.get("current_month")
    
    # Detect changes
    has_changes = False
    if previous_line:
        detector = ChangeDetector()
        prev_dict = previous_line.__dict__ if hasattr(previous_line, "__dict__") else previous_line
        topic_code = str(line_dict.get("topic_code", ""))
        
        changes = detector.detect_changes(prev_dict, line_dict, topic_code)
        has_changes = len(changes) > 0
    
    if custom_explanation:
        return {
            "text": custom_explanation.custom_text if hasattr(custom_explanation, "custom_text") else str(custom_explanation),
            "is_custom": True,
            "is_retro": is_retro,
            "has_changes": has_changes,
        }
    else:
        return {
            "text": generate_auto_explanation(budget_line, previous_line),
            "is_custom": False,
            "is_retro": is_retro,
            "has_changes": has_changes,
        }
