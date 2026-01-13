#!/usr/bin/env python
"""Debug script to check ports and CVEs"""
import sys
sys.path.insert(0, r'c:\Users\dhqkh\CVE_Scan')

from web.services.scan_service import scan_service

# Get scans with results
scans = scan_service.list_scans(include_results=True)
scans_with_results = [s for s in scans if s.get("results") and len(s.get("results", {})) > 0]

if scans_with_results:
    scan = scans_with_results[0]
    results = scan.get("results", {})
    
    # Check a few hosts with ports
    ports_found = False
    for host_label, host_data in list(results.items())[:10]:
        ports = host_data.get("ports", [])
        if ports and len(ports) > 0:
            print(f"\n=== Host: {host_label} ===")
            print(f"Ports count: {len(ports)}")
            
            for i, port_info in enumerate(ports[:2]):
                print(f"\nPort {i+1}:")
                print(f"  port: {port_info.get('port')}")
                print(f"  service: {port_info.get('service')}")
                cves = port_info.get("cves", [])
                print(f"  CVEs count: {len(cves)}")
                if cves:
                    print(f"  First CVE: {cves[0].get('id')}")
            
            ports_found = True
            break
    
    if not ports_found:
        print("\n⚠️ No ports with CVEs found in first 10 hosts!")
        print("\nScanning all hosts for any port data...")
        
        host_count = 0
        port_count = 0
        cve_count = 0
        
        for host_label, host_data in results.items():
            ports = host_data.get("ports", [])
            if ports:
                host_count += 1
                port_count += len(ports)
                for port_info in ports:
                    cves = port_info.get("cves", [])
                    cve_count += len(cves)
        
        print(f"\nSummary:")
        print(f"  Hosts with ports: {host_count}")
        print(f"  Total ports: {port_count}")
        print(f"  Total CVEs: {cve_count}")
