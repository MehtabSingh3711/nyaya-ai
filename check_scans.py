import sqlite3
import json

conn = sqlite3.connect('nyaya_history.db')
cur = conn.cursor()
rows = cur.execute('select scan_id, contract_name, status, results_json from scans').fetchall()
for r in rows:
    print("="*60)
    print(f"SCAN ID: {r[0]}")
    print(f"NAME: {r[1]}")
    print(f"STATUS: {r[2]}")
    if r[3]:
        try:
            data = json.loads(r[3])
            print(f"MESSAGE/ERROR: {data.get('message')}")
            print(f"FINDINGS COUNT: {len(data.get('findings', []))}")
        except Exception as e:
            print(f"PARSE ERROR: {e}")
    else:
        print("NO RESULTS JSON")
conn.close()
