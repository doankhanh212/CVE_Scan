from web.services.scan_service import scan_service

scans = scan_service.list_scans(include_results=True)
print(f'Total scans: {len(scans)}')
print(f'Scans with results: {sum(1 for s in scans if s.get("results"))}')

# Check vulnerability data
vuln_count = 0
for scan in scans:
    results = scan.get('results', {})
    for host, host_data in results.items():
        if isinstance(host_data, dict):
            if "gui" in host_data:
                ports = host_data.get("gui", {}).get("ports", [])
            elif "ports" in host_data:
                ports = host_data.get("ports", [])
            else:
                ports = []
            
            for port in ports:
                cves = port.get("cves", [])
                vuln_count += len(cves)

print(f'Total vulnerabilities: {vuln_count}')
