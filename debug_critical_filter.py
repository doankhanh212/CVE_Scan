import json
import glob

# Find latest scan file
scan_files = glob.glob("data/scans/scan_*.json")
if not scan_files:
    print("No scan files found!")
    exit()

latest_scan = max(scan_files, key=lambda x: x)
print(f"Analyzing: {latest_scan}\n")

with open(latest_scan, 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get("results", {})
print(f"Total hosts: {len(results)}")

critical_count = 0
high_count = 0
severity_formats = set()

# Sample first 5 critical CVEs
critical_samples = []

for host_label, host_data in results.items():
    ports = host_data.get("ports", [])
    for port_info in ports:
        cves_list = port_info.get("cves", [])
        for cve in cves_list:
            severity = cve.get("severity", {})
            
            # Track all severity formats
            if isinstance(severity, dict):
                severity_label = severity.get("label", "unknown")
                severity_formats.add(f"dict:label={severity_label}")
            else:
                severity_label = str(severity)
                severity_formats.add(f"string:{severity_label}")
            
            # Count
            if severity_label.upper() == "CRITICAL":
                critical_count += 1
                if len(critical_samples) < 5:
                    critical_samples.append({
                        "id": cve.get("id"),
                        "severity": severity,
                        "host": host_label,
                        "port": port_info.get("port")
                    })
            elif severity_label.upper() == "HIGH":
                high_count += 1

print(f"\n=== Severity Count ===")
print(f"CRITICAL: {critical_count}")
print(f"HIGH: {high_count}")
print(f"Total (C+H): {critical_count + high_count}")

print(f"\n=== Severity Formats Found ===")
for fmt in sorted(severity_formats):
    print(f"  - {fmt}")

print(f"\n=== Critical CVE Samples ===")
for sample in critical_samples:
    print(f"  {sample['id']} @ {sample['host']}:{sample['port']}")
    print(f"    severity: {sample['severity']}")
