"""
Test script to verify Dashboard and Vulnerabilities data flow
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.services.scan_service import scan_service

print("=" * 60)
print("Testing Dashboard & Vulnerabilities Data Flow")
print("=" * 60)

# Reload scans from disk
print("\n[1] Reloading scans from disk...")
scan_service.reload_scans_from_disk()

# List scans (lightweight - no results, but includes summary)
print("\n[2] Listing scans (lightweight mode)...")
scans = scan_service.list_scans(include_results=False)
print(f"  Found {len(scans)} scans")

# Check each scan
print("\n[3] Checking each scan:")
for scan in scans:
    scan_id = scan.get("scan_id", "unknown")[:8]
    status = scan.get("status", "unknown")
    has_summary = "summary" in scan
    has_results = "results" in scan
    
    print(f"\n  Scan: {scan_id}...")
    print(f"    Status: {status}")
    print(f"    Has summary: {has_summary}")
    print(f"    Has results: {has_results} (should be False in lightweight mode)")
    
    if has_summary:
        summary = scan["summary"]
        print(f"    Summary:")
        print(f"      - Hosts: {summary.get('hosts_scanned', 0)}")
        print(f"      - Ports: {summary.get('open_ports', 0)}")
        print(f"      - CVEs: {summary.get('total_cves', 0)}")
        print(f"      - Critical: {summary.get('severity', {}).get('critical', 0)}")
    else:
        print(f"    ⚠️ WARNING: No summary found!")

# Test Dashboard stats calculation
print("\n[4] Testing Dashboard stats...")
completed = [s for s in scans if s.get("status") == "completed"]
print(f"  Completed scans: {len(completed)}")

if completed:
    latest = max(completed, key=lambda s: s.get("end_time") or "")
    summary = latest.get("summary", {})
    
    print(f"\n  Latest scan stats:")
    print(f"    - Hosts scanned: {summary.get('hosts_scanned', 0)}")
    print(f"    - Open ports: {summary.get('open_ports', 0)}")
    print(f"    - Total CVEs: {summary.get('total_cves', 0)}")
    print(f"    - Critical: {summary.get('severity', {}).get('critical', 0)}")
    print(f"    - High: {summary.get('severity', {}).get('high', 0)}")
    print(f"    - Medium: {summary.get('severity', {}).get('medium', 0)}")
    print(f"    - Low: {summary.get('severity', {}).get('low', 0)}")

# Test Vulnerabilities data (need full results)
print("\n[5] Testing Vulnerabilities data...")
scans_with_results = scan_service.list_scans(include_results=True)
vuln_count = 0

for scan in scans_with_results:
    results = scan.get("results", {})
    for host, host_data in results.items():
        ports = host_data.get("ports", [])
        for port_data in ports:
            cves = port_data.get("cves", [])
            vuln_count += len(cves)

print(f"  Total vulnerabilities across all scans: {vuln_count}")

print("\n" + "=" * 60)
print("✅ Test complete!")
print("=" * 60)
print("\nNext steps:")
print("  1. Start web app: python app.py")
print("  2. Open browser: http://localhost:5000")
print("  3. Check Dashboard page for stats")
print("  4. Check Vulnerabilities page for CVE list")
