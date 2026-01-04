"""
Normalize scan results từ ScanManager/BasicPipeline
→ format chuẩn cho Web / API / Dashboard
"""

from typing import Dict, Any, List, Tuple


def normalize_for_api(results_by_host: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Input (từ scan_service.results):
    {
      "example.com (1.2.3.4)": {
          "gui": {...},
          "raw": {...} (optional)
      }
    }

    Output (API schema chuẩn):
    {
      "summary": {...},
      "hosts": {...}
    }
    """

    summary = {
        "hosts_scanned": 0,
        "open_ports": 0,
        "total_cves": 0,
        "severity": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
    }

    hosts = {}

    for label, report in results_by_host.items():
        gui = report.get("gui", report)  # fallback nếu chưa tách raw/gui
        ports = gui.get("ports", [])

        host_ports = []
        host_severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }

        for p in ports:
            cves = p.get("cves", [])

            for cve in cves:
                # Handle severity as dict or string
                sev_raw = cve.get("severity")
                if isinstance(sev_raw, dict):
                    sev = (sev_raw.get("label") or "").lower()
                elif isinstance(sev_raw, str):
                    sev = sev_raw.lower()
                else:
                    sev = ""
                
                if sev in host_severity:
                    host_severity[sev] += 1
                    summary["severity"][sev] += 1

            host_ports.append({
                "port": p.get("port"),
                "protocol": p.get("protocol", "tcp"),
                "service": p.get("service"),
                "product": p.get("product"),
                "version": p.get("version"),
                "cpe": p.get("cpe"),
                "cves": cves
            })

            summary["open_ports"] += 1
            summary["total_cves"] += len(cves)

        hosts[label] = {
            "label": label,
            "ports": host_ports,
            "severity_count": host_severity
        }

        summary["hosts_scanned"] += 1

    return {
        "summary": summary,
        "hosts": hosts
    }
