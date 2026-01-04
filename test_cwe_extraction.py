#!/usr/bin/env python3
"""Test CWE extraction from CVE description"""

# Test data - actual CVE from scan
cve_data = {
    "id": "CVE-2023-49441",
    "description": "dnsmasq 2.9 is vulnerable to Integer Overflow via forward_query.",
    "product": "dnsmasq",
}

# CWE inference logic
cwe_mapping = {
    'buffer overflow': 120,
    'heap overflow': 122,
    'stack overflow': 674,
    'integer overflow': 190,
    'sql injection': 89,
    'xss': 79,
}

description = (cve_data.get('description') or '').lower()
product = (cve_data.get('product') or '').lower()

inferred_cwe = set()
for keyword, cwe_id in cwe_mapping.items():
    if keyword in description or keyword in product:
        inferred_cwe.add(cwe_id)
        print(f"✓ Found '{keyword}' in description → CWE-{cwe_id}")

if inferred_cwe:
    print(f"\n✅ Extracted CWEs: {list(inferred_cwe)}")
else:
    print(f"\n⚠️ No CWEs found, using defaults: [79, 89, 434]")
    inferred_cwe = [79, 89, 434]

print(f"\nFinal CWE list: {list(inferred_cwe)}")
