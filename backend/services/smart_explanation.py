"""
Smart Explanation Engine — Detailed formula breakdowns and change detection.

Provides:
1. Formula breakdown with colored constants (RED=31, PURPLE=33, ORANGE=cost, BLUE=variables, GREEN=%)
2. Layer-based explanations (summary → formula → why it changed)
3. Change detection with smart explanations (children count, cost changes, retro payments, etc.)
4. Constants highlighting with tooltips
5. Estimated job calculations for significant changes
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal


class FormulaComponent:
    """Represents a single component in a formula breakdown."""
    def __init__(self, value: Any, label: str, color: str, is_constant: bool = False, tooltip: str = ""):
        self.value = value
        self.label = label
        self.color = color  # "blue", "orange", "green", "red-bold", "purple-bold"
        self.is_constant = is_constant
        self.tooltip = tooltip


class FormulaBreakdown:
    """Represents a full formula breakdown with colored components."""
    def __init__(self, formula_text: str, components: List[Dict[str, Any]]):
        self.formula_text = formula_text  # e.g., "מספר ילדים × עלות לילד × אחוז השתתפות = סכום"
        self.components = components  # List of component dicts with color info


class SmartExplanationLayer:
    """Three-layer explanation for a budget line."""
    def __init__(self):
        self.summary = ""  # One-line summary with color-coded box
        self.formula = None  # FormulaBreakdown (collapsible)
        self.why_changed = None  # Change explanation (collapsible)


class SmartExplanationEngine:
    """Generates smart, detailed explanations with formula breakdowns."""
    
    # Ministry constants
    CONSTANTS = {
        "31": {
            "color": "red-bold",
            "tooltip": "31 ילדים לכיתה — קבוע למקבלי מענק"
        },
        "33": {
            "color": "purple-bold",
            "tooltip": "33 ילדים לכיתה — קבוע לאינם מקבלי מענק"
        },
        "90": {
            "color": "green-bold",
            "tooltip": "אחוז השתתפות משרד החינוך — 90%"
        },
        "100": {
            "color": "green-bold",
            "tooltip": "אחוז השתתפות משרד החינוך — 100%"
        },
        "68": {
            "color": "green-bold",
            "tooltip": "אחוז השתתפות — פסיכולוגים חינוכיים"
        },
        "75": {
            "color": "green-bold",
            "tooltip": "אחוז השתתפות — קצין ביקור סדיר"
        },
    }

    @staticmethod
    def generate_explanation(budget_line: Dict[str, Any], previous_line: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate smart explanation with all layers.
        
        Args:
            budget_line: Current month's budget line
            previous_line: Previous month's budget line (for change detection)
        
        Returns:
            Dict with:
            - summary: one-line summary with color code
            - formula: formula breakdown with colored components
            - why_changed: explanation of changes from previous month
            - constants_used: list of constants highlighted
            - estimated_jobs_change: if applicable for code 19
        """
        topic_code = str(budget_line.get("topic_code", ""))
        line_type = str(budget_line.get("line_type", "regular")).lower()
        amount = float(budget_line.get("amount", 0))
        
        result = {
            "summary": SmartExplanationEngine._generate_summary(budget_line, line_type, amount),
            "formula": None,
            "why_changed": None,
            "constants_used": [],
            "estimated_jobs_change": None,
        }
        
        # Generate formula breakdown based on topic code
        if topic_code == "3":
            result["formula"] = SmartExplanationEngine._formula_children_categories(budget_line)
        elif topic_code == "19":
            result["formula"] = SmartExplanationEngine._formula_positions(budget_line)
            if previous_line:
                result["estimated_jobs_change"] = SmartExplanationEngine._calculate_jobs_change(budget_line, previous_line)
        elif topic_code == "33":
            result["formula"] = SmartExplanationEngine._formula_government_employees(budget_line)
        elif topic_code in ["50", "47", "5"]:
            # Generic formula for other codes
            result["formula"] = SmartExplanationEngine._formula_generic(budget_line, topic_code)
        
        # Detect changes from previous month
        if previous_line:
            result["why_changed"] = SmartExplanationEngine._explain_changes(budget_line, previous_line, topic_code, line_type)
        
        return result

    @staticmethod
    def _generate_summary(line: Dict[str, Any], line_type: str, amount: float) -> Dict[str, str]:
        """Generate one-sentence summary with color coding."""
        num_children = line.get("num_children", 0)
        num_positions = line.get("num_positions", 0)
        cost_per_unit = line.get("cost_per_child") or line.get("cost_per_position", 0)
        topic_code = str(line.get("topic_code", ""))
        
        if line_type == "retro":
            period_month = line.get("period_month", "")
            return {
                "color_box": "amber",
                "icon": "💼",
                "text": f"תשלום רטרו עבור {period_month}",
                "amount": f"₪{amount:,.2f}"
            }
        elif topic_code == "33":
            return {
                "color_box": "red",
                "icon": "⬇️",
                "text": "ניכוי — גננות עובדות מדינה",
                "amount": f"₪{abs(amount):,.2f}"
            }
        elif num_children > 0:
            return {
                "color_box": "green",
                "icon": "👨‍👩‍👧‍👦",
                "text": f"תשלום שוטף — {num_children} ילדים × ₪{cost_per_unit:,.2f}",
                "amount": f"₪{amount:,.2f}"
            }
        elif num_positions > 0:
            return {
                "color_box": "blue",
                "icon": "👤",
                "text": f"תשלום שוטף — {num_positions:.1f} משרות × ₪{cost_per_unit:,.2f}",
                "amount": f"₪{amount:,.2f}"
            }
        else:
            return {
                "color_box": "gray",
                "icon": "📊",
                "text": "תשלום שוטף",
                "amount": f"₪{amount:,.2f}"
            }

    @staticmethod
    def _formula_children_categories(line: Dict[str, Any]) -> Dict[str, Any]:
        """Formula for code 3 (children categories like kindergarten)."""
        num_children = line.get("num_children", 0)
        cost_per_child = line.get("cost_per_child", 0)
        percentage = line.get("ministry_percentage", 100)
        amount = line.get("amount", 0)
        
        return {
            "formula_text": "מספר ילדים × עלות לילד × אחוז השתתפות = סכום",
            "components": [
                {
                    "value": num_children,
                    "label": "ילדים",
                    "position": "first",
                    "color": "blue",
                    "is_constant": False,
                    "tooltip": "מספר שמשתנה מחודש לחודש"
                },
                {
                    "value": f"₪{cost_per_child:,.2f}",
                    "label": "עלות לילד",
                    "position": "second",
                    "color": "orange",
                    "is_constant": False,
                    "tooltip": ""
                },
                {
                    "value": f"{percentage}%",
                    "label": "אחוז השתתפות",
                    "position": "third",
                    "color": "green-bold",
                    "is_constant": True,
                    "tooltip": SmartExplanationEngine.CONSTANTS.get(str(percentage), {}).get("tooltip", "")
                },
                {
                    "value": f"₪{amount:,.2f}",
                    "label": "סכום סופי",
                    "position": "result",
                    "color": "gray",
                    "is_constant": False,
                    "tooltip": ""
                },
            ]
        }

    @staticmethod
    def _formula_positions(line: Dict[str, Any]) -> Dict[str, Any]:
        """Formula for code 19 (positions like assistants)."""
        num_positions = line.get("num_positions", 0)
        cost_per_position = line.get("cost_per_position", 0)
        percentage = line.get("ministry_percentage", 90)
        amount = line.get("amount", 0)
        
        return {
            "formula_text": "מספר משרות × עלות תרשמ × אחוז השתתפות = סכום",
            "components": [
                {
                    "value": f"{num_positions:.2f}",
                    "label": "משרות",
                    "position": "first",
                    "color": "blue",
                    "is_constant": False,
                    "tooltip": "מספר שמשתנה מחודש לחודש"
                },
                {
                    "value": f"₪{cost_per_position:,.2f}",
                    "label": "עלות למשרה",
                    "position": "second",
                    "color": "orange",
                    "is_constant": False,
                    "tooltip": ""
                },
                {
                    "value": f"{percentage}%",
                    "label": "אחוז השתתפות",
                    "position": "third",
                    "color": "green-bold",
                    "is_constant": True,
                    "tooltip": f"משרד החינוך משתתף ב-{percentage}% מהעלות"
                },
                {
                    "value": f"₪{amount:,.2f}",
                    "label": "סכום סופי",
                    "position": "result",
                    "color": "gray",
                    "is_constant": False,
                    "tooltip": ""
                },
            ]
        }

    @staticmethod
    def _formula_government_employees(line: Dict[str, Any]) -> Dict[str, Any]:
        """Formula for code 33 (government employees deduction)."""
        amount = line.get("amount", 0)
        
        return {
            "formula_text": "ניכוי עלות גננות עובדות מדינה",
            "components": [
                {
                    "value": f"₪{abs(amount):,.2f}",
                    "label": "ניכוי",
                    "position": "single",
                    "color": "red-bold",
                    "is_constant": False,
                    "tooltip": "גננות אלו הן עובדות מדינה — עלותן מנוכה מהתקציב"
                },
            ]
        }

    @staticmethod
    def _formula_generic(line: Dict[str, Any], topic_code: str) -> Dict[str, Any]:
        """Generic formula for other topic codes."""
        amount = line.get("amount", 0)
        description = line.get("description", f"קוד {topic_code}")
        
        return {
            "formula_text": description,
            "components": [
                {
                    "value": f"₪{amount:,.2f}",
                    "label": "סכום",
                    "position": "single",
                    "color": "gray",
                    "is_constant": False,
                    "tooltip": ""
                },
            ]
        }

    @staticmethod
    def _explain_changes(current: Dict[str, Any], previous: Dict[str, Any], topic_code: str, line_type: str) -> Dict[str, Any]:
        """Explain why the amount changed from previous month."""
        curr_children = float(current.get("num_children", 0))
        prev_children = float(previous.get("num_children", 0))
        curr_amount = float(current.get("amount", 0))
        prev_amount = float(previous.get("amount", 0))
        curr_cost = float(current.get("cost_per_child") or current.get("cost_per_position", 0))
        prev_cost = float(previous.get("cost_per_child") or previous.get("cost_per_position", 0))
        curr_pct = float(current.get("ministry_percentage", 0))
        prev_pct = float(previous.get("ministry_percentage", 0))
        
        amount_diff = curr_amount - prev_amount
        
        explanations = []
        
        # 1. Check if children/positions count changed
        if curr_children != prev_children:
            children_diff = curr_children - prev_children
            impact = children_diff * curr_cost
            reason = "רישום חדש / חזרה לאחר היעדרות" if children_diff > 0 else "עזיבה / הרשמה ביטחונית"
            explanations.append({
                "title": "📊 מספר הילדים השתנה",
                "description": f"עלה מ-{int(prev_children)} ל-{int(curr_children)} ({'+' if children_diff > 0 else ''}{int(children_diff)} ילד)",
                "calculation": f"ילד נוסף × ₪{curr_cost:,.2f} לילד = ₪{impact:,.2f}",
                "reason": reason
            })
        
        # 2. Check if cost per child changed
        elif curr_cost != prev_cost:
            cost_diff = curr_cost - prev_cost
            impact = curr_children * cost_diff
            explanations.append({
                "title": "💵 עלות לילד השתנתה",
                "description": f"עדכון מ-₪{prev_cost:,.2f} ל-₪{curr_cost:,.2f} (+₪{cost_diff:,.2f})",
                "calculation": f"{int(curr_children)} ילדים × ₪{cost_diff:,.2f} = ₪{impact:,.2f}",
                "reason": "עדכון טבלת שכר — משפיע על כלל הילדים"
            })
        
        # 3. Check if percentage changed
        elif curr_pct != prev_pct:
            pct_diff = curr_pct - prev_pct
            explanations.append({
                "title": "📈 אחוז השתתפות השתנה",
                "description": f"מ-{int(prev_pct)}% ל-{int(curr_pct)}% (+{int(pct_diff)}%)",
                "reason": f"משרד החינוך מממן כעת {int(curr_pct)}% במקום {int(prev_pct)}%"
            })
        
        # 4. Check if this is a retro payment
        elif line_type == "retro":
            period_month = current.get("period_month", "")
            explanations.append({
                "title": "💼 תשלום רטרו",
                "description": f"תשלום עבור {period_month} שאושר באיחור",
                "reason": "זהו תשלום רגיל — לא מצביע על בעיה"
            })
        
        # Fallback: just note the amount change
        elif abs(amount_diff) > 0.01:
            explanations.append({
                "title": "📊 הסכום השתנה",
                "description": f"מ-₪{prev_amount:,.2f} ל-₪{curr_amount:,.2f}",
                "change_amount": f"₪{amount_diff:,.2f}",
                "change_percentage": f"{(amount_diff / prev_amount * 100) if prev_amount != 0 else 0:.1f}%"
            })
        
        return {
            "has_changes": len(explanations) > 0,
            "explanations": explanations
        }

    @staticmethod
    def _calculate_jobs_change(current: Dict[str, Any], previous: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        For code 19 (positions), calculate if significant job changes are likely.
        Returns estimated number of new positions.
        """
        if current.get("topic_code") != "19":
            return None
        
        curr_amount = float(current.get("amount", 0))
        prev_amount = float(previous.get("amount", 0))
        amount_diff = abs(curr_amount - prev_amount)
        
        # Only show if significant change
        if amount_diff < 10000:
            return None
        
        cost_per_position = float(current.get("cost_per_position", 0))
        if cost_per_position == 0:
            return None
        
        estimated_jobs = amount_diff / cost_per_position
        
        return {
            "amount_change": f"₪{amount_diff:,.2f}",
            "cost_per_position": f"₪{cost_per_position:,.2f}",
            "estimated_positions": f"{estimated_jobs:.1f}",
            "warning": "⚠️ לבדיקת רואה החשבון — יש לוודא מול רשימת המשרות המאושרות"
        }
