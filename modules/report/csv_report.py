import csv
from typing import Dict, Any


def export_csv(report: Dict[str, Any], path: str) -> bool:
    """Export JSONReport-style report to CSV.

    CSV columns: Host, Port, Service, Version, CVE ID, Severity, Score, Description
    """
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Include Device column (may be empty when exporting from JSONReport)
            writer.writerow(["Host", "Device", "Port", "Service", "Version", "CVE ID", "Severity", "Score", "Description"])

            for host in report.get("hosts", []):
                target = host.get("target") or ""
                # build service map by name
                service_map = {s.get("name"): s for s in host.get("services", [])}

                for v in host.get("vulnerabilities", []):
                    service_name = v.get("service")
                    svc = service_map.get(service_name, {})

                    port = svc.get("port")
                    service = service_name
                    version = svc.get("version")
                    cve_id = v.get("cve_id")

                    sev = v.get("severity") or {}
                    if isinstance(sev, dict):
                        sev_label = sev.get("label")
                        sev_score = sev.get("score")
                    else:
                        sev_label = sev
                        sev_score = None

                    description = v.get("description") or ""

                    # JSONReport does not carry device name; leave empty
                    writer.writerow([
                        target,
                        "",
                        port,
                        service,
                        version,
                        cve_id,
                        sev_label,
                        sev_score,
                        description
                    ])
        return True
    except Exception:
        return False
