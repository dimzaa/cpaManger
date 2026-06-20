"""
One-shot migration: create code_history + backfill from existing runs.

Run after pushing Priority-3 code & Render redeploy:

    $env:DATABASE_URL = "postgresql://..."
    python migrate_code_history.py
"""
import os, sys, psycopg2

DDL = """
CREATE TABLE IF NOT EXISTS code_history (
    id SERIAL PRIMARY KEY,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(id),
    topic_code VARCHAR(10) NOT NULL,
    year_month VARCHAR(7) NOT NULL,
    run_id INTEGER NOT NULL REFERENCES monthly_runs(id) ON DELETE CASCADE,
    topic_name VARCHAR(255),
    amount_total DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_regular DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_retro_pos DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_retro_neg DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    line_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_code_history_muni_code_month ON code_history(municipality_id, topic_code, year_month);",
    "CREATE INDEX IF NOT EXISTS ix_code_history_muni ON code_history(municipality_id);",
    "CREATE INDEX IF NOT EXISTS ix_code_history_topic_code ON code_history(topic_code);",
    "CREATE INDEX IF NOT EXISTS ix_code_history_year_month ON code_history(year_month);",
    "CREATE INDEX IF NOT EXISTS ix_code_history_run_id ON code_history(run_id);",
]

def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn or "postgres" not in dsn:
        print("ERROR: DATABASE_URL not set or not Postgres", file=sys.stderr); sys.exit(1)
    conn = psycopg2.connect(dsn); conn.autocommit = True; cur = conn.cursor()

    print("Step 1: DDL")
    cur.execute(DDL)
    for idx in INDEXES: cur.execute(idx)
    print("  done.")

    print("Step 2: backfill from existing runs")
    cur.execute("SELECT id, municipality_id, month FROM monthly_runs ORDER BY municipality_id, month")
    runs = cur.fetchall()
    print(f"  {len(runs)} runs to process.")
    for rid, muni, ym in runs:
        # Wipe existing rows for (muni, ym)
        cur.execute("DELETE FROM code_history WHERE municipality_id = %s AND year_month = %s", (muni, ym))
        # Insert one row per topic_code
        cur.execute("""
            INSERT INTO code_history (municipality_id, topic_code, year_month, run_id, topic_name,
                                      amount_total, amount_regular, amount_retro_pos, amount_retro_neg, line_count)
            SELECT %s, topic_code, %s, %s, MAX(budget_topic),
                   ROUND(COALESCE(SUM(amount), 0)::numeric, 2),
                   ROUND(COALESCE(SUM(amount) FILTER (WHERE NOT is_retro), 0)::numeric, 2),
                   ROUND(COALESCE(SUM(amount) FILTER (WHERE is_retro AND amount > 0), 0)::numeric, 2),
                   ROUND(COALESCE(SUM(amount) FILTER (WHERE is_retro AND amount < 0), 0)::numeric, 2),
                   COUNT(*)
            FROM budget_lines
            WHERE run_id = %s
            GROUP BY topic_code
        """, (muni, ym, rid, rid))
        print(f"  run {rid} (muni {muni}, {ym}): inserted {cur.rowcount} history rows")

    print("\nStep 3: verification")
    cur.execute("""
        SELECT municipality_id, COUNT(DISTINCT year_month) AS months, COUNT(DISTINCT topic_code) AS codes,
               COUNT(*) AS rows, ROUND(SUM(amount_total)::numeric, 2) AS total
        FROM code_history GROUP BY municipality_id ORDER BY municipality_id
    """)
    for r in cur.fetchall():
        print(f"  muni {r[0]}: {r[1]} months, {r[2]} codes, {r[3]} rows, total=₪{r[4]}")
    cur.close(); conn.close()
    print("\nDone.")

if __name__ == "__main__": main()
