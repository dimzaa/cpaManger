"""
File parser service for the budget management system.

Handles:
- Extraction of ZIP files
- Reading CSV files with proper Hebrew encoding (UTF-8-sig)
- Parsing invoice and breakdown files
- Returning structured data for further processing
"""

import zipfile
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, Any
import tempfile
import os
import re


class FileParserException(Exception):
    """Raised when file parsing fails."""
    pass


class FileParser:
    """
    Parses Ministry budget files in ZIP format.
    
    Handles both:
    1. Structured format: invoice.csv + breakdown.csv (English columns)
    2. Ministry format: [code]_[month]_[year][TABLE].csv with Hebrew columns
    
    Extracts municipality_code, month, year from FILENAME instead of requiring columns.
    """
    
    # Expected column names (in English)
    INVOICE_COLUMNS = {
        "municipality_code", "municipality_name", "total", "month", "year"
    }
    
    BREAKDOWN_COLUMNS = {
        "municipality_code", "municipality_name", "budget_topic", "topic_code",
        "amount", "period_month", "current_month", "line_type", "is_retro"
    }
    
    # Ministry Hebrew column mappings
    HEBREW_COLUMN_MAP = {
        # Municipality info (from all files)
        "סמל מוטב": "municipality_code",
        "שם מוטב": "municipality_name",
        
        # Month/Year (from filename, but also in files)
        "חודש חישוב": "month_str",  # e.g., "3/2026"
        
        # Budget line info
        "קוד נושא": "budget_code",
        "תאור תת נושא": "budget_description",
        "תאור נושא": "budget_topic_chesh",
        
        # Amounts and costs
        "סכום מחושב": "total",
        "סכום מחושב קודם": "previous_total",
        "הפרש מחושב": "difference",
        "עלות": "cost",
        "סך הכל מגיע": "total_due",
        "שולם": "paid",
        "הפרש לתשלום": "gap",
        
        # Details
        "מספר ילדים": "children_count",
        "אחוז": "percentage",
        "אחוז הנחה": "discount_percentage",
        "השתתפות הורים": "parent_participation",
        "השתתפות רשות": "municipality_participation",
        "סך משרות": "total_positions",
        "מספר משרות מדווחות": "reported_positions",
        
        # Other fields
        "זכאות למענק": "grant_eligibility",
        "חודש תחולה": "effective_month",
    }
    
    @staticmethod
    def parse_ministry_filename(filename: str) -> Dict[str, Any]:
        """
        Parse Ministry CSV filename to extract metadata.
        
        Filename format: [municipalityCode]_[month]_[year][TableName].csv
        Examples:
        - 10406544_3_2026MUCARIM.csv → {municipality_code: '10406544', month: 3, year: 2026, table: 'MUCARIM'}
        - 10406544_3_2026GY033.csv → {municipality_code: '10406544', month: 3, year: 2026, table: 'GY033'}
        
        Args:
            filename: CSV filename (with or without .csv extension)
            
        Returns:
            Dict with 'municipality_code', 'month', 'year', 'table' keys
            
        Raises:
            FileParserException: If filename doesn't match expected format
        """
        name = Path(filename).stem  # Remove .csv extension
        
        # Try to match pattern: [code]_[month]_[year][TABLE]
        import re
        match = re.match(r'(\d+)_(\d+)_(\d+)(.+)', name)
        
        if not match:
            raise FileParserException(f"Could not parse Ministry filename: {filename}. Expected format: [municipalityCode]_[month]_[year][TableName].csv")
        
        municipality_code, month, year, table_name = match.groups()
        
        return {
            "municipality_code": int(municipality_code),
            "month": int(month),
            "year": int(year),
            "table": table_name.upper(),
            "filename": filename,
        }
    
    @staticmethod
    def map_hebrew_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Map Hebrew column names to English equivalents.
        
        Creates new columns with English names while preserving original data.
        Handles both Hebrew column names and English (for mixed formats).
        
        Args:
            df: DataFrame with Hebrew column names
            
        Returns:
            DataFrame with English column names (originals also kept)
        """
        # Map columns based on the Hebrew->English mapping
        for hebrew_col, english_col in FileParser.HEBREW_COLUMN_MAP.items():
            if hebrew_col in df.columns:
                df[english_col] = df[hebrew_col]
        
        return df
    
    @staticmethod
    def prepare_ministry_invoice(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
        """
        Prepare Ministry invoice DataFrame for cross-reference analysis.
        
        Maps Hebrew column names and ensures required columns.
        
        Args:
            df: Invoice DataFrame from Ministry CSV (with Hebrew columns)
            month: Month number (e.g., 3 for March)
            year: Year number (e.g., 2026)
            
        Returns:
            DataFrame with proper column names for analysis
        """
        result = df.copy()
        
        # Ensure required columns exist
        if 'municipality_code' not in result.columns:
            result['municipality_code'] = 0
        if 'municipality_name' not in result.columns and 'שם מוטב' in result.columns:
            result['municipality_name'] = df['שם מוטב']
        if 'total' not in result.columns and 'סכום מחושב' in result.columns:
            result['total'] = df['סכום מחושב']
        elif 'total' not in result.columns:
            result['total'] = 0
        
        if 'month' not in result.columns:
            result['month'] = month
        if 'year' not in result.columns:
            result['year'] = year
        
        return result
    
    @staticmethod
    def prepare_ministry_breakdown(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
        """
        Prepare Ministry breakdown DataFrame for cross-reference analysis.
        
        Maps Hebrew column names to expected column names and computes required columns.
        
        Args:
            df: Breakdown DataFrame from Ministry CSV (with Hebrew columns)
            month: Month number (e.g., 3 for March)
            year: Year number (e.g., 2026)
            
        Returns:
            DataFrame with proper column names for analysis
        """
        # Map columns
        columns_to_keep = {
            'municipality_code',
            'municipality_name',
            'budget_code',
            'budget_description',
            'total',
            'cost',
            'percentage',
            'children_count',
            'effective_month',
            'grant_eligibility',
        }
        
        # Build result DataFrame with mapped columns
        result = df[[col for col in columns_to_keep if col in df.columns]].copy()
        
        # Rename for cross-reference analysis compatibility
        result['budget_topic'] = df['budget_description'] if 'budget_description' in df.columns else ''
        result['topic_code'] = df['budget_code'] if 'budget_code' in df.columns else 0
        result['amount'] = df['total'] if 'total' in df.columns else 0
        
        # Add current_month as the month the file represents (numeric)
        # The file shows payments made in this month/year
        result['current_month'] = month  # Numeric: 3 for March
        
        # Add period_month from effective_month (חודש תחולה)
        # Extract month number from "MM/YYYY" format
        if 'effective_month' in df.columns:
            # Extract both month number AND year from "MM/YYYY" format (e.g., "09/2025" → month=9, year=2025)
            # Bug fix: previously only extracted month number, losing the year — retro payments from a
            # prior year (e.g., "09/2025" in a March 2026 file) were saved with the wrong year.
            def extract_month_and_year(month_str):
                try:
                    if pd.isna(month_str):
                        return month, year
                    parts = str(month_str).split('/')
                    if len(parts) == 2:
                        return int(parts[0]), int(parts[1])
                    return int(parts[0]), year
                except:
                    return month, year

            parsed = df['effective_month'].apply(extract_month_and_year)
            result['period_month'] = parsed.apply(lambda x: x[0])
            result['period_year'] = parsed.apply(lambda x: x[1])
        else:
            result['period_month'] = month
            result['period_year'] = year

        # Add year from metadata (file's year, used for current_month)
        result['year'] = year
        result['month'] = month

        # Add line_type: default to 'regular' for now (all Ministry lines are regular unless marked)
        result['line_type'] = 'regular'

        # Add is_retro: True if period month+year differs from current month+year
        result['is_retro'] = (result['period_month'] != result['current_month']) | (result['period_year'] != result['year'])
        
        # Ensure required columns exist
        for col in ['municipality_code', 'budget_topic', 'topic_code', 'amount', 'current_month', 'period_month', 'line_type', 'is_retro']:
            if col not in result.columns:
                if col == 'municipality_code':
                    result[col] = 0
                elif col == 'topic_code':
                    result[col] = 0
                elif col in ['amount', 'current_month', 'period_month']:
                    result[col] = 0
                elif col == 'is_retro':
                    result[col] = False
                else:
                    result[col] = ''
        
        return result

    @staticmethod
    def prepare_gy(df: pd.DataFrame, topic_code: str, month: int, year: int) -> pd.DataFrame:
        """
        Prepare a GY### subtopic-detail file into a breakdown DataFrame.

        The Ministry GY files contain the PER-SUBTOPIC breakdown for a given
        purple-booklet code (e.g. GY003 for code 3: כיתות גן חובה/חינוך מיוחד/השלמה/3-4).

        Amount semantics (CRITICAL):
          * הפרש מחושב (difference)  → the settlement/adjustment for THIS invoice
                                        (positive = owed to the municipality,
                                         negative = deduction in this invoice).
          * סכום מחושב  (total)      → the full monthly entitlement as of this
                                        period. Using this as "amount" would
                                        massively inflate retro totals because
                                        each retro month would be counted
                                        at full entitlement instead of the
                                        delta that actually changed. This bug
                                        is precisely what made earlier ingestions
                                        show ₪2.2M retro for code 3 instead of
                                        the correct ~₪18K.

        So: ``amount = הפרש מחושב`` (mapped earlier to ``difference``).

        Args:
            df: Raw GY DataFrame (Hebrew columns, already mapped via map_hebrew_columns)
            topic_code: Purple-booklet code this file belongs to (e.g. "3", "19", "33")
            month: Calc month from filename (1-12)
            year:  Calc year from filename

        Returns:
            breakdown_df with English column names that mirror prepare_cheshbonit's
            output so it can be concatenated without further mapping.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        result = df.copy()

        # Subtopic / topic name
        if 'budget_description' in result.columns:
            subtopic = result['budget_description']
        elif 'תאור תת נושא' in df.columns:
            subtopic = df['תאור תת נושא']
        else:
            subtopic = pd.Series([''] * len(result))

        # Settlement delta — the amount that actually moves on this invoice.
        diff_col = None
        for cand in ('difference', 'הפרש מחושב'):
            if cand in result.columns:
                diff_col = cand
                break
        if diff_col is None:
            # No delta column — fall back to 0 rather than using סכום מחושב.
            result['amount'] = 0.0
        else:
            result['amount'] = pd.to_numeric(result[diff_col], errors='coerce').fillna(0.0)

        # Municipality metadata — pass-through if already present.
        if 'municipality_code' not in result.columns and 'סמל מוטב' in df.columns:
            result['municipality_code'] = df['סמל מוטב']
        if 'municipality_name' not in result.columns and 'שם מוטב' in df.columns:
            result['municipality_name'] = df['שם מוטב']

        # Topic code + topic description (subtopic name becomes the user-facing label).
        result['topic_code'] = str(topic_code)
        result['budget_topic'] = subtopic.astype(str)

        # Period vs calc month: GY files carry חודש תחולה per-row.
        def _extract_month_and_year(month_str):
            try:
                if pd.isna(month_str):
                    return month, year
                parts = str(month_str).split('/')
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
                return int(parts[0]), year
            except Exception:
                return month, year

        eff_col = None
        for cand in ('effective_month', 'חודש תחולה'):
            if cand in (result.columns if cand == 'effective_month' else df.columns):
                eff_col = cand
                break
        if eff_col == 'effective_month':
            parsed = result['effective_month'].apply(_extract_month_and_year)
        elif eff_col == 'חודש תחולה':
            parsed = df['חודש תחולה'].apply(_extract_month_and_year)
        else:
            parsed = pd.Series([(month, year)] * len(result))
        result['period_month'] = parsed.apply(lambda x: x[0])
        result['period_year'] = parsed.apply(lambda x: x[1])

        result['current_month'] = month
        result['year'] = year
        result['month'] = month
        result['is_retro'] = (result['period_month'] != month) | (result['period_year'] != year)
        result['line_type'] = 'gy'

        # Children count for formula variance.
        if 'children_count' not in result.columns and 'מספר ילדים' in df.columns:
            result['children_count'] = pd.to_numeric(df['מספר ילדים'], errors='coerce')

        # Percentage / participation fields when present.
        if 'percentage' not in result.columns and 'אחוז' in df.columns:
            result['percentage'] = pd.to_numeric(df['אחוז'], errors='coerce')

        return result

    @staticmethod
    def _parse_period_cell(raw, default_month: int, default_year: int):
        """
        Parse a חודש תחולה cell, which can appear in either order:

          * ``MM/YYYY``  — MUTAVIM, SHARATIM, MUCARIM, SHEFI, MOADON, GY…
          * ``YYYY/MM``  — HASAOT

        Returns (month, year). Falls back to (default_month, default_year) on
        anything unparseable or NaN.
        """
        try:
            if pd.isna(raw):
                return default_month, default_year
        except Exception:
            # Non-pandas scalar (e.g. plain None)
            if raw is None:
                return default_month, default_year

        s = str(raw).strip()
        if not s:
            return default_month, default_year

        # Numeric YYYYMM form (e.g. 202501)
        if s.isdigit() and len(s) == 6:
            try:
                y = int(s[:4])
                m = int(s[4:])
                if 1 <= m <= 12:
                    return m, y
            except Exception:
                pass

        parts = s.split('/')
        if len(parts) != 2:
            try:
                return int(parts[0]), default_year
            except Exception:
                return default_month, default_year

        try:
            a, b = int(parts[0]), int(parts[1])
        except Exception:
            return default_month, default_year

        # MM/YYYY vs YYYY/MM disambiguation:
        #   * four-digit a → YYYY/MM (HASAOT)
        #   * otherwise   → MM/YYYY
        if a > 12 and b <= 12:
            return b, a   # YYYY/MM
        if b > 12 and a <= 12:
            return a, b   # MM/YYYY
        # Both ≤12 (ambiguous): pick MM/YYYY since most files use that.
        return a, b if b > 31 else (a, b)

    @staticmethod
    def prepare_detail(df: pd.DataFrame, file_type: str, month: int, year: int) -> pd.DataFrame:
        """
        Prepare a Ministry detail file (MUTAVIM / SHARATIM / SHEFI / HASAOT /
        MUCARIM) into a breakdown DataFrame shaped like ``prepare_cheshbonit``
        output.

        Amount semantics mirror ``prepare_gy``:
          * ``amount = הפרש מחושב`` (per-invoice delta) — NOT ``סכום מחושב``.
          * ``is_retro = period ≠ calc month/year``.

        Each file has its own idiosyncrasies (SHEFI carries two ``חודש תחולה``
        columns, HASAOT uses YYYY/MM, MUCARIM/SHARATIM carry ``סמל מוסד``);
        those are normalised here so the caller can concat these rows directly
        into the breakdown with the GY rows.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        raw = df
        result = pd.DataFrame(index=raw.index)

        # --- municipality passthrough ---------------------------------------
        if 'סמל מוטב' in raw.columns:
            result['municipality_code'] = raw['סמל מוטב']
        if 'שם מוטב' in raw.columns:
            result['municipality_name'] = raw['שם מוטב']

        # --- topic code -----------------------------------------------------
        if 'קוד נושא' not in raw.columns:
            # Detail file without a topic code is not useful here —
            # return empty so the caller keeps the CHESHBONIT rows.
            return pd.DataFrame()
        result['topic_code'] = raw['קוד נושא'].astype(str)

        # --- subtopic label -------------------------------------------------
        # Priority: תאור תת נושא > נושא > תאור נושא
        label_col = None
        for cand in ('תאור תת נושא', 'נושא', 'תאור נושא'):
            if cand in raw.columns:
                label_col = cand
                break
        if label_col is not None:
            result['budget_topic'] = raw[label_col].astype(str)
        else:
            result['budget_topic'] = ''

        # --- amount (הפרש מחושב) -------------------------------------------
        if 'הפרש מחושב' in raw.columns:
            result['amount'] = pd.to_numeric(raw['הפרש מחושב'], errors='coerce').fillna(0.0)
        else:
            # No delta column — we cannot safely use this file. Return empty.
            return pd.DataFrame()

        # --- institution fields --------------------------------------------
        if 'סמל מוסד' in raw.columns:
            result['institution_code'] = raw['סמל מוסד']
        if 'שם מוסד' in raw.columns:
            result['institution_name'] = raw['שם מוסד']

        # --- unit / position / children counts -----------------------------
        if 'מספר יחידות' in raw.columns:
            result['children_count'] = pd.to_numeric(raw['מספר יחידות'], errors='coerce')
        elif 'מספר ילדים' in raw.columns:
            result['children_count'] = pd.to_numeric(raw['מספר ילדים'], errors='coerce')

        if 'מספר משרות' in raw.columns:
            result['positions'] = pd.to_numeric(raw['מספר משרות'], errors='coerce')

        if 'אחוז' in raw.columns:
            result['percentage'] = pd.to_numeric(raw['אחוז'], errors='coerce')
        elif 'אחוז השתתפות' in raw.columns:
            result['percentage'] = pd.to_numeric(raw['אחוז השתתפות'], errors='coerce')

        # --- period parsing -------------------------------------------------
        if 'חודש תחולה' in raw.columns:
            # SHEFI has TWO חודש תחולה columns — prefer the first (string form).
            period_series = raw['חודש תחולה']
            if isinstance(period_series, pd.DataFrame):
                period_series = period_series.iloc[:, 0]
            parsed = period_series.apply(
                lambda v: FileParser._parse_period_cell(v, month, year)
            )
            result['period_month'] = parsed.apply(lambda x: x[0])
            result['period_year'] = parsed.apply(lambda x: x[1])
        else:
            result['period_month'] = month
            result['period_year'] = year

        result['current_month'] = month
        result['year'] = year
        result['month'] = month
        result['is_retro'] = (
            (result['period_month'] != month) | (result['period_year'] != year)
        )
        result['line_type'] = file_type.lower()

        return result

    @staticmethod
    def prepare_yadaniim(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
        """
        Prepare YADANIIM — ad-hoc "manual" advances.

        Unlike formula-driven files, YADANIIM rows have NO ``הפרש מחושב`` —
        the ``סכום מחושב`` column IS the settlement this invoice (e.g. a
        ``מקדמת מערכת`` advance). These rows close reconciliation gaps where
        CHESHBONIT הפרש לתשלום = detail הפרש + YADANIIM סכום.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        raw = df
        result = pd.DataFrame(index=raw.index)

        if 'קוד נושא' not in raw.columns or 'סכום מחושב' not in raw.columns:
            return pd.DataFrame()

        if 'סמל מוטב' in raw.columns:
            result['municipality_code'] = raw['סמל מוטב']
        if 'שם מוטב' in raw.columns:
            result['municipality_name'] = raw['שם מוטב']
        if 'סמל מוסד' in raw.columns:
            result['institution_code'] = raw['סמל מוסד']
        if 'שם מוסד' in raw.columns:
            result['institution_name'] = raw['שם מוסד']

        result['topic_code'] = raw['קוד נושא'].astype(str)
        result['budget_topic'] = (
            raw['נושא'].astype(str) if 'נושא' in raw.columns else ''
        )
        result['amount'] = pd.to_numeric(
            raw['סכום מחושב'], errors='coerce'
        ).fillna(0.0)

        if 'חודש תחולה' in raw.columns:
            parsed = raw['חודש תחולה'].apply(
                lambda v: FileParser._parse_period_cell(v, month, year)
            )
            result['period_month'] = parsed.apply(lambda x: x[0])
            result['period_year'] = parsed.apply(lambda x: x[1])
        else:
            result['period_month'] = month
            result['period_year'] = year

        result['current_month'] = month
        result['year'] = year
        result['month'] = month
        result['is_retro'] = (
            (result['period_month'] != month) | (result['period_year'] != year)
        )
        result['line_type'] = 'yadaniim'

        return result

    @staticmethod
    def prepare_moadon(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
        """
        Prepare MOADON — after-school clubs (מועדוניות).

        MOADON has no ``קוד נושא`` column because it always maps to Ministry
        code 242 (מועדוניות ברשויות). Each row is one club-configuration;
        ``הפרש מחושב`` is the delta this invoice.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        raw = df
        result = pd.DataFrame(index=raw.index)

        if 'הפרש מחושב' not in raw.columns:
            return pd.DataFrame()

        if 'סמל מוטב' in raw.columns:
            result['municipality_code'] = raw['סמל מוטב']
        if 'שם מוטב' in raw.columns:
            result['municipality_name'] = raw['שם מוטב']

        result['topic_code'] = '242'
        # Build a descriptive label from the per-row attributes.
        def _label(r):
            typ = r.get('סוג מועדונית', '')
            hrs = r.get('שעות הפעלה', '')
            cnt = r.get('מספר מועדוניות', '')
            return f"מועדונית — סוג {typ}, {hrs}, {cnt} מועד'"
        result['budget_topic'] = raw.apply(_label, axis=1)

        result['amount'] = pd.to_numeric(
            raw['הפרש מחושב'], errors='coerce'
        ).fillna(0.0)

        if 'מספר מועדוניות' in raw.columns:
            result['children_count'] = pd.to_numeric(
                raw['מספר מועדוניות'], errors='coerce'
            )
        if 'אחוז השתתפות' in raw.columns:
            result['percentage'] = pd.to_numeric(
                raw['אחוז השתתפות'], errors='coerce'
            )

        if 'חודש תחולה' in raw.columns:
            parsed = raw['חודש תחולה'].apply(
                lambda v: FileParser._parse_period_cell(v, month, year)
            )
            result['period_month'] = parsed.apply(lambda x: x[0])
            result['period_year'] = parsed.apply(lambda x: x[1])
        else:
            result['period_month'] = month
            result['period_year'] = year

        result['current_month'] = month
        result['year'] = year
        result['month'] = month
        result['is_retro'] = (
            (result['period_month'] != month) | (result['period_year'] != year)
        )
        result['line_type'] = 'moadon'

        return result

    @staticmethod
    def prepare_sacal(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
        """
        Prepare SACAL — high-school budget (סל תלמיד על-יסודי).

        No ``קוד נושא`` column; always maps to Ministry code 1 (שכ"ל על-יסודי).
        Each row is a class × subject at one institution. ``הפרש מחושב`` is
        the delta this invoice. The formula inputs ((1)–(5)) are preserved
        for later formula-variance attribution.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        raw = df
        result = pd.DataFrame(index=raw.index)

        if 'הפרש מחושב' not in raw.columns:
            return pd.DataFrame()

        if 'סמל מוטב' in raw.columns:
            result['municipality_code'] = raw['סמל מוטב']
        if 'שם מוטב' in raw.columns:
            result['municipality_name'] = raw['שם מוטב']
        if 'סמל מוסד' in raw.columns:
            result['institution_code'] = raw['סמל מוסד']
        if 'שם מוסד' in raw.columns:
            result['institution_name'] = raw['שם מוסד']

        result['topic_code'] = '1'
        # Label per row: "<institution>: class <grade>, stream <megama>"
        def _label(r):
            grade = r.get('מקבילה/כיתה', '')
            megama = r.get('מגמה', '')
            return f"שכ\"ל על-יסודי — כיתה {grade}, מגמה {megama}"
        result['budget_topic'] = raw.apply(_label, axis=1)

        result['amount'] = pd.to_numeric(
            raw['הפרש מחושב'], errors='coerce'
        ).fillna(0.0)

        if '(1) מספר תלמידים' in raw.columns:
            result['children_count'] = pd.to_numeric(
                raw['(1) מספר תלמידים'], errors='coerce'
            )

        if 'חודש תחולה' in raw.columns:
            parsed = raw['חודש תחולה'].apply(
                lambda v: FileParser._parse_period_cell(v, month, year)
            )
            result['period_month'] = parsed.apply(lambda x: x[0])
            result['period_year'] = parsed.apply(lambda x: x[1])
        else:
            result['period_month'] = month
            result['period_year'] = year

        result['current_month'] = month
        result['year'] = year
        result['month'] = month
        result['is_retro'] = (
            (result['period_month'] != month) | (result['period_year'] != year)
        )
        result['line_type'] = 'sacal'

        return result

    # ------------------------------------------------------------------
    # Phase-2 parsers: formula-input files (no amounts, just drivers)
    # ------------------------------------------------------------------

    # School-year month columns (Sept → Aug), with the typo the Ministry
    # ships in MISROT/MISROTGY ("אוגיסט" instead of "אוגוסט").
    _SCHOOL_YEAR_MONTHS = (
        ("ספטמבר",  1), ("אוקטובר", 2), ("נובמבר",  3), ("דצמבר",  4),
        ("ינואר",   5), ("פברואר", 6), ("מרץ",     7), ("אפריל",  8),
        ("מאי",     9), ("יוני",   10), ("יולי",   11), ("אוגוסט", 12),
        ("אוגיסט", 12),  # Ministry typo variant — same month
    )

    @staticmethod
    def prepare_ichluskitot(df: pd.DataFrame) -> pd.DataFrame:
        """
        Flatten ICHLUSKITOT into one row per (institution, class, month).

        Source columns:
            שנה, סמל מוטב, שם מוטב, סמל מוסד, שם מוסד, כיתה, מקבילה,
            תאור סוג כיתה, מס. תלמידים מינימלי/מקסימלי בכיתה,
            ספטמבר..אוגוסט (counts)

        Returns one row per (class, month) with the monthly student count.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        out = []
        for _, row in df.iterrows():
            base = {
                "school_year": int(row["שנה"]) if "שנה" in row.index and pd.notna(row.get("שנה")) else None,
                "institution_code": str(row.get("סמל מוסד", "")).strip() or None,
                "institution_name": str(row.get("שם מוסד", "")).strip() or None,
                "class_level": int(row["כיתה"]) if "כיתה" in row.index and pd.notna(row.get("כיתה")) else None,
                "stream": int(row["מקבילה"]) if "מקבילה" in row.index and pd.notna(row.get("מקבילה")) else None,
                "class_type": str(row.get("תאור סוג כיתה", "")).strip() or None,
                "min_students": (
                    int(row["מס. תלמידים מינימלי בכיתה"])
                    if "מס. תלמידים מינימלי בכיתה" in row.index
                    and pd.notna(row.get("מס. תלמידים מינימלי בכיתה"))
                    else None
                ),
                "max_students": (
                    int(row["מס. תלמידים מקסימלי בכיתה"])
                    if "מס. תלמידים מקסימלי בכיתה" in row.index
                    and pd.notna(row.get("מס. תלמידים מקסימלי בכיתה"))
                    else None
                ),
            }
            for col, m in FileParser._SCHOOL_YEAR_MONTHS:
                if col not in row.index:
                    continue
                v = row[col]
                if pd.isna(v):
                    continue
                try:
                    count = int(v)
                except Exception:
                    continue
                out.append({**base, "month": m, "student_count": count})
        return pd.DataFrame(out)

    @staticmethod
    def prepare_misrot(df: pd.DataFrame, scope: str = "institution") -> pd.DataFrame:
        """
        Flatten MISROT (or MISROTGY) into one row per (institution, role, month).

        scope='institution' → MISROT: rows carry ``סמל מוסד`` / ``שם מוסד``.
        scope='gy'          → MISROTGY: rows carry ``סמל ישוב`` / ``שם ישוב``
                              (no institution — village-level kindergarten FTE).

        Non-zero FTE values only — the sparse zero-filled matrix isn't useful.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        out = []
        for _, row in df.iterrows():
            inst_code = None
            inst_name = None
            village_code = None
            village_name = None
            if scope == "institution":
                if "סמל מוסד" in row.index and pd.notna(row.get("סמל מוסד")):
                    inst_code = str(row["סמל מוסד"]).strip()
                if "שם מוסד" in row.index and pd.notna(row.get("שם מוסד")):
                    inst_name = str(row["שם מוסד"]).strip()
            else:  # 'gy'
                if "סמל ישוב" in row.index and pd.notna(row.get("סמל ישוב")):
                    village_code = str(row["סמל ישוב"]).strip()
                if "שם ישוב" in row.index and pd.notna(row.get("שם ישוב")):
                    village_name = str(row["שם ישוב"]).strip()

            role = str(row.get("תאור תפקיד", "")).strip()
            role_category = str(row.get("שיוך תפקיד", "")).strip() or None
            if not role:
                continue

            for col, m in FileParser._SCHOOL_YEAR_MONTHS:
                if col not in row.index:
                    continue
                v = row[col]
                if pd.isna(v):
                    continue
                try:
                    fte = float(v)
                except Exception:
                    continue
                if fte == 0:
                    continue
                out.append({
                    "scope": scope,
                    "institution_code": inst_code,
                    "institution_name": inst_name,
                    "village_code": village_code,
                    "village_name": village_name,
                    "role": role,
                    "role_category": role_category,
                    "month": m,
                    "fte": fte,
                })
        return pd.DataFrame(out)

    @staticmethod
    def prepare_hasmaslulim(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
        """
        Flatten HASMASLULIM into per-route audit rows.

        Preserves the full vehicle + company + cost-component detail for each
        bus route. Numeric coercion for cost components with safe fallback to
        NULL when the field is absent.
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()

        def _s(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            s = str(v).strip()
            return s or None

        def _f(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            try:
                return float(v)
            except Exception:
                return None

        def _i(v):
            f = _f(v)
            return int(f) if f is not None else None

        out = []
        for _, row in df.iterrows():
            period_month = None
            period_year = None
            pm_raw = row.get("חודש תחולה")
            if pd.notna(pm_raw):
                period_month, period_year = FileParser._parse_period_cell(pm_raw, month, year)

            out.append({
                "route_number": _s(row.get("מספר מסלול")),
                "route_type": _s(row.get("תיאור סוג מסלול")),
                "payment_group": _s(row.get("תיאור קבוצה לתשלום")),
                "period": _s(row.get("תיאור תקופת מסלול")),
                "direction": _s(row.get("תיאור כיוון נסיעה")),
                "company_code": _s(row.get("חברת הסעה")),
                "company_name": _s(row.get("תיאור חברת הסעה")),
                "topic_code": _s(row.get("קוד נושא")) or "0",
                "topic_name": _s(row.get("שם נושא")),
                "localities": _s(row.get("ישובים")),
                "institutions": _s(row.get("מוסדות")),
                "vehicle_code": _s(row.get("סמל רכב")),
                "vehicle_type": _s(row.get("תיאור סמל רכב")),
                "license_plate": _s(row.get("מספר רישוי")),
                "days": _i(row.get("ימי ביצוע")),
                "vehicle_count": _i(row.get("כמות רכבים")),
                "km_per_trip": _f(row.get("קמ בנסיעה")),
                "daily_cost": _f(row.get("עלות יומית")),
                "participation_pct": _f(row.get("אחוז השתתפות")),
                "vat_factor": _f(row.get("מע''מ")),
                "escalation": _f(row.get("התייקרות מצטברת")),
                "calculated_total": _f(row.get("סכום מחושב")),
                "period_month": period_month,
                "period_year": period_year,
                "notes": _s(row.get("הערה")),
            })
        return pd.DataFrame(out)

    @staticmethod
    def extract_institution_roster(temp_dir: str) -> Dict[str, Any]:
        """
        Minimal stub: returns an empty mapping.

        The full high-school institution roster extractor was truncated from
        this snapshot. Returning an empty dict lets the upload route continue
        without exceptions — the main billing/breakdown ingestion (CHESHBONIT +
        GY) is unaffected; only per-institution breakdown tables are skipped.
        """
        return {}

    @staticmethod
    def prepare_cheshbonit(df: pd.DataFrame, month: int, year: int):
        """
        Prepare CHESHBONIT billing file into (invoice_df, breakdown_df).

        invoice_df: one row with municipality totals (total=sum_paid, total_due=sum_due)
        breakdown_df: one row per CHESHBONIT line with amount=gap per line
        """
        result = df.copy()

        # Normalize column names
        if 'budget_code' in result.columns:
            result['topic_code'] = result['budget_code'].astype(str)
        elif 'קוד נושא' in df.columns:
            result['topic_code'] = df['קוד נושא'].astype(str)
        else:
            result['topic_code'] = '0'

        if 'budget_topic_chesh' in result.columns:
            result['budget_topic'] = result['budget_topic_chesh']
        elif 'תאור נושא' in df.columns:
            result['budget_topic'] = df['תאור נושא']
        else:
            result['budget_topic'] = ''

        for col, hebrew in [('total_due', 'סך הכל מגיע'), ('paid', 'שולם'), ('gap', 'הפרש לתשלום')]:
            if col not in result.columns and hebrew in df.columns:
                result[col] = pd.to_numeric(df[hebrew], errors='coerce').fillna(0)
            elif col not in result.columns:
                result[col] = 0.0

        # Ensure numeric types for aggregations
        result['total_due'] = pd.to_numeric(result['total_due'], errors='coerce').fillna(0)
        result['paid'] = pd.to_numeric(result['paid'], errors='coerce').fillna(0)
        result['gap'] = pd.to_numeric(result['gap'], errors='coerce').fillna(0)

        # invoice_df: aggregated per municipality
        invoice_agg = result.groupby(['municipality_code', 'municipality_name']).agg(
            total=('paid', 'sum'),
            total_due=('total_due', 'sum')
        ).reset_index()
        invoice_agg['month'] = month
        invoice_agg['year'] = year
        invoice_df = invoice_agg

        # breakdown_df: one row per billing line
        def extract_month_and_year(month_str):
            try:
                if pd.isna(month_str):
                    return month, year
                parts = str(month_str).split('/')
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
                return int(parts[0]), year
            except:
                return month, year

        if 'effective_month' in result.columns:
            parsed = result['effective_month'].apply(extract_month_and_year)
            result['period_month'] = parsed.apply(lambda x: x[0])
            result['period_year'] = parsed.apply(lambda x: x[1])
        else:
            result['period_month'] = month
            result['period_year'] = year

        result['current_month'] = month
        result['year'] = year
        result['month'] = month
        result['amount'] = result['gap']
        result['is_retro'] = (result['period_month'] != month) | (result['period_year'] != year)
        result['line_type'] = 'cheshbonit'

        breakdown_df = result
        return invoice_df, breakdown_df
    
    @staticmethod
    def extract_zip(zip_path: str) -> Tuple[str, list]:
        """
        Extract ZIP file and return temporary directory path.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Tuple of (temp_dir, list_of_csv_files)
            
        Raises:
            FileParserException: If ZIP extraction fails
        """
        try:
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find CSV files in the extracted directory
            csv_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.csv'):
                        csv_files.append(os.path.join(root, file))
            
            if not csv_files:
                raise FileParserException("No CSV files found in ZIP")
            
            return temp_dir, csv_files
        
        except zipfile.BadZipFile as e:
            raise FileParserException(f"Invalid ZIP file: {str(e)}")
        except Exception as e:
            raise FileParserException(f"Error extracting ZIP: {str(e)}")
    
    @staticmethod
    def read_csv_with_hebrew(file_path: str) -> pd.DataFrame:
        """
        Read CSV file with proper Hebrew encoding support.
        
        Uses UTF-8-sig encoding to handle Israeli budget files.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            pandas DataFrame
            
        Raises:
            FileParserException: If CSV reading fails
        """
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            return df
        except Exception as e:
            raise FileParserException(f"Error reading CSV {file_path}: {str(e)}")
    
    @staticmethod
    def validate_invoice_df(df: pd.DataFrame) -> None:
        """
        Validate invoice DataFrame structure.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            FileParserException: If validation fails
        """
        missing_cols = FileParser.INVOICE_COLUMNS - set(df.columns)
        if missing_cols:
            raise FileParserException(
                f"Invoice CSV missing columns: {missing_cols}. "
                f"Expected: {FileParser.INVOICE_COLUMNS}"
            )
        
        if df.empty:
            raise FileParserException("Invoice CSV is empty")
    
    @staticmethod
    def validate_breakdown_df(df: pd.DataFrame) -> None:
        """
        Validate breakdown DataFrame structure.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            FileParserException: If validation fails
        """
        missing_cols = FileParser.BREAKDOWN_COLUMNS - set(df.columns)
        if missing_cols:
            raise FileParserException(
                f"Breakdown CSV missing columns: {missing_cols}. "
                f"Expected: {FileParser.BREAKDOWN_COLUMNS}"
            )
        
        if df.empty:
            raise FileParserException("Breakdown CSV is empty")
    
    @staticmethod
    def parse_zip(zip_path: str) -> Dict[str, Any]:
        """
        Main method: Parse a ZIP file and return structured data.
        
        Handles both:
        1. Structured format: invoice.csv + breakdown.csv (English columns)
        2. Ministry format: [code]_[month]_[year][TABLE].csv (Hebrew columns, metadata from filename)
        
        Ministry format:
        - Extracts municipality_code, month, year from FILENAME (not columns)
        - Uses CHESHBONIT.csv as billing source for both invoice and breakdown
        - GY*.csv files are optional and not required for billing totals
        - Maps Hebrew column names to English
        
        Args:
            zip_path: Path to ZIP file from Ministry
            
        Returns:
            Dictionary containing:
            {
                "invoice_df": DataFrame (with English columns),
                "breakdown_df": DataFrame (with English columns),
                "temp_dir": temporary directory (must be cleaned up),
                "municipalities": set of municipality codes found,
                "metadata": dict with extraction info
            }
            
        Raises:
            FileParserException: If parsing fails at any step
        """
        temp_dir = None
        # Formula-input tables (no amounts — just drivers). Populated by
        # Step 4f if the relevant files are present in the ZIP.
        formula_inputs: Dict[str, pd.DataFrame] = {}
        # Structured reconciliation warnings. Mirrors the ``⚠️``/``✓``
        # prints below so the admin UI can surface them without grepping
        # stdout. See ``IngestionWarning`` model for the persisted shape.
        warnings: list = []

        def _warn(
            severity: str,
            category: str,
            message: str,
            *,
            file_type: str = None,
            topic_code: str = None,
            detail_sum: float = None,
            aux_sum: float = None,
            cheshbonit_sum: float = None,
            delta: float = None,
        ) -> None:
            warnings.append(
                {
                    "severity": severity,
                    "category": category,
                    "file_type": file_type,
                    "topic_code": topic_code,
                    "detail_sum": detail_sum,
                    "aux_sum": aux_sum,
                    "cheshbonit_sum": cheshbonit_sum,
                    "delta": delta,
                    "message": message[:500],  # model column cap
                }
            )
        try:
            # Step 1: Extract ZIP
            temp_dir, csv_files = FileParser.extract_zip(zip_path)
            
            print(f"\n📂 Found {len(csv_files)} CSV files in ZIP:")
            for f in csv_files:
                print(f"   - {Path(f).name}")
            
            # Step 2: Detect format (Ministry vs Structured) by attempting filename parsing
            ministry_format = False
            metadata = {}
            
            try:
                # Try to parse first file to detect Ministry format
                first_filename = Path(csv_files[0]).name
                metadata = FileParser.parse_ministry_filename(first_filename)
                ministry_format = True
                print(f"✓ Detected Ministry format")
                print(f"  Municipality: {metadata['municipality_code']}, Month: {metadata['month']}/{metadata['year']}")
            except FileParserException:
                # Not Ministry format, will try structured format
                print(f"⚠️  Not Ministry format, trying structured format (invoice.csv / breakdown.csv)...")
            
            # Step 3: Parse files based on detected format
            if ministry_format:
                print(f"\n🔄 Processing Ministry format files...")

                # Find invoice (CHESHBONIT) file + any GY subtopic-detail files
                # + any cross-cutting detail files (MUTAVIM/SHARATIM/SHEFI/
                # HASAOT/MUCARIM). Detail files carry ``הפרש מחושב`` per row
                # and let us break CHESHBONIT lines out by subtopic / institution.
                invoice_file = None
                gy_files: Dict[str, str] = {}   # topic_code -> file path
                detail_files: Dict[str, str] = {}  # file_type -> file path
                aux_files: Dict[str, str] = {}  # additive aux: yadaniim/moadon/sacal
                formula_files: Dict[str, str] = {}  # no-amount drivers
                _DETAIL_TYPES = (
                    "mutavim", "sharatim", "shefi", "hasaot", "mucarim"
                )
                _AUX_TYPES = ("yadaniim", "moadon", "sacal")
                _FORMULA_TYPES = ("ichluskitot", "misrotgy", "misrot", "hasmaslulim")

                for csv_file in csv_files:
                    filename_lower = Path(csv_file).name.lower()
                    if "cheshbonit" in filename_lower:
                        invoice_file = csv_file
                        print(f"   ✓ Invoice (CHESHBONIT): {Path(csv_file).name}")
                        continue

                    m = re.search(r"gy0*(\d+)", filename_lower)
                    if m and filename_lower.startswith(str(metadata['municipality_code'])):
                        code = str(int(m.group(1)))  # "003" → "3"
                        gy_files[code] = csv_file
                        print(f"   ✓ Detail (GY{m.group(1)}): {Path(csv_file).name}")
                        continue

                    matched = False
                    for dt in _DETAIL_TYPES:
                        if dt in filename_lower:
                            detail_files[dt] = csv_file
                            print(f"   ✓ Detail ({dt.upper()}): {Path(csv_file).name}")
                            matched = True
                            break
                    if matched:
                        continue

                    for at in _AUX_TYPES:
                        if at in filename_lower:
                            aux_files[at] = csv_file
                            print(f"   ✓ Aux ({at.upper()}): {Path(csv_file).name}")
                            matched = True
                            break
                    if matched:
                        continue

                    # Formula-input files are matched longest-first so
                    # MISROTGY isn't misclassified as MISROT.
                    for ft in sorted(_FORMULA_TYPES, key=len, reverse=True):
                        if ft in filename_lower:
                            formula_files[ft] = csv_file
                            print(f"   ✓ Formula ({ft.upper()}): {Path(csv_file).name}")
                            break

                if not invoice_file:
                    raise FileParserException(
                        f"Could not find CHESHBONIT (billing) file in Ministry format ZIP. "
                        f"Expected a file with 'CHESHBONIT' in the name. "
                        f"Found: {[Path(f).name for f in csv_files]}"
                    )

                # Flag expected-but-absent aux/formula files so the UI can
                # show "Feb ZIP shipped without YADANIIM" explicitly.
                for at in _AUX_TYPES:
                    if at not in aux_files:
                        _warn(
                            "info",
                            "missing_file",
                            f"No {at.upper()} file present in ZIP",
                            file_type=at.upper(),
                        )
                for ft in _FORMULA_TYPES:
                    if ft not in formula_files:
                        _warn(
                            "info",
                            "missing_file",
                            f"No {ft.upper()} file present in ZIP",
                            file_type=ft.upper(),
                        )

                # Step 4a: Read CHESHBONIT as both invoice and breakdown
                print(f"\n📖 Reading CHESHBONIT billing file...")
                cheshbonit_raw = FileParser.read_csv_with_hebrew(invoice_file)
                print(f"   Rows: {len(cheshbonit_raw)}, Columns: {list(cheshbonit_raw.columns)[:6]}")
                cheshbonit_mapped = FileParser.map_hebrew_columns(cheshbonit_raw)
                invoice_df, cheshbonit_breakdown_df = FileParser.prepare_cheshbonit(
                    cheshbonit_mapped, metadata['month'], metadata['year']
                )
                print(f"   ✓ invoice_df: {len(invoice_df)} municipalities")
                print(f"   ✓ CHESHBONIT breakdown: {len(cheshbonit_breakdown_df)} lines")
                print(f"   Total paid (שולם): {invoice_df['total'].sum():,.0f}")
                print(f"   Total due (מגיע): {invoice_df['total_due'].sum():,.0f}")
                print(f"   Total gap: {invoice_df['total_due'].sum() - invoice_df['total'].sum():,.0f}")

                # Step 4b: Read GY### files for subtopic detail.
                # Strategy: for any code that has a GY file, REPLACE its
                # CHESHBONIT rows with the GY subtopic breakdown. The totals
                # should match (CHESHBONIT הפרש לתשלום ≡ sum of GY הפרש מחושב
                # for the same code and period), but GY gives us per-subtopic
                # rows + num_children for formula variance.
                gy_breakdowns = []
                if gy_files:
                    print(f"\n📖 Reading GY subtopic-detail files ({len(gy_files)} codes)...")
                    for code, gy_path in gy_files.items():
                        try:
                            gy_raw = FileParser.read_csv_with_hebrew(gy_path)
                            gy_mapped = FileParser.map_hebrew_columns(gy_raw)
                            gy_br = FileParser.prepare_gy(
                                gy_mapped, code, metadata['month'], metadata['year']
                            )
                            if len(gy_br) > 0:
                                gy_breakdowns.append(gy_br)
                                print(
                                    f"   ✓ GY{int(code):03d}: {len(gy_br)} subtopic rows, "
                                    f"sum(amount)={gy_br['amount'].sum():,.2f}"
                                )
                        except Exception as exc:
                            print(f"   ⚠️  Skipping {Path(gy_path).name}: {exc}")
                            _warn(
                                "error",
                                "file_parse_error",
                                f"Skipping {Path(gy_path).name}: {exc}",
                                file_type=f"GY{int(code):03d}",
                                topic_code=str(code),
                            )

                # Step 4c: Read cross-cutting detail files (MUTAVIM / SHARATIM
                # / SHEFI / HASAOT / MUCARIM) for per-institution / per-subtopic
                # rows. Each of these carries ``קוד נושא`` + ``הפרש מחושב`` so
                # we can tie out against CHESHBONIT per-code before swapping.
                #
                # Priority order (most specific wins): GY > MUTAVIM > SHARATIM
                # > SHEFI > HASAOT > MUCARIM. A code covered by an earlier
                # source is NOT replaced again by a later one.
                _DETAIL_PRIORITY = (
                    "mutavim", "sharatim", "shefi", "hasaot", "mucarim"
                )
                detail_breakdowns: list = []
                # Codes already covered by GY (can't be overwritten by detail).
                already_covered: set = set()
                if gy_breakdowns:
                    gy_concat = pd.concat(gy_breakdowns, ignore_index=True, sort=False)
                    already_covered = set(gy_concat['topic_code'].astype(str).unique())

                # Pre-compute per-code sum of CHESHBONIT הפרש לתשלום for tie-out.
                cb_by_code = (
                    cheshbonit_breakdown_df.groupby(
                        cheshbonit_breakdown_df['topic_code'].astype(str)
                    )['amount'].sum().to_dict()
                )

                if detail_files:
                    print(
                        f"\n📖 Reading cross-cutting detail files "
                        f"({len(detail_files)} types)..."
                    )
                    for dt in _DETAIL_PRIORITY:
                        if dt not in detail_files:
                            continue
                        path = detail_files[dt]
                        try:
                            raw = FileParser.read_csv_with_hebrew(path)
                            prepared = FileParser.prepare_detail(
                                raw, dt, metadata['month'], metadata['year']
                            )
                            if prepared is None or len(prepared) == 0:
                                print(f"   ⚠️  {dt.upper()}: no rows produced, skipping")
                                _warn(
                                    "warn",
                                    "empty_detail",
                                    f"{dt.upper()}: no rows produced, skipping",
                                    file_type=dt.upper(),
                                )
                                continue

                            # Per-code tie-out: keep only rows whose code-level
                            # sum matches CHESHBONIT within 1 agora.
                            sums = prepared.groupby(
                                prepared['topic_code'].astype(str)
                            )['amount'].sum()
                            safe_codes: list = []
                            for code, detail_sum in sums.items():
                                if code in already_covered:
                                    continue
                                cb_sum = cb_by_code.get(str(code))
                                if cb_sum is None:
                                    continue
                                if abs(float(detail_sum) - float(cb_sum)) < 0.01:
                                    safe_codes.append(code)
                                else:
                                    print(
                                        f"   ⚠️  {dt.upper()}:{code} skipped — "
                                        f"detail sum {float(detail_sum):,.2f} ≠ "
                                        f"CHESHBONIT {float(cb_sum):,.2f} "
                                        f"(Δ={float(detail_sum) - float(cb_sum):,.2f})"
                                    )
                                    _warn(
                                        "warn",
                                        "tie_out_mismatch",
                                        (
                                            f"{dt.upper()}:{code} skipped — detail "
                                            f"sum {float(detail_sum):,.2f} ≠ "
                                            f"CHESHBONIT {float(cb_sum):,.2f}"
                                        ),
                                        file_type=dt.upper(),
                                        topic_code=str(code),
                                        detail_sum=float(detail_sum),
                                        cheshbonit_sum=float(cb_sum),
                                        delta=float(detail_sum) - float(cb_sum),
                                    )
                            if not safe_codes:
                                print(f"   ⚠️  {dt.upper()}: no codes tied out, skipping")
                                _warn(
                                    "warn",
                                    "tie_out_mismatch",
                                    f"{dt.upper()}: no codes tied out, skipping",
                                    file_type=dt.upper(),
                                )
                                continue
                            subset = prepared[
                                prepared['topic_code'].astype(str).isin(safe_codes)
                            ].copy()
                            detail_breakdowns.append(subset)
                            already_covered.update(safe_codes)
                            print(
                                f"   ✓ {dt.upper()}: {len(subset)} rows across "
                                f"{len(safe_codes)} codes, sum={subset['amount'].sum():,.2f}"
                            )
                        except Exception as exc:
                            print(f"   ⚠️  Skipping {Path(path).name}: {exc}")
                            _warn(
                                "error",
                                "file_parse_error",
                                f"Skipping {Path(path).name}: {exc}",
                                file_type=dt.upper(),
                            )

                # Step 4d: Read auxiliary files (YADANIIM / MOADON / SACAL).
                # These are ADDITIVE sources — each augments (not replaces)
                # whatever the detail/GY files already contribute for a given
                # code. A code is "fully covered" only when detail_sum +
                # aux_sum (for all aux files touching that code) equals
                # CHESHBONIT gap to within 1 agora.
                #
                # Per-code hard mappings for aux files that lack ``קוד נושא``:
                _AUX_FIXED_CODE = {"moadon": "242", "sacal": "1"}

                aux_breakdowns_by_code: Dict[str, list] = {}
                if aux_files:
                    print(
                        f"\n📖 Reading auxiliary files ({len(aux_files)} types)..."
                    )
                    for at, path in aux_files.items():
                        try:
                            raw = FileParser.read_csv_with_hebrew(path)
                            if at == "yadaniim":
                                prepared = FileParser.prepare_yadaniim(
                                    raw, metadata['month'], metadata['year']
                                )
                            elif at == "moadon":
                                prepared = FileParser.prepare_moadon(
                                    raw, metadata['month'], metadata['year']
                                )
                            elif at == "sacal":
                                prepared = FileParser.prepare_sacal(
                                    raw, metadata['month'], metadata['year']
                                )
                            else:
                                continue

                            if prepared is None or len(prepared) == 0:
                                print(f"   ⚠️  {at.upper()}: no rows produced, skipping")
                                _warn(
                                    "warn",
                                    "empty_aux",
                                    f"{at.upper()}: no rows produced, skipping",
                                    file_type=at.upper(),
                                )
                                continue

                            # For sacal/moadon, override topic_code with the
                            # fixed Ministry code (file doesn't carry it).
                            if at in _AUX_FIXED_CODE:
                                prepared['topic_code'] = _AUX_FIXED_CODE[at]

                            # Group by topic_code for later additive tie-out.
                            for code, sub in prepared.groupby(
                                prepared['topic_code'].astype(str)
                            ):
                                aux_breakdowns_by_code.setdefault(
                                    str(code), []
                                ).append(sub.copy())
                            print(
                                f"   ✓ {at.upper()}: {len(prepared)} rows, "
                                f"sum={prepared['amount'].sum():,.2f}, "
                                f"codes={sorted(prepared['topic_code'].astype(str).unique().tolist())}"
                            )
                        except Exception as exc:
                            print(f"   ⚠️  Skipping {Path(path).name}: {exc}")
                            _warn(
                                "error",
                                "file_parse_error",
                                f"Skipping {Path(path).name}: {exc}",
                                file_type=at.upper(),
                            )

                # Step 4e: Recompute per-code coverage using detail + aux sums.
                # Detail breakdowns that already tied out stay. For codes that
                # DIDN'T tie via detail alone, check whether adding aux files
                # closes the gap — if so, include the aux rows + any rejected
                # detail rows for that code.
                detail_concat = (
                    pd.concat(detail_breakdowns, ignore_index=True, sort=False)
                    if detail_breakdowns else pd.DataFrame()
                )
                covered_by_detail = (
                    set(detail_concat['topic_code'].astype(str).unique())
                    if len(detail_concat) else set()
                )

                # Also re-read all detail files in raw form (regardless of
                # tie-out) to recompute per-code sums for the additive pass —
                # we need the FULL detail contribution, not just the safe bits.
                all_detail_raw: list = []
                if detail_files:
                    for dt, path in detail_files.items():
                        try:
                            rr = FileParser.read_csv_with_hebrew(path)
                            pp = FileParser.prepare_detail(
                                rr, dt, metadata['month'], metadata['year']
                            )
                            if pp is not None and len(pp) > 0:
                                all_detail_raw.append(pp)
                        except Exception:
                            pass
                all_detail_raw_df = (
                    pd.concat(all_detail_raw, ignore_index=True, sort=False)
                    if all_detail_raw else pd.DataFrame()
                )
                detail_sum_by_code: Dict[str, float] = {}
                if len(all_detail_raw_df):
                    for code, s in all_detail_raw_df.groupby(
                        all_detail_raw_df['topic_code'].astype(str)
                    )['amount'].sum().items():
                        detail_sum_by_code[str(code)] = float(s)

                # Aux codes that need to be combined with detail
                additive_rows: list = []
                for code, subs in aux_breakdowns_by_code.items():
                    aux_concat = pd.concat(subs, ignore_index=True, sort=False)
                    aux_sum = float(aux_concat['amount'].sum())
                    detail_sum = detail_sum_by_code.get(code, 0.0)
                    cb_sum = float(cb_by_code.get(code, 0.0))
                    combined = detail_sum + aux_sum
                    if abs(combined - cb_sum) < 0.01:
                        # Combined tie-out succeeds. Include aux rows AND any
                        # detail rows for this code that were previously
                        # rejected.
                        additive_rows.append(aux_concat)
                        if code not in covered_by_detail and len(all_detail_raw_df):
                            extra = all_detail_raw_df[
                                all_detail_raw_df['topic_code'].astype(str) == code
                            ]
                            if len(extra):
                                additive_rows.append(extra.copy())
                                covered_by_detail.add(code)
                        else:
                            covered_by_detail.add(code)
                        print(
                            f"   ✓ Code {code}: additive tie-out — detail "
                            f"{detail_sum:,.2f} + aux {aux_sum:,.2f} = "
                            f"{combined:,.2f} (CHESHBONIT {cb_sum:,.2f})"
                        )
                        _warn(
                            "info",
                            "additive_closure",
                            (
                                f"Code {code}: additive tie-out — detail "
                                f"{detail_sum:,.2f} + aux {aux_sum:,.2f} = "
                                f"{combined:,.2f} (CHESHBONIT {cb_sum:,.2f})"
                            ),
                            topic_code=str(code),
                            detail_sum=detail_sum,
                            aux_sum=aux_sum,
                            cheshbonit_sum=cb_sum,
                            delta=combined - cb_sum,
                        )
                    else:
                        print(
                            f"   ⚠️  Code {code}: additive tie-out failed — "
                            f"detail {detail_sum:,.2f} + aux {aux_sum:,.2f} = "
                            f"{combined:,.2f} ≠ CHESHBONIT {cb_sum:,.2f} "
                            f"(Δ={combined - cb_sum:,.2f}) — keeping CHESHBONIT row"
                        )
                        _warn(
                            "warn",
                            "additive_closure_failed",
                            (
                                f"Code {code}: additive tie-out failed — detail "
                                f"{detail_sum:,.2f} + aux {aux_sum:,.2f} = "
                                f"{combined:,.2f} ≠ CHESHBONIT {cb_sum:,.2f}"
                            ),
                            topic_code=str(code),
                            detail_sum=detail_sum,
                            aux_sum=aux_sum,
                            cheshbonit_sum=cb_sum,
                            delta=combined - cb_sum,
                        )

                # Merge everything: drop CHESHBONIT rows for codes covered by
                # GY, detail, or additive aux, then concat the replacement rows.
                all_replacements: list = []
                if gy_breakdowns:
                    all_replacements.extend(gy_breakdowns)
                if detail_breakdowns:
                    all_replacements.extend(detail_breakdowns)
                if additive_rows:
                    all_replacements.extend(additive_rows)

                if all_replacements:
                    repl_df = pd.concat(all_replacements, ignore_index=True, sort=False)
                    covered_codes = set(repl_df['topic_code'].astype(str).unique())
                    kept_cheshbonit = cheshbonit_breakdown_df[
                        ~cheshbonit_breakdown_df['topic_code'].astype(str).isin(covered_codes)
                    ].copy()
                    breakdown_df = pd.concat(
                        [kept_cheshbonit, repl_df], ignore_index=True, sort=False
                    )
                    print(
                        f"\n✓ Merged breakdown: {len(kept_cheshbonit)} CHESHBONIT rows "
                        f"(codes without detail) + {len(repl_df)} detail rows "
                        f"= {len(breakdown_df)} total"
                    )
                else:
                    breakdown_df = cheshbonit_breakdown_df

                # Step 4f: Parse formula-input files (class enrollment,
                # staff positions, transportation routes). These don't alter
                # the breakdown — they populate sister tables used for
                # driver attribution ("why did code 3 go up ₪12K? because
                # class 10-3 enrollment dropped 18 → 17").
                if formula_files:
                    print(
                        f"\n📖 Reading formula-input files "
                        f"({len(formula_files)} types)..."
                    )
                    for ft, path in formula_files.items():
                        try:
                            raw = FileParser.read_csv_with_hebrew(path)
                            if ft == "ichluskitot":
                                df_out = FileParser.prepare_ichluskitot(raw)
                                formula_inputs["class_enrollments"] = df_out
                                print(
                                    f"   ✓ ICHLUSKITOT: {len(df_out)} "
                                    f"(class,month) rows"
                                )
                            elif ft == "misrot":
                                df_out = FileParser.prepare_misrot(raw, scope="institution")
                                formula_inputs["staff_positions_institution"] = df_out
                                print(
                                    f"   ✓ MISROT: {len(df_out)} nonzero "
                                    f"(inst,role,month) FTE rows"
                                )
                            elif ft == "misrotgy":
                                df_out = FileParser.prepare_misrot(raw, scope="gy")
                                formula_inputs["staff_positions_gy"] = df_out
                                print(
                                    f"   ✓ MISROTGY: {len(df_out)} nonzero "
                                    f"(village,role,month) FTE rows"
                                )
                            elif ft == "hasmaslulim":
                                df_out = FileParser.prepare_hasmaslulim(
                                    raw, metadata['month'], metadata['year']
                                )
                                formula_inputs["transport_routes"] = df_out
                                print(
                                    f"   ✓ HASMASLULIM: {len(df_out)} routes, "
                                    f"total={df_out['calculated_total'].sum():,.2f}"
                                    if len(df_out) else "   ✓ HASMASLULIM: 0 routes"
                                )
                        except Exception as exc:
                            print(f"   ⚠️  Skipping {Path(path).name}: {exc}")
                            _warn(
                                "error",
                                "formula_input_error",
                                f"Skipping {Path(path).name}: {exc}",
                                file_type=ft.upper(),
                            )

                # Step 5: Extract unique municipalities
                municipalities = {metadata['municipality_code']}

            else:
                # Structured format: look for invoice.csv and breakdown.csv
                print(f"\n🔄 Processing structured format files...")

                invoice_file = None
                breakdown_file = None

                for csv_file in csv_files:
                    filename = Path(csv_file).name.lower()
                    if "invoice" in filename or "summary" in filename:
                        invoice_file = csv_file
                    elif "breakdown" in filename or "detail" in filename:
                        breakdown_file = csv_file

                if not invoice_file or not breakdown_file:
                    raise FileParserException(
                        f"Could not find invoice.csv and breakdown.csv in structured format. "
                        f"Found: {[Path(f).name for f in csv_files]}"
                    )

                print(f"   ✓ Identified structured CSVs")
                invoice_df = FileParser.read_csv_with_hebrew(invoice_file)
                breakdown_df = FileParser.read_csv_with_hebrew(breakdown_file)
                municipalities = set(invoice_df['municipality_code'].astype(int).unique())

            # Return the assembled dict.
            return {
                "invoice_df": invoice_df,
                "breakdown_df": breakdown_df,
                "temp_dir": temp_dir,
                "municipalities": municipalities,
                "metadata": metadata,
                "formula_inputs": formula_inputs,
                "warnings": warnings,
            }
        except Exception:
            # Outer try — re-raise; caller decides whether to log or wrap.
            raise
        finally:
            # NOTE: temp_dir deliberately NOT removed here — upload.py still
            # reads institution roster files from it after parse_zip returns.
            # Cleanup is the caller's responsibility.
            pass
