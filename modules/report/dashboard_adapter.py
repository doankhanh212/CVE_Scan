"""
Dashboard Adapter (OpenVAS-style)
--------------------------------
Chuyển JSONReport schema → data dễ render cho HTML dashboard (thuần HTML/CSS)

Input: JSON output từ JSONReport.generate()
Output: dict đơn giản cho Jinja / Flask / FastAPI / GUI HTML
"""

from typing import Dict, Any, List
import datetime


class DashboardAdapter:
    """
    DashboardAdapter
    ----------------
    - Không scan
    - Không xử lý CVE
    - Chỉ đọc JSONReport schema và transform
    """

    def __init__(self, report: Dict[str, Any]):
        self.report = report

    # ==================================================
    # PUBLIC
    # ==================================================
    def build(self) -> Dict[str, Any]:
        """
        Entry point cho dashboard
        """

        meta = self.report.get("meta", {})
        hosts = self.report.get("hosts", [])

        return {
            "generated_at": meta.get("generated_at"),
            "generator": meta.get("generator"),
            "schema": meta.get("schema"),
            "summary": self._build_global_summary(hosts),
            "hosts": [self._build_host(h) for h in hosts]
        }

    # ==================================================
    # GLOBAL SUMMARY
    # ==================================================
    def _build_global_summary(self, hosts: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {
            "hosts": len(hosts),
            "vulnerabilities": 0,
            "by_severity": {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "INFO": 0
            }
        }

        for host in hosts:
            host_summary = host.get("summary", {})
            summary["vulnerabilities"] += host_summary.get("total", 0)

            for sev, count in host_summary.get("by_severity", {}).items():
                if sev in summary["by_severity"]:
                    summary["by_severity"][sev] += count

        return summary

    # ==================================================
    # HOST
    # ==================================================
    def _build_host(self, host: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "target": host.get("target"),
            "scan_type": host.get("scan_type"),
            "summary": host.get("summary", {}),
            "services": self._build_services(host.get("services", [])),
            "vulnerabilities": self._build_vulnerabilities(host.get("vulnerabilities", []))
        }

    # ==================================================
    # SERVICES
    # ==================================================
    def _build_services(self, services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []

        for svc in services:
            result.append({
                "name": svc.get("name"),
                "product": svc.get("product"),
                "version": svc.get("version"),
                "port": svc.get("port"),
                "protocol": svc.get("protocol"),
                "os": svc.get("os")
            })

        return result

    # ==================================================
    # VULNERABILITIES
    # ==================================================
    def _build_vulnerabilities(self, vulns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []

        for v in vulns:
            sev = v.get("severity", {})
            cvss4 = v.get("cvss4", {})

            result.append({
                "cve_id": v.get("cve_id"),
                "service": v.get("service"),
                "severity_label": sev.get("label", "INFO"),
                "severity_score": sev.get("score"),
                "severity_version": sev.get("version"),
                "vector": sev.get("vector"),
                "cvss4_score": cvss4.get("score"),
                "description": self._shorten(v.get("description", {})),
                "references": v.get("references", [])
            })

        return result

    # ==================================================
    # UTILS
    # ==================================================
    def _shorten(self, desc: Dict[str, Any], limit: int = 160) -> str:
        if not desc:
            return ""
        text = desc.get("short") or desc.get("full") or ""
        return text[:limit]
