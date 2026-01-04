"""
Test vulnerabilities API endpoint
"""
import sys
sys.path.insert(0, r'c:\Users\dhqkh\CVE_Scan')

from web.services.scan_service import scan_service

print("=" * 60)
print("Test Vulnerabilities Data")
print("=" * 60)

# Get scans with results
scans = scan_service.list_scans(include_results=True)
scans_with_results = [s for s in scans if s.get("results") and len(s.get("results", {})) > 0]

print(f"\n[1] Scans with results: {len(scans_with_results)}")

vulns = []
for scan in scans_with_results:
    results = scan.get("results", {})
    print(f"\n[2] Scan {scan['scan_id'][:8]}...")
    print(f"    Results hosts: {list(results.keys())}")
    
    for host, host_data in results.items():
        # Check structure
        if "ports" in host_data:
            ports = host_data.get("ports", [])
        else:
            print(f"    ⚠️ Host {host} has no 'ports' key!")
            print(f"    Keys: {list(host_data.keys())}")
            continue
        
        print(f"    Host {host}: {len(ports)} ports")
        
        for port_data in ports:
            cves = port_data.get("cves", [])
            print(f"      Port {port_data.get('port')}: {len(cves)} CVEs")
            vulns.extend(cves)

print(f"\n[3] Total vulnerabilities: {len(vulns)}")
if len(vulns) > 0:
    print(f"    First CVE: {vulns[0]}")
