#!/usr/bin/env python3
"""Debug script to check CVE data structure"""

from web.services.scan_service import scan_service
import json

scans = scan_service.list_scans(include_results=True)
print(f"Total scans: {len(scans)}")

if scans and len(scans) > 0 and scans[0].get('results'):
    results = scans[0]['results']
    print(f"Scan 0 results keys (hosts): {list(results.keys())[:5]}")
    
    # Get first host
    if results:
        first_host_ip = list(results.keys())[0]
        host_data = results[first_host_ip]
        print(f"\n=== Host {first_host_ip} ===")
        
        if isinstance(host_data, dict) and 'ports' in host_data:
            ports = host_data['ports']
            print(f"Ports: {len(ports)}")
            
            if ports and len(ports) > 0:
                port = ports[0]
                print(f"\nFirst port keys: {list(port.keys()) if isinstance(port, dict) else type(port)}")
                print(f"First port: {json.dumps(port, indent=2, default=str)[:1500]}")
