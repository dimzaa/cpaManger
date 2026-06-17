import sqlite3
conn = sqlite3.connect('cpa.db')
c = conn.cursor()

print('=== MONTHLY_RUNS FOR MUNICIPALITY 10406544 ===')
c.execute('SELECT r.id, m.code, m.name, r.month, r.year, r.status FROM monthly_runs r JOIN municipalities m ON r.municipality_id = m.id WHERE m.code = ?', ('10406544',))
for row in c.fetchall():
    print(f'  {row}')

print('\n=== BUDGET_LINES FOR MUNICIPALITY 10406544 (first 5) ===')
c.execute('SELECT bl.budget_topic, bl.current_month, bl.period_month, bl.amount FROM budget_lines bl WHERE bl.municipality_id = 4 LIMIT 5')
for row in c.fetchall():
    print(f'  {row}')

conn.close()
