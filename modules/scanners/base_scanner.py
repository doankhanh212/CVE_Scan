# modules/scanners/base_scanner.py

from abc import ABC, abstractmethod
from typing import Dict, Any
import ipaddress


class BaseScanner(ABC):
    """
    Base interface cho mọi scanner engine
    (nmap, rustscan, masscan, ...)
    """

    def __init__(self, ports: str = "1-1024"):
        self.ports = ports

    @abstractmethod
    def scan_host(self, host: str) -> Dict[int, Dict[str, Any]]:
        """
        Scan 1 host

        Return format:
        {
            port: {
                "service": str,
                "version": str,
                "product": str,
                "state": str,
                "os": str
            }
        }
        """
        raise NotImplementedError

    def scan_range(self, cidr: str) -> Dict[str, Dict[int, Dict[str, Any]]]:
        """
        Scan CIDR range (default implementation)
        """
        results = {}

        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except Exception:
            return results

        for ip in net.hosts():
            ip_str = str(ip)
            host_result = self.scan_host(ip_str)
            if host_result:
                results[ip_str] = host_result

        return results
