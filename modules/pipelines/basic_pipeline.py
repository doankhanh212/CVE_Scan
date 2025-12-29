from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import socket
import ipaddress

from modules.scanners.nmap_scanner import NmapScanner
from modules.scanners.rustscan_scanner import RustScanScanner
from modules.discovery.asset_discovery import AssetDiscovery
from modules.discovery.host_discovery import HostDiscovery
from modules.cve.cpe_builder import build_cpe
from modules.cve.cve_matcher import CVEMatcher
from modules.report.json_report import JSONReport

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BasicPipeline:
    """
    BasicPipeline (Unauthenticated Scan OpenVAS-style)
    ---------------------------------------------------
    NEW Flow (v2):
    0. Asset Discovery: Hostname → DNS → WHOIS → ASN → Reverse DNS
    1. RustScan → discover open ports
    2. Nmap -sV → service detection
    3. Build CPE (heuristic-aware)
    4. Match CVE
    5. Normalize output
    """

    def __init__(self, config: dict, logger=None, progress_cb=None, host_result_cb=None, stop_event=None):
        self.config = config
        self.logger = logger or (lambda msg, lvl="INFO": None)
        self.progress_cb = progress_cb
        # Optional: emit per-IP results up to ScanManager/GUI
        self.host_result_cb = host_result_cb
        self.stop_event = stop_event
        # Max concurrent IP scans (RustScan+Nmap per IP)
        self.max_concurrent_scans = int(config.get("max_concurrent_scans", 4))
        # Cap CVEs per service to avoid overwhelming outputs on broad CPEs
        self.cve_max_per_service = int(config.get("cve_max_per_service", 50))
        # Year window to keep CVEs recent (e.g., last 10 years). 0/None disables.
        self.cve_year_window = int(config.get("cve_year_window", 10))
        # Toggle CIDR-expanded IP scanning and cap overall scan IPs
        self.scan_cidr_assets = bool(config.get("scan_cidr_expansion", False))
        self.max_scan_ips = int(config.get("max_scan_ips", 64))
        # Adaptive policy: scan all alive if small CIDR (e.g., /24)
        self.scan_policy = str(config.get("scan_policy", "fixed")).lower()
        self.adaptive_full_scan_prefixlen = int(config.get("adaptive_full_scan_prefixlen", 24))

        self.logger("BasicPipeline initialized", "SYSTEM")

        # NEW: Asset discovery
        self.asset_discovery = AssetDiscovery(
            logger=self.logger,
            progress_cb=self.progress_cb,
            max_cidr_ips=config.get("max_cidr_ips", 1024),
            enable_reverse_dns_pre_scan=bool(config.get("reverse_dns_pre_scan", False))
        )

        # NEW: Host discovery (PING to filter live hosts)
        self.host_discovery = HostDiscovery(
            timeout=config.get("ping_timeout", 1),
            retries=config.get("ping_retries", 3),
            workers=config.get("ping_workers", 100),
            logger=self.logger,
            progress_cb=self.progress_cb
        )

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
            local_db_path=(config.get("local_db_path") if config.get("use_local_db") else None),
            year_window=self.cve_year_window
        )

        # When using a local DB we prefer offline CPE heuristics (no NVD API calls)
        self.cpe_use_remote = not bool(config.get("use_local_db", False))

        self.reporter = JSONReport()

    # ==================================================
    # PUBLIC
    # ==================================================
    def execute_batch(self, targets: List[str], input_mode: str = None) -> Dict[str, Any]:
        """
        Execute scan for multiple targets. Expands CIDR if present.
        Returns multi-host result with per_host_results list.
        
        input_mode: "IP/CIDR" | "Hostname (Domain)" | None
          - "IP/CIDR": Skip AssetDiscovery, go directly to ping→scan
          - "Hostname (Domain)": Use AssetDiscovery (DNS→WHOIS→CIDR expansion)
          - None: Use AssetDiscovery (default for backward compatibility)
        """
        all_per_host_results = []
        all_aggregate = {"services": {}, "vulnerabilities": {}}
        
        # ============================================================
        # Check Input Mode routing
        # ============================================================
        if input_mode == "IP/CIDR":
            self.logger("🔧 Input Mode: IP/CIDR → Skipping AssetDiscovery (direct ping→scan)", "INFO")
            # Expand CIDR targets to individual IPs
            expanded_ips = []
            for target in targets:
                if "/" in target:
                    # CIDR notation
                    try:
                        network = ipaddress.ip_network(target, strict=False)
                        ips = [str(ip) for ip in network.hosts()]
                        self.logger(f"🌐 Expanded CIDR {target} → {len(ips)} IPs", "INFO")
                        expanded_ips.extend(ips)
                    except Exception as e:
                        self.logger(f"❌ Failed to expand CIDR {target}: {e}", "ERROR")
                else:
                    # Plain IP
                    expanded_ips.append(target)
            
            # 1️⃣ Ping check to find alive hosts (use threaded ping for Windows stability)
            self.logger(f"🏓 Ping check for {len(expanded_ips)} IP(s)", "INFO")
            try:
                alive_ips = self.host_discovery.discover_ping(expanded_ips)
            except AttributeError:
                # Fallback if method not available
                alive_ips = self.host_discovery.discover(expanded_ips)
            
            if not alive_ips:
                self.logger("❌ No alive hosts found", "ERROR")
                return {
                    "multi_host": True,
                    "per_host_results": [],
                    "aggregate": all_aggregate
                }
            
            # 2️⃣ Scan alive IPs
            self.logger(f"✅ Found {len(alive_ips)} alive host(s)", "SUCCESS")
            per_host_results = self._scan_hosts(alive_ips)
            
            return {
                "multi_host": True,
                "per_host_results": per_host_results,
                "aggregate": all_aggregate
            }
        
        # ============================================================
        # Standard path: process all targets through asset discovery
        # ============================================================
        self.logger("🔧 Input Mode: Hostname → Using AssetDiscovery (DNS→WHOIS→CIDR)", "INFO")
        
        # 0️⃣ Asset Discovery for all targets
        self.logger(f"ℹ️ Phát hiện tài sản cho {len(targets)} target(s)", "INFO")
        assets = self.asset_discovery.discover(targets)
        
        # Determine policy
        full_scan = False
        self.logger(f"[Policy] Configured scan_policy={self.scan_policy}", "INFO")
        
        if self.scan_policy == "cidr_full":
            full_scan = True
            self.logger("[Policy] CIDR full-scan enabled → include CIDR and scan all alive hosts", "INFO")
        elif self.scan_policy == "adaptive":
            try:
                prefixlens = []
                for ip, a in assets.items():
                    if a.cidr:
                        try:
                            prefixlens.append(ipaddress.ip_network(a.cidr, strict=False).prefixlen)
                        except Exception:
                            pass
                if prefixlens and min(prefixlens) >= self.adaptive_full_scan_prefixlen:
                    full_scan = True
                    self.logger(f"[Adaptive] Detected small CIDR (/{min(prefixlens)}) → scan all alive hosts", "INFO")
            except Exception:
                pass

        include_cidr = self.scan_cidr_assets or full_scan
        cap_for_filter = None if full_scan else self.max_scan_ips
        self.logger(f"[Policy] include_cidr={include_cidr}, full_scan={full_scan}, cap={cap_for_filter}", "INFO")

        # Filter for scan
        scan_ips = self.asset_discovery.filter_for_scan(
            assets,
            include_cidr=include_cidr,
            max_scan_ips=cap_for_filter
        )
        
        if not scan_ips:
            self.logger("No IPs to scan after filtering", "WARN")
            return self.reporter.generate({"services": {}, "vulnerabilities": {}})

        # 0B️⃣ Ping all targets at once
        self.logger(f"ℹ️ Kiểm tra tính sống của {len(scan_ips)} IP(s)...", "INFO")
        self.host_discovery.discover(scan_ips)
        
        # Get live hosts
        alive_ips = []
        while not self.host_discovery.alive_queue.empty():
            alive_ips.append(self.host_discovery.alive_queue.get())

        # Notify GUI of alive count
        try:
            if self.progress_cb:
                self.progress_cb("ping", 100, {"alive": len(alive_ips)})
        except Exception:
            pass
        
        if not alive_ips:
            self.logger("No alive hosts after ping", "WARN")
            return self.reporter.generate({"services": {}, "vulnerabilities": {}})
        
        # Cap alive IPs if needed
        if not full_scan and self.max_scan_ips and len(alive_ips) > self.max_scan_ips:
            try:
                alive_ips.sort(key=lambda ip: assets[ip].scan_priority if ip in assets else 100)
            except Exception:
                pass
            alive_ips = alive_ips[:self.max_scan_ips]
            self.logger(f"[Adaptive] Alive IPs capped to {len(alive_ips)} by max_scan_ips", "INFO")

        # ============================================================
        # SCAN ALL ALIVE IPs (concurrently) - Common for both paths
        # ============================================================
        total = max(1, len(alive_ips))
        completed = 0

        def _scan_one(scan_ip: str) -> Tuple[str, Dict[str, Any]]:
            try:
                display_label = scan_ip
                hostname_hint = None
                
                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}

                if scan_ip in assets:
                    asset = assets[scan_ip]
                    try:
                        if asset.hostnames:
                            host_alias = sorted(asset.hostnames)[0]
                            hostname_hint = host_alias
                            display_label = f"{host_alias} ({scan_ip})"
                    except Exception:
                        display_label = scan_ip
                    
                    self.logger(
                        f"ℹ️ [{scan_ip}] → {scan_ip} (confidence: {asset.confidence:.2f}, ASN: {asset.asn}, CIDR: {asset.cidr})",
                        "INFO",
                    )

                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}

                # 1️⃣ RustScan
                self.logger(f"ℹ️ [{scan_ip}] Quét port nhanh (RustScan)", "INFO")
                ports = self._discover_ports(scan_ip)
                if not ports:
                    self.logger(f"ℹ️ [{scan_ip}] Không phát hiện port mở", "INFO")
                    normalized_empty = {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                    return scan_ip, normalized_empty

                port_list = ", ".join(str(p) for p in sorted(ports))
                self.logger(f"ℹ️ [{scan_ip}] Phát hiện {len(ports)} port mở: {port_list}", "INFO")

                # 2️⃣ Nmap
                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                self.logger(f"ℹ️ [{scan_ip}] Quét dịch vụ (Nmap)", "INFO")
                scan_data = self.nmap.scan_host(target=scan_ip, ports=ports)

                # Service summary
                services = []
                for p, i in (scan_data or {}).items():
                    prod = i.get("product") or i.get("service") or ""
                    ver = i.get("version") or ""
                    services.append((p, prod, ver))
                if services:
                    lines = [f"ℹ️ [{scan_ip}] Dịch vụ phát hiện:"]
                    for idx2, (port, prod, ver) in enumerate(sorted(services)):
                        prefix = "   └─" if idx2 == len(services) - 1 else "   ├─"
                        lines.append(f"{prefix} {port}/tcp → {prod} {ver}".rstrip())
                    self.logger("\n".join(lines), "INFO")

                normalized = self._normalize_scan_data(target=scan_ip, scan_data=scan_data or {})
                # Post-scan: attempt reverse DNS
                if not hostname_hint:
                    try:
                        hostname = socket.gethostbyaddr(scan_ip)[0]
                        if hostname:
                            hostname_hint = hostname
                            display_label = f"{hostname} ({scan_ip})"
                    except (socket.herror, socket.timeout, Exception):
                        pass
                normalized["target_label"] = display_label
                return display_label, normalized
            except Exception as e:
                self.logger(f"[ERROR] Scan IP {scan_ip} failed: {e}", "ERROR")
                empty = {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                empty["target_label"] = display_label
                return display_label, empty

        # Run concurrent scans
        with ThreadPoolExecutor(max_workers=self.max_concurrent_scans) as executor:
            futures = {executor.submit(_scan_one, ip): ip for ip in alive_ips}
            for fut in as_completed(futures):
                scan_ip = futures[fut]
                try:
                    label, normalized = fut.result()
                except Exception as e:
                    self.logger(f"[ERROR] Future for {scan_ip} failed: {e}", "ERROR")
                    label, normalized = scan_ip, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}

                # Merge into aggregate
                all_aggregate["services"].update(normalized.get("services", {}))
                all_aggregate["vulnerabilities"].update(normalized.get("vulnerabilities", {}))

                # Emit per-IP result to GUI
                if self.host_result_cb:
                    try:
                        per_host_report = self.reporter.generate(normalized)
                        self.host_result_cb(scan_ip, per_host_report)
                        all_per_host_results.append((label, per_host_report))
                    except Exception:
                        pass

                # Progress update per completed IP
                completed += 1
                if self.progress_cb:
                    try:
                        percent = int(completed * 100 / total)
                        self.progress_cb("scan", percent, f"Scanning {label}")
                    except Exception:
                        pass

                # Host summary by severity
                total_cves = 0
                sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
                for s in normalized.get("vulnerabilities", {}).values():
                    for c in s.get("cves", []):
                        label_sev = (c.get("severity") if isinstance(c.get("severity"), str) else (c.get("severity", {}).get("label") if c.get("severity") else "INFO"))
                        if label_sev in sev_counts:
                            sev_counts[label_sev] += 1
                        total_cves += 1

                if total_cves > 0:
                    msg_parts = []
                    for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                        if sev_counts[lvl]:
                            msg_parts.append(f"{sev_counts[lvl]} {lvl}")
                    self.logger(f"[{scan_ip}] Mapping CPE → CVE", "INFO")
                    self.logger(f"[{scan_ip}] Phát hiện {' | '.join(msg_parts)}", "WARN")
                else:
                    self.logger(f"[{scan_ip}] Mapping CPE → CVE — không tìm thấy CVE", "INFO")
                
                self.logger(f"✅ [SCAN] Hoàn tất host: {label}", "SUCCESS")

        self.logger(f"✅ ✅ Hoàn tất quét {len(alive_ips)} host(s)", "SUCCESS")

        # Return multi-host result
        return {
            "multi_host": True,
            "per_host_results": all_per_host_results,
            "aggregate": self.reporter.generate(all_aggregate)
        }

    def execute(self, target: str) -> Dict[str, Any]:
        # Host start
        self.logger(f"🖥️ [SCAN] Host: {target}", "SYSTEM")

        # 0️⃣ NEW: Asset Discovery (Hostname → DNS → WHOIS → Reverse DNS)
        self.logger(f"ℹ️ [{target}] Phát hiện tài sản (DNS + WHOIS + ASN)", "INFO")
        assets = self.asset_discovery.discover([target])

        # Determine adaptive policy based on resolved IP CIDR(s)
        full_scan = False
        self.logger(f"[Policy] Configured scan_policy={self.scan_policy}", "INFO")
        
        if self.scan_policy == "cidr_full":
            full_scan = True
            self.logger("[Policy] CIDR full-scan enabled → include CIDR and scan all alive hosts", "INFO")
        elif self.scan_policy == "adaptive":
            try:
                # Resolve set: IPs obtained via DNS for this target
                resolved_ips = {ip for ip, a in assets.items() if "dns" in set(a.source)}
                prefixlens = []
                for ip, a in assets.items():
                    if ip in resolved_ips and a.cidr:
                        try:
                            import ipaddress
                            prefixlens.append(ipaddress.ip_network(a.cidr, strict=False).prefixlen)
                        except Exception:
                            pass
                # If any CIDR is small (>= /24), scan all alive hosts
                if prefixlens and max(prefixlens) >= self.adaptive_full_scan_prefixlen:
                    full_scan = True
                    self.logger(f"[Adaptive] Detected CIDR /{max(prefixlens)} → scan all alive hosts", "INFO")
            except Exception:
                pass

        include_cidr = self.scan_cidr_assets or full_scan
        cap_for_filter = None if full_scan else self.max_scan_ips
        self.logger(f"[Policy] include_cidr={include_cidr}, full_scan={full_scan}, cap={cap_for_filter}", "INFO")

        # Filter for scan (confidence >= 0.70) with CIDR + adaptive controls
        scan_ips = self.asset_discovery.filter_for_scan(
            assets,
            include_cidr=include_cidr,
            max_scan_ips=cap_for_filter
        )
        
        if not scan_ips:
            self.logger(f"[SCAN] Không có IP để quét (confidence quá thấp)", "WARN")
            return self.reporter.generate({"services": {}, "vulnerabilities": {}})

        # 0B️⃣ NEW: PING filter - only scan alive hosts
        self.logger(f"ℹ️ Kiểm tra tính sống của {len(scan_ips)} IP(s)...", "INFO")
        self.host_discovery.discover(scan_ips)
        
        # Get live hosts from discovery queue
        alive_ips = []
        while not self.host_discovery.alive_queue.empty():
            alive_ips.append(self.host_discovery.alive_queue.get())

        # Notify GUI of alive count right after ping completes
        try:
            if self.progress_cb:
                self.progress_cb("ping", 100, {"alive": len(alive_ips)})
        except Exception:
            pass
        
        if not alive_ips:
            self.logger(f"[SCAN] Không có IP sống (ping failed)", "WARN")
            return self.reporter.generate({"services": {}, "vulnerabilities": {}})
        
        # If not full-scan, cap alive IPs by priority
        if not full_scan and self.max_scan_ips and len(alive_ips) > self.max_scan_ips:
            try:
                alive_ips.sort(key=lambda ip: assets[ip].scan_priority if ip in assets else 100)
            except Exception:
                pass
            alive_ips = alive_ips[:self.max_scan_ips]
            self.logger(f"[Adaptive] Alive IPs capped to {len(alive_ips)} by max_scan_ips", "INFO")

        # Prioritize: use original resolved IP if alive, else use first alive
        primary_ip = next((ip for ip in scan_ips if ip in alive_ips), alive_ips[0])

        # ============================================================
        # SCAN ALL ALIVE IPs (concurrently)
        # ============================================================
        all_results = {"services": {}, "vulnerabilities": {}, "scan_type": "basic"}
        per_host_results: List[Tuple[str, Dict[str, Any]]] = []  # (ip, report)

        total = max(1, len(alive_ips))
        completed = 0

        def _scan_one(scan_ip: str) -> Tuple[str, Dict[str, Any]]:
            try:
                display_label = scan_ip
                hostname_hint = None
                
                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}

                if scan_ip in assets:
                    asset = assets[scan_ip]
                    # Prefer the first discovered hostname for display
                    try:
                        if asset.hostnames:
                            host_alias = sorted(asset.hostnames)[0]
                            hostname_hint = host_alias
                            display_label = f"{host_alias} ({scan_ip})"
                    except Exception:
                        display_label = scan_ip
                    
                    # Log asset metadata
                    self.logger(
                        f"ℹ️ [{target}] → {scan_ip} (confidence: {asset.confidence:.2f}, ASN: {asset.asn}, CIDR: {asset.cidr})",
                        "INFO",
                    )
                
                # Defer reverse DNS: will perform after scan completes

                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}

                # 1️⃣ RustScan
                self.logger(f"ℹ️ [{scan_ip}] Quét port nhanh (RustScan)", "INFO")
                ports = self._discover_ports(scan_ip)
                if not ports:
                    self.logger(f"ℹ️ [{scan_ip}] Không phát hiện port mở", "INFO")
                    normalized_empty = {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                    return scan_ip, normalized_empty

                port_list = ", ".join(str(p) for p in sorted(ports))
                self.logger(f"ℹ️ [{scan_ip}] Phát hiện {len(ports)} port mở: {port_list}", "INFO")

                # 2️⃣ Nmap
                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                self.logger(f"ℹ️ [{scan_ip}] Quét dịch vụ (Nmap)", "INFO")
                scan_data = self.nmap.scan_host(target=scan_ip, ports=ports)

                # Service summary
                services = []
                for p, i in (scan_data or {}).items():
                    prod = i.get("product") or i.get("service") or ""
                    ver = i.get("version") or ""
                    services.append((p, prod, ver))
                if services:
                    lines = [f"ℹ️ [{scan_ip}] Dịch vụ phát hiện:"]
                    for idx2, (port, prod, ver) in enumerate(sorted(services)):
                        prefix = "   └─" if idx2 == len(services) - 1 else "   ├─"
                        lines.append(f"{prefix} {port}/tcp → {prod} {ver}".rstrip())
                    self.logger("\n".join(lines), "INFO")

                normalized = self._normalize_scan_data(target=scan_ip, scan_data=scan_data or {})
                # Post-scan: attempt reverse DNS if we still don't have a hostname
                if not hostname_hint:
                    try:
                        hostname = socket.gethostbyaddr(scan_ip)[0]
                        if hostname:
                            hostname_hint = hostname
                            display_label = f"{hostname} ({scan_ip})"
                    except (socket.herror, socket.timeout, Exception):
                        pass
                # carry display label for GUI/export
                normalized["target_label"] = display_label
                return display_label, normalized
            except Exception as e:
                # Return empty normalized on error to keep pipeline moving
                self.logger(f"[ERROR] Scan IP {scan_ip} failed: {e}", "ERROR")
                empty = {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                empty["target_label"] = display_label
                return display_label, empty

        # Run concurrent scans
        with ThreadPoolExecutor(max_workers=self.max_concurrent_scans) as executor:
            futures = {executor.submit(_scan_one, ip): ip for ip in alive_ips}
            for fut in as_completed(futures):
                scan_ip = futures[fut]
                try:
                    label, normalized = fut.result()
                except Exception as e:
                    self.logger(f"[ERROR] Future for {scan_ip} failed: {e}", "ERROR")
                    label, normalized = scan_ip, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}

                # Merge into aggregate
                all_results["services"].update(normalized.get("services", {}))
                all_results["vulnerabilities"].update(normalized.get("vulnerabilities", {}))

                # Emit per-IP result to GUI
                if self.host_result_cb:
                    try:
                        per_host_report = self.reporter.generate(normalized)
                        self.host_result_cb(label, per_host_report)
                        per_host_results.append((label, per_host_report))
                    except Exception:
                        pass

                # Progress update per completed IP
                completed += 1
                if self.progress_cb:
                    try:
                        percent = int(completed * 100 / total)
                        self.progress_cb("scan", percent, f"Scanning {label}")
                    except Exception:
                        pass

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
                self.logger(f"[{scan_ip}] Mapping CPE → CVE", "INFO")
                self.logger(f"[{scan_ip}] Phát hiện {' | '.join(msg_parts)}", "WARN")
            else:
                self.logger(f"[{scan_ip}] Mapping CPE → CVE — không tìm thấy CVE", "INFO")

        # Host complete
        self.logger(f"[SCAN] Hoàn tất host: {target}", "SUCCESS")

        # Return aggregated results PLUS per-host results so upstream can fan-out
        return {
            "multi_host": True,
            "per_host_results": per_host_results,
            "aggregate": self.reporter.generate(all_results)
        }

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
            # 1️⃣ BUILD CPE from Nmap service + version (with Windows guards)
            # ==================================================
            if not product:
                self.logger(
                    f"Skipping port {port}/{service}: no product detected",
                    "INFO"
                )
                continue

            # Guard rails for noisy Windows mappings
            product_for_cpe = product
            pl = product.lower()
            try:
                if "microsoft windows rpc" in pl:
                    # Always treat as msrpc application to avoid generic Windows OS CPE explosion
                    product_for_cpe = "msrpc"
                elif "microsoft windows active directory" in pl or "active directory" in pl:
                    product_for_cpe = "active_directory"
                elif "microsoft windows kerberos" in pl or pl == "kerberos":
                    product_for_cpe = "kerberos"
            except Exception:
                product_for_cpe = product

            cpe = build_cpe(product_for_cpe, version if version else None, use_remote=self.cpe_use_remote)

            if not cpe or cpe == "N/A":
                self.logger(
                    f"Could not build CPE for {product} {version}",
                    "WARN"
                )
                continue

            # ==================================================
            # 2️⃣ MATCH CVE using CPE
            # ==================================================
            cves = self.matcher.match_by_cpe(cpe, max_results=self.cve_max_per_service, year_window=self.cve_year_window)
            
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

    def _scan_hosts(self, alive_ips: List[str], assets_map: Dict[str, Any] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Scan list of alive IPs (after ping check).
        Returns list of (display_label, result_dict) tuples.
        
        assets_map: optional dict of {ip: Asset} for hostname/ASN context
        """
        per_host_results = []
        completed = 0
        total = len(alive_ips)
        
        def _scan_one(scan_ip: str):
            try:
                display_label = scan_ip
                hostname_hint = None
                
                # Get asset context if available
                if assets_map and scan_ip in assets_map:
                    asset = assets_map[scan_ip]
                    if asset.hostname:
                        hostname_hint = asset.hostname
                        display_label = f"{asset.hostname} ({scan_ip})"
                
                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                
                # 1️⃣ RustScan
                self.logger(f"ℹ️ [{scan_ip}] Quét port nhanh (RustScan)", "INFO")
                ports = self._discover_ports(scan_ip)
                if not ports:
                    self.logger(f"ℹ️ [{scan_ip}] Không phát hiện port mở", "INFO")
                    normalized_empty = {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                    normalized_empty["target_label"] = display_label
                    return display_label, normalized_empty
                
                port_list = ", ".join(str(p) for p in sorted(ports))
                self.logger(f"ℹ️ [{scan_ip}] Phát hiện {len(ports)} port mở: {port_list}", "INFO")
                
                # 2️⃣ Nmap
                if self.stop_event and self.stop_event.is_set():
                    return display_label, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                self.logger(f"ℹ️ [{scan_ip}] Quét dịch vụ (Nmap)", "INFO")
                scan_data = self.nmap.scan_host(target=scan_ip, ports=ports)
                
                # Service summary
                services = []
                for p, i in (scan_data or {}).items():
                    prod = i.get("product") or i.get("service") or ""
                    ver = i.get("version") or ""
                    services.append((p, prod, ver))
                if services:
                    lines = [f"ℹ️ [{scan_ip}] Dịch vụ phát hiện:"]
                    for idx2, (port, prod, ver) in enumerate(sorted(services)):
                        prefix = "   └─" if idx2 == len(services) - 1 else "   ├─"
                        lines.append(f"{prefix} {port}/tcp → {prod} {ver}".rstrip())
                    self.logger("\n".join(lines), "INFO")
                
                normalized = self._normalize_scan_data(target=scan_ip, scan_data=scan_data or {})
                # Post-scan: attempt reverse DNS if we still don't have a hostname
                if not hostname_hint:
                    try:
                        hostname = socket.gethostbyaddr(scan_ip)[0]
                        if hostname:
                            hostname_hint = hostname
                            display_label = f"{hostname} ({scan_ip})"
                    except (socket.herror, socket.timeout, Exception):
                        pass
                normalized["target_label"] = display_label
                return display_label, normalized
            except Exception as e:
                self.logger(f"[ERROR] Scan IP {scan_ip} failed: {e}", "ERROR")
                empty = {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                empty["target_label"] = display_label if 'display_label' in locals() else scan_ip
                return (display_label if 'display_label' in locals() else scan_ip), empty
        
        # Run concurrent scans
        with ThreadPoolExecutor(max_workers=self.max_concurrent_scans) as executor:
            futures = {executor.submit(_scan_one, ip): ip for ip in alive_ips}
            for fut in as_completed(futures):
                scan_ip = futures[fut]
                try:
                    label, normalized = fut.result()
                except Exception as e:
                    self.logger(f"[ERROR] Future for {scan_ip} failed: {e}", "ERROR")
                    label, normalized = scan_ip, {"target": scan_ip, "scan_type": "basic", "services": {}, "vulnerabilities": {}}
                
                # Emit per-IP result to GUI
                if self.host_result_cb:
                    try:
                        per_host_report = self.reporter.generate(normalized)
                        self.host_result_cb(scan_ip, per_host_report)
                        per_host_results.append((label, per_host_report))
                    except Exception:
                        pass
                else:
                    per_host_results.append((label, normalized))
                
                # Progress update per completed IP
                completed += 1
                if self.progress_cb:
                    try:
                        percent = int(completed * 100 / total)
                        self.progress_cb("scan", percent, f"Scanning {label}")
                    except Exception:
                        pass
                
                # Host summary by severity
                total_cves = 0
                sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
                for s in normalized.get("vulnerabilities", {}).values():
                    for c in s.get("cves", []):
                        label_sev = (c.get("severity") if isinstance(c.get("severity"), str) else (c.get("severity", {}).get("label") if c.get("severity") else "INFO"))
                        if label_sev in sev_counts:
                            sev_counts[label_sev] += 1
                        total_cves += 1
                
                if total_cves > 0:
                    msg_parts = []
                    for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                        if sev_counts[lvl]:
                            msg_parts.append(f"{sev_counts[lvl]} {lvl}")
                    self.logger(f"[{scan_ip}] Mapping CPE → CVE", "INFO")
                    self.logger(f"[{scan_ip}] Phát hiện {' | '.join(msg_parts)}", "WARN")
                else:
                    self.logger(f"[{scan_ip}] Mapping CPE → CVE — không tìm thấy CVE", "INFO")
                
                self.logger(f"✅ [SCAN] Hoàn tất host: {label}", "SUCCESS")
        
        return per_host_results
