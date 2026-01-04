"""
Asset Discovery Module (DNS + WHOIS + ASN + Reverse DNS)
========================================================

Flow:
  Input: Domain/Hostname
    ↓
  DNS Resolution (A/AAAA records, concurrent)
    ↓
  IP + WHOIS → ASN → CIDR
    ↓
  Reverse DNS
    ↓
  Asset Inventory: {IP, CIDR, ASN, Hostname, Confidence}

Fallback: WHOIS timeout → continue with IP only (lower confidence)
"""

import socket
import logging
import ipaddress
import time
from typing import Dict, List, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ======================================================================
# WHOIS LIBRARY - Try ipwhois first, fallback to manual
# ======================================================================
try:
    from ipwhois import IPWhois
    _HAVE_IPWHOIS = True
except ImportError:
    _HAVE_IPWHOIS = False
    logger.warning("ipwhois not installed - WHOIS/ASN lookups disabled")
    
try:
    import requests
    _HAVE_REQUESTS = True
except ImportError:
    _HAVE_REQUESTS = False
    logger.warning("requests not installed - RIPEstat fallback disabled")


# ======================================================================
# CONSTANTS
# ======================================================================
DNS_TIMEOUT = 5  # seconds
WHOIS_TIMEOUT = 10  # seconds
REVERSE_DNS_TIMEOUT = 5  # seconds
MAX_DNS_WORKERS = 10
CONFIDENCE_SCORES = {
    "dns_resolved": 1.0,          # Found via DNS
    "whois_success": 0.95,        # WHOIS lookup success
    "whois_timeout": 0.70,        # WHOIS timed out, fallback to IP
    "reverse_dns": 0.85,          # Reverse DNS found
    "cidr_inferred": 0.75,        # Inferred from ASN CIDR
    "cidr_asset": 0.75,           # Asset from explicit CIDR expansion
}


# ======================================================================
# ASSET CLASS
# ======================================================================
class Asset:
    """Single asset (IP + metadata)"""

    def __init__(self, ip: str):
        self.ip = ip
        self.try_parse_type()
        self.hostnames: Set[str] = set()
        self.asn: Optional[str] = None
        self.cidr: Optional[str] = None
        self.country: Optional[str] = None
        self.org: Optional[str] = None
        self.confidence: float = 0.0
        self.source: List[str] = []  # "dns", "whois", "reverse_dns", etc.
        self.scan_priority: int = 100  # Lower = higher priority (1-255)

    def try_parse_type(self):
        """Determine if IPv4 or IPv6"""
        try:
            self.addr_obj = ip_address(self.ip)
            self.is_ipv4 = isinstance(self.addr_obj, IPv4Address)
            self.is_ipv6 = isinstance(self.addr_obj, IPv6Address)
        except ValueError:
            self.addr_obj = None
            self.is_ipv4 = False
            self.is_ipv6 = False

    def add_hostname(self, hostname: str):
        """Add hostname to asset"""
        if hostname and hostname not in self.hostnames:
            self.hostnames.add(hostname)

    def add_source(self, source: str):
        """Track data source"""
        if source not in self.source:
            self.source.append(source)

    def update_confidence(self, confidence: float):
        """Update confidence (use max)"""
        self.confidence = max(self.confidence, confidence)

    def to_dict(self) -> Dict:
        """Export as dict"""
        return {
            "ip": self.ip,
            "type": "IPv4" if self.is_ipv4 else ("IPv6" if self.is_ipv6 else "Unknown"),
            "hostnames": sorted(list(self.hostnames)),
            "asn": self.asn,
            "cidr": self.cidr,
            "org": self.org,
            "country": self.country,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "scan_priority": self.scan_priority,
        }

    def __repr__(self):
        hosts_str = ", ".join(self.hostnames) if self.hostnames else "N/A"
        return f"Asset(ip={self.ip}, hosts={hosts_str}, asn={self.asn}, conf={self.confidence:.2f})"


