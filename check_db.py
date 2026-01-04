import sqlite3

conn = sqlite3.connect('modules/cve/nvd_cve.db')
cur = conn.cursor()

# Count total CVEs
cur.execute('SELECT COUNT(*) FROM cve')
total = cur.fetchone()[0]
print(f'Total CVEs in DB: {total}')

# Sample CVEs
cur.execute('SELECT id, cvss_base_score, cvss_severity FROM cve ORDER BY RANDOM() LIMIT 5')
print('\nSample CVEs:')
for row in cur.fetchall():
    print(f'  {row[0]} - Score: {row[1]} - Severity: {row[2]}')

# Check for specific products
print('\n\nChecking for common products in CPE data:')
for product in ['openssh', 'apache', 'nginx', 'microsoft', 'linux']:
    cur.execute('SELECT COUNT(*) FROM cve WHERE cve_cpe LIKE ?', (f'%{product}%',))
    count = cur.fetchone()[0]
    print(f'  {product}: {count} CVEs')

conn.close()
