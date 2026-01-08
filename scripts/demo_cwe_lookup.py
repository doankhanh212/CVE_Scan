#!/usr/bin/env python3
"""Quick demo of CWE lookup service."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.cve.cwe_lookup import CWELookup

lookup = CWELookup()

# Test CWE-79 (XSS)
print("=== CWE-79: Cross-site Scripting ===\n")

cwe = lookup.get_cwe("CWE-79")
if cwe:
    print(f"Name: {cwe['name']}")
    print(f"Extended Description: {cwe['extended_description'][:200]}...\n")

consequences = lookup.get_consequences("CWE-79")
print(f"Consequences ({len(consequences)}):")
for cons in consequences[:3]:
    print(f"  - Scope: {cons['scope']}, Impact: {cons['impact']}")

mitigations = lookup.get_mitigations("CWE-79")
print(f"\nMitigations ({len(mitigations)}):")
for mit in mitigations[:3]:
    print(f"  - Phase: {mit['phase']}")
    print(f"    Description: {mit['description'][:100]}...\n")

lookup.close()
