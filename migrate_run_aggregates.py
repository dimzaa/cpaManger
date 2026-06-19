"""
One-shot migration script for Priority-1 dashboard aggregates.

Run this AFTER pushing the new column definitions to GitHub and waiting for
Render's redeploy to finish.

What it does (in order, idempotent):
  1. ALTER TABLE monthly_runs ADD COLUMN if the column doesn't exist.
     (Postgres only — SQLite handles this differently but local dev DBs
     get rebuilt anyway by Base.metadata.create_all.)
  2. Backfill every existing run by computing its aggregates from
     budget_lines.
  3. Print before/after summary.

Run from PowerShell (with $env:DATABASE_URL set to the Neon URL):

    cd "C:\\Users\\zahal\\OneDrive\\מסמכים\\שולחן העבודה\\uncatagorized\\github\\cpa"
    $env:DATABASE_URL = "postgresql://..."
    python migrate_run_aggregates.py
"""
import os
import sys

import psycopg2


NEW_COLUMNS = [
    ("regular_total", "DOUBLE PRECISION"),
    ("retro_positive_total", "DOUBLE PRECISION"),
    ("retro_negative_total", "DOUBLE PRECISION"),
    ("topics_count", "INTEGER"),
    ("lines_count", "INTEGER"),
]


def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL env var not set.", file=sys.stderr)
        sys.exit(1)
    if "postgres" not in dsn:
        print("ERROR: this script only handles Postgres (DSN doesn't look like it).", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()

    # ── Step 1: add columns if missing ────────────────────────────────────
    print("Step 1: schema migration")
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'monthly_runs' AND table_schema = 'public'
    """)
    existing = {r[0] for r in cur.fetchall()}
    for col_name, col_type in NEW_COLUMNS:
        if col_name in existing:
            print(f"  - {col_name}: already exists, skipping")
            continue
        sql = f"ALTER TABLE monthly_runs ADD COLUMN {col_name} {col_type}"
        print(f"  - {col_name}: adding ({sql})")
        cur.execute(sql)
    print("Step 1 complete.\n")

    # ── Step 2: backfill via the service ─────────────────────────────────
    # We do the backfill in raw SQL here rather than importing the service —
    # this script must run standalone without pulling in the full backend
    # (which would fail on Render-specific imports). The math is identical.
    print("Step 2: backfilling existing rows from budget_lines")

    cur.execute("SELECT id FROM monthly_runs ORDER BY id")
    run_ids = [r[0] for r in cur.fetchall()]
    print(f"  Found {len(run_ids)} existing runs.")

    for rid in run_ids:
        cur.execute("""
            SELECT
                ROUND(COALESCE(SUM(amount) FILTER (WHERE NOT is_retro), 0)::numeric, 2),
                ROUND(COALESCE(SUM(amount) FILTER (WHERE is_retro AND amount > 0), 0)::numeric, 2),
                ROUND(COALESCE(SUM(amount) FILTER (WHERE is_retro AND amount < 0), 0)::numeric, 2),
                COUNT(DISTINCT topic_code),
                COUNT(*)
            FROM budget_lines
            WHERE run_id = %s
        """, (rid,))
        regular, retro_pos, retro_neg, topics, lines = cur.fetchone()
        cur.execute("""
            UPDATE monthly_runs
            SET regular_total = %s,
                retro_positive_total = %s,
                retro_negative_total = %s,
                topics_count = %s,
                lines_count = %s
            WHERE id = %s
        """, (float(regular), float(retro_pos), float(retro_neg), int(topics), int(lines), rid))
        print(
            f"  run {rid}: regular=₪{regular} retro+=₪{retro_pos} "
            f"retro-=₪{retro_neg} topics={topics} lines={lines}"
        )
    print("Step 2 complete.\n")

    # ── Step 3: verify ────────────────────────────────────────────────────
    print("Step 3: verification — current state of monthly_runs")
    cur.execute("""
        SELECT id, municipality_id, month,
               ROUND(breakdown_total::numeric, 2),
               ROUND(regular_total::numeric, 2),
               ROUND(retro_positive_total::numeric, 2),
               ROUND(retro_negative_total::numeric, 2),
               topics_count, lines_count
        FROM monthly_runs
        ORDER BY id
    """)
    rows = cur.fetchall()
    print(f"  {'id':>3} {'muni':>4} {'month':>8} {'breakdown':>14} {'regular':>14} {'retro+':>12} {'retro-':>12} {'topics':>7} {'lines':>6}")
    for r in rows:
        print(f"  {r[0]:>3} {r[1]:>4} {r[2]:>8} {str(r[3]):>14} {str(r[4]):>14} {str(r[5]):>12} {str(r[6]):>12} {str(r[7]):>7} {str(r[8]):>6}")

    cur.close()
    conn.close()
    print("\nDone. Push the code, wait for Render redeploy, then re-run this script "
          "if you want to re-sync after any backfills.")


if __name__ == "__main__":
    main()
