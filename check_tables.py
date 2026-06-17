import sqlite3
from backend.config import DATABASE_URL
import os

# Extract database path from DATABASE_URL
if "sqlite:///" in DATABASE_URL:
    db_path = DATABASE_URL.replace("sqlite:///", "")
    # Handle both relative and absolute paths
    if not os.path.isabs(db_path):
        # Relative path - make it absolute from current directory
        db_path = os.path.join(os.getcwd(), db_path)
else:
    db_path = "cpa.db"

print(f"Checking database at: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")
print(f"File size: {os.path.getsize(db_path) if os.path.exists(db_path) else 'N/A'}")

db = sqlite3.connect(db_path)
cursor = db.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()

print('\nDatabase tables:')
for table in tables:
    print(f'  - {table[0]}')

print(f'\nTotal: {len(tables)} tables')
db.close()
