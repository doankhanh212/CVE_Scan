#!/usr/bin/env python
"""Debug script to check all scans and their data"""
import sys
sys.path.insert(0, r'c:\Users\dhqkh\CVE_Scan')

from web.services.scan_service import scan_service
import json

# Get all scans WITHOUT results (lightweight)
scans = scan_service.list_scans(include_results=False)
print(f"Total scans in system: {len(scans)}")
print("\n" + "="*80)

for i, scan in enumerate(scans):
    print(f"\n[Scan {i+1}]")
    print(f"  Scan ID: {scan['scan_id']}")
    print(f"  Status: {scan['status']}")
    print(f"  Start time: {scan.get('start_time')}")
    print(f"  End time: {scan.get('end_time')}")
    print(f"  Hosts: {len(scan.get('hosts', []))}")
    print(f"  Has summary: {'summary' in scan}")
    
    if 'summary' in scan:
        summary = scan['summary']
        print(f"  Summary:")
        print(f"    - hosts_scanned: {summary.get('hosts_scanned')}")
        print(f"    - open_ports: {summary.get('open_ports')}")
        print(f"    - total_cves: {summary.get('total_cves')}")
        print(f"    - severity: {summary.get('severity')}")

print("\n" + "="*80)
print("\nNow checking actual results data...")

# Get scans WITH results
scans_full = scan_service.list_scans(include_results=True)
scans_with_results = [s for s in scans_full if s.get("results") and len(s.get("results", {})) > 0]

print(f"\nScans with results: {len(scans_with_results)}")

for i, scan in enumerate(scans_with_results):
    results = scan.get("results", {})
    print(f"\n[Scan with results {i+1}]")
    print(f"  Scan ID: {scan['scan_id'][:8]}...")
    print(f"  Hosts in results: {len(results)}")
    
    # Count CVEs
    total_cves = 0
    for host_label, host_data in results.items():
        ports = host_data.get("ports", [])
        for port_data in ports:
            cves = port_data.get("cves", [])
            total_cves += len(cves)
    
    print(f"  Total CVEs in results: {total_cves}")
