"""
PDF Report Generator — Hebrew RTL support via ReportLab + arabic_reshaper + python-bidi

Generates:
  1. Monthly budget reports
  2. Comparison reports (all months)
"""

import os
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image,
    PageBreak, HRFlowable, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from bidi.algorithm import get_display
import arabic_reshaper

logger = logging.getLogger(__name__)

# ─── Font registration ────────────────────────────────────────────────────────

_FONTS_REGISTERED = False

def register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return True
    font_dir = os.path.join(os.path.dirname(__file__), '..', 'fonts')
    try:
        pdfmetrics.registerFont(TTFont('Heebo', os.path.join(font_dir, 'Heebo-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('Heebo-Bold', os.path.join(font_dir, 'Heebo-Bold.ttf')))
        _FONTS_REGISTERED = True
        logger.info("Heebo fonts registered")
        return True
    except Exception as e:
        logger.warning(f"Could not register Heebo fonts: {e}. Using Helvetica fallback.")
        return False


def _font(bold=False):
    if _FONTS_REGISTERED:
        return 'Heebo-Bold' if bold else 'Heebo'
    return 'Helvetica-Bold' if bold else 'Helvetica'


# ─── Hebrew text reshaping ────────────────────────────────────────────────────

def rh(text: Any) -> str:
    """Reshape + bidi-display Hebrew text for proper RTL PDF rendering."""
    if text is None:
        return ''
    s = str(text)
    if not s:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(s)
        return get_display(reshaped)
    except Exception:
        return s


def fmt_shekel(n: float) -> str:
    if n is None:
        return '—'
    try:
        return f'₪{n:,.0f}'
    except Exception:
        return str(n)


# ─── Page sizes ───────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4   # 595.28 pt × 841.89 pt

# ─── Color constants ──────────────────────────────────────────────────────────

COLOR_DARK_BLUE   = colors.HexColor('#1E3A5F')
COLOR_BLUE        = colors.HexColor('#3B82F6')
COLOR_LIGHT_BLUE  = colors.HexColor('#EFF6FF')
COLOR_GREEN       = colors.HexColor('#10B981')
COLOR_GREEN_LIGHT = colors.HexColor('#D1FAE5')
COLOR_RED         = colors.HexColor('#EF4444')
COLOR_RED_LIGHT   = colors.HexColor('#FEE2E2')
COLOR_AMBER       = colors.HexColor('#F59E0B')
COLOR_AMBER_LIGHT = colors.HexColor('#FEF3C7')
COLOR_GRAY        = colors.HexColor('#6B7280')
COLOR_GRAY_LIGHT  = colors.HexColor('#F9FAFB')
COLOR_GRAY_ROW    = colors.HexColor('#F3F4F6')
COLOR_WHITE       = colors.white
COLOR_BLACK       = colors.black

HEB_MONTHS = {
    '01': 'ינואר', '02': 'פברואר', '03': 'מרץ',   '04': 'אפריל',
    '05': 'מאי',   '06': 'יוני',   '07': 'יולי',   '08': 'אוגוסט',
    '09': 'ספטמבר','10': 'אוקטובר','11': 'נובמבר', '12': 'דצמבר',
}

HEB_DAYS = {
    1: 'א', 2: 'ב', 3: 'ג', 4: 'ד', 5: 'ה', 6: 'ו', 7: 'ז', 8: 'ח', 9: 'ט',
    10: 'י', 11: 'יא', 12: 'יב', 13: 'יג', 14: 'יד', 15: 'טו', 16: 'טז',
    17: 'יז', 18: 'יח', 19: 'יט', 20: 'כ', 21: 'כא', 22: 'כב', 23: 'כג',
    24: 'כד', 25: 'כה', 26: 'כו', 27: 'כז', 28: 'כח', 29: 'כט', 30: 'ל',
    31: 'לא',
}


def format_month_hebrew(month_str: str) -> str:
    """'2026-03' → 'מרץ 2026'"""
    try:
        y, m = month_str[:4], month_str[5:7]
        return f"{HEB_MONTHS.get(m, m)} {y}"
    except Exception:
        return month_str


def format_hebrew_date(d: date) -> str:
    """Format date as Hebrew day + month + year, e.g. יז אפריל 2026."""
    day_heb = HEB_DAYS.get(d.day, str(d.day))
    month_heb = HEB_MONTHS.get(f'{d.month:02d}', str(d.month))
    return f'{day_heb} {month_heb} {d.year}'


# ─── Style helpers ────────────────────────────────────────────────────────────

def _ps(size=10, bold=False, color=COLOR_BLACK, align=TA_RIGHT, leading=None) -> ParagraphStyle:
    return ParagraphStyle(
        'custom',
        fontName=_font(bold),
        fontSize=size,
        textColor=color,
        alignment=align,
        leading=leading or (size * 1.4),
        wordWrap='RTL',
        encoding='utf-8',
    )


# ─── Header / Footer callback ─────────────────────────────────────────────────

def make_page_header_footer(municipality_name: str, month_display: str,
                            branding: Optional[Dict] = None):
    """Return a function usable as onFirstPage/onLaterPages in doc.build()."""

    def _draw(canvas, doc):
        canvas.saveState()
        w, h = doc.pagesize

        firm_name = (branding or {}).get('firm_name', '') if branding else ''
        primary_hex = (branding or {}).get('primary_color', '#1E3A5F') if branding else '#1E3A5F'
        try:
            hdr_color = colors.HexColor(primary_hex)
        except Exception:
            hdr_color = COLOR_DARK_BLUE

        # ── Top header line ──
        canvas.setFillColor(hdr_color)
        canvas.rect(1.5 * cm, h - 2 * cm, w - 3 * cm, 0.5, fill=1, stroke=0)

        # Municipality + month (top right)
        canvas.setFont(_font(True), 9)
        canvas.setFillColor(COLOR_DARK_BLUE)
        canvas.drawRightString(w - 2 * cm, h - 1.6 * cm,
                               rh(f'{municipality_name} — {month_display}'))

        # Logo (top left) if branding has logo
        logo_path = (branding or {}).get('logo_path', '') if branding else ''
        if logo_path and os.path.exists(logo_path):
            try:
                canvas.drawImage(logo_path, 2 * cm, h - 1.9 * cm,
                                 width=2.5 * cm, height=0.9 * cm,
                                 preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        # ── Bottom footer line ──
        canvas.setFillColor(hdr_color)
        canvas.rect(1.5 * cm, 1.5 * cm, w - 3 * cm, 0.5, fill=1, stroke=0)

        # Footer text
        canvas.setFont(_font(), 8)
        canvas.setFillColor(COLOR_GRAY)

        # Left: firm name
        if firm_name:
            canvas.drawString(2 * cm, 1.1 * cm, rh(firm_name))

        # Center: page number
        page_num = rh(f'עמוד {doc.page}')
        canvas.drawCentredString(w / 2, 1.1 * cm, page_num)

        # Right: date
        gen_date = rh(datetime.now().strftime('%d/%m/%Y'))
        canvas.drawRightString(w - 2 * cm, 1.1 * cm, gen_date)

        canvas.restoreState()

    return _draw


# ─── Cover page ───────────────────────────────────────────────────────────────

def build_cover_page(municipality_name: str, month_display: str,
                     branding: Optional[Dict],
                     invoice_total: float, breakdown_total: float,
                     difference: float, is_balanced: bool) -> list:
    story = []
    story.append(Spacer(1, 1.5 * cm))

    # Logo
    logo_path = (branding or {}).get('logo_path', '') if branding else ''
    if logo_path and os.path.exists(logo_path):
        try:
            img = Image(logo_path)
            img.drawWidth = 5 * cm
            img.drawHeight = 3 * cm
            img._restrictSize(5 * cm, 3 * cm)
            story.append(img)
            story.append(Spacer(1, 0.5 * cm))
        except Exception:
            pass

    # Firm name
    firm_name = (branding or {}).get('firm_name', '') if branding else ''
    if firm_name:
        story.append(Paragraph(rh(firm_name), _ps(16, bold=True, align=TA_CENTER,
                                                    color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.3 * cm))

    # Horizontal rule
    story.append(HRFlowable(width='100%', thickness=2, color=COLOR_DARK_BLUE))
    story.append(Spacer(1, 1 * cm))

    # Main title
    story.append(Paragraph(rh('דוח תקציב חודשי'), _ps(20, bold=True, align=TA_CENTER,
                                                         color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.5 * cm))

    # Municipality name
    story.append(Paragraph(rh(municipality_name), _ps(26, bold=True, align=TA_CENTER,
                                                         color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.3 * cm))

    # Month
    story.append(Paragraph(rh(month_display), _ps(16, align=TA_CENTER, color=COLOR_GRAY)))
    story.append(Spacer(1, 1.5 * cm))

    # Key numbers box
    status_text = 'מאוזן ✓' if is_balanced else 'חריגה ⚠'
    status_color = COLOR_GREEN if is_balanced else COLOR_RED

    data = [
        [rh('פריט'), rh('סכום')],
        [rh('סכום מגיע'),  rh(fmt_shekel(invoice_total))],
        [rh('סכום שולם'),  rh(fmt_shekel(breakdown_total))],
        [rh('הפרש'),       rh(fmt_shekel(difference))],
        [rh('סטטוס'),      rh(status_text)],
    ]

    tbl = Table(data, colWidths=[8 * cm, 8 * cm])
    tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), _font(True)),
        ('FONTNAME', (0, 1), (-1, -1), _font()),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('BACKGROUND', (0, 1), (-1, -2), COLOR_LIGHT_BLUE),
        ('BACKGROUND', (0, -1), (-1, -1),
         COLOR_GREEN_LIGHT if is_balanced else COLOR_RED_LIGHT),
        ('TEXTCOLOR', (1, -1), (1, -1), status_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFDBFE')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [COLOR_WHITE, COLOR_LIGHT_BLUE]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 1.5 * cm))

    # Generation date
    story.append(Paragraph(rh(f'הופק ב: {datetime.now().strftime("%d/%m/%Y %H:%M")}'),
                            _ps(9, align=TA_CENTER, color=COLOR_GRAY)))

    # Contact info
    if branding:
        firm_phone = branding.get('firm_phone', '')
        firm_email = branding.get('firm_email', '')
        firm_addr  = branding.get('firm_address', '')
        contact_parts = [p for p in [firm_phone, firm_email, firm_addr] if p]
        if contact_parts:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(rh(' | '.join(contact_parts)),
                                    _ps(9, align=TA_CENTER, color=COLOR_GRAY)))

    return story


# ─── Summary page ─────────────────────────────────────────────────────────────

def build_summary_page(municipality_name: str, month_display: str,
                       invoice_total: float, breakdown_total: float,
                       difference: float, retro_total: float,
                       by_code: List[Dict], anomalies: List[Dict]) -> list:
    story = []

    story.append(Paragraph(rh('סיכום מנהלים'), _ps(18, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.5 * cm))

    # 4 key metric boxes
    metrics = [
        (rh('סכום מגיע'),  rh(fmt_shekel(invoice_total)),   COLOR_LIGHT_BLUE),
        (rh('סכום שולם'),  rh(fmt_shekel(breakdown_total)), COLOR_GREEN_LIGHT),
        (rh('הפרש'),       rh(fmt_shekel(difference)),      COLOR_RED_LIGHT if abs(difference) > 1 else COLOR_GREEN_LIGHT),
        (rh('רטרו'),       rh(fmt_shekel(retro_total)),     COLOR_AMBER_LIGHT),
    ]

    metric_data = [[m[0] for m in metrics], [m[1] for m in metrics]]
    metric_tbl = Table(metric_data, colWidths=[4 * cm] * 4)
    metric_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), _font(True)),
        ('FONTNAME', (0, 1), (-1, 1), _font(True)),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), COLOR_LIGHT_BLUE),
        ('BACKGROUND', (1, 0), (1, -1), COLOR_GREEN_LIGHT),
        ('BACKGROUND', (2, 0), (2, -1), COLOR_RED_LIGHT if abs(difference) > 1 else COLOR_GREEN_LIGHT),
        ('BACKGROUND', (3, 0), (3, -1), COLOR_AMBER_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(metric_tbl)
    story.append(Spacer(1, 0.8 * cm))

    # Budget by code
    if by_code:
        story.append(Paragraph(rh('תקציב לפי קוד'), _ps(13, bold=True)))
        story.append(Spacer(1, 0.3 * cm))

        header = [rh('%'), rh('שינוי'), rh('סכום'), rh('תיאור'), rh('קוד')]
        rows = [header]
        for c in by_code:
            chg = c.get('change_pct')
            if chg is not None:
                arrow = '⬆️' if chg > 0 else ('⬇️' if chg < 0 else '➡️')
                chg_str = rh(f'{arrow} {chg:+.1f}%')
                chg_bg = COLOR_GREEN_LIGHT if chg > 0 else COLOR_RED_LIGHT
            else:
                chg_str = rh('—')
                chg_bg = COLOR_WHITE

            total_pct = c.get('pct_of_total', 0)
            rows.append([
                rh(f'{total_pct:.1f}%'),
                Paragraph(chg_str, _ps(9, align=TA_CENTER)),
                rh(fmt_shekel(c.get('total', 0))),
                rh(c.get('name', '')),
                rh(str(c.get('code', ''))),
            ])

        code_tbl = Table(rows, colWidths=[2 * cm, 3.5 * cm, 5 * cm, 4.5 * cm, 1.5 * cm])
        code_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), _font(True)),
            ('FONTNAME', (0, 1), (-1, -1), _font()),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_DARK_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_WHITE, COLOR_GRAY_LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(code_tbl)
        story.append(Spacer(1, 0.8 * cm))

    # Anomalies alert
    if anomalies:
        story.append(Paragraph(rh('נקודות לתשומת לב:'), _ps(11, bold=True, color=COLOR_RED)))
        story.append(Spacer(1, 0.2 * cm))
        for a in anomalies[:5]:
            bullet = f"{'⚠️' if a.get('severity') == 'medium' else '🔴'} {a.get('description', '')}"
            story.append(Paragraph(rh(bullet), _ps(9)))
            story.append(Spacer(1, 0.15 * cm))

    return story


# ─── Budget detail table ──────────────────────────────────────────────────────

def build_budget_table(budget_lines: List[Dict], explanations: Dict[str, str]) -> list:
    story = []
    story.append(Paragraph(rh('פירוט תקציב מלא'), _ps(18, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.5 * cm))

    if not budget_lines:
        story.append(Paragraph(rh('אין נתוני תקציב לחודש זה'), _ps(10, color=COLOR_GRAY)))
        return story

    # Group by code
    from collections import defaultdict
    groups: Dict[str, list] = defaultdict(list)
    code_names: Dict[str, str] = {}
    for line in budget_lines:
        code = str(line.get('topic_code', ''))
        groups[code].append(line)
        code_names[code] = line.get('budget_topic', code)

    col_widths = [4.5 * cm, 2.5 * cm, 2.5 * cm, 3.5 * cm, 3.5 * cm]
    header_labels = [rh('הסבר'), rh('סכום'), rh('סוג'), rh('חודש תחולה'), rh('נושא')]

    grand_total = 0.0

    for code in sorted(groups.keys()):
        lines = groups[code]
        group_total = sum(l.get('amount', 0) for l in lines)
        grand_total += group_total

        # Group header row
        group_title = rh(f'{code_names[code]} — קוד {code} | סה"כ: {fmt_shekel(group_total)}')
        group_header_data = [[group_title, '', '', '', '']]
        grp_tbl = Table(group_header_data, colWidths=col_widths)
        grp_tbl.setStyle(TableStyle([
            ('SPAN', (0, 0), (-1, 0)),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_DARK_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), _font(True)),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
        ]))
        story.append(grp_tbl)

        # Line rows
        line_rows = [header_labels]
        for i, line in enumerate(lines):
            amt    = line.get('amount', 0)
            period = line.get('period_month', '')
            ltype  = line.get('line_type', 'regular')
            is_retro = line.get('is_retro', False)

            expl = explanations.get(str(line.get('topic_code', '')), '')
            expl_text = rh(str(expl)[:60] + '...' if len(str(expl)) > 60 else str(expl))

            amt_str = rh(fmt_shekel(amt))
            type_str = rh('רטרו' if is_retro else 'רגיל')
            topic_str = rh(str(line.get('budget_topic', ''))[:30])
            period_str = rh(period)

            line_rows.append([expl_text, amt_str, type_str, period_str, topic_str])

        line_tbl = Table(line_rows, colWidths=col_widths)
        row_colors = []
        for i in range(1, len(line_rows)):
            line = lines[i - 1]
            if line.get('is_retro'):
                row_colors.extend([
                    ('BACKGROUND', (0, i), (-1, i), COLOR_AMBER_LIGHT),
                ])
            elif line.get('amount', 0) < 0:
                row_colors.extend([
                    ('BACKGROUND', (0, i), (-1, i), COLOR_RED_LIGHT),
                ])
            elif i % 2 == 0:
                row_colors.extend([
                    ('BACKGROUND', (0, i), (-1, i), COLOR_GRAY_LIGHT),
                ])

        line_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), _font(True)),
            ('FONTNAME', (0, 1), (-1, -1), _font()),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_GRAY_ROW),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ] + row_colors))
        story.append(line_tbl)

        # Group total footer
        footer_data = [[rh(f'סה"כ קוד {code}: {fmt_shekel(group_total)}'), '', '', '', '']]
        footer_tbl = Table(footer_data, colWidths=col_widths)
        footer_tbl.setStyle(TableStyle([
            ('SPAN', (0, 0), (-1, 0)),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_BLUE),
            ('FONTNAME', (0, 0), (-1, 0), _font(True)),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ]))
        story.append(footer_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Grand total
    total_data = [[rh(f'סה"כ כללי: {fmt_shekel(grand_total)}'), '', '', '', '']]
    total_tbl = Table(total_data, colWidths=col_widths)
    total_tbl.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), _font(True)),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]))
    story.append(total_tbl)

    return story


