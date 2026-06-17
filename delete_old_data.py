import sqlite3

conn = sqlite3.connect('cpa.db')
c = conn.cursor()

print('Deleting old data for municipality 10406544...')

# Get the municipality ID
c.execute('SELECT id FROM municipalities WHERE code = ?', ('10406544',))
mun_id = c.fetchone()

if mun_id:
    mun_id = mun_id[0]
    
    # Delete budget lines
    c.execute('DELETE FROM budget_lines WHERE municipality_id = ?', (mun_id,))
    print(f'  Deleted {c.rowcount} budget lines')
    
    # Delete monthly runs
    c.execute('DELETE FROM monthly_runs WHERE municipality_id = ?', (mun_id,))
    print(f'  Deleted {c.rowcount} monthly runs')
    
    conn.commit()
    print('✅ Old data deleted')
else:
    print('❌ Municipality not found')

conn.close()
