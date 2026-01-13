#!/usr/bin/env python
"""Quick test for _extract_top_ports function"""
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
        labels.append(f"{service}:{port_num}")
    
    values = [p[1] for p in sorted_ports]
    
    return labels, values


# Test case 1: Empty data
print("Test 1 - Empty data:")
result = _extract_top_ports({})
print(f"  Result: {result}")
assert result == ([], []), "Should return empty lists"

# Test case 2: GUI-style structure with CVEs
print("\nTest 2 - GUI-style structure with CVEs:")
test_data = {
    "192.168.1.100": {
        "gui": {
            "ports": [
                {
                    "port": 22,
                    "service": "ssh",
                    "cves": [
                        {"id": "CVE-2021-1234"},
                        {"id": "CVE-2021-5678"}
                    ]
                },
                {
                    "port": 80,
                    "service": "http",
                    "cves": [
                        {"id": "CVE-2021-9999"}
                    ]
                }
            ]
        }
    }
}
labels, values = _extract_top_ports(test_data)
print(f"  Labels: {labels}")
print(f"  Values: {values}")
assert labels == ["ssh:22", "http:80"], f"Expected ['ssh:22', 'http:80'], got {labels}"
assert values == [2, 1], f"Expected [2, 1], got {values}"

# Test case 3: Multiple hosts
print("\nTest 3 - Multiple hosts with aggregation:")
test_data = {
    "192.168.1.100": {
        "gui": {
            "ports": [
                {
                    "port": 22,
                    "service": "ssh",
                    "cves": [{"id": "CVE-2021-1"}, {"id": "CVE-2021-2"}]
                }
            ]
        }
    },
    "192.168.1.101": {
        "gui": {
            "ports": [
                {
                    "port": 22,
                    "service": "ssh",
                    "cves": [{"id": "CVE-2021-3"}]
                }
            ]
        }
    }
}
labels, values = _extract_top_ports(test_data)
print(f"  Labels: {labels}")
print(f"  Values: {values}")
assert labels == ["ssh:22"], f"Expected ['ssh:22'], got {labels}"
assert values == [3], f"Expected [3], got {values}"

# Test case 4: No CVEs
print("\nTest 4 - Ports with no CVEs:")
test_data = {
    "192.168.1.100": {
        "gui": {
            "ports": [
                {
                    "port": 22,
                    "service": "ssh",
                    "cves": []
                }
            ]
        }
    }
}
labels, values = _extract_top_ports(test_data)
print(f"  Labels: {labels}")
print(f"  Values: {values}")
assert labels == [], f"Expected [], got {labels}"
assert values == [], f"Expected [], got {values}"

print("\n✅ All tests passed!")
