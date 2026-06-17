import re

from backend.services.monthly_memo_engine import MemoConfig, generate_monthly_memo


def _base_data(current_amount: float, previous_amount: float | None):
    current = [
        {"topic_code": "3", "budget_topic": "גני ילדים", "amount": current_amount * 0.5, "period_month": "2026-03", "is_retro": False},
        {"topic_code": "19", "budget_topic": "עוזרות", "amount": current_amount * 0.3, "period_month": "2026-03", "is_retro": False},
        {"topic_code": "33", "budget_topic": "גננות מדינה", "amount": current_amount * 0.2, "period_month": "2026-03", "is_retro": False},
    ]
    prev = []
    if previous_amount is not None:
        prev = [
            {"topic_code": "3", "budget_topic": "גני ילדים", "amount": previous_amount * 0.5, "period_month": "2026-02", "is_retro": False},
            {"topic_code": "19", "budget_topic": "עוזרות", "amount": previous_amount * 0.3, "period_month": "2026-02", "is_retro": False},
            {"topic_code": "33", "budget_topic": "גננות מדינה", "amount": previous_amount * 0.2, "period_month": "2026-02", "is_retro": False},
        ]

    return {
        "municipality_name": "עיריית בדיקה",
        "current_lines": current,
        "previous_lines": prev,
        "due_amount": current_amount + 1000,
        "paid_amount": current_amount,
        "gap_amount": 1000,
        "code_metadata": {
            "3": {"category": "גני ילדים", "name_short": "שכ\"ל"},
            "19": {"category": "גני ילדים", "name_short": "עוזרות"},
            "33": {"category": "גני ילדים", "name_short": "גננות"},
        },
    }


def test_structural_headings_match_reference_order():
    data = _base_data(300000, 260000)
    res = generate_monthly_memo("2026-03", data)

    # Section order extracted from in-repo reference (כפר קרע.pdf)
    expected = ["1. גנים", "2. הסעות", "3. תיכון", "4. כללי"]
    pos = [res.html.find(h) for h in expected]
    assert all(p >= 0 for p in pos)
    assert pos == sorted(pos)

    # Minimal tag hierarchy check for email block structure
    assert "<div dir=\"rtl\"" in res.html
    assert "<table role=\"presentation\"" in res.html


def test_narrative_branch_up():
    data = _base_data(300000, 200000)
    cfg = MemoConfig(growth_threshold_pct=5.0, flat_threshold_pct=2.0)
    res = generate_monthly_memo("2026-03", data, cfg)
    assert "התקבולים עלו" in res.structured.headline


def test_narrative_branch_flat():
    data = _base_data(300000, 297000)  # ~1% change
    cfg = MemoConfig(growth_threshold_pct=5.0, flat_threshold_pct=2.0)
    res = generate_monthly_memo("2026-03", data, cfg)
    assert "נותרו יציבים" in res.structured.headline


def test_narrative_branch_down():
    data = _base_data(240000, 300000)
    cfg = MemoConfig(growth_threshold_pct=5.0, flat_threshold_pct=2.0)
    res = generate_monthly_memo("2026-03", data, cfg)
    assert "התקבולים ירדו" in res.structured.headline


def test_edge_no_prior_period():
    data = _base_data(200000, None)
    res = generate_monthly_memo("2026-03", data)
    assert "אין נתוני השוואה" in res.structured.headline
    assert res.structured.metrics.previous_total is None


def test_edge_zero_previous_denominator_no_nan():
    data = _base_data(120000, 0)
    res = generate_monthly_memo("2026-03", data)
    assert "NaN" not in res.html
    assert "None" not in res.html
    assert "undefined" not in res.html


def test_edge_missing_segments_and_all_zero_month():
    data = {
        "municipality_name": "עירייה 0",
        "current_lines": [],
        "previous_lines": [],
        "due_amount": 0,
        "paid_amount": 0,
        "gap_amount": 0,
        "code_metadata": {},
    }
    res = generate_monthly_memo("2026-03", data)
    # no empty bullets
    for sec in res.structured.sections:
        assert sec.bullets
        assert all(b.text.strip() for b in sec.bullets)


def test_html_escaping_for_dynamic_text():
    data = _base_data(250000, 200000)
    data["municipality_name"] = "עיריית <בדיקה> & שות'"
    data["current_lines"][0]["budget_topic"] = "גני <ילדים> & מיוחדים"
    res = generate_monthly_memo("2026-03", data)

    assert "עיריית &lt;בדיקה&gt; &amp; שות&#x27;" in res.html
    assert "גני &lt;ילדים&gt; &amp; מיוחדים" in res.html


def test_determinism_same_input_same_html_bytes():
    data = _base_data(260000, 210000)
    a = generate_monthly_memo("2026-03", data)
    b = generate_monthly_memo("2026-03", data)
    assert a.html == b.html


def test_plain_text_contains_key_figures_from_html():
    data = _base_data(310000, 250000)
    res = generate_monthly_memo("2026-03", data)

    # Extract all formatted currency figures that appear in html and verify
    # each appears in plain-text fallback too.
    figures = set(re.findall(r"₪[0-9,]+", res.html))
    for f in figures:
        assert f in res.text
