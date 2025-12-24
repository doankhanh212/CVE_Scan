from typing import Dict, Any
import logging

from modules.scanners.authenticated_scanner import AuthenticatedScanner
from modules.cve.cpe_builder import build_cpe
from modules.cve.cve_matcher import CVEMatcher
from modules.report.json_report import JSONReport

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AuthenticatedPipeline:
    """
    AuthenticatedPipeline (OpenVAS-style)
    ------------------------------------
    SSH / WinRM → software → CPE → CVE
    """

    def __init__(self, config: dict, logger_cb=None):
        self.config = config
        self.logger = logger_cb or (lambda msg, lvl="INFO": None)

        # 🔥 Pass logger_cb tới AuthenticatedScanner
        self.scanner = AuthenticatedScanner(logger=self.logger)

        self.matcher = CVEMatcher(
            api_key=config.get("nvd_api_key"),
            local_db_path=(config.get("local_db_path") if config.get("use_local_db") else None)
        )

        # Prefer offline CPE heuristics if using local DB
        self.cpe_use_remote = not bool(config.get("use_local_db", False))

        self.reporter = JSONReport()

        self.logger("AuthenticatedPipeline initialized", "SYSTEM")

    # ==================================================
    # PUBLIC
    # ==================================================
    def execute(
        self,
        target: str,
        auth: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:

        if not auth:
            raise ValueError("Authenticated scan requires auth credentials")

        self.logger(f"Start AUTHENTICATED scan for {target}", "INFO")

        raw_data = self.scanner.scan_host(
            target=target,
            auth=auth
        )

        self.logger(f"[PIPELINE] Raw data received: {bool(raw_data)}", "INFO")
        if raw_data:
            self.logger(f"[PIPELINE] Raw data keys: {raw_data.keys()}", "INFO")
            if "software" in raw_data:
                self.logger(f"[PIPELINE] Software count: {len(raw_data.get('software', []))}", "INFO")
            if "os" in raw_data:
                self.logger(f"[PIPELINE] OS info: {raw_data.get('os')}", "INFO")

        if not raw_data:
            self.logger("Authenticated scan returned empty result", "WARN")
            return {}

        normalized = self._normalize_scan_data(
            target=target,
            scan_data=raw_data
        )

        return self.reporter.generate(normalized)

    # ==================================================
    # INTERNAL
    # ==================================================
    def _normalize_scan_data(
        self,
        target: str,
        scan_data: Dict[str, Any]
    ) -> Dict[str, Any]:

        services: Dict[str, Any] = {}
        vulnerabilities: Dict[str, Any] = {}

        os_info = scan_data.get("os", {})
        packages = scan_data.get("software", [])

        # ==========================================
        # 1️⃣ OS-level CVE matching
        # ==========================================
        if os_info and os_info.get("os_name"):
            os_name = os_info.get("os_name", "").strip()
            os_version = os_info.get("os_version", "").strip()
            
            if os_name:
                os_cpe = build_cpe(os_name, os_version if os_version else None, use_remote=self.cpe_use_remote)
                
                if os_cpe and os_cpe != "N/A":
                    cves = self.matcher.match_by_cpe(os_cpe)
                    if cves:
                        self.logger(f"[{target}] [AUTH] OS {os_name} {os_version} → found {len(cves)} CVE(s)", "WARN")
                        vulnerabilities["os"] = {
                            "cpe": os_cpe,
                            "info": os_info,
                            "cves": cves
                        }

        # ==========================================
        # 2️⃣ Package-level CVE matching
        # ==========================================
        for item in packages:
            try:
                # Unpack (name, version) tuple from SSH/WinRM scanner
                name, version = item
            except (ValueError, TypeError):
                continue

            name = (name or "").strip()
            version = (version or "").strip()
            
            if not name:
                continue

            service_key = f"{name}:{version}" if version else name

            services[service_key] = {
                "product": name,
                "version": version,
                "type": "package"
            }

            # Build CPE from package name + version
            cpe = build_cpe(name, version if version else None, use_remote=self.cpe_use_remote)
            if not cpe or cpe == "N/A":
                continue

            # Match CVE using CPE
            cves = self.matcher.match_by_cpe(cpe)
            
            if cves:
                # Count severities for logging
                sev_counts = {}
                for c in cves:
                    lbl = (c.get("severity") if isinstance(c.get("severity"), str) 
                           else (c.get("severity", {}).get("label") if c.get("severity") else "INFO"))
                    sev_counts[lbl] = sev_counts.get(lbl, 0) + 1
                
                parts = [f"{v} {k}" for k, v in sev_counts.items()]
                self.logger(f"[{target}] [AUTH] {name} {version} → {' | '.join(parts)}", "WARN")
                
                vulnerabilities[service_key] = {
                    "cpe": cpe,
                    "info": services[service_key],
                    "cves": cves
                }

        # ==========================================
        # 3️⃣ Summary logging
        # ==========================================
        total_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for v in vulnerabilities.values():
            for c in v.get("cves", []):
                lbl = (c.get("severity") if isinstance(c.get("severity"), str) 
                       else (c.get("severity", {}).get("label") if c.get("severity") else "INFO"))
                if lbl in total_counts:
                    total_counts[lbl] += 1

        msg_parts = []
        for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            if total_counts[lvl]:
                msg_parts.append(f"{total_counts[lvl]} {lvl}")
        if msg_parts:
            self.logger(f"[{target}] [AUTH] Summary: {' | '.join(msg_parts)}", "WARN")

        return {
            "target": target,
            "scan_type": "authenticated",
            "services": services,
            "vulnerabilities": vulnerabilities
        }