# ─── Changes page ─────────────────────────────────────────────────────────────

def build_changes_page(changes: List[Dict], current_month: str, prev_month: str) -> list:
    story = []
    cur_display  = format_month_hebrew(current_month)
    prev_display = format_month_hebrew(prev_month)

    story.append(Paragraph(
        rh(f'שינויים מהחודש הקודם'), _ps(18, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Paragraph(
        rh(f'השוואה: {prev_display} → {cur_display}'), _ps(11, color=COLOR_GRAY)))
    story.append(Spacer(1, 0.5 * cm))

    if not changes:
        story.append(Paragraph(rh('לא זוהו שינויים משמעותיים'), _ps(10, color=COLOR_GRAY)))
        return story

    header = [rh('%'), rh('שינוי'), rh(cur_display), rh(prev_display), rh('תיאור'), rh('קוד')]
    rows = [header]

    for c in changes:
        pct = c.get('change_pct', 0) or 0
        delta = c.get('change_amount', 0) or 0
        arrow = '⬆️' if pct > 0 else ('⬇️' if pct < 0 else '➡️')
        rows.append([
            rh(f'{pct:+.1f}%'),
            rh(f'{arrow} {fmt_shekel(delta)}'),
            rh(fmt_shekel(c.get('current_total', 0))),
            rh(fmt_shekel(c.get('prev_total', 0))),
            rh(str(c.get('name', ''))[:30]),
            rh(str(c.get('code', ''))),
        ])

    col_widths = [2 * cm, 3.5 * cm, 3 * cm, 3 * cm, 4 * cm, 1 * cm]
    tbl = Table(rows, colWidths=col_widths)

    style = [
        ('FONTNAME', (0, 0), (-1, 0), _font(True)),
        ('FONTNAME', (0, 1), (-1, -1), _font()),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(rows)):
        pct = changes[i - 1].get('change_pct', 0) or 0
        if pct > 0:
            style.append(('BACKGROUND', (0, i), (1, i), COLOR_GREEN_LIGHT))
        elif pct < 0:
            style.append(('BACKGROUND', (0, i), (1, i), COLOR_RED_LIGHT))
        elif i % 2 == 0:
            style.append(('BACKGROUND', (0, i), (-1, i), COLOR_GRAY_LIGHT))

    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    return story


# ─── Anomalies page ───────────────────────────────────────────────────────────

def build_anomalies_page(anomalies: List[Dict]) -> list:
    story = []
    story.append(Paragraph(rh('נקודות לבדיקה'), _ps(18, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.5 * cm))

    for a in anomalies:
        severity = a.get('severity', 'medium')
        icon = '🔴' if severity == 'high' else '⚠️'
        title = a.get('title') or a.get('description', '')
        desc  = a.get('description', '')
        rec   = a.get('recommendation', '')

        story.append(Paragraph(rh(f'{icon} {title}'), _ps(11, bold=True)))
        if desc and desc != title:
            story.append(Paragraph(rh(desc), _ps(9, color=COLOR_GRAY)))
        if rec:
            story.append(Paragraph(rh(f'המלצה: {rec}'), _ps(9, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.4 * cm))

    return story


# ─── Comparison report ────────────────────────────────────────────────────────

def build_comparison_table(runs: List[Dict], all_lines: Dict[str, List[Dict]]) -> list:
    story = []
    story.append(Paragraph(rh('השוואה בין חודשים'), _ps(18, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.5 * cm))

    if not runs:
        story.append(Paragraph(rh('אין נתונים להשוואה'), _ps(10, color=COLOR_GRAY)))
        return story

    months = [r['month'] for r in runs]
    month_displays = [format_month_hebrew(m) for m in months]

    # Collect all codes
    all_codes: Dict[str, str] = {}
    for m in months:
        for line in all_lines.get(m, []):
            code = str(line.get('topic_code', ''))
            all_codes[code] = line.get('budget_topic', code)

    # Header: קוד + month columns + שינוי
    col_count = len(months) + 3  # code, name, months..., change indicator
    col_widths = [1.5 * cm, 4 * cm] + [3 * cm] * len(months) + [2.5 * cm]

    header = [rh('שינוי')] + [rh(d) for d in reversed(month_displays)] + [rh('תיאור'), rh('קוד')]
    rows = [header]

    for code in sorted(all_codes.keys()):
        name = all_codes[code]
        month_totals = []
        for m in months:
            total = sum(l.get('amount', 0) for l in all_lines.get(m, [])
                        if str(l.get('topic_code', '')) == code)
            month_totals.append(total)

        if all(t == 0 for t in month_totals):
            continue

        # Change indicator: compare first vs last
        first_val = month_totals[0]
        last_val  = month_totals[-1]
        if first_val and first_val != 0:
            pct_change = (last_val - first_val) / abs(first_val) * 100
            arrow = '⬆️' if pct_change > 0 else ('⬇️' if pct_change < 0 else '➡️')
            change_str = rh(f'{arrow} {pct_change:+.1f}%')
        else:
            change_str = rh('—')

        row = [change_str]
        for t in reversed(month_totals):
            row.append(rh(fmt_shekel(t)))
        row += [rh(name[:25]), rh(code)]
        rows.append(row)

    tbl = Table(rows, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), _font(True)),
        ('FONTNAME', (0, 1), (-1, -1), _font()),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_WHITE, COLOR_GRAY_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    return story


def build_municipality_letter(
    municipality_name: str,
    month: str,
    invoice_total: float,
    difference: float,
    by_code: List[Dict],
    budget_lines: List[Dict],
    branding: Optional[Dict] = None,
    breakdown_total: float = 0,
    retro_total: float = 0,
    changes: Optional[List[Dict]] = None,
    prev_month: Optional[str] = None,
    anomalies: Optional[List[Dict]] = None,
    explanations: Optional[Dict[str, str]] = None,
    tie_out: Optional[Dict] = None,
    variance_drivers: Optional[Dict] = None,
    explained_coverage: Optional[Dict] = None,
    ytd: Optional[Dict] = None,
    peer_benchmark: Optional[Dict] = None,
    formula_variance: Optional[Dict] = None,
) -> list:
    """Build a professional Hebrew municipality letter page.

    Produces a CPA-grade budget review letter in Hebrew (RTL) with the standard
    sections used in Israeli municipal/Ministry-of-Education monthly reports:

      1. סיכום — introductory paragraph with the headline allocation.
      2. פירוט תשלומים לפי נושא — per-topic-code breakdown table.
      3. תשלומים רטרואקטיביים — retro lines with their original period month.
      4. שינויים מול חודש קודם — variance table vs. the prior processed month.
      5. ממצאים חריגים — flagged anomalies (imbalance, large retro, etc.).
      6. סטטוס התאמה — reconciliation status block.
      7. הערות והסברים — topic-level narrative explanations (if present).
      8. סיום ובקרה — sign-off block with CPA firm name, date, contact.
    """
    changes = changes or []
    anomalies = anomalies or []
    explanations = explanations or {}
    story = []

    month_display = format_month_hebrew(month)
    heb_today = format_hebrew_date(date.today())
    is_balanced = abs(difference or 0) < 1
    has_retro = any(bool(line.get('is_retro')) for line in budget_lines)
    retro_lines = [line for line in budget_lines if line.get('is_retro')]

    # Header
    logo_path = (branding or {}).get('logo_path', '') if branding else ''
    firm_name = (branding or {}).get('firm_name', '') if branding else ''

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path)
            logo.drawWidth = 3.5 * cm
            logo.drawHeight = 1.6 * cm
            logo._restrictSize(3.5 * cm, 1.6 * cm)
            logo.hAlign = 'RIGHT'
            story.append(logo)
            story.append(Spacer(1, 0.2 * cm))
        except Exception:
            pass

    if firm_name:
        story.append(Paragraph(rh(firm_name), _ps(15, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph(rh(heb_today), _ps(10, color=COLOR_GRAY)))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(rh(f'לכבוד: {municipality_name}'), _ps(12, bold=True)))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(rh(f'הנדון: תשלומי משרד החינוך — {month_display}'), _ps(12, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.4 * cm))

    # Body - Section 1: Summary paragraph
    story.append(Paragraph(rh('1. סיכום'), _ps(11, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.1 * cm))
    summary_text = (
        f'ברצוננו להביא לידיעתכם כי משרד החינוך העביר לרשותכם בחודש {month_display} '
        f'סך של {fmt_shekel(invoice_total)} בגין תקצוב מוסדות החינוך.'
    )
    story.append(Paragraph(rh(summary_text), _ps(11, leading=18)))
    story.append(Spacer(1, 0.4 * cm))

    # Body - Section 2: Payment breakdown table
    story.append(Paragraph(rh('2. פירוט תשלומים לפי נושא'), _ps(11, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.2 * cm))

    # Build table rows directly from budget lines to guarantee one summed row per topic_code.
    code_sums: Dict[str, float] = {}
    code_names: Dict[str, str] = {}
    for line in budget_lines:
        code = str(line.get('topic_code', '') or '').strip()
        if not code:
            continue
        amount = float(line.get('amount', 0) or 0)
        code_sums[code] = code_sums.get(code, 0.0) + amount
        if code not in code_names:
            code_names[code] = str(line.get('budget_topic', '') or code)

    # Fallback to precomputed by_code when no detailed lines are available.
    if not code_sums and by_code:
        for item in by_code:
            code = str(item.get('code', '') or '').strip()
            if not code:
                continue
            code_sums[code] = float(item.get('total', 0) or 0)
            code_names[code] = str(item.get('name', '') or code)

    def _code_sort_key(code: str):
        try:
            return (0, int(code))
        except Exception:
            return (1, code)

    rows = [[rh('קוד'), rh('תיאור'), rh('סכום')]]
    total_amount = 0.0
    for code in sorted(code_sums.keys(), key=_code_sort_key):
        amount = code_sums[code]
        total_amount += amount
        rows.append([rh(code), rh(code_names.get(code, code)), rh(fmt_shekel(amount))])
    rows.append([rh('סה"כ'), '', rh(fmt_shekel(total_amount))])

    breakdown_tbl = Table(rows, colWidths=[2.5 * cm, 9.5 * cm, 4 * cm])
    breakdown_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), _font(True)),
        ('FONTNAME', (0, 1), (-1, -2), _font()),
        ('FONTNAME', (0, -1), (-1, -1), _font(True)),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_DARK_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [COLOR_WHITE, COLOR_GRAY_LIGHT]),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_LIGHT_BLUE),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D1D5DB')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether([breakdown_tbl]))
    story.append(Spacer(1, 0.4 * cm))

    # Body - Section 3: Retro payments
    if has_retro:
        story.append(Paragraph(rh('3. תשלומים רטרואקטיביים'), _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(rh('כלולים בסכום הנ"ל תשלומים רטרואקטיביים:'), _ps(10)))
        story.append(Spacer(1, 0.15 * cm))

        retro_rows = [[rh('קוד'), rh('חודש תחולה'), rh('סכום')]]
        for line in retro_lines:
            retro_rows.append([
                rh(str(line.get('topic_code', ''))),
                rh(str(line.get('period_month', '') or '—')),
                rh(fmt_shekel(float(line.get('amount', 0) or 0))),
            ])

        retro_tbl = Table(retro_rows, colWidths=[3 * cm, 8.5 * cm, 4.5 * cm])
        retro_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), _font(True)),
            ('FONTNAME', (0, 1), (-1, -1), _font()),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_AMBER),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_WHITE, COLOR_AMBER_LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D1D5DB')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether([retro_tbl]))
        story.append(Spacer(1, 0.35 * cm))

    # Body - Section 4: Changes vs previous month
    if changes:
        prev_display = format_month_hebrew(prev_month) if prev_month else 'חודש קודם'
        story.append(Paragraph(
            rh(f'4. שינויים מול {prev_display}'),
            _ps(11, bold=True, color=COLOR_DARK_BLUE),
        ))
        story.append(Spacer(1, 0.15 * cm))
        # Sort by magnitude of change, largest first
        sorted_changes = sorted(
            changes, key=lambda c: abs(float(c.get('change_amount', 0) or 0)), reverse=True
        )
        change_rows = [[rh('קוד'), rh('תיאור'), rh('חודש קודם'), rh('חודש נוכחי'), rh('שינוי'), rh('%')]]
        for c in sorted_changes[:15]:  # cap at 15 rows to keep page tidy
            delta = float(c.get('change_amount', 0) or 0)
            pct = c.get('change_pct')
            pct_str = f'{pct:+.1f}%' if pct is not None else '—'
            sign = '+' if delta > 0 else ''
            change_rows.append([
                rh(str(c.get('code', ''))),
                rh(str(c.get('name', ''))),
                rh(fmt_shekel(float(c.get('prev_total', 0) or 0))),
                rh(fmt_shekel(float(c.get('current_total', 0) or 0))),
                rh(f'{sign}{fmt_shekel(abs(delta)) if delta < 0 else fmt_shekel(delta)}'),
                rh(pct_str),
            ])
        change_tbl = Table(change_rows,
                           colWidths=[1.8 * cm, 5.2 * cm, 3 * cm, 3 * cm, 2.5 * cm, 1.5 * cm])
        change_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), _font(True)),
            ('FONTNAME', (0, 1), (-1, -1), _font()),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_WHITE, COLOR_GRAY_LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#D1D5DB')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether([change_tbl]))
        story.append(Spacer(1, 0.35 * cm))

    # Body - Section 5: Anomalies / flagged items
    if anomalies:
        story.append(Paragraph(rh('5. ממצאים חריגים'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.15 * cm))
        severity_color = {
            'high': COLOR_RED_LIGHT, 'medium': COLOR_AMBER_LIGHT, 'low': COLOR_LIGHT_BLUE,
        }
        severity_border = {
            'high': COLOR_RED, 'medium': COLOR_AMBER, 'low': COLOR_BLUE,
        }
        severity_label = {'high': 'חמור', 'medium': 'בינוני', 'low': 'קל'}
        for a in anomalies:
            sev = a.get('severity', 'medium')
            bg = severity_color.get(sev, COLOR_AMBER_LIGHT)
            border = severity_border.get(sev, COLOR_AMBER)
            title = a.get('title', 'ממצא')
            desc = a.get('description', '')
            rec = a.get('recommendation', '')
            label = severity_label.get(sev, '')
            body_lines = [rh(f'[{label}] {title}'), rh(desc)]
            if rec:
                body_lines.append(rh(f'המלצה: {rec}'))
            anom_tbl = Table([[l] for l in body_lines], colWidths=[16 * cm])
            anom_tbl.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), _font(True)),
                ('FONTNAME', (0, 1), (-1, -1), _font()),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, -1), bg),
                ('BOX', (0, 0), (-1, -1), 0.7, border),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(anom_tbl)
            story.append(Spacer(1, 0.15 * cm))
        story.append(Spacer(1, 0.2 * cm))

    # Body - Section 6: Balance status
    story.append(Paragraph(rh('6. סטטוס התאמה'), _ps(11, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.1 * cm))
    if is_balanced:
        status_text = 'הסכום שהתקבל תואם לפירוט (מאוזן).'
        status_bg = COLOR_GREEN_LIGHT
        status_color = COLOR_GREEN
    else:
        status_text = f'שימו לב: קיים הפרש של {fmt_shekel(difference)} בין הסכום שהתקבל לפירוט.'
        status_bg = COLOR_RED_LIGHT
        status_color = COLOR_RED

    status_tbl = Table([[rh(status_text)]], colWidths=[16 * cm])
    status_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), _font(True)),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), status_bg),
        ('TEXTCOLOR', (0, 0), (-1, -1), status_color),
        ('BOX', (0, 0), (-1, -1), 0.6, status_color),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(status_tbl)
    story.append(Spacer(1, 0.3 * cm))

    # Tie-out reconciliation proof (CPA workpaper style)
    if tie_out:
        tie_rows = [[
            rh('בדיקה'),
            rh('סכום'),
        ]]
        tie_rows.append([rh('סך שורות פירוט (Σ lines)'), rh(fmt_shekel(tie_out.get('sum_of_lines', 0)))])
        tie_rows.append([rh('סכום חשבונית (invoice)'), rh(fmt_shekel(tie_out.get('invoice_total', 0)))])
        tie_rows.append([rh('סכום פירוט (breakdown)'), rh(fmt_shekel(tie_out.get('breakdown_total', 0)))])
        breaks = tie_out.get('breaks', {}) or {}
        tie_rows.append([
            rh('הפרש: שורות − חשבונית'),
            rh(fmt_shekel(breaks.get('lines_vs_invoice', 0))),
        ])
        tie_rows.append([
            rh('הפרש: שורות − פירוט'),
            rh(fmt_shekel(breaks.get('lines_vs_breakdown', 0))),
        ])
        tie_rows.append([
            rh('הפרש: חשבונית − פירוט'),
            rh(fmt_shekel(breaks.get('invoice_vs_breakdown', 0))),
        ])
        tie_tbl = Table(tie_rows, colWidths=[10 * cm, 6 * cm])
        tie_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _font(True)),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_DARK_BLUE),
            ('GRID', (0, 0), (-1, -1), 0.4, COLOR_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(tie_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Body - Section 6a: Variance drivers waterfall
    if variance_drivers and variance_drivers.get('has_prev_month') and variance_drivers.get('drivers'):
        story.append(Paragraph(rh('6א. רכיבי השינוי המובילים'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.1 * cm))
        prev_disp = variance_drivers.get('previous_month_display', '')
        intro = (
            f'שינוי כולל בחודש הדיווח מול {prev_disp}: '
            f'{fmt_shekel(variance_drivers.get("total_delta", 0))}. '
            f'להלן רכיבי ההשפעה העיקריים, ממוינים לפי היקף ב-₪:'
        )
        story.append(Paragraph(rh(intro), _ps(10, leading=15)))
        story.append(Spacer(1, 0.2 * cm))

        drv_rows = [[rh('קוד'), rh('נושא'), rh('שינוי ב-₪'), rh('שינוי %'), rh('חלק מהשינוי')]]
        for d in variance_drivers['drivers'][:6]:
            sign = '+' if d.get('delta_abs', 0) >= 0 else ''
            pct = d.get('delta_pct')
            pct_str = f'{pct:+.1f}%' if pct is not None else '—'
            share = d.get('share_of_total_change_pct')
            share_str = f'{share:+.0f}%' if share is not None else '—'
            drv_rows.append([
                rh(str(d.get('topic_code', ''))),
                rh(str(d.get('topic_name', ''))),
                rh(f'{sign}{fmt_shekel(d.get("delta_abs", 0))}'),
                rh(pct_str),
                rh(share_str),
            ])
        drv_tbl = Table(drv_rows, colWidths=[1.5 * cm, 6.5 * cm, 3.5 * cm, 2 * cm, 2.5 * cm])
        drv_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _font(True)),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_DARK_BLUE),
            ('GRID', (0, 0), (-1, -1), 0.4, COLOR_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(drv_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Body - Section 6b: Explained-vs-unexplained coverage
    if explained_coverage and explained_coverage.get('has_prev_month'):
        ratio = explained_coverage.get('coverage_ratio_pct', 0)
        naked_cnt = explained_coverage.get('naked_codes_count', 0)
        covered_txt = (
            f'אחוז כיסוי הסברים לסכומי השינוי: {ratio}%. '
            f'סך שינויים מוסברים: {fmt_shekel(explained_coverage.get("explained_delta_abs", 0))}. '
            f'סך שינויים ללא הסבר מאושר: '
            f'{fmt_shekel(explained_coverage.get("unexplained_delta_abs", 0))}.'
        )
        if naked_cnt:
            covered_txt += f' מזוהים {naked_cnt} קודים ללא הסבר ≥₪1,000.'
        story.append(Paragraph(rh('6ב. כיסוי הסברים לשינויים'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.1 * cm))
        cov_bg = COLOR_GREEN_LIGHT if ratio >= 80 else (COLOR_RED_LIGHT if ratio < 50 else None)
        if cov_bg:
            cov_tbl = Table([[rh(covered_txt)]], colWidths=[16 * cm])
            cov_tbl.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), _font(True)),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, -1), cov_bg),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(cov_tbl)
        else:
            story.append(Paragraph(rh(covered_txt), _ps(10, leading=15)))
        story.append(Spacer(1, 0.4 * cm))

    # Body - Section 7: Topic-level explanations
    if explanations:
        story.append(Paragraph(rh('7. הערות והסברים'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.15 * cm))
        # Resolve code → topic name
        code_to_name = {}
        for line in budget_lines:
            c = str(line.get('topic_code', '') or '').strip()
            if c and c not in code_to_name:
                code_to_name[c] = str(line.get('budget_topic', '') or c)
        for code, text in explanations.items():
            code_str = str(code)
            name = code_to_name.get(code_str, code_str)
            story.append(Paragraph(rh(f'• {name} (קוד {code_str}):'),
                                   _ps(10, bold=True, color=COLOR_DARK_BLUE)))
            story.append(Paragraph(rh(str(text)), _ps(10, leading=15)))
            story.append(Spacer(1, 0.15 * cm))
        story.append(Spacer(1, 0.2 * cm))

    # Body - Section 8: YTD cumulative per topic
    if ytd and ytd.get('by_code'):
        story.append(Paragraph(rh('8. סך מצטבר לפי קוד (YTD)'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.1 * cm))
        ytd_intro = (
            f'סך מצטבר מ-{ytd.get("start_month_display", "")} עד '
            f'{ytd.get("end_month_display", "")} '
            f'({ytd.get("months_covered_count", 0)} חודשים עם נתונים).'
        )
        story.append(Paragraph(rh(ytd_intro), _ps(10, leading=15)))
        story.append(Spacer(1, 0.2 * cm))

        ytd_rows = [[rh('קוד'), rh('נושא'), rh('סך מצטבר'),
                     rh('רטרו'), rh('ממוצע/חודש'), rh('% רטרו')]]
        for r in ytd['by_code']:
            ytd_rows.append([
                rh(str(r.get('topic_code', ''))),
                rh(str(r.get('topic_name', ''))),
                rh(fmt_shekel(r.get('ytd_total', 0))),
                rh(fmt_shekel(r.get('ytd_retro', 0))),
                rh(fmt_shekel(r.get('avg_per_month', 0))),
                rh(f'{r.get("retro_share_pct", 0)}%'),
            ])
        ytd_rows.append([
            rh(''),
            rh('סך הכל'),
            rh(fmt_shekel(ytd.get('ytd_total', 0))),
            rh(fmt_shekel(ytd.get('ytd_retro', 0))),
            rh(fmt_shekel(ytd.get('avg_per_month', 0))),
            rh(f'{ytd.get("ytd_retro_share_pct", 0)}%'),
        ])
        ytd_tbl = Table(
            ytd_rows,
            colWidths=[1.5 * cm, 5.5 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 1.5 * cm],
        )
        ytd_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _font(True)),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_DARK_BLUE),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_LIGHT_BLUE),
            ('FONTNAME', (0, -1), (-1, -1), _font(True)),
            ('GRID', (0, 0), (-1, -1), 0.4, COLOR_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(ytd_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Body - Section 8א: Smart bullets (auto-computed facts) ─────────────────
    if ytd and ytd.get('smart_bullets'):
        story.append(Paragraph(rh('8א. תובנות מחושבות אוטומטית'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.1 * cm))
        for b in ytd['smart_bullets']:
            story.append(Paragraph(rh(f'• {b}'), _ps(10, leading=15)))
        # Fiscal-year gap highlighted one-liner
        fy_gap = ytd.get('fiscal_year_cumulative_gap')
        if fy_gap is not None and abs(fy_gap) > 0.5:
            sign_word = 'עודף' if fy_gap < 0 else 'חוסר'
            story.append(Paragraph(
                rh(f'מגיע: {fmt_shekel(ytd.get("fiscal_year_due_total", 0))} '
                   f'| שולם: {fmt_shekel(ytd.get("fiscal_year_paid_total", 0))} '
                   f'| פער מצטבר: {fmt_shekel(abs(fy_gap))} ({sign_word}).'),
                _ps(10, leading=15, bold=True),
            ))
        if ytd.get('projected_annual'):
            story.append(Paragraph(
                rh(f'תחזית שנתית (לפי חציון חודשי): '
                   f'{fmt_shekel(ytd.get("projected_annual", 0))} — '
                   f'נצברו עד כה {ytd.get("pct_of_projected_annual", 0)}%.'),
                _ps(10, leading=15),
            ))
        story.append(Spacer(1, 0.4 * cm))

    # Body - Section 10: Peer benchmark (outliers vs peer medians) ───────────
    if peer_benchmark and peer_benchmark.get('has_peer_data') and peer_benchmark.get('by_code'):
        story.append(Paragraph(rh('10. השוואה לרשויות עמיתות'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.1 * cm))
        outliers = peer_benchmark.get('outlier_count', 0)
        peer_intro = (
            f'השוואת סכומים לפי נושא מול חציון {peer_benchmark.get("peer_count", 0)} רשויות '
            f'שהגישו נתונים לחודש זה. '
        )
        if outliers:
            peer_intro += f'זוהו {outliers} נושאים חריגים (±30% מהחציון).'
        else:
            peer_intro += 'כל הנושאים נמצאים בטווח העמיתים.'
        story.append(Paragraph(rh(peer_intro), _ps(10, leading=15)))
        story.append(Spacer(1, 0.2 * cm))

        peer_rows = [[rh('נושא'), rh('הרשות'), rh('חציון'),
                      rh('ממוצע'), rh('סטייה'), rh('סטטוס')]]
        for r in peer_benchmark['by_code'][:10]:
            flag = r.get('flag')
            status_txt = ('גבוה מעמיתים' if flag == 'above_peers'
                          else 'נמוך מעמיתים' if flag == 'below_peers'
                          else 'בטווח')
            dev = r.get('deviation_pct')
            dev_txt = f'{"+" if dev is not None and dev > 0 else ""}{dev}%' if dev is not None else '—'
            peer_rows.append([
                rh(f'{r.get("topic_name", "")} ({r.get("topic_code", "")})'),
                rh(fmt_shekel(r.get('my_amount', 0))),
                rh(fmt_shekel(r.get('peer_median', 0))),
                rh(fmt_shekel(r.get('peer_avg', 0))),
                rh(dev_txt),
                rh(status_txt),
            ])
        peer_tbl = Table(
            peer_rows,
            colWidths=[4.5 * cm, 3 * cm, 3 * cm, 3 * cm, 1.6 * cm, 2.4 * cm],
        )
        peer_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _font(True)),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_DARK_BLUE),
            ('GRID', (0, 0), (-1, -1), 0.4, COLOR_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(peer_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Body - Section 11: Purple-booklet formula variance ─────────────────────
    # Only render rows where we can actually say something meaningful — skip
    # "no_formula" rows entirely to avoid cluttering the section with topics
    # for which the Purple Booklet has no per-child rate. Keep "no_children_data"
    # rows because they're informative ("we know the rate, kids data is missing").
    fv_rows_src = (formula_variance or {}).get('by_code') or []
    fv_rows_visible = [r for r in fv_rows_src if r.get('flag') != 'no_formula']
    if formula_variance and fv_rows_visible and formula_variance.get('expected_total', 0) > 0:
        story.append(Paragraph(rh('11. סטייה מנוסחת הספר הסגול'),
                               _ps(11, bold=True, color=COLOR_DARK_BLUE)))
        story.append(Spacer(1, 0.1 * cm))
        material_cnt = formula_variance.get('material_count', 0)
        missing_cnt = formula_variance.get('missing_kids_count', 0)
        total_pct = formula_variance.get('variance_pct')
        total_pct_txt = (f'{"+" if total_pct is not None and total_pct > 0 else ""}{total_pct}%'
                         if total_pct is not None else '—')
        fml_intro = (
            f'השוואה בין הצפוי על פי הספר הסגול (מספר ילדים × תעריף לדלי) '
            f'לבין הסכום שדווח בפועל. '
            f'סטייה כוללת: {total_pct_txt}. '
        )
        if material_cnt:
            fml_intro += f'מזוהים {material_cnt} נושאים עם סטייה מהותית (>5%). '
        if missing_cnt:
            fml_intro += f'עבור {missing_cnt} נושאים חסרים נתוני מספר ילדים לחישוב.'
        story.append(Paragraph(rh(fml_intro), _ps(10, leading=15)))
        story.append(Spacer(1, 0.2 * cm))

        fml_rows = [[rh('נושא'), rh('חישוב'), rh('צפוי'),
                     rh('בפועל (רגיל)'), rh('סטייה %'), rh('סטטוס')]]
        for r in fv_rows_visible:
            flag = r.get('flag')
            status_txt = {
                'in_line': 'בקו הנוסחה',
                'material': 'סטייה מהותית',
                'critical': 'סטייה קריטית',
                'no_children_data': 'חסר מספר ילדים',
                'no_formula': 'ללא נוסחה זמינה',
            }.get(flag, '—')
            vp = r.get('variance_pct')
            vp_txt = f'{"+" if vp is not None and vp > 0 else ""}{vp}%' if vp is not None else '—'
            expected_txt = fmt_shekel(r.get('expected_amount', 0)) if r.get('expected_amount') is not None else '—'
            fml_rows.append([
                rh(f'{r.get("topic_name", "")} ({r.get("topic_code", "")})'),
                rh(r.get('formula') or '—'),
                rh(expected_txt),
                rh(fmt_shekel(r.get('actual_regular', 0))),
                rh(vp_txt),
                rh(status_txt),
            ])
        fml_rows.append([
            rh('סך הכל (עם נוסחה)'),
            rh(''),
            rh(fmt_shekel(formula_variance.get('expected_total', 0))),
            rh(fmt_shekel(formula_variance.get('actual_regular_total', 0))),
            rh(total_pct_txt),
            rh(''),
        ])
        fml_tbl = Table(
            fml_rows,
            colWidths=[4 * cm, 4 * cm, 2.7 * cm, 2.7 * cm, 1.6 * cm, 2.5 * cm],
        )
        fml_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _font(True)),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_DARK_BLUE),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_LIGHT_BLUE),
            ('FONTNAME', (0, -1), (-1, -1), _font(True)),
            ('GRID', (0, 0), (-1, -1), 0.4, COLOR_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(fml_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Body - Section 12: Sign-off block
    story.append(Paragraph(rh('12. סיום ובקרה'),
                           _ps(11, bold=True, color=COLOR_DARK_BLUE)))
    story.append(Spacer(1, 0.1 * cm))
    disclaimer = (
        'דוח זה הופק על בסיס הנתונים שהועברו לרו"ח מטעם הרשות ומשרד החינוך '
        'לחודש הדיווח הנדון. הדוח נועד לסקירה ובקרה בלבד ואינו מהווה תחליף '
        'לבחינה ישירה של מסמכי המקור.'
    )
    story.append(Paragraph(rh(disclaimer), _ps(9, leading=14, color=COLOR_GRAY)))
    story.append(Spacer(1, 0.5 * cm))

    # Signature block — right-aligned table with firm name, date, contact
    firm_name_sig = (branding or {}).get('firm_name', '') if branding else ''
    phone = (branding or {}).get('firm_phone', '') if branding else ''
    email = (branding or {}).get('firm_email', '') if branding else ''
    today_heb = format_hebrew_date(date.today())

    story.append(Paragraph(rh('בברכה,'), _ps(10)))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width='40%', thickness=0.8, color=COLOR_GRAY, hAlign='RIGHT'))
    story.append(Spacer(1, 0.1 * cm))
    if firm_name_sig:
        story.append(Paragraph(rh(firm_name_sig), _ps(11, bold=True)))
    story.append(Paragraph(rh('רואי חשבון'), _ps(9, color=COLOR_GRAY)))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(rh(f'תאריך: {today_heb}'), _ps(9, color=COLOR_GRAY)))

    contact_parts = [p for p in [phone, email] if p]
    if contact_parts:
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(rh(f'לפרטים נוספים: {" | ".join(contact_parts)}'),
                               _ps(9, color=COLOR_GRAY)))

    return story


