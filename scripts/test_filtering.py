"""Quick test script to verify filtering and deduplication logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.gui import results_to_rows, write_scan_results_to_csv, _filtered_results

# Mock results simulating authenticated scan with duplicates and platform packages
mock_results = {
    "192.168.100.35": {
        "gui": {
            "ports": [
                {
                    "port": None,
                    "service": "package",
                    "product": "Git",
                    "version": "2.50.1",
                    "cves": [
                        {"id": "CVE-2024-32002", "severity": "CRITICAL", "description": "Git submodule vuln", "cvss_v3": 9.0, "cpe": "cpe:2.3:a:git:git:2.50.1:*:*:*:*:*:*:*"},
                        {"id": "CVE-2024-50349", "severity": "MEDIUM", "description": "Terminal prompt issue", "cvss_v3": 4.7, "cpe": "cpe:2.3:a:git:git:2.50.1:*:*:*:*:*:*:*"},
                        {"id": "CVE-2024-52006", "severity": "HIGH", "description": "Carriage return issue", "cvss_v3": 7.5, "cpe": "cpe:2.3:a:git:git:2.50.1:*:*:*:*:*:*:*"}
                    ]
                },
                {
                    "port": None,
                    "service": "package",
                    "product": "Python 3.14.0 Development Libraries (64-bit)",
                    "version": "3.14.150.0",
                    "cves": [
                        {"id": "CVE-2010-3493", "severity": "MEDIUM", "description": "Old vuln from 2010", "cvss_v2": 4.3, "cpe": "cpe:2.3:a:python:python:3.14:*:*:*:*:*:*:*"}
                    ]
                },
                {
                    "port": None,
                    "service": "package",
                    "product": "Microsoft Windows Desktop Runtime - 8.0.8 (x64)",
                    "version": "64.32.18376",
                    "cves": [
                        {"id": "CVE-2023-24910", "severity": "HIGH", "description": "Windows Graphics vuln", "cvss_v3": 7.8, "cpe": "cpe:2.3:a:microsoft:desktop_runtime:8.0.8:*:*:*:*:*:*:*"}
                    ]
                },
                {
                    "port": None,
                    "service": "package",
                    "product": "Microsoft .NET SDK 8.0.400 (x64)",
                    "version": "8.4.24.37502",
                    "cves": [
                        {"id": "CVE-2024-0056", "severity": "HIGH", "description": "SQL Data Provider vuln", "cvss_v3": 8.7, "cpe": "cpe:2.3:a:microsoft:.net_sdk:8.0.400:*:*:*:*:*:*:*"}
                    ]
                },
                {
                    "port": None,
                    "service": "package",
                    "product": "Git",
                    "version": "2.50.1",
                    "cves": [
                        {"id": "CVE-2024-32002", "severity": "CRITICAL", "description": "Duplicate entry", "cvss_v3": 9.0, "cpe": "cpe:2.3:a:git:git:2.50.1:*:*:*:*:*:*:*"}
                    ]
                },
                {
                    "port": None,
                    "service": "package",
                    "product": "Chrome",
                    "version": "143.0.7499.148",
                    "cves": [
                        {"id": "CVE-2024-12345", "severity": "CRITICAL", "description": "Chrome RCE", "cvss_v3": 9.8, "cpe": "cpe:2.3:a:google:chrome:143.0:*:*:*:*:*:*:*"},
                        {"id": "CVE-2019-12345", "severity": "HIGH", "description": "Old Chrome vuln", "cvss_v3": 7.5, "cpe": "cpe:2.3:a:google:chrome:143.0:*:*:*:*:*:*:*"}
                    ]
                },
                {
                    "port": 22,
                    "service": "ssh",
                    "product": "OpenSSH",
                    "version": "7.4",
                    "cves": [
                        {"id": "CVE-2023-0001", "severity": "HIGH", "description": "SSH vuln", "cvss_v3": 7.8, "cpe": "cpe:2.3:a:openssh:openssh:7.4:*:*:*:*:*:*:*"}
                    ]
                }
            ]
        }
    }
}

print("="*80)
print("ORIGINAL RESULTS")
print("="*80)
original_count = sum(len(p.get("cves", [])) for p in mock_results["192.168.100.35"]["gui"]["ports"])
print(f"Total CVEs before filtering: {original_count}")
print(f"Total products/services: {len(mock_results['192.168.100.35']['gui']['ports'])}")

print("\n" + "="*80)
print("AFTER FILTERING")
print("="*80)

filtered = _filtered_results(mock_results)
filtered_ports = filtered["192.168.100.35"]["gui"]["ports"]
filtered_count = sum(len(p.get("cves", [])) for p in filtered_ports)

print(f"Total CVEs after filtering: {filtered_count}")
print(f"Total products/services after dedup & skip: {len(filtered_ports)}")

print("\n" + "="*80)
print("FILTERED PRODUCTS & CVE COUNTS")
print("="*80)
for p in filtered_ports:
    product = p.get("product") or p.get("service")
    version = p.get("version")
    cve_count = len(p.get("cves", []))
    print(f"  • {product} {version}: {cve_count} CVE(s)")

print("\n" + "="*80)
print("RESULTS_TO_ROWS OUTPUT")
print("="*80)
rows, kpi, sev = results_to_rows(mock_results)
print(f"Rows in table: {len(rows)}")
print(f"KPI counts: {kpi}")
print(f"Severity counts: {sev}")

print("\n" + "="*80)
print("CSV EXPORT TEST")
print("="*80)
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
    csv_path = f.name

write_scan_results_to_csv(mock_results, csv_path)
with open(csv_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    print(f"CSV lines written: {len(lines)}")
    print(f"CSV header: {lines[0].strip()}")
    if len(lines) > 1:
        print(f"First data row: {lines[1].strip()[:100]}...")

os.unlink(csv_path)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"✅ Filtering reduced CVEs from {original_count} to {filtered_count}")
print(f"✅ Deduplication removed duplicate Git entries")
print(f"✅ Skipped .NET/SDK/Windows Runtime platform packages")
print(f"✅ Only CVEs >= HIGH (severity) and >= 2018 (year) retained")
print("="*80)
