"""One-shot migration for code_anomalies. Requires Priority-2 already migrated."""
import os, sys, psycopg2

DDL = """
CREATE TABLE IF NOT EXISTS code_anomalies (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES monthly_runs(id) ON DELETE CASCADE,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(id),
    topic_code VARCHAR(10) NOT NULL,
    flag_type VARCHAR(20) NOT NULL,
    previous_value DOUBLE PRECISION,
    current_value DOUBLE PRECISION,
    delta DOUBLE PRECISION,
    delta_pct DOUBLE PRECISION,
    narrative VARCHAR(500),
    acknowledged_by_cpa BOOLEAN NOT NULL DEFAULT false,
    acknowledged_at TIMESTAMP,
    acknowledged_by_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_anomaly_run_code_flag ON code_anomalies(run_id, topic_code, flag_type);",
    "CREATE INDEX IF NOT EXISTS ix_anomaly_run ON code_anomalies(run_id);",
    "CREATE INDEX IF NOT EXISTS ix_anomaly_muni ON code_anomalies(municipality_id);",
    "CREATE INDEX IF NOT EXISTS ix_anomaly_ack ON code_anomalies(acknowledged_by_cpa);",
]

def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn or "postgres" not in dsn:
        print("ERROR: DATABASE_URL not set or not Postgres", file=sys.stderr); sys.exit(1)
    conn = psycopg2.connect(dsn); conn.autocommit = True; cur = conn.cursor()
    cur.execute(DDL)
    for idx in INDEXES: cur.execute(idx)
    print("✓ table + indexes created")

    print("Backfilling from topic_summaries...")
    cur.execute("SELECT id FROM monthly_runs ORDER BY id")
    run_ids = [r[0] for r in cur.fetchall()]
    for rid in run_ids:
        cur.execute("DELETE FROM code_anomalies WHERE run_id = %s", (rid,))
        # Insert from topic_summaries with anomaly_flag != normal
        cur.execute("""
            INSERT INTO code_anomalies (run_id, municipality_id, topic_code, flag_type,
                                        previous_value, current_value, delta, delta_pct, narrative)
            SELECT run_id, municipality_id, topic_code, anomaly_flag,
                   prev_month_amount, amount_total, delta_abs, delta_pct,
                   CASE
                     WHEN anomaly_flag = 'new' THEN
                       'קוד ' || topic_code || ' (' || COALESCE(topic_name, '') || ') חדש החודש'
                     WHEN anomaly_flag = 'disappeared' THEN
                       'קוד ' || topic_code || ' (' || COALESCE(topic_name, '') || ') נעלם החודש'
                     WHEN anomaly_flag = 'outlier' THEN
                       'קוד ' || topic_code || ' (' || COALESCE(topic_name, '') || ') השתנה ב-' || COALESCE(ROUND(delta_pct::numeric, 1)::text, '?') || '%%'
                     ELSE 'קוד ' || topic_code
                   END
            FROM topic_summaries
            WHERE run_id = %s AND anomaly_flag <> 'normal'
        """, (rid,))
        n_flag = cur.rowcount
        # Plus tie_out_gap rows
        cur.execute("""
            INSERT INTO code_anomalies (run_id, municipality_id, topic_code, flag_type,
                                        previous_value, current_value, delta, delta_pct, narrative)
            SELECT run_id, municipality_id, topic_code, 'tie_out_gap',
                   NULL, amount_total, tie_out_diff, NULL,
                   'קוד ' || topic_code || ': פער של ₪' || ABS(tie_out_diff)::text || ' בין החשבונית לפירוט'
            FROM topic_summaries
            WHERE run_id = %s AND ABS(tie_out_diff) > 0.01
            ON CONFLICT (run_id, topic_code, flag_type) DO NOTHING
        """, (rid,))
        n_tie = cur.rowcount
        print(f"  run {rid}: {n_flag} flag-based, {n_tie} tie_out_gap")
    cur.close(); conn.close()
    print("Done.")

if __name__ == "__main__": main()
