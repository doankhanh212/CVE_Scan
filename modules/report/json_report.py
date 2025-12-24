"""
JSON Report Generator (OpenVAS-style)
------------------------------------
Chuẩn hóa output scan thành JSON thống nhất cho:
- GUI
- Export file
- Admin Dashboard
- API tương lai

Schema tổng quát:

{
  "meta": {...},
  "hosts": [
    {
      "target": "1.2.3.4",
      "scan_type": "basic | authenticated",
      "services": [...],
      "vulnerabilities": [...]
    }
  ],
  "gui": {
    "ports": [...]
  }
}
"""

from typing import Dict, Any, List
import json
import datetime
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class JSONReport:
    """
    JSONReport
    ----------
    - Nhận raw scan data từ pipeline
    - Chuẩn hóa theo OpenVAS-style JSON
    - Sinh thêm GUI adapter (flattened)
    """

    def __init__(self):
        pass

    # ==================================================
    # PUBLIC
    # ==================================================
    def generate(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point cho pipeline

        scan_result:
        - Output của BasicPipeline.execute()
        - HOẶC AuthenticatedPipeline.execute()
        """

        report = {
            "meta": self._build_meta(),
            "hosts": []
        }

        try:
            host_block = self._build_host(scan_result)
            report["hosts"].append(host_block)
        except Exception as e:
            logger.error("Build host report failed: %s", e)

        # 🔥 GUI adapter (CHO GUI + CSV)
        report["gui"] = self._build_gui_adapter(report)

        return report

    # ==================================================
    # META
    # ==================================================
    def _build_meta(self) -> Dict[str, Any]:
        return {
            "generator": "CVE-Scanner-Enterprise",
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "schema": "openvas-compatible",
            "cvss_versions_supported": ["2.0", "3.0", "3.1", "4.0"]
        }

    # ==================================================
    # HOST
    # ==================================================
    def _build_host(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize host-level data
        """

        target = data.get("target", "N/A")
        scan_type = data.get("scan_type", "basic")

        services = self._build_services(data)
        vulns = self._build_vulnerabilities(data)

        return {
            "target": target,
            "scan_type": scan_type,
            "summary": self._build_summary(vulns),
            "services": services,
            "vulnerabilities": vulns
        }

    # ==================================================
    # SERVICES
    # ==================================================
    def _build_services(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chuẩn hóa service / package info
        """

        services = []

        # BasicPipeline style
        raw_services = data.get("services") or data.get("scan_data") or {}

        for name, info in raw_services.items():
            services.append({
                "name": name,
                "product": info.get("product"),
                "version": info.get("version"),
                "vendor": info.get("vendor"),
                "port": info.get("port"),
                "protocol": info.get("protocol"),
                "os": info.get("os")
            })

        return services

    # ==================================================
    # VULNERABILITIES
    # ==================================================
    def _build_vulnerabilities(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chuẩn hóa CVE list
        """

        vulns: List[Dict[str, Any]] = []

        raw_vulns = data.get("vulnerabilities") or {}

        for name, block in raw_vulns.items():
            cpe = block.get("cpe")
            info = block.get("info", {})
            cves = block.get("cves", [])

            for cve in cves:
                vulns.append({
                    "cve_id": cve.get("id"),
                    "service": name,
                    "cpe": cpe,
                    "description": cve.get("description", {}).get("full"),
                    "severity": cve.get("severity"),
                    "cvss4": cve.get("cvss4"),
                    "references": cve.get("references"),
                    "source": cve.get("source"),
                    "evidence": {
                        "product": info.get("product"),
                        "version": info.get("version"),
                        "os": info.get("os")
                    }
                })

        return vulns

    # ==================================================
    # SUMMARY
    # ==================================================
    def _build_summary(self, vulns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Tổng hợp severity giống OpenVAS
        """

        summary = {
            "total": len(vulns),
            "by_severity": {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "INFO": 0
            }
        }

        for v in vulns:
            sev = (
                v.get("severity", {})
                .get("label", "INFO")
            )
            if sev not in summary["by_severity"]:
                sev = "INFO"
            summary["by_severity"][sev] += 1

        return summary

    # ==================================================
    # GUI ADAPTER (CỰC KỲ QUAN TRỌNG)
    # ==================================================
    def _build_gui_adapter(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert OpenVAS-style JSON → GUI-friendly structure

        Output:
        {
          "ports": [
            {
              "port": int,
              "service": str,
              "version": str,
              "cves": [...]
            }
          ]
        }
        """

        ports: List[Dict[str, Any]] = []

        for host in report.get("hosts", []):
            # map service name -> service info
            service_map = {s["name"]: s for s in host.get("services", [])}

            # gather CVEs by service
            cves_by_service: Dict[str, List[Dict[str, Any]]] = {}
            for vuln in host.get("vulnerabilities", []):
                svc_name = vuln.get("service") or ""
                svc = service_map.get(svc_name, {})

                sev = vuln.get("severity") or {}
                cvss_v2 = sev.get("score") if sev.get("version") == "2.0" else None
                cvss_v3 = sev.get("score") if sev.get("version") in ("3.0", "3.1") else None
                cvss_v4 = (vuln.get("cvss4") or {}).get("score")

                cves_by_service.setdefault(svc_name, []).append({
                    "id": vuln.get("cve_id"),
                    "description": vuln.get("description"),
                    "severity": vuln.get("severity"),
                    "cvss_v2": cvss_v2,
                    "cvss_v3": cvss_v3,
                    "cvss_v4": cvss_v4,
                    "cpe": vuln.get("cpe")
                })

            # emit all services, even if no CVEs
            for svc_name, svc in service_map.items():
                ports.append({
                    "port": svc.get("port"),
                    "service": svc_name,
                    "product": svc.get("product"),
                    "version": svc.get("version"),
                    "cves": cves_by_service.get(svc_name, [])
                })

        return {
            "ports": ports
        }


# ==================================================
# Optional helper (export to file)
# ==================================================
def export_json(report: Dict[str, Any], path: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