# ======================================================================
# DNS RESOLUTION (CONCURRENT)
# ======================================================================
class DNSResolver:
    """Concurrent DNS resolver with timeout"""

    def __init__(self, timeout: int = DNS_TIMEOUT, max_workers: int = MAX_DNS_WORKERS):
        self.timeout = timeout
        self.max_workers = max_workers

    def resolve_hostname(self, hostname: str) -> List[str]:
        """
        Resolve hostname to IPs (A + AAAA records)
        Returns: List of IP strings
        """
        try:
            # Set socket timeout for this resolution
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.timeout)
            
            try:
                # getaddrinfo returns (family, type, proto, canonname, sockaddr)
                # sockaddr for IPv4 is (ip, port)
                # sockaddr for IPv6 is (ip, port, flowinfo, scope_id)
                results = socket.getaddrinfo(
                    hostname,
                    None,  # No specific port
                    socket.AF_UNSPEC,  # Both IPv4 and IPv6
                    socket.SOCK_STREAM
                )
            finally:
                socket.setdefaulttimeout(old_timeout)

            ips = []
            for family, socktype, proto, canonname, sockaddr in results:
                ip = sockaddr[0]
                if ip not in ips:
                    ips.append(ip)

            logger.debug(f"[DNS] {hostname} → {ips}")
            return ips

        except socket.gaierror as e:
            logger.debug(f"[DNS] {hostname} failed: {e}")
            return []
        except socket.timeout:
            logger.debug(f"[DNS] {hostname} timeout")
            return []
        except Exception as e:
            logger.warning(f"[DNS] {hostname} unexpected error: {e}")
            return []

    def resolve_many(self, hostnames: List[str]) -> Dict[str, List[str]]:
        """
        Resolve multiple hostnames concurrently
        Returns: {hostname: [ips]}
        """
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.resolve_hostname, h): h
                for h in hostnames
            }

            for future in as_completed(futures):
                hostname = futures[future]
                try:
                    ips = future.result(timeout=self.timeout)
                    results[hostname] = ips
                except Exception as e:
                    logger.warning(f"[DNS] {hostname} executor error: {e}")
                    results[hostname] = []

        return results


# ======================================================================
# WHOIS / ASN LOOKUP
# ======================================================================
class WHOISLookup:
    """WHOIS + ASN lookup with timeout"""

    def __init__(self, timeout: int = WHOIS_TIMEOUT):
        self.timeout = timeout

    @staticmethod
    def _extract_best_cidr(ip: str, results: Dict) -> Optional[str]:
        """Extract the most specific CIDR containing `ip` from ipwhois results."""

        def _candidate_strings(value) -> List[str]:
            if not value:
                return []
            if isinstance(value, str):
                # ipwhois can return comma/space-separated CIDRs
                parts = []
                for chunk in value.replace(";", ",").replace(" ", ",").split(","):
                    chunk = chunk.strip()
                    if chunk:
                        parts.append(chunk)
                return parts
            if isinstance(value, list):
                out: List[str] = []
                for item in value:
                    out.extend(_candidate_strings(item))
                return out
            return []

        ip_obj = None
        try:
            ip_obj = ip_address(ip)
        except Exception:
            return None

        candidates: List[str] = []

        # Legacy top-level keys
        candidates.extend(_candidate_strings(results.get("cidr")))
        candidates.extend(_candidate_strings(results.get("asn_cidr")))

        # RDAP structure: results['network']['cidr']
        network = results.get("network")
        if isinstance(network, dict):
            candidates.extend(_candidate_strings(network.get("cidr")))

        # WHOIS structure: results['nets'][*]['cidr']
        nets = results.get("nets")
        if isinstance(nets, list):
            for net in nets:
                if isinstance(net, dict):
                    candidates.extend(_candidate_strings(net.get("cidr")))

        best_net = None
        for cidr in candidates:
            try:
                net = ip_network(cidr, strict=False)
                if ip_obj in net:
                    if best_net is None or net.prefixlen > best_net.prefixlen:
                        best_net = net
            except Exception:
                continue

        return str(best_net) if best_net else None

    def lookup_ip(self, ip: str) -> Tuple[Optional[str], Optional[str], Optional[str], bool]:
        """
        Lookup IP via WHOIS → ASN, CIDR, Org
        Returns: (asn, cidr, org, success)
        success=False if timeout (still return partial data)
        """
        if not _HAVE_IPWHOIS:
            return None, None, None, False

        try:
            whois = IPWhois(ip, timeout=self.timeout)
            
            # Try RDAP first (newer, more reliable), fallback to WHOIS
            try:
                results = whois.lookup_rdap()
            except Exception:
                try:
                    results = whois.lookup_whois()
                except Exception as e:
                    # Both failed
                    raise e

            asn = results.get("asn")

            # ipwhois RDAP/WHOIS results often nest CIDR under `network` or `nets`
            cidr = self._extract_best_cidr(ip, results)
            
            # Handle org field (can be dict or string)
            org_field = results.get("org")
            if isinstance(org_field, dict):
                org_name = org_field.get("name")
            else:
                org_name = org_field
            
            # Fallback to asn_registry if org not found
            if not org_name:
                org_name = results.get("asn_registry")

            # RDAP often provides network name, which is better than empty
            if not org_name:
                network = results.get("network")
                if isinstance(network, dict):
                    org_name = network.get("name")

            logger.debug(f"[WHOIS] {ip} → ASN={asn}, CIDR={cidr}, Org={org_name}")
            return asn, cidr, org_name, True

        except Exception as e:
            # Check if timeout
            if isinstance(e, socket.timeout) or "timeout" in str(e).lower():
                logger.debug(f"[WHOIS] {ip} timeout (continuing with lower confidence)")
                return None, None, None, False
            else:
                logger.debug(f"[WHOIS] {ip} failed: {e}")
                return None, None, None, False

    def lookup_many(self, ips: List[str]) -> Dict[str, Dict]:
        """
        Lookup multiple IPs concurrently
        Returns: {ip: {asn, cidr, org, success}}
        """
        results = {}

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.lookup_ip, ip): ip
                for ip in ips
            }

            # Do not enforce a global timeout here; let each future respect self.timeout
            # If we timeout the as_completed loop, we get "futures unfinished" and abort the scan.
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    asn, cidr, org, success = future.result(timeout=self.timeout)
                    results[ip] = {
                        "asn": asn,
                        "cidr": cidr,
                        "org": org,
                        "success": success
                    }
                except Exception as e:
                    logger.warning(f"[WHOIS] {ip} executor error: {e}")
                    results[ip] = {"asn": None, "cidr": None, "org": None, "success": False}

        return results


