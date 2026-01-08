#!/usr/bin/env python
"""Quick test of EPSS database + Likelihood calculator"""

import sqlite3
from modules.cve.likelihood_calculator import LikelihoodCalculator

# Verify database was created
db_path = 'modules/cve/epss.db'
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM epss')
    count = cursor.fetchone()[0]
    print(f'✓ EPSS Database: {count:,} records')

# Input CVE from user
cve_id = input("\nEnter CVE ID (e.g. CVE-2023-12345): ").strip().upper()

# Input CVSS base score
cvss_base = float(input("Enter CVSS base score: ").strip())

# Test likelihood calculator
calc = LikelihoodCalculator(db_path)

vuln = {
    'id': cve_id,
    'cvss_v3': {'baseScore': cvss_base}
}

# Enrich
enriched = calc.enrich_vulnerability_with_likelihood(vuln, cve_id)

print('\n✓ Likelihood enrichment:')
print(f'  CVE: {enriched["id"]}')
print(f'  CVSS: {enriched["cvss_v3"]["baseScore"]}')
print(f'  EPSS: {enriched["likelihood"]["epss"]}')
print(f'  Likelihood Score: {enriched["likelihood"]["score"]:.5f}')
print(f'  Likelihood Level: {enriched["likelihood"]["level"]}')

print('\n✓ System ready for production use!')
