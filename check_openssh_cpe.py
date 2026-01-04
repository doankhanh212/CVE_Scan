import sqlite3

conn = sqlite3.connect('modules/cve/nvd_cve.db')
cur = conn.cursor()

# Check for openssh
print("Checking OpenSSH CPEs in database:")
cur.execute("SELECT DISTINCT cve_cpe FROM cve WHERE cve_cpe LIKE '%openssh%' LIMIT 10")
for row in cur.fetchall():
    cpes = eval(row[0]) if row[0] else []
    for cpe in cpes[:2]:
        print(f"  {cpe}")

# Check a specific OpenSSH version
print("\nSearching for OpenSSH 7.4:")
cur.execute("SELECT id, cve_cpe, cvss_base_score FROM cve WHERE cve_cpe LIKE '%openssh%' AND cve_cpe LIKE '%7.4%' LIMIT 5")
for row in cur.fetchall():
    print(f"  {row[0]} - Score: {row[2]}")
    cpes = eval(row[1]) if row[1] else []
    if cpes:
        print(f"    CPE: {cpes[0]}")

conn.close()