# ======================================================================
# REVERSE DNS
# ======================================================================
class ReverseDNS:
    """Reverse DNS lookups"""

    def __init__(self, timeout: int = REVERSE_DNS_TIMEOUT):
        self.timeout = timeout

    def reverse_lookup(self, ip: str) -> Optional[str]:
        """
        Reverse DNS lookup (IP → Hostname)
        Returns: hostname or None
        """
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)
            logger.debug(f"[RevDNS] {ip} → {hostname}")
            return hostname
        except socket.herror:
            logger.debug(f"[RevDNS] {ip} not found")
            return None
        except socket.timeout:
            logger.debug(f"[RevDNS] {ip} timeout")
            return None
        except Exception as e:
            logger.debug(f"[RevDNS] {ip} error: {e}")
            return None

    def reverse_lookup_many(self, ips: List[str]) -> Dict[str, Optional[str]]:
        """Reverse lookup multiple IPs concurrently"""
        results = {}

        with ThreadPoolExecutor(max_workers=MAX_DNS_WORKERS) as executor:
            futures = {
                executor.submit(self.reverse_lookup, ip): ip
                for ip in ips
            }

            for future in as_completed(futures):
                ip = futures[future]
                try:
                    hostname = future.result(timeout=self.timeout)
                    results[ip] = hostname
                except Exception as e:
                    logger.warning(f"[RevDNS] {ip} executor error: {e}")
                    results[ip] = None

        return results


