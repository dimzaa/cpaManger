"""
One-shot migration: create topic_summaries + backfill from existing runs.

Run after pushing the Priority-2 code to GitHub and Render finishes redeploying.

    cd "C:\\Users\\zahal\\OneDrive\\מסמכים\\שולחן העבודה\\uncatagorized\\github\\cpa"
    $env:DATABASE_URL = "postgresql://..."
    python migrate_topic_summaries.py

What it does (idempotent):
  1. CREATE TABLE IF NOT EXISTS topic_summaries (+ unique index).
  2. For every existing monthly_runs.id (in chronological order so the
     prev_run lookups work as we go), wipe & recompute its topic rows.
  3. Print a summary table.
"""
import os
import sys

import psycopg2


DDL = """
CREATE TABLE IF NOT EXISTS topic_summaries (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES monthly_runs(id) ON DELETE CASCADE,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(id),
    topic_code VARCHAR(10) NOT NULL,
    topic_name VARCHAR(255),

    amount_total DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_regular DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_retro_pos DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_retro_neg DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    prev_run_id INTEGER REFERENCES monthly_runs(id),
    prev_month_amount DOUBLE PRECISION,
    delta_abs DOUBLE PRECISION,
    delta_pct DOUBLE PRECISION,

    anomaly_flag VARCHAR(20) NOT NULL DEFAULT 'normal',
    tie_out_diff DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    n_institutions INTEGER NOT NULL DEFAULT 0,
    top_institution_code VARCHAR(20),
    top_institution_name VARCHAR(255),
    top_institution_amount DOUBLE PRECISION,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_topic_summary_run_code ON topic_summaries(run_id, topic_code);",
    "CREATE INDEX IF NOT EXISTS ix_topic_summaries_run_id ON topic_summaries(run_id);",
    "CREATE INDEX IF NOT EXISTS ix_topic_summaries_municipality_id ON topic_summaries(municipality_id);",
    "CREATE INDEX IF NOT EXISTS ix_topic_summaries_topic_code ON topic_summaries(topic_code);",
    "CREATE INDEX IF NOT EXISTS ix_topic_summaries_prev_run_id ON topic_summaries(prev_run_id);",
]


def recompute_one_run(cur, run_id, muni_id, run_month):
    # Wipe existing
    cur.execute("DELETE FROM topic_summaries WHERE run_id = %s", (run_id,))

    # Find prev_run
    cur.execute("""
        SELECT id FROM monthly_runs
        WHERE municipality_id = %s AND id <> %s AND month < %s
        ORDER BY month DESC LIMIT 1
    """, (muni_id, run_id, run_month))
    row = cur.fetchone()
    prev_run_id = row[0] if row else None

    # Per-topic aggregates from budget_lines for this run
    cur.execute("""
        SELECT topic_code,
               ROUND(COALESCE(SUM(amount), 0)::numeric, 2),
               ROUND(COALESCE(SUM(amount) FILTER (WHERE NOT is_retro), 0)::numeric, 2),
               ROUND(COALESCE(SUM(amount) FILTER (WHERE is_retro AND amount > 0), 0)::numeric, 2),
               ROUND(COALESCE(SUM(amount) FILTER (WHERE is_retro AND amount < 0), 0)::numeric, 2),
               MAX(budget_topic)
        FROM budget_lines
        WHERE run_id = %s
        GROUP BY topic_code
    """, (run_id,))
    aggs = cur.fetchall()

    inserted = 0
    flag_counts = {"new": 0, "outlier": 0, "normal": 0}

    for topic_code, amt_total, amt_reg, amt_pos, amt_neg, topic_name in aggs:
        amt_total = float(amt_total)
        # Prev amount
        prev_amount = None
        if prev_run_id is not None:
            cur.execute("""
                SELECT ROUND(COALESCE(SUM(amount), 0)::numeric, 2)
                FROM budget_lines
                WHERE run_id = %s AND topic_code = %s
            """, (prev_run_id, topic_code))
            v = cur.fetchone()[0]
            prev_amount = float(v) if v is not None else None

        delta_abs = None
        delta_pct = None
        eff_prev_run_id = None
        if prev_amount is not None:
            eff_prev_run_id = prev_run_id
            delta_abs = round(amt_total - prev_amount, 2)
            if prev_amount != 0:
                delta_pct = round(delta_abs / abs(prev_amount) * 100.0, 2)

        # Classify
        if prev_amount is None or prev_amount == 0.0:
            flag = "new" if abs(amt_total) > 1.0 else "normal"
        elif delta_pct is not None and abs(delta_pct) > 50.0:
            flag = "outlier"
        else:
            flag = "normal"
        flag_counts[flag] = flag_counts.get(flag, 0) + 1

        # Tie-out diff
        cur.execute("""
            SELECT delta FROM ingestion_warnings
            WHERE run_id = %s AND topic_code = %s
              AND category IN ('tie_out_mismatch', 'additive_closure_failed')
            ORDER BY id DESC LIMIT 1
        """, (run_id, str(topic_code)))
        w = cur.fetchone()
        tie_diff = float(w[0]) if w and w[0] is not None else 0.0

        # Institutions: query budget_line_institutions JOIN budget_lines.
        # If budget_line_institutions is empty (it usually is — the high-school stub
        # in upload.py was truncated), this returns 0/NULL gracefully.
        cur.execute("""
            SELECT COUNT(DISTINCT bli.institution_code)
            FROM budget_line_institutions bli
            JOIN budget_lines bl ON bl.id = bli.budget_line_id
            WHERE bl.run_id = %s AND bl.topic_code = %s
        """, (run_id, topic_code))
        n_inst = int((cur.fetchone() or (0,))[0] or 0)
        cur.execute("""
            SELECT bli.institution_code, bli.institution_name,
                   ROUND(SUM(bli.amount)::numeric, 2) AS s
            FROM budget_line_institutions bli
            JOIN budget_lines bl ON bl.id = bli.budget_line_id
            WHERE bl.run_id = %s AND bl.topic_code = %s
            GROUP BY bli.institution_code, bli.institution_name
            ORDER BY ABS(SUM(bli.amount)) DESC LIMIT 1
        """, (run_id, topic_code))
        trow = cur.fetchone()
        if trow:
            top_code, top_name, top_amt = trow
        else:
            top_code, top_name, top_amt = None, None, None

        cur.execute("""
            INSERT INTO topic_summaries (
                run_id, municipality_id, topic_code, topic_name,
                amount_total, amount_regular, amount_retro_pos, amount_retro_neg,
                prev_run_id, prev_month_amount, delta_abs, delta_pct,
                anomaly_flag, tie_out_diff,
                n_institutions, top_institution_code, top_institution_name, top_institution_amount
            ) VALUES (%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s, %s,%s,%s,%s)
        """, (
            run_id, muni_id, str(topic_code), (topic_name or "")[:255] if topic_name else None,
            amt_total, float(amt_reg), float(amt_pos), float(amt_neg),
            eff_prev_run_id, prev_amount, delta_abs, delta_pct,
            flag, round(tie_diff, 2),
            n_inst, (str(top_code) if top_code is not None else None),
            (str(top_name)[:255] if top_name else None), float(top_amt) if top_amt is not None else None,
        ))
        inserted += 1

    return inserted, flag_counts, prev_run_id


def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL env var not set.", file=sys.stderr)
        sys.exit(1)
    if "postgres" not in dsn:
        print("ERROR: this script handles Postgres only.", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()

    print("Step 1: create table + indexes")
    cur.execute(DDL)
    for idx in INDEXES:
        cur.execute(idx)
    print("  done.\n")

    print("Step 2: backfill from existing monthly_runs (chronological)")
    cur.execute("""
        SELECT id, municipality_id, month
        FROM monthly_runs
        ORDER BY municipality_id, month
    """)
    runs = cur.fetchall()
    print(f"  {len(runs)} runs to process.")

    for rid, muni, mon in runs:
        n, flags, prev = recompute_one_run(cur, rid, muni, mon)
        print(f"  run {rid} (muni {muni}, {mon}): {n} topics, anomalies={flags}, prev_run={prev}")

    print("\nStep 3: verification")
    cur.execute("""
        SELECT run_id, COUNT(*) AS n, ROUND(SUM(amount_total)::numeric, 2) AS total
        FROM topic_summaries GROUP BY run_id ORDER BY run_id
    """)
    print(f"  {'run_id':>6} {'topics':>7} {'sum_amount_total':>20}")
    for row in cur.fetchall():
        print(f"  {row[0]:>6} {row[1]:>7} {str(row[2]):>20}")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
