from typing import Dict, Any, List
import logging

from modules.scanners.nmap_scanner import NmapScanner
from modules.scanners.rustscan_scanner import RustScanScanner
from modules.cve.cpe_builder import build_cpe
from modules.cve.cve_matcher import CVEMatcher
from modules.report.json_report import JSONReport

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BasicPipeline:
    """
    BasicPipeline (Unauthenticated Scan OpenVAS-style)
    ---------------------------------------------------
    Flow:
    1. RustScan → discover open ports
    2. Nmap -sV → service detection
    3. Build CPE (heuristic-aware)
    4. Match CVE
    5. Normalize output
    """

    def __init__(self, config: dict, logger=None, progress_cb=None):
        self.config = config
        self.logger = logger or (lambda msg, lvl="INFO": None)
        self.progress_cb = progress_cb

        self.logger("BasicPipeline initialized", "SYSTEM")

        self.rustscan = RustScanScanner(
            timeout=config.get("rustscan_timeout", 1500),
            ulimit=config.get("rustscan_ulimit", 5000)
        )

        self.nmap = NmapScanner(
            timeout=config.get("nmap_timeout", 60),
            logger=self.logger
        )

        self.matcher = CVEMatcher(
            api_key=config.get("nvd_api_key"),
            local_db_path=(config.get("local_db_path") if config.get("use_local_db") else None)
        )

        # When using a local DB we prefer offline CPE heuristics (no NVD API calls)
        self.cpe_use_remote = not bool(config.get("use_local_db", False))

        self.reporter = JSONReport()

    # ==================================================
    # PUBLIC
    # ==================================================
    def execute(self, target: str) -> Dict[str, Any]:
        # Host start
        self.logger(f"🖥️ [SCAN] Host: {target}", "SYSTEM")

        # 1️⃣ RustScan
        self.logger(f"ℹ️ [{target}] Quét port nhanh (RustScan)", "INFO")
        ports = self._discover_ports(target)
        if ports:
            port_list = ", ".join(str(p) for p in sorted(ports))
            self.logger(f"ℹ️ [{target}] Phát hiện {len(ports)} port mở: {port_list}", "INFO")
        else:
            self.logger(f"ℹ️ [{target}] Không phát hiện port mở", "INFO")
            # Early exit: no ports found, skip Nmap and CVE matching
            self.logger(f"[SCAN] Hoàn tất host: {target} (no services detected)", "SUCCESS")
            return self.reporter.generate({"services": {}, "vulnerabilities": {}})

        # 2️⃣ Nmap (only run if RustScan found ports)
        self.logger(f"ℹ️ [{target}] Quét dịch vụ (Nmap)", "INFO")
        scan_data = self.nmap.scan_host(target=target, ports=ports)

        # After Nmap: produce nice service summary log
        services = []
        for p, i in (scan_data or {}).items():
            prod = i.get("product") or i.get("service") or ""
            ver = i.get("version") or ""
            services.append((p, prod, ver))

        if services:
            # Build tree formatted message
            lines = [f"ℹ️ [{target}] Dịch vụ phát hiện:"]
            for idx, (port, prod, ver) in enumerate(sorted(services)):
                prefix = "   └─" if idx == len(services) - 1 else "   ├─"
                lines.append(f"{prefix} {port}/tcp → {prod} {ver}".rstrip())
            self.logger("\n".join(lines), "INFO")
        else:
            # keep quiet if no services
            pass
        # 3️⃣ Normalize + CPE + CVE
        normalized = self._normalize_scan_data(
            target=target,
            scan_data=scan_data or {}
        )

        # Host summary by severity
        total_cves = 0
        sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for s in normalized.get("vulnerabilities", {}).values():
            for c in s.get("cves", []):
                label = (c.get("severity") if isinstance(c.get("severity"), str) else (c.get("severity", {}).get("label") if c.get("severity") else "INFO"))
                if label in sev_counts:
                    sev_counts[label] += 1
                total_cves += 1

        if total_cves > 0:
            # summarize critical/high first
            msg_parts = []
            for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                if sev_counts[lvl]:
                    msg_parts.append(f"{sev_counts[lvl]} {lvl}")
            self.logger(f"[{target}] Mapping CPE → CVE", "INFO")
            self.logger(f"[{target}] Phát hiện {' | '.join(msg_parts)}", "WARN")
        else:
            self.logger(f"[{target}] Mapping CPE → CVE — không tìm thấy CVE", "INFO")

        # Host complete
        self.logger(f"[SCAN] Hoàn tất host: {target}", "SUCCESS")

        return self.reporter.generate(normalized)

    # ==================================================
    # INTERNAL
    # ==================================================
    def _discover_ports(self, target: str) -> List[int]:
        try:
            self.logger("Running RustScan", "INFO")
            ports = self.rustscan.scan(target)
            if ports:
                self.logger(f"RustScan found {len(ports)} open ports", "INFO")
                return ports
        except Exception as e:
            self.logger(f"RustScan failed: {e}", "WARN")

        return []

    def _normalize_scan_data(
        self,
        target: str,
        scan_data: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:

        services: Dict[str, Any] = {}
        vulnerabilities: Dict[str, Any] = {}

        # ==========================================
        # Process each service detected by Nmap
        # ==========================================
        for port, info in scan_data.items():
            service = (info.get("service") or "").lower()
            product = (info.get("product") or "").strip()
            version = (info.get("version") or "").strip()

            service_name = f"{info.get('service')}:{port}"

            services[service_name] = {
                "port": port,
                "protocol": info.get("protocol", "tcp"),
                "product": product,
                "version": version,
                "os": info.get("os")
            }

            # ==================================================
            # 1️⃣ BUILD CPE from Nmap service + version
            # ==================================================
            # Simple flow: 
            # - If product is empty → skip (no CVE to match)
            # - Otherwise → build CPE from product + version
            
            if not product:
                self.logger(
                    f"Skipping port {port}/{service}: no product detected",
                    "INFO"
                )
                continue

            cpe = build_cpe(product, version if version else None, use_remote=self.cpe_use_remote)

            if not cpe or cpe == "N/A":
                self.logger(
                    f"Could not build CPE for {product} {version}",
                    "WARN"
                )
                continue

            # ==================================================
            # 2️⃣ MATCH CVE using CPE
            # ==================================================
            cves = self.matcher.match_by_cpe(cpe)
            
            if cves:
                self.logger(
                    f"[{target}] {product} {version} → found {len(cves)} CVE(s)",
                    "INFO"
                )
            
            vulnerabilities[service_name] = {
                "cpe": cpe,
                "info": services[service_name],
                "cves": cves
            }

        return {
            "target": target,
            "scan_type": "basic",
            "services": services,
            "vulnerabilities": vulnerabilities
        }
