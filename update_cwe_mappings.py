#!/usr/bin/env python3
import json

# Load existing CWE mappings
with open('c:/Users/dhqkh/CVE_Scan/config/cwe_mapping.json', 'r') as f:
    data = json.load(f)

# New CWEs to add
new_cwes = [
    {
        "cwe_id": 120,
        "cwe_name": "Buffer Copy without Checking Size of Input",
        "owasp_codes": ["A06:2021"],
        "mitre_techniques": ["T1190"],
        "severity": "CRITICAL"
    },
    {
        "cwe_id": 122,
        "cwe_name": "Heap-based Buffer Overflow",
        "owasp_codes": ["A06:2021"],
        "mitre_techniques": ["T1190"],
        "severity": "CRITICAL"
    },
    {
        "cwe_id": 190,
        "cwe_name": "Integer Overflow or Wraparound",
        "owasp_codes": ["A06:2021"],
        "mitre_techniques": ["T1190"],
        "severity": "HIGH"
    },
    {
        "cwe_id": 362,
        "cwe_name": "Concurrent Execution using Shared Resource with Improper Synchronization",
        "owasp_codes": ["A06:2021"],
        "mitre_techniques": ["T1530"],
        "severity": "MEDIUM"
    },
    {
        "cwe_id": 416,
        "cwe_name": "Use After Free",
        "owasp_codes": ["A06:2021"],
        "mitre_techniques": ["T1190"],
        "severity": "CRITICAL"
    },
    {
        "cwe_id": 476,
        "cwe_name": "Null Pointer Dereference",
        "owasp_codes": ["A06:2021"],
        "mitre_techniques": [],
        "severity": "MEDIUM"
    },
    {
        "cwe_id": 611,
        "cwe_name": "Improper Restriction of XML External Entity Reference",
        "owasp_codes": ["A05:2021"],
        "mitre_techniques": ["T1190"],
        "severity": "HIGH"
    },
    {
        "cwe_id": 674,
        "cwe_name": "Uncontrolled Recursion",
        "owasp_codes": ["A06:2021"],
        "mitre_techniques": [],
        "severity": "MEDIUM"
    }
]

# Add new CWEs
for new_cwe in new_cwes:
    # Check if CWE already exists
    existing = [m for m in data['mappings'] if m['cwe_id'] == new_cwe['cwe_id']]
    if not existing:
        data['mappings'].append(new_cwe)
        print(f"✓ Added CWE-{new_cwe['cwe_id']}")
    else:
        print(f"⚠ CWE-{new_cwe['cwe_id']} already exists")

# Sort by CWE ID
data['mappings'].sort(key=lambda x: x['cwe_id'])

# Save back
with open('c:/Users/dhqkh/CVE_Scan/config/cwe_mapping.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\n✅ Updated CWE mappings. Total: {len(data['mappings'])}")