# ─── Main report generator ────────────────────────────────────────────────────

def generate_monthly_report(
    municipality_id: int,
    municipality_name: str,
    month: str,
    budget_lines: List[Dict],
    explanations: Dict[str, str],
    invoice_total: float,
    breakdown_total: float,
    difference: float,
    retro_total: float,
    by_code: List[Dict],
    changes: List[Dict],
    prev_month: Optional[str],
    anomalies: List[Dict],
    branding: Optional[Dict] = None,
    tie_out: Optional[Dict] = None,
    variance_drivers: Optional[Dict] = None,
    explained_coverage: Optional[Dict] = None,
    ytd: Optional[Dict] = None,
    peer_benchmark: Optional[Dict] = None,
    formula_variance: Optional[Dict] = None,
) -> str:
    """
    Generate a complete monthly budget report PDF.
    Returns the file path of the generated PDF.
    """
    register_fonts()

    month_display = format_month_hebrew(month)
    filename = f"report_{municipality_id}_{month}_monthly.pdf"
    output_dir = os.path.join('backend', 'reports', str(municipality_id))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=rh(f'דוח תקציב — {municipality_name} — {month_display}'),
    )

    story = build_municipality_letter(
        municipality_name=municipality_name,
        month=month,
        invoice_total=invoice_total,
        difference=difference,
        by_code=by_code,
        budget_lines=budget_lines,
        branding=branding,
        breakdown_total=breakdown_total,
        retro_total=retro_total,
        changes=changes,
        prev_month=prev_month,
        anomalies=anomalies,
        explanations=explanations,
        tie_out=tie_out,
        variance_drivers=variance_drivers,
        explained_coverage=explained_coverage,
        ytd=ytd,
        peer_benchmark=peer_benchmark,
        formula_variance=formula_variance,
    )

    page_cb = make_page_header_footer(municipality_name, month_display, branding)
    doc.build(story, onFirstPage=page_cb, onLaterPages=page_cb)

    return output_path


def generate_comparison_report(
    municipality_id: int,
    municipality_name: str,
    runs: List[Dict],
    all_lines: Dict[str, List[Dict]],
    branding: Optional[Dict] = None,
) -> str:
    """
    Generate a comparison report covering all available months.
    Returns the file path.
    """
    register_fonts()

    filename = f"report_{municipality_id}_all_comparison.pdf"
    output_dir = os.path.join('backend', 'reports', str(municipality_id))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=rh(f'דוח השוואה — {municipality_name}'),
    )

    story = []

    month_display = rh('כל החודשים')

    # Cover
    story.extend(build_cover_page(
        municipality_name,
        rh('השוואה — כל החודשים'),
        branding, 0, 0, 0, True,
    ))
    story.append(PageBreak())

    # Comparison table
    story.extend(build_comparison_table(runs, all_lines))

    page_cb = make_page_header_footer(municipality_name, 'השוואה', branding)
    doc.build(story, onFirstPage=page_cb, onLaterPages=page_cb)

    return output_path
