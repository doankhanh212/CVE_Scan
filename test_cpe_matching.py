#!/usr/bin/env python
"""Test CPE matching với local DB"""
import sys
sys.path.insert(0, '.')

from modules.cve.cpe_builder import build_cpe
from modules.cve.cve_matcher import CVEMatcher

# Test CPE building
print("=" * 60)
print("TEST 1: CPE Building")
print("=" * 60)

test_services = [
    ("Microsoft Windows RPC", None),
    ("Microsoft HTTPAPI httpd", "2.0"),
    ("VMware Authentication Daemon", "1.10"),
    ("OpenSSH", "7.4"),
    ("Apache httpd", "2.4.29"),
    ("nginx", "1.18.0"),
]

for service, version in test_services:
    cpe = build_cpe(service, version)
    print(f"{service:40} {version or 'N/A':10} → {cpe}")

# Test CVE matching with local DB
print("\n" + "=" * 60)
print("TEST 2: CVE Matching (Local DB)")
print("=" * 60)

matcher = CVEMatcher(
    api_key=None,
    local_db_path="modules/cve/nvd_cve.db",
    year_window=10
)

print(f"\nMatcher initialized: {matcher.fetcher_type}")
print(f"Fetcher available: {matcher.fetcher is not None}\n")

# Test with some CPEs
test_cpes = [
    "cpe:2.3:a:microsoft:http_api:2.0:*:*:*:*:*:*:*",
    "cpe:2.3:a:vmware:authentication_daemon:1.10:*:*:*:*:*:*:*",
    "cpe:2.3:a:openbsd:openssh:7.4:*:*:*:*:*:*:*",
    "cpe:2.3:a:apache:http_server:2.4.29:*:*:*:*:*:*:*",
]

for cpe in test_cpes:
    print(f"\nSearching CVE for: {cpe}")
    cves = matcher.match_by_cpe(cpe, max_results=5)
    print(f"  Found {len(cves)} CVEs")
    for cve in cves[:3]:
        severity = cve.get('severity', {})
        if isinstance(severity, dict):
            sev_label = severity.get('label', 'N/A')
            sev_score = severity.get('score', 'N/A')
        else:
            sev_label = severity
            sev_score = 'N/A'
        print(f"    - {cve.get('id')}: {sev_label} ({sev_score})")
