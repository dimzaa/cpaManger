"""
One-shot admin seeder. Run from PowerShell:

    $env:DATABASE_URL = "postgresql://...your-neon-string..."
    python seed_admin.py

Creates:
  * municipality 'כפר קרע' / code 10406544 (if missing)
  * admin user 'admin@cpa.com' / password 'admin1234' (if missing)

Idempotent — safe to re-run.

Does NOT depend on the backend code, so pandas/sqlalchemy install failures
on the local machine don't block this. Uses raw psycopg2 only.
"""

import os
import sys
import psycopg2
import bcrypt

DSN = os.environ.get("DATABASE_URL")
if not DSN:
    print("ERROR: DATABASE_URL env var not set.")
    print("In PowerShell:  $env:DATABASE_URL = \"postgresql://...\"")
    sys.exit(1)

print(f"Connecting to {DSN.split('@')[-1].split('?')[0]}...")
conn = psycopg2.connect(DSN)
conn.autocommit = True
cur = conn.cursor()

# 1. Sanity check — list tables Render's startup should have created.
cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
n_tables = cur.fetchone()[0]
print(f"Public tables in Neon: {n_tables}")

if n_tables == 0:
    print("\nNo tables found. Render hasn't initialized the DB yet.")
    print("Fix: open https://cpamanger.onrender.com/health in your browser,")
    print("wait ~30 sec for the JSON response (wakes the service + runs init),")
    print("then re-run this script.")
    sys.exit(1)

cur.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='public' ORDER BY table_name"
)
for (t,) in cur.fetchall():
    print(f"  - {t}")

# 2. Municipality.
cur.execute("SELECT id FROM municipalities WHERE code = %s", ('10406544',))
row = cur.fetchone()
if row:
    muni_id = row[0]
    print(f"\nMunicipality already exists: id={muni_id}")
else:
    cur.execute(
        "INSERT INTO municipalities (name, code, is_test) "
        "VALUES (%s, %s, false) RETURNING id",
        ('כפר קרע', '10406544'),
    )
    muni_id = cur.fetchone()[0]
    print(f"\nMunicipality created: id={muni_id}")

# 3. Admin user.
cur.execute("SELECT id FROM users WHERE email = %s", ('admin@cpa.com',))
row = cur.fetchone()
if row:
    print(f"Admin already exists: id={row[0]} (login still works)")
else:
    pwd_hash = bcrypt.hashpw(b'admin1234', bcrypt.gensalt()).decode()
    cur.execute(
        "INSERT INTO users (email, hashed_password, role, is_active, is_test) "
        "VALUES (%s, %s, %s, true, false) RETURNING id",
        ('admin@cpa.com', pwd_hash, 'admin'),
    )
    admin_id = cur.fetchone()[0]
    print(f"Admin created: id={admin_id}")
    print(f"  email:    admin@cpa.com")
    print(f"  password: admin1234")
    print(f"  (change this in the UI after first login)")

cur.close()
conn.close()
print("\nDone. Log in at your Vercel URL.")
