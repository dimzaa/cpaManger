"""
Smart Explanation Engine — REAL formulas from Ministry of Education Purple Booklet (חוברת תקצוב).

Implements official Ministry budget formulas for:
- Code 3: שכר לימוד גני ילדים
- Code 19: עוזרות גננות  
- Code 33: גננות עובדות מדינה (DEDUCTION)
- Code 45: קצין ביקור סדיר
- Code 47: פסיכולוגים חינוכיים

Each explanation has 3 layers:
1. Summary (color-coded pill, always visible)
2. Formula breakdown (collapsible, with colored constants & variables)
3. Why it changed (collapsible, only if changes detected)
"""

from typing import Dict, List, Optional, Any


class SmartExplanationEngine:
    """Generates smart explanations with REAL Ministry of Education formulas."""
    
    # Ministry constants with official Hebrew explanations
    CONSTANTS = {
        "31": {
            "color": "red-bold",
            "tooltip": "קבוע משרד החינוך — 31 ילדים לכיתה עבור רשויות המקבלות מענק איזון ממשרד הפנים"
        },
        "33": {
            "color": "purple-bold",
            "tooltip": "קבוע משרד החינוך — 33 ילדים לכיתה עבור רשויות שאינן מקבלות מענק איזון"
        },
        "90": {
            "color": "green-bold",
            "tooltip": "משרד החינוך ממן 90% מעלות גני ילדים גיל 3-4. 10% נותרים באחריות הרשות המקומית"
        },
        "100": {
            "color": "green-bold",
            "tooltip": "גני חובה גיל 5-6 — משרד החינוך מממן 100% מהעלות"
        },
        "68": {
            "color": "green-bold",
            "tooltip": "פסיכולוגים חינוכיים — משרד החינוך משתתף ב-68% מעלות המשרה"
        },
        "75": {
            "color": "green-bold",
            "tooltip": "קצין ביקור סדיר — משרד החינוך משתתף ב-75% מעלות המשרה"
        },
    }

    @staticmethod
    def generate_explanation(budget_line: Dict[str, Any], previous_line: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate smart explanation with REAL Ministry formulas."""
        topic_code = str(budget_line.get("topic_code", ""))
        line_type = str(budget_line.get("line_type", "regular")).lower()
        
        result = {
            "summary": SmartExplanationEngine._generate_summary(budget_line, line_type, topic_code),
            "formula": None,
            "why_changed": None,
            "grant_status": None,
        }
        
        # Generate formula based on REAL Ministry code
        if topic_code == "3":
            result["formula"] = SmartExplanationEngine._formula_code_3(budget_line)
            result["grant_status"] = SmartExplanationEngine._get_grant_status(budget_line)
        elif topic_code == "19":
            result["formula"] = SmartExplanationEngine._formula_code_19(budget_line)
        elif topic_code == "33":
            result["formula"] = SmartExplanationEngine._formula_code_33(budget_line)
        elif topic_code == "45":
            result["formula"] = SmartExplanationEngine._formula_code_45(budget_line)
        elif topic_code == "47":
            result["formula"] = SmartExplanationEngine._formula_code_47(budget_line)
        
        # Detect changes
        if previous_line:
            result["why_changed"] = SmartExplanationEngine._explain_changes(budget_line, previous_line, topic_code)
        
        return result

    @staticmethod
    def _generate_summary(line: Dict[str, Any], line_type: str, topic_code: str) -> Dict[str, str]:
        """Layer 1: Generate one-sentence summary with color coding."""
        num_children = float(line.get("num_children", 0))
        num_positions = float(line.get("num_positions", 0))
        cost_per_unit = float(line.get("cost_per_child") or line.get("cost_per_position", 0))
        amount = float(line.get("amount", 0))
        
        if line_type == "retro":
            return {
                "color_box": "amber",
                "icon": "💼",
                "text": f"תשלום רטרו עבור {line.get('period_month', '')}",
                "amount": f"₪{amount:,.2f}"
            }
        elif topic_code == "33":
            return {
                "color_box": "red",
                "icon": "⬇️",
                "text": "ניכוי — גננות עובדות מדינה",
                "description": "(שכרן מנוכה מתקציב הרשות)",
                "amount": f"₪{abs(amount):,.2f}"
            }
        elif num_children > 0 and cost_per_unit > 0:
            return {
                "color_box": "green",
                "icon": "👨‍👩‍👧",
                "text": f"תשלום שוטף — {int(num_children)} ילדים",
                "subtitle": f"× ₪{cost_per_unit:,.2f} לילד",
                "amount": f"₪{amount:,.2f}"
            }
        elif num_positions > 0 and cost_per_unit > 0:
            return {
                "color_box": "blue",
                "icon": "👤",
                "text": f"תשלום שוטף — {num_positions:.2f} משרות",
                "subtitle": f"× ₪{cost_per_unit:,.2f} למשרה",
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
    def _formula_code_3(line: Dict[str, Any]) -> Dict[str, Any]:
        """
        CODE 3 — REAL Ministry formula for kindergarten tuition (שכ״ל גן ילדים)
        
        Formula:
          עלות ילד = עלות גן כוללת ÷ [31 or 33]
          תשלום = עלות ילד × מספר ילדים × אחוז_השתתפות
        
        Where:
          - [31] = constant for municipalities WITH מענק איזון
          - [33] = constant for municipalities WITHOUT מענق איזון
          - Percentage = 90% (ages 3-4) or 100% (ages 5-6)
        """
        num_children = float(line.get("num_children", 0))
        cost_per_child = float(line.get("cost_per_child", 0))
        ministry_percentage = float(line.get("ministry_percentage", 90))
        amount = float(line.get("amount", 0))
        grant_code = line.get("grant_code", "31")
        
        return {
            "formula_text": f"מספר ילדים × עלות לילד × {int(ministry_percentage)}% = סכום",
            "sub_formula": f"עלות ילד = עלות גן כוללת ÷ [{grant_code}]",
            "breakdown_text": "(חישוב עלות היסוד: הוצאות גננת + תוכן + ניהול ÷ מספר ילדים בכיתה)",
            "components": [
                {
                    "value": int(num_children),
                    "label": "מספר ילדים",
                    "color": "blue",
                    "is_constant": False,
                    "tooltip": "משתנה מחודש לחודש בהתאם לרישומים"
                },
                {
                    "value": f"₪{cost_per_child:,.2f}",
                    "label": "עלות לילד",
                    "color": "orange",
                    "is_constant": False,
                    "tooltip": f"חישוב: (עלות גן כוללת) ÷ {grant_code}"
                },
                {
                    "value": f"{int(ministry_percentage)}%",
                    "label": "אחוז השתתפות משרד",
                    "color": "green-bold",
                    "is_constant": True,
                    "tooltip": SmartExplanationEngine.CONSTANTS.get(str(int(ministry_percentage)), {}).get("tooltip", "")
                },
                {
                    "result": True,
                    "value": f"₪{amount:,.2f}",
                    "label": "סכום סופי",
                    "color": "gray",
                }
            ]
        }

    @staticmethod
    def _formula_code_19(line: Dict[str, Any]) -> Dict[str, Any]:
        """
        CODE 19 — REAL Ministry formula for kindergarten assistants (עוזרות גננות)
        
        Formula:
          תשלום = מספר משרות × עלות משרה × 100%
          Ministry pays 90%, municipality pays 10%
          
        For 6-day kindergartens: multiply by 1.1785 (additional 17.85% for Friday)
        """
        num_positions = float(line.get("num_positions", 0))
        cost_per_position = float(line.get("cost_per_position", 0))
        six_day_multiplier = float(line.get("six_day_multiplier", 1.0))
        amount = float(line.get("amount", 0))
        
        components = [
            {
                "value": f"{num_positions:.2f}",
                "label": "משרות מאושרות",
                "color": "blue",
                "is_constant": False,
                "tooltip": "מספר משרות עוזרות גננות המאושרות על ידי משרד החינוך"
            },
            {
                "value": f"₪{cost_per_position:,.2f}",
                "label": "עלות משרה",
                "color": "orange",
                "is_constant": False,
                "tooltip": "עלות חודשית לפי טבלת שכר משרד החינוך"
            },
            {
                "value": "100%",
                "label": "כיסוי",
                "color": "green-bold",
                "is_constant": True,
                "tooltip": "המשרה מכוסה במלואה (משרד 90% + רשות 10%)"
            },
        ]
        
        if six_day_multiplier > 1.0:
            components.append({
                "value": f"× {six_day_multiplier:.4f}",
                "label": "כפל יום ו'",
                "color": "red-bold",
                "is_constant": True,
                "tooltip": "הוסף 17.85% עבור ממלא מקום ביום שישי"
            })
        
        components.append({
            "result": True,
            "value": f"₪{amount:,.2f}",
            "label": "סכום סופי",
            "color": "gray"
        })
        
        formula = "מספר משרות × עלות משרה × 100%"
        if six_day_multiplier > 1.0:
            formula += f" × {six_day_multiplier:.4f}"
        
        return {
            "formula_text": formula,
            "sub_formula": "משרד החינוך משלם 90% | הרשות משלמת 10%",
            "components": components
        }

    @staticmethod
    def _formula_code_33(line: Dict[str, Any]) -> Dict[str, Any]:
        """
        CODE 33 — Government employees DEDUCTION (גננות עובדות מדינה)
        
        This is a DEDUCTION (negative amount).
        Government-employed teachers' salary is deducted back from municipality budget.
        """
        amount = float(line.get("amount", 0))
        
        return {
            "formula_text": "ניכוי שכר גננות עובדות מדינה",
            "explanation": "גננות אלו הן עובדות מדינה — שכרן מנוכה מתקציב הרשות",
            "components": [
                {
                    "result": True,
                    "value": f"({abs(amount):,.2f})₪",
                    "label": "סכום הניכוי",
                    "color": "red-bold",
                    "tooltip": "זהו ניכוי חוקי — שכר גננות עובדות מדינה"
                }
            ]
        }

    @staticmethod
    def _formula_code_45(line: Dict[str, Any]) -> Dict[str, Any]:
        """
        CODE 45 — Regular Supervisor (קצין ביקור סדיר)
        
        Formula:
          תשלום = מספר קב״סים × עלות משרה × 75%
        """
        num_positions = float(line.get("num_positions", 0))
        cost_per_position = float(line.get("cost_per_position", 0))
        amount = float(line.get("amount", 0))
        
        return {
            "formula_text": "מספר קב״סים × עלות משרה × 75%",
            "sub_formula": "משרד החינוך משתתף ב-75% | הרשות משלמת 25%",
            "components": [
                {
                    "value": f"{num_positions:.2f}",
                    "label": "משרות קצין ביקור",
                    "color": "blue",
                    "is_constant": False
                },
                {
                    "value": f"₪{cost_per_position:,.2f}",
                    "label": "עלות משרה",
                    "color": "orange",
                    "is_constant": False
                },
                {
                    "value": "75%",
                    "label": "אחוז השתתפות",
                    "color": "green-bold",
                    "is_constant": True,
                    "tooltip": SmartExplanationEngine.CONSTANTS.get("75", {}).get("tooltip", "")
                },
                {
                    "result": True,
                    "value": f"₪{amount:,.2f}",
                    "label": "סכום סופי",
                    "color": "gray"
                }
            ]
        }

    @staticmethod
    def _formula_code_47(line: Dict[str, Any]) -> Dict[str, Any]:
        """
        CODE 47 — Educational Psychologists (פסיכולוגים חינוכיים)
        
        Formula:
          תשלום = מספר פסיכולוגים × עלות משרה × 68%
        """
        num_positions = float(line.get("num_positions", 0))
        cost_per_position = float(line.get("cost_per_position", 0))
        amount = float(line.get("amount", 0))
        
        return {
            "formula_text": "מספר פסיכולוגים × עלות משרה × 68%",
            "sub_formula": "משרד החינוך משתתף ב-68% | הרשות משלמת 32%",
            "components": [
                {
                    "value": f"{num_positions:.2f}",
                    "label": "משרות פסיכולוגים",
                    "color": "blue",
                    "is_constant": False
                },
                {
                    "value": f"₪{cost_per_position:,.2f}",
                    "label": "עלות משרה",
                    "color": "orange",
                    "is_constant": False
                },
                {
                    "value": "68%",
                    "label": "אחוז השתתפות",
                    "color": "green-bold",
                    "is_constant": True,
                    "tooltip": SmartExplanationEngine.CONSTANTS.get("68", {}).get("tooltip", "")
                },
                {
                    "result": True,
                    "value": f"₪{amount:,.2f}",
                    "label": "סכום סופי",
                    "color": "gray"
                }
            ]
        }

    @staticmethod
    def _get_grant_status(line: Dict[str, Any]) -> Dict[str, str]:
        """Indicate which constant applies (31 vs 33)."""
        grant_code = line.get("grant_code", "31")
        
        if grant_code == "31":
            return {
                "code": "31",
                "text": "הרשות מקבלת מענק איזון",
                "explanation": "משרד החינוך מחשב לפי [31] ילדים לכיתה עבור רשויות המקבלות מענק איזון ממשרד הפנים"
            }
        else:
            return {
                "code": "33",
                "text": "הרשות אינה מקבלת מענק איזון",
                "explanation": "משרד החינוך מחשב לפי [33] ילדים לכיתה עבור רשויות שאינן מקבלות מענק איזון"
            }

    @staticmethod
    def _explain_changes(current: Dict[str, Any], previous: Dict[str, Any], topic_code: str) -> Dict[str, Any]:
        """Layer 3: Explain why amount changed from previous month."""
        curr_children = float(current.get("num_children", 0))
        prev_children = float(previous.get("num_children", 0))
        curr_positions = float(current.get("num_positions", 0))
        prev_positions = float(previous.get("num_positions", 0))
        curr_amount = float(current.get("amount", 0))
        prev_amount = float(previous.get("amount", 0))
        curr_cost = float(current.get("cost_per_child") or current.get("cost_per_position", 0))
        prev_cost = float(previous.get("cost_per_child") or previous.get("cost_per_position", 0))
        
        amount_diff = curr_amount - prev_amount
        explanations = []
        
        # Children count change
        if abs(curr_children - prev_children) > 0.1:
            children_diff = curr_children - prev_children
            impact = children_diff * curr_cost
            reason = "רישום חדש / חזרה לאחר היעדרות" if children_diff > 0 else "עזיבת ילד / הרשמה ביטחונית"
            explanations.append({
                "title": "📊 מספר הילדים השתנה",
                "description": f"מ-{int(prev_children)} ל-{int(curr_children)} ({'+' if children_diff > 0 else ''}{int(children_diff)})",
                "calculation": f"{int(abs(children_diff))} ילדים × ₪{curr_cost:,.2f} = {'+' if children_diff > 0 else ''}₪{impact:,.2f}",
                "reason": reason
            })
        
        # Positions count change  
        elif abs(curr_positions - prev_positions) > 0.01:
            positions_diff = curr_positions - prev_positions
            impact = positions_diff * curr_cost
            reason = "הוספת משרה מאושרת חדשה" if positions_diff > 0 else "סיום משרה"
            explanations.append({
                "title": "💼 מספר המשרות השתנה",
                "description": f"מ-{prev_positions:.2f} ל-{curr_positions:.2f} ({'+' if positions_diff > 0 else ''}{positions_diff:.2f})",
                "calculation": f"{abs(positions_diff):.2f} משרות × ₪{curr_cost:,.2f} = {'+' if positions_diff > 0 else ''}₪{impact:,.2f}",
                "reason": reason
            })
        
        # Cost per unit change
        elif abs(curr_cost - prev_cost) > 0.01:
            cost_diff = curr_cost - prev_cost
            quantity = curr_children if curr_children > 0 else curr_positions
            impact = quantity * cost_diff
            explanations.append({
                "title": "💵 עלות לילד / משרה השתנתה",
                "description": f"עדכון מ-₪{prev_cost:,.2f} ל-₪{curr_cost:,.2f}",
                "calculation": f"{quantity:.0f} × ₪{cost_diff:,.2f} = {'+' if cost_diff > 0 else ''}₪{impact:,.2f}",
                "reason": "עדכון טבלת שכר משרד החינוך"
            })
        
        # Retro payment
        elif current.get("line_type") == "retro":
            explanations.append({
                "title": "💼 תשלום רטרו",
                "description": f"תשלום עבור {current.get('period_month', '')}",
                "reason": "תשלום בגין חודשים קודמים שאושר באיחור"
            })
        
        # Generic amount change
        elif abs(amount_diff) > 0.01:
            pct_change = (amount_diff / abs(prev_amount) * 100) if prev_amount != 0 else 0
            explanations.append({
                "title": "📊 הסכום השתנה",
                "description": f"מ-₪{prev_amount:,.2f} ל-₪{curr_amount:,.2f}",
                "change": f"{'+' if amount_diff > 0 else ''}₪{amount_diff:,.2f} ({pct_change:+.1f}%)"
            })
        
        return {
            "has_changes": len(explanations) > 0,
            "explanations": explanations
        }