# ======================================================================
# ASN → PREFIXES (RIPEstat fallback for CIDR)
# ======================================================================
class ASNPrefixFetcher:
    """Fetch announced prefixes for an ASN via RIPEstat (no API key)."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    @staticmethod
    def _normalize_asn(asn: str) -> str:
        s = str(asn).upper().strip()
        return s if s.startswith("AS") else f"AS{s}"

    def get_prefixes(self, asn: str) -> List[str]:
        if not _HAVE_REQUESTS:
            return []
        try:
            resource = self._normalize_asn(asn)
            url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource={resource}"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                logger.debug(f"[RIPEstat] {resource} HTTP {resp.status_code}")
                return []
            data = resp.json()
            prefixes = data.get("data", {}).get("prefixes", [])
            out: List[str] = []
            for p in prefixes:
                pref = p.get("prefix")
                if pref and pref not in out:
                    out.append(pref)
            logger.debug(f"[RIPEstat] {resource} → {len(out)} prefixes")
            return out
        except Exception as e:
            logger.debug(f"[RIPEstat] error: {e}")
            return []


# ======================================================================
# CIDR EXPANSION (Asset Inventory only, not for scan)
# ======================================================================
class CIDRExpander:
    """Expand CIDR to IP list for asset inventory"""

    @staticmethod
    def expand_cidr(cidr: str, max_ips: int = 256) -> List[str]:
        """
        Expand CIDR to IP list (limited to max_ips)
        Returns: List of IP strings (max_ips elements)
        """
        try:
            network = ip_network(cidr, strict=False)
            ips = [str(ip) for ip in list(network.hosts())[:max_ips]]
            logger.debug(f"[CIDR] {cidr} expanded to {len(ips)} IPs")
            return ips
        except Exception as e:
            logger.warning(f"[CIDR] {cidr} expansion failed: {e}")
            return []


# ======================================================================
# MAIN ASSET DISCOVERY ORCHESTRATOR
# ======================================================================
class AssetDiscovery:
    """
    Discover assets from domain/hostname
    Flow: Hostname → DNS → IP → WHOIS → ASN → CIDR → Reverse DNS
    """

    def __init__(self, logger=None, progress_cb=None, max_cidr_ips=1024, enable_reverse_dns_pre_scan=True):
        self.logger = logger or (lambda msg, lvl="INFO": None)
        self.progress_cb = progress_cb
        self.max_cidr_ips = max_cidr_ips  # Configurable CIDR expansion limit
        self.dns_resolver = DNSResolver()
        self.whois = WHOISLookup()
        self.reverse_dns = ReverseDNS()
        self.cidr_expander = CIDRExpander()
        self.asn_prefixes = ASNPrefixFetcher()
        self.enable_reverse_dns_pre_scan = bool(enable_reverse_dns_pre_scan)

    def discover(self, hostnames: List[str]) -> Dict[str, Asset]:
        """
        Discover assets from list of hostnames, IPs, or CIDR ranges
        Returns: {ip: Asset} mapping
        """
        assets = {}

        self.logger(f"[AssetDiscovery] Starting with {len(hostnames)} targets", "SYSTEM")

        # Pre-process targets: separate CIDR, IPs, and hostnames
        cidr_targets = []
        ip_targets = []
        hostname_targets = []
        
        for target in hostnames:
            target = target.strip()
            if not target:
                continue
            
            # Check if CIDR notation
            if "/" in target:
                try:
                    network = ipaddress.ip_network(target, strict=False)
                    cidr_targets.append(network)
                    continue
                except Exception:
                    pass
            
            # Check if plain IP
            try:
                ipaddress.ip_address(target)
                ip_targets.append(target)
                continue
            except Exception:
                pass
            
            # Must be hostname
            hostname_targets.append(target)
        
        # Process CIDR ranges: expand to individual IPs and add to assets
        if cidr_targets:
            self.logger(f"[AssetDiscovery] Expanding {len(cidr_targets)} CIDR range(s)...", "INFO")
            for network in cidr_targets:
                cidr_str = str(network)
                hosts_in_cidr = list(network.hosts())
                
                # Cap CIDR expansion to prevent memory issues
                if len(hosts_in_cidr) > self.max_cidr_ips:
                    self.logger(f"  ⚠️ {cidr_str} has {len(hosts_in_cidr)} IPs, capping at {self.max_cidr_ips}", "WARN")
                    hosts_in_cidr = hosts_in_cidr[:self.max_cidr_ips]
                
                self.logger(f"  ✓ {cidr_str} → {len(hosts_in_cidr)} IPs", "SUCCESS")
                
                for ip in hosts_in_cidr:
                    ip_str = str(ip)
                    if ip_str not in assets:
                        assets[ip_str] = Asset(ip_str)
                    assets[ip_str].cidr = cidr_str
                    assets[ip_str].add_source("cidr_expansion")
                    assets[ip_str].update_confidence(CONFIDENCE_SCORES["cidr_asset"])
        
        # Process plain IPs: add directly to assets
        if ip_targets:
            self.logger(f"[AssetDiscovery] Processing {len(ip_targets)} direct IP(s)...", "INFO")
            for ip in ip_targets:
                if ip not in assets:
                    assets[ip] = Asset(ip)
                assets[ip].add_source("direct_ip")
                assets[ip].update_confidence(CONFIDENCE_SCORES["dns_resolved"])
        
        # Step 1: DNS Resolution for hostnames only
        if hostname_targets:
            self.logger(f"[AssetDiscovery] Step 1/4: DNS Resolution for {len(hostname_targets)} hostname(s)...", "INFO")
            dns_results = self.dns_resolver.resolve_many(hostname_targets)

            for hostname, resolved_ips in dns_results.items():
                if resolved_ips:
                    self.logger(
                        f"  ✓ {hostname} → {', '.join(resolved_ips)}", "SUCCESS"
                    )
                    for ip in resolved_ips:
                        if ip not in assets:
                            assets[ip] = Asset(ip)
                        assets[ip].add_hostname(hostname)
                        assets[ip].add_source("dns")
                        assets[ip].update_confidence(CONFIDENCE_SCORES["dns_resolved"])
                else:
                    self.logger(f"  ✗ {hostname} → no resolution", "WARN")
        else:
            self.logger("[AssetDiscovery] Step 1/4: DNS Resolution... (skipped, no hostnames)", "INFO")

        # Collect all IPs for subsequent steps
        ips = list(assets.keys())
        
        if not ips:
            self.logger("[AssetDiscovery] No IPs after processing, stopping", "WARN")
            return assets

        # Step 2: WHOIS → ASN → CIDR
        self.logger(f"[AssetDiscovery] Step 2/4: WHOIS lookup for {len(ips)} IPs...", "INFO")
        whois_results = self.whois.lookup_many(ips)

        for ip, result in whois_results.items():
            if ip not in assets:
                assets[ip] = Asset(ip)

            assets[ip].asn = result.get("asn")
            assets[ip].org = result.get("org")
            assets[ip].cidr = result.get("cidr")

            if result.get("success"):
                self.logger(
                    f"  ✓ {ip} → ASN={result['asn']}, CIDR={result['cidr']}", "SUCCESS"
                )
                assets[ip].update_confidence(CONFIDENCE_SCORES["whois_success"])
                assets[ip].add_source("whois")

                # If WHOIS returned ASN but no CIDR, try RIPEstat to infer prefixes
                if not assets[ip].cidr and assets[ip].asn:
                    try:
                        ip_obj = ip_address(ip)
                        prefixes = self.asn_prefixes.get_prefixes(assets[ip].asn)
                        # keep only prefixes that contain the resolved IP
                        matching = []
                        for pref in prefixes:
                            try:
                                net = ip_network(pref, strict=False)
                                if ip_obj in net:
                                    matching.append(net)
                            except Exception:
                                continue
                        if matching:
                            # choose most specific (largest prefix length)
                            best = max(matching, key=lambda n: n.prefixlen)
                            assets[ip].cidr = str(best)
                            assets[ip].add_source("ripe_announced_prefix")
                            assets[ip].update_confidence(CONFIDENCE_SCORES["cidr_inferred"])
                            self.logger(
                                f"    ↳ inferred CIDR via RIPEstat: {assets[ip].cidr}", "INFO"
                            )
                    except Exception as e:
                        self.logger(f"    ↳ RIPEstat inference failed: {e}", "WARN")
            else:
                # Timeout or error - continue with lower confidence
                self.logger(
                    f"  ⚠ {ip} → WHOIS failed, continuing with lower confidence", "WARN"
                )
                assets[ip].update_confidence(CONFIDENCE_SCORES["whois_timeout"])
                assets[ip].add_source("whois_timeout")

        # Step 3: Reverse DNS (optional pre-scan)
        if self.enable_reverse_dns_pre_scan:
            self.logger(f"[AssetDiscovery] Step 3/4: Reverse DNS for {len(ips)} IPs...", "INFO")
            reverse_results = self.reverse_dns.reverse_lookup_many(ips)

            for ip, hostname in reverse_results.items():
                if ip not in assets:
                    assets[ip] = Asset(ip)

                if hostname:
                    assets[ip].add_hostname(hostname)
                    assets[ip].add_source("reverse_dns")
                    assets[ip].update_confidence(CONFIDENCE_SCORES["reverse_dns"])
                    self.logger(f"  ✓ {ip} → {hostname}", "SUCCESS")
        else:
            self.logger("[AssetDiscovery] Step 3/4: Reverse DNS (skipped by config)", "INFO")

        # Step 4: CIDR Asset Inventory (not for scan, just inventory)
        self.logger("[AssetDiscovery] Step 4/4: Asset Inventory from CIDR...", "INFO")
        cidr_assets = {}

        for ip, asset in assets.items():
            if asset.cidr:
                # Expand CIDR to configured limit (enterprise: configurable via max_cidr_ips)
                # /22 = 1024 IPs, /24 = 256 IPs - scan all alive hosts
                cidr_ips = self.cidr_expander.expand_cidr(asset.cidr, max_ips=self.max_cidr_ips)
                for cidr_ip in cidr_ips:
                    if cidr_ip not in assets:
                        cidr_asset = Asset(cidr_ip)
                        cidr_asset.cidr = asset.cidr
                        cidr_asset.asn = asset.asn
                        cidr_asset.org = asset.org
                        cidr_asset.update_confidence(CONFIDENCE_SCORES["cidr_inferred"])
                        cidr_asset.add_source("cidr_inferred")
                        cidr_assets[cidr_ip] = cidr_asset

        # Merge CIDR assets (lower priority)
        for ip, asset in cidr_assets.items():
            if ip not in assets:
                assets[ip] = asset

        # Step 5: Reverse DNS on CIDR IPs (optional pre-scan)
        all_cidr_ips = list(cidr_assets.keys())
        if self.enable_reverse_dns_pre_scan and all_cidr_ips:
            self.logger(f"[AssetDiscovery] Step 5/5: Reverse DNS for {len(all_cidr_ips)} CIDR IPs...", "INFO")
            cidr_reverse_results = self.reverse_dns.reverse_lookup_many(all_cidr_ips)
            
            for ip, hostname in cidr_reverse_results.items():
                if ip in assets and hostname:
                    assets[ip].add_hostname(hostname)
                    assets[ip].add_source("reverse_dns_cidr")
                    assets[ip].update_confidence(CONFIDENCE_SCORES["reverse_dns"])
                    self.logger(f"  ✓ {ip} → {hostname}", "SUCCESS")
        elif all_cidr_ips:
            self.logger("[AssetDiscovery] Step 5/5: Reverse DNS on CIDR (skipped by config)", "INFO")

        self.logger(f"[AssetDiscovery] Complete: {len(assets)} assets discovered", "SUCCESS")

        return assets

    def filter_for_scan(
        self,
        assets: Dict[str, Asset],
        include_cidr: bool = True,
        max_scan_ips: Optional[int] = None
    ) -> List[str]:
        """
        Filter assets to determine which IPs to scan.
        - High confidence (>=0.85): priority 1
        - Medium confidence (0.70-0.85): priority 50
        - Low confidence (<0.70): inventory-only

        Optional controls:
          * include_cidr: if False, skip assets that only came from CIDR expansion
          * max_scan_ips: cap the number of IPs returned after sorting
        """
        scan_ips: List[str] = []
        skipped_cidr = 0

        for ip, asset in assets.items():
            sources = set(asset.source)
            # CIDR-expanded assets have only cidr_inferred/reverse_dns_cidr sources
            is_cidr_only = (
                "cidr_inferred" in sources
                and not (sources - {"cidr_inferred", "reverse_dns_cidr"})
            )

            if is_cidr_only and not include_cidr:
                skipped_cidr += 1
                asset.scan_priority = 255
                continue

            if asset.confidence >= 0.70:
                scan_ips.append(ip)
                if asset.confidence >= 0.85:
                    asset.scan_priority = 1  # High priority
                else:
                    asset.scan_priority = 50  # Medium priority
            else:
                asset.scan_priority = 255  # Inventory only, no scan

        # Sort by priority before applying cap
        scan_ips.sort(key=lambda ip: assets[ip].scan_priority)

        capped = False
        if max_scan_ips and max_scan_ips > 0 and len(scan_ips) > max_scan_ips:
            scan_ips = scan_ips[:max_scan_ips]
            capped = True

        inventory_only = len(assets) - len(scan_ips)
        self.logger(
            f"[AssetDiscovery] {len(scan_ips)} assets marked for scan "
            f"({max(inventory_only, 0)} inventory-only)"
            + (f", skipped {skipped_cidr} CIDR-expanded (config)" if skipped_cidr else "")
            + ("; capped by max_scan_ips" if capped else ""),
            "INFO"
        )

        return scan_ips
