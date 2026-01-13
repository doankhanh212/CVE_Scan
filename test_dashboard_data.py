#!/usr/bin/env python
"""Debug script to check dashboard data"""
import sys
sys.path.insert(0, r'c:\Users\dhqkh\CVE_Scan')

from web.services.scan_service import scan_service
from collections import defaultdict

# Get scans with results
scans = scan_service.list_scans(include_results=True)
print(f"Total scans: {len(scans)}")

scans_with_results = [s for s in scans if s.get("results") and len(s.get("results", {})) > 0]
print(f"Scans with results: {len(scans_with_results)}")

if scans_with_results:
    scan = scans_with_results[0]
    print(f"\nLatest scan: {scan['scan_id']}")
    results = scan.get("results", {})
    
    print(f"\nResults keys (hosts): {list(results.keys())}")
    
    if results:
        first_host = list(results.keys())[0]
        host_data = results[first_host]
        
        print(f"\n=== Host: {first_host} ===")
        print(f"Type: {type(host_data)}")
        print(f"Keys: {list(host_data.keys()) if isinstance(host_data, dict) else 'N/A'}")
        
        # Check structure
        if "gui" in host_data:
            print(f"Has 'gui' key: True")
            gui_data = host_data.get("gui", {})
            print(f"  gui keys: {list(gui_data.keys())}")
            ports = gui_data.get("ports", [])
            print(f"  ports count: {len(ports)}")
            if ports and len(ports) > 0:
                port = ports[0]
                print(f"  first port keys: {list(port.keys())}")
                cves = port.get("cves", [])
                print(f"  first port CVEs count: {len(cves)}")
        
        elif "ports" in host_data:
            print(f"Has 'ports' key: True")
            ports = host_data.get("ports", [])
            print(f"  ports count: {len(ports)}")
        else:
            print(f"No 'gui' or 'ports' key - data structure mismatch!")
