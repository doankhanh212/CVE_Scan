from typing import Dict, Any, List, Optional, Tuple
try:
    import nmap
    _HAVE_NMAP = True
except Exception:
    nmap = None
    _HAVE_NMAP = False
import re


class NmapScanner:
    """
    NmapScanner (Service Detection)
    """

    def __init__(self, timeout: int = 60, logger=None):
        self.timeout = timeout
        self.logger = logger or (lambda msg, lvl="INFO": print(f"[{lvl}] {msg}"))
        if _HAVE_NMAP:
            try:
                self.nm = nmap.PortScanner()
            except Exception as e:
                self.logger(f"python-nmap available but PortScanner initialization failed: {e}", "ERROR")
                self.nm = None
        else:
            self.logger("python-nmap not installed; NmapScanner disabled", "WARN")
            self.nm = None

    # Heuristics: lightweight extrainfo parsing
    def _parse_extrainfo(self, extrainfo: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Try to extract product and version from extrainfo banners.
        Returns (product, version) or (None, None)
        """
        if not extrainfo:
            return None, None

        # common pattern: ProductName <sep> Version (e.g. "OpenSSH 7.4p1", "Apache httpd 2.4.49")
        m = re.search(r"([A-Za-z0-9\-_.]+)[/ ]+([0-9][0-9A-Za-z\.-]*)", extrainfo)
        if m:
            prod = m.group(1)
            ver = m.group(2)
            # special-case: "Apache httpd 2.4.49" -> prefer 'Apache' over 'httpd'
            if prod.lower() in ("httpd", "server"):
                first = extrainfo.strip().split()[0]
                prod = first
            return prod, ver

        # fallback: take first token
        token = extrainfo.strip().split()[0]
        return token, None

    def _normalize_service(self, svc: Dict[str, Any], port: int) -> Tuple[str, str, str]:
        """Return (name, product, version) after applying heuristics."""
        # minimal well-known port -> service name map to improve heuristics
        well_known = {
            22: "ssh",
            80: "http",
            443: "https",
            53: "dns",
            3306: "mysql",
            1433: "mssql",
            3389: "rdp",
            21: "ftp",
            25: "smtp",
            445: "microsoft-ds",
            5900: "vnc",
        }

        raw_name = (svc.get("name") or svc.get("service") or "")
        # clean obvious 'portNNN' or 'portNNNN:NNNN' strings
        name = raw_name.split(":")[0]
        name = name.strip()

        product = svc.get("product") or ""
        version = svc.get("version") or ""

        # if there's extra banner info, try to parse it
        extrainfo = svc.get("extrainfo") or svc.get("reason") or ""
        if (not product or product.strip() == "") and extrainfo:
            p, v = self._parse_extrainfo(extrainfo)
            if p:
                product = p
            if v and not version:
                version = v

        # filter out noisy placeholder values that don't indicate real product
        placeholders = {"syn-ack", "no-response", "tcpwrapped", "unknown", "port", "reset", "refused", "filtered"}
        if product and product.strip().lower() in placeholders:
            product = ""

        # if product still empty and port is well-known, prefer canonical name
        if (not product or product.strip() == "") and port in well_known:
            product = well_known[port]

        # prefer a sensible name if current name is empty or a generic 'portNNN' or placeholder
        if (not name or name.startswith("port") or name.lower() in placeholders):
            if port in well_known:
                name = well_known[port]
            elif raw_name:
                # use raw_name if present
                name = raw_name
            else:
                name = f"port{port}"

        # final normalization
        name = name.lower()
        product = product or name
        version = version or ""

        return name, product, version

    def scan_host(
        self,
        target: str,
        ports: Optional[List[int]] = None
    ) -> Dict[int, Dict[str, Any]]:

        if not self.nm:
            self.logger("Nmap scanner not available; skipping service detection", "WARN")
            return {}

        arguments = self._build_arguments(ports)

        self.logger(f"Running Nmap against {target}", "INFO")
        self.logger(f"Nmap arguments: {arguments}", "DEBUG")

        try:
            self.nm.scan(
                hosts=target,
                arguments=arguments
            )
        except Exception as e:
            self.logger(f"Nmap scan failed: {e}", "ERROR")
            return {}

        results = self._parse_results(target)

        # BasicPipeline will log service details; keep Nmap scanner quiet
        pass

        return results

    # ==================================================
    def _build_arguments(self, ports: Optional[List[int]]) -> str:
        base = "-sV -Pn"

        if ports:
            port_str = ",".join(str(p) for p in sorted(set(ports)))
            return f"{base} -p {port_str}"

        return f"{base} -p 1-65535"

    def _parse_results(self, target: str) -> Dict[int, Dict[str, Any]]:

        results: Dict[int, Dict[str, Any]] = {}

        if target not in self.nm.all_hosts():
            self.logger(f"No host data returned for {target}", "WARN")
            return results

        host = self.nm[target]

        protocols = host.all_protocols()

        # 🔥 FIX 3 – FALLBACK CHO WINDOWS / python-nmap BUG
        if not protocols:
            self.logger(
                "No protocols returned by python-nmap, fallback to TCP layer",
                "WARN"
            )
            if "tcp" in host:
                protocols = ["tcp"]
            else:
                return results

        # minimal well-known port -> service name map to improve heuristics
        well_known = {
            22: "ssh",
            80: "http",
            443: "https",
            53: "dns",
            3306: "mysql",
            1433: "mssql",
            3389: "rdp",
            21: "ftp",
            25: "smtp",
            445: "microsoft-ds",
            5900: "vnc",
        }

        for proto in protocols:
            for port in host[proto]:
                svc = host[proto][port]

                name, product, version = self._normalize_service(svc, port)

                results[port] = {
                    "port": port,
                    "protocol": proto,
                    "service": name,
                    "product": product,
                    "version": version,
                    "os": svc.get("ostype")
                }

                self.logger(
                    f"Service detected: {port}/{proto} -> {name} {product} {version}".strip(),
                    "INFO"
                )

        return results

