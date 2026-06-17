"""
Change Detection Service

Detects specific changes between budget line entries from different months/years.
Explains what changed and calculates impact (₪ difference, percentage change, etc).

Change Types:
- Children count increase/decrease (most common for kindergart)
- Cost per child updates (annual adjustments)
- Participation percentage changes
- Grant eligibility change (מקבל מענק / לא מקבל)
- Retro payments (from earlier month)
- Shortage/adjustment corrections
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class DetectedChange:
    """Represents a single detected change between budget lines."""
    
    def __init__(
        self,
        change_type: str,
        field_name: str,
        previous_value,
        current_value,
        impact_amount: Optional[float] = None,
        impact_pct: Optional[float] = None,
        hebrew_description: str = "",
    ):
        self.change_type = change_type  # "numeric", "categorical", "grant_status", "retro"
        self.field_name = field_name  # e.g., "num_children", "cost_per_child"
        self.previous_value = previous_value
        self.current_value = current_value
        self.impact_amount = impact_amount
        self.impact_pct = impact_pct
        self.hebrew_description = hebrew_description
        
    def to_dict(self):
        return {
            "change_type": self.change_type,
            "field_name": self.field_name,
            "previous": self._format_value(self.previous_value),
            "current": self._format_value(self.current_value),
            "impact_shekel": self.impact_amount,
            "impact_pct": self.impact_pct,
            "hebrew_description": self.hebrew_description,
        }
    
    def _format_value(self, value):
        """Format value for display (currency, percentage, or raw)."""
        if isinstance(value, (int, float)):
            if abs(value) > 0.1:  # Probably currency
                return f"₪{value:,.2f}"
            elif value < 1:  # Probably percentage
                return f"{value*100:.1f}%"
        return str(value)


class ChangeDetector:
    """Detects changes between budget line entries."""
    
    # Field mappings for different topic codes
    CRITICAL_FIELDS = {
        "3": ["num_children", "cost_per_child", "participation_pct"],  # Kindergarten
        "5": ["num_units", "cost_per_unit"],  # Attendance officers
        "19": ["num_units", "cost_per_unit"],  # Teacher assistants
        "33": ["cost_per_unit"],  # State employee teachers
        "47": ["num_units", "cost_per_unit"],  # Psychological services
        "50": ["num_children", "cost_per_child"],  # Student transport
    }
    
    def __init__(self):
        pass
    
    def detect_changes(
        self,
        previous_line: Dict,
        current_line: Dict,
        topic_code: str,
    ) -> List[DetectedChange]:
        """
        Detect changes between two budget line entries.
        
        Args:
            previous_line: Budget line from previous month (dict)
            current_line: Budget line from current month (dict)
            topic_code: e.g., "3", "19", "50"
        
        Returns:
            List of DetectedChange objects
        """
        changes = []
        
        if not previous_line or not current_line:
            return changes
        
        # Check for numeric field changes
        changes.extend(self._detect_numeric_changes(
            previous_line, current_line, topic_code
        ))
        
        # Check for categorical changes
        changes.extend(self._detect_categorical_changes(
            previous_line, current_line
        ))
        
        # Check for grant status changes
        changes.extend(self._detect_grant_changes(
            previous_line, current_line
        ))
        
        # Check for retro payment
        if self._is_retro_payment(previous_line, current_line):
            changes.extend(self._create_retro_change(
                previous_line, current_line
            ))
        
        return changes
    
    def _detect_numeric_changes(
        self,
        prev: Dict,
        curr: Dict,
        topic_code: str,
    ) -> List[DetectedChange]:
        """Detect changes in numeric fields (children, cost, etc)."""
        changes = []
        fields_to_check = self.CRITICAL_FIELDS.get(topic_code, [])
        
        for field in fields_to_check:
            if field not in prev or field not in curr:
                continue
            
            prev_val = self._parse_numeric(prev.get(field))
            curr_val = self._parse_numeric(curr.get(field))
            
            if prev_val is None or curr_val is None:
                continue
            
            if prev_val != curr_val:
                # Calculate impact
                impact_amount = None
                impact_pct = None
                
                # For children/units count
                if field in ["num_children", "num_units"]:
                    diff = curr_val - prev_val
                    if prev_val != 0:
                        impact_pct = (diff / prev_val) * 100
                    
                    # Calculate financial impact if we have cost info
                    cost_field = "cost_per_child" if field == "num_children" else "cost_per_unit"
                    if cost_field in curr:
                        cost = self._parse_numeric(curr.get(cost_field))
                        if cost:
                            impact_amount = float(diff * cost)
                
                # For cost changes
                elif field in ["cost_per_child", "cost_per_unit"]:
                    diff = curr_val - prev_val
                    if prev_val != 0:
                        impact_pct = (diff / prev_val) * 100
                    
                    # Calculate financial impact if we have children/units
                    qty_field = "num_children" if field == "cost_per_child" else "num_units"
                    if qty_field in curr:
                        qty = self._parse_numeric(curr.get(qty_field))
                        if qty:
                            impact_amount = float(diff * qty)
                
                # For participation percentage changes
                elif field == "participation_pct":
                    diff_pct = (curr_val - prev_val) * 100
                    impact_pct = diff_pct
                
                hebrew_desc = self._get_hebrew_description_numeric(
                    field, prev_val, curr_val
                )
                
                change = DetectedChange(
                    change_type="numeric",
                    field_name=field,
                    previous_value=prev_val,
                    current_value=curr_val,
                    impact_amount=impact_amount,
                    impact_pct=impact_pct,
                    hebrew_description=hebrew_desc,
                )
                changes.append(change)
        
        return changes
    
    def _detect_categorical_changes(
        self,
        prev: Dict,
        curr: Dict,
    ) -> List[DetectedChange]:
        """Detect changes in categorical fields (status, type, etc)."""
        changes = []
        
        categorical_fields = [
            "status",
            "payment_type",
            "allocation_type",
            "sub_topic",
        ]
        
        for field in categorical_fields:
            if field not in prev or field not in curr:
                continue
            
            prev_val = str(prev.get(field, "")).strip()
            curr_val = str(curr.get(field, "")).strip()
            
            if prev_val and curr_val and prev_val != curr_val:
                hebrew_desc = self._get_hebrew_description_categorical(
                    field, prev_val, curr_val
                )
                
                change = DetectedChange(
                    change_type="categorical",
                    field_name=field,
                    previous_value=prev_val,
                    current_value=curr_val,
                    hebrew_description=hebrew_desc,
                )
                changes.append(change)
        
        return changes
    
    def _detect_grant_changes(
        self,
        prev: Dict,
        curr: Dict,
    ) -> List[DetectedChange]:
        """Detect changes in grant eligibility."""
        changes = []
        
        prev_grant = self._parse_bool(prev.get("receives_grant"))
        curr_grant = self._parse_bool(curr.get("receives_grant"))
        
        if prev_grant is not None and curr_grant is not None:
            if prev_grant != curr_grant:
                hebrew_desc = (
                    "הרשות הפכה להיות זכאית למענק"
                    if curr_grant
                    else "הרשות כבר לא זכאית למענק"
                )
                
                change = DetectedChange(
                    change_type="grant_status",
                    field_name="receives_grant",
                    previous_value="לא מקבל" if not prev_grant else "מקבל",
                    current_value="לא מקבל" if not curr_grant else "מקבל",
                    hebrew_description=hebrew_desc,
                )
                changes.append(change)
        
        return changes
    
    def _is_retro_payment(self, prev: Dict, curr: Dict) -> bool:
        """Check if current entry is a retro payment from an earlier period."""
        
        prev_month = str(prev.get("month", "")).strip()
        curr_month = str(curr.get("month", "")).strip()
        
        if not prev_month or not curr_month or prev_month == curr_month:
            return False
        
        # Chop by comparing YYYY-MM strings
        try:
            # prev_month might be "2025-12", curr_month might be "2026-01"
            prev_parts = prev_month.split("-")
            curr_parts = curr_month.split("-")
            
            if len(prev_parts) >= 2 and len(curr_parts) >= 2:
                prev_year, prev_m = int(prev_parts[0]), int(prev_parts[1])
                curr_year, curr_m = int(curr_parts[0]), int(curr_parts[1])
                
                prev_date = datetime(prev_year, prev_m, 1)
                curr_date = datetime(curr_year, curr_m, 1)
                
                # Retro payment: current month payment but from earlier period
                return prev_date < curr_date
        except (ValueError, IndexError):
            pass
        
        return False
    
    def _create_retro_change(
        self,
        prev: Dict,
        curr: Dict,
    ) -> List[DetectedChange]:
        """Create a retro payment change entry."""
        changes = []
        
        prev_month = prev.get("month", "")
        curr_amount = self._parse_numeric(curr.get("amount", 0))
        
        hebrew_desc = f"תשלום רטרואקטיבי בגין תקופה קודמת ({prev_month})"
        
        change = DetectedChange(
            change_type="retro",
            field_name="period_month",
            previous_value=prev_month,
            current_value=curr.get("month", ""),
            impact_amount=float(curr_amount) if curr_amount else 0,
            hebrew_description=hebrew_desc,
        )
        changes.append(change)
        
        return changes
    
    def _parse_numeric(self, value) -> Optional[float]:
        """Safely parse numeric values."""
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            
            # Remove common currency symbols and formatting
            str_val = str(value).replace("₪", "").replace(",", "").strip()
            
            return float(str_val)
        except (ValueError, TypeError):
            return None
    
    def _parse_bool(self, value) -> Optional[bool]:
        """Safely parse boolean values."""
        if value is None:
            return None
        
        if isinstance(value, bool):
            return value
        
        str_val = str(value).lower().strip()
        return str_val in ["true", "yes", "1", "כן", "מקבל"]
    
    def _get_hebrew_description_numeric(
        self,
        field: str,
        prev_val: float,
        curr_val: float,
    ) -> str:
        """Generate Hebrew description for numeric changes."""
        
        if field == "num_children":
            diff = int(curr_val - prev_val)
            verb = "ירדו" if diff < 0 else "עלו"
            abs_diff = abs(diff)
            return f"מספר הילדים {verb} ב-{abs_diff} ילדים (מ-{int(prev_val)} ל-{int(curr_val)})"
        
        elif field == "num_units":
            diff = int(curr_val - prev_val)
            verb = "ירד" if diff < 0 else "עלה"
            abs_diff = abs(diff)
            return f"מספר התקנים {verb} ב-{abs_diff} (מ-{int(prev_val)} ל-{int(curr_val)})"
        
        elif field == "cost_per_child":
            diff = curr_val - prev_val
            verb = "ירדה" if diff < 0 else "עלתה"
            pct_change = (abs(diff) / prev_val) * 100
            return f"העלות לילד {verb} ב-{pct_change:.1f}% (מ-₪{prev_val:.2f} ל-₪{curr_val:.2f})"
        
        elif field == "cost_per_unit":
            diff = curr_val - prev_val
            verb = "ירדה" if diff < 0 else "עלתה"
            pct_change = (abs(diff) / prev_val) * 100 if prev_val != 0 else 0
            return f"העלות ליחידה {verb} ב-{pct_change:.1f}% (מ-₪{prev_val:.2f} ל-₪{curr_val:.2f})"
        
        elif field == "participation_pct":
            pct_diff = (curr_val - prev_val) * 100
            verb = "ירדה" if curr_val < prev_val else "עלתה"
            return f"אחוז ההשתתפות {verb} מ-{prev_val*100:.1f}% ל-{curr_val*100:.1f}%"
        
        return f"שינוי ב-{field}: {prev_val} → {curr_val}"
    
    def _get_hebrew_description_categorical(
        self,
        field: str,
        prev_val: str,
        curr_val: str,
    ) -> str:
        """Generate Hebrew description for categorical changes."""
        
        if field == "status":
            return f"סטטוס השורה השתנה מ-{prev_val} ל-{curr_val}"
        
        elif field == "payment_type":
            type_names = {
                "regular": "תשלום רגיל",
                "retro": "תשלום רטרואקטיבי",
                "shortage": "חוסר / קיצוץ",
                "adjustment": "התאמה טכנית",
            }
            prev_name = type_names.get(prev_val, prev_val)
            curr_name = type_names.get(curr_val, curr_val)
            return f"סוג התשלום השתנה מ-{prev_name} ל-{curr_name}"
        
        elif field == "sub_topic":
            return f"נושא משנה השתנה מ-{prev_val} ל-{curr_val}"
        
        return f"שינוי ב-{field}: {prev_val} → {curr_val}"
