#!/usr/bin/env python
"""Test port label deduplication"""
import sys
sys.path.insert(0, r'c:\Users\dhqkh\CVE_Scan')

from collections import defaultdict

def _extract_top_ports(scan_results):
    """Extract top vulnerable ports from scan results"""
    port_count = defaultdict(int)
    port_services = {}
    
    if not scan_results:
        return [], []
    
    if not isinstance(scan_results, dict):
        return [], []
    
    # Count CVEs per port across all hosts
    for host_label, host_data in scan_results.items():
        if not isinstance(host_data, dict):
            continue
        
        # Handle GUI-style structure: { "gui": { "ports": [...] } }
        ports = []
        if "gui" in host_data:
            ports = host_data.get("gui", {}).get("ports", [])
        elif "ports" in host_data:
            ports = host_data.get("ports", [])
        
        # Count CVEs by port
        for port_data in ports:
            if not isinstance(port_data, dict):
                continue
            
            port_num = port_data.get("port", "unknown")
            service_name = port_data.get("service", "unknown")
            cves = port_data.get("cves", [])
            
            # Count CVEs for this port
            cve_count = len(cves) if isinstance(cves, list) else 0
            if cve_count > 0:
                port_services[port_num] = service_name
                port_count[port_num] += cve_count
    
    # Sort by CVE count descending - show top 10 ports
    sorted_ports = sorted(port_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Format labels with service:port format
    labels = []
    for p in sorted_ports:
        port_num = p[0]
        service = port_services.get(port_num, "unknown")
        
        # Check if service name already contains port (e.g., "ssh:22")
        # If yes, use as-is; if no, append port number
        if ":" in service and service.split(":")[-1].strip().isdigit():
            labels.append(service)  # Already has port
        else:
            labels.append(f"{service}:{port_num}")  # Add port
    
    values = [p[1] for p in sorted_ports]
    
    return labels, values


# Test case: Service name already contains port
print("Test - Service name with port (like real data):")
test_data = {
    "192.168.1.100": {
        "ports": [
            {
                "port": 22,
                "service": "ssh:22",  # Already has port
                "cves": [{"id": "CVE-2021-1"}, {"id": "CVE-2021-2"}]
            },
            {
                "port": 80,
                "service": "http:80",  # Already has port
                "cves": [{"id": "CVE-2021-3"}]
            },
            {
                "port": 443,
                "service": "https",  # No port
                "cves": [{"id": "CVE-2021-4"}]
            }
        ]
    }
}

labels, values = _extract_top_ports(test_data)
print(f"  Labels: {labels}")
print(f"  Values: {values}")

# Check for duplicates
expected = ["ssh:22", "http:80", "https:443"]
if labels == expected:
    print("  ✅ PASS - No duplicate port numbers!")
else:
    print(f"  ❌ FAIL - Expected {expected}, got {labels}")
    sys.exit(1)

print("\n✅ All deduplication tests passed!")
