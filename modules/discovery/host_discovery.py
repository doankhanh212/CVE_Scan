# modules/discovery/host_discovery.py

import subprocess
import threading
from queue import Queue
from threading import Event
from typing import List
import re


class HostDiscovery:
    """
    HostDiscovery using Nmap -sn for fast subnet/CIDR scanning.
    
    Nmap -sn is significantly faster than sequential ping:
    - Uses ARP scan on LAN (instant detection)
    - Uses TCP SYN/ICMP in parallel for distant subnets
    - Automatically handles firewall bypass
    
    For CIDR ranges: use discover_cidr(cidr_range)
    For individual IPs: use discover(ip_list)
    """

    def __init__(self, timeout=1, retries=3, workers=100, logger=None, progress_cb=None):
        self.timeout = timeout
        self.retries = retries
        self.workers = workers
        self.logger = logger or (lambda msg, lvl="INFO": None)
        self.progress_cb = progress_cb

        self.alive_queue = Queue()
        self.finished = Event()

        self.total = 1
        self.done = 0
        self._lock = threading.Lock()

    def _parse_nmap_output(self, output: str) -> List[str]:
        """Parse nmap -sn output and return only IPs that are UP.

        Supports both grepable output (preferred via `-oG -`) and the
        standard human-readable output. Handles lines with hostnames like
        "Nmap scan report for some-host (192.168.1.1)" and ensures we only
        include IPs where a subsequent line indicates "Host is up".
        """
        alive_ips: List[str] = []

        # 1) Prefer grepable format if present
        # Example: "Host: 192.168.1.1 (hostname)  Status: Up"
        for line in output.splitlines():
            m = re.search(r"Host:\s+([0-9]{1,3}(?:\.[0-9]{1,3}){3}|[0-9a-fA-F:]+).*Status:\s+Up", line)
            if m:
                alive_ips.append(m.group(1))

        if alive_ips:
            return alive_ips

        # 2) Fallback: parse human-readable output
        # We require "Host is up" after the corresponding report line.
        lines = output.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            ip = None
            # Case A: IP only
            m_ip_only = re.search(r"^Nmap scan report for\s+([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s*$", line)
            # Case B: Hostname (IP)
            m_with_host = re.search(r"^Nmap scan report for\s+.*\(([0-9]{1,3}(?:\.[0-9]{1,3}){3})\)\s*$", line)
            if m_ip_only:
                ip = m_ip_only.group(1)
            elif m_with_host:
                ip = m_with_host.group(1)

            if ip:
                # Look ahead until next report or end; include only if "Host is up" found
                j = i + 1
                while j < len(lines) and not lines[j].startswith("Nmap scan report"):
                    if "Host is up" in lines[j]:
                        alive_ips.append(ip)
                        break
                    j += 1
                i = j
            else:
                i += 1

        return alive_ips

    def _run_nmap_sn(self, target: str) -> List[str]:
        """
        Run 'nmap -sn' on target (IP, IP list, or CIDR range).
        For long IP lists, use -iL (input file) to avoid command line overflow.
        For CIDR ranges, use direct CIDR notation (fastest).
        """
        import tempfile
        import os
        
        temp_file = None
        try:
            # If target contains spaces, it's a space-separated IP list
            # Write to temp file and use -iL flag
            if ' ' in target:
                # Create temporary file with IP list
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    # Write each IP on a new line
                    ips = target.split()
                    for ip in ips:
                        f.write(ip + '\n')
                    temp_file = f.name
                
                cmd = [
                    "nmap",
                    "-sn",
                    "-PR",  # ARP discovery on local networks
                    "-PE",  # ICMP Echo
                    "-PP",  # ICMP Timestamp
                    "-PS", "22,80,443,445,3389",  # TCP SYN probes
                    "-PA", "80,443",  # TCP ACK probes
                    "-T4",
                    "--min-parallelism", "100",
                    "-n",
                    "-oG", "-",
                    "-iL", temp_file
                ]
                self.logger(f"[NMAP-SN] Running nmap (extended probes) on {len(ips)} IPs (via temp file)", "INFO")
            else:
                # Single IP or CIDR range - use directly
                cmd = [
                    "nmap",
                    "-sn",
                    "-PR",  # ARP discovery on local networks
                    "-PE",  # ICMP Echo
                    "-PP",  # ICMP Timestamp
                    "-PS", "22,80,443,445,3389",  # TCP SYN probes
                    "-PA", "80,443",  # TCP ACK probes
                    "-T4",
                    "--min-parallelism", "100",
                    "-n",
                    "-oG", "-",
                    target
                ]
                self.logger(f"[NMAP-SN] Running (extended probes): {' '.join(cmd)}", "INFO")

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5 minute max timeout
                text=True
            )

            if proc.returncode != 0:
                self.logger(f"[NMAP-SN] Warning: nmap returned {proc.returncode}", "WARN")
                self.logger(f"[NMAP-SN] stderr: {proc.stderr[:200]}", "WARN")

            # Debug: Log raw output sample
            output_preview = proc.stdout[:500] if len(proc.stdout) > 500 else proc.stdout
            self.logger(f"[NMAP-SN] Raw output preview:\n{output_preview}", "DEBUG")

            # Parse output
            alive_ips = self._parse_nmap_output(proc.stdout)
            
            # Debug: Log parse result
            self.logger(f"[NMAP-SN] Parser found {len(alive_ips)} alive IPs from {len(proc.stdout)} bytes of output", "DEBUG")
            
            return alive_ips

        except FileNotFoundError:
            self.logger("Nmap not found in PATH; install nmap to use host discovery", "ERROR")
            return []
        except subprocess.TimeoutExpired:
            self.logger("Nmap scan timed out (5 minutes)", "ERROR")
            return []
        except Exception as e:
            self.logger(f"Nmap scan error: {e}", "ERROR")
            return []
        finally:
            # Cleanup temp file if created
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def discover(self, targets: List[str]) -> List[str]:
        """
        Discover alive hosts from targets (individual IPs or small list).
        For large CIDR ranges, use discover_cidr() instead.
        
        Returns: List of alive IP addresses
        """
        if not targets:
            self.logger("No targets provided", "WARN")
            self.finished.set()
            return []

        # Reset state
        self.total = len(targets)
        self.done = 0
        self.finished.clear()

        # For individual IPs, run nmap with all targets at once
        target_str = " ".join(targets)
        self.logger(f"[NMAP-SN] Scanning {len(targets)} target(s)", "INFO")

        alive_ips = self._run_nmap_sn(target_str)

        # Populate alive_queue
        for ip in alive_ips:
            self.alive_queue.put(ip)

        self.done = self.total
        if self.progress_cb:
            self.progress_cb("ping", 100)

        # Store count for external consumers
        self.alive_total = len(alive_ips)

        self.finished.set()

        # Summary
        self.logger(
            f"[NMAP-SN] Hoàn tất: {len(alive_ips)} host đang hoạt động (from {self.total} targets)",
            "SUCCESS"
        )
        
        return alive_ips

    def discover_cidr(self, cidr_range: str) -> List[str]:
        """
        Discover alive hosts in a CIDR range (e.g., 192.168.1.0/24).
        Much faster than discover() for large subnets.
        
        Returns: List of alive IP addresses
        """
        self.finished.clear()
        self.logger(f"[NMAP-SN] Scanning CIDR range: {cidr_range}", "INFO")

        alive_ips = self._run_nmap_sn(cidr_range)

        # Populate alive_queue
        for ip in alive_ips:
            self.alive_queue.put(ip)

        self.total = 1  # Simplified progress for CIDR scans
        self.done = 1

        if self.progress_cb:
            self.progress_cb("ping", 100)

        # Store count for external consumers
        self.alive_total = len(alive_ips)

        self.finished.set()

        # Summary
        self.logger(
            f"[NMAP-SN] Hoàn tất: {len(alive_ips)} host đang hoạt động trong {cidr_range}",
            "SUCCESS"
        )
        
        return alive_ips

    def _ping_one(self, ip: str) -> bool:
        """Ping a single IP with OS-appropriate flags. Returns True if alive."""
        import platform
        system = platform.system().lower()

        success_count = 0
        for attempt in range(max(1, int(self.retries))):
            try:
                if system == "windows":
                    # -n count, -w timeout(ms)
                    cmd = ["ping", "-n", "1", "-w", str(int(self.timeout * 1000)), ip]
                else:
                    # -c count, -W timeout(s)
                    cmd = ["ping", "-c", "1", "-W", str(int(max(1, self.timeout))), ip]

                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=max(1, int(self.timeout) + 2))

                out = proc.stdout.lower()
                if system == "windows":
                    # Windows success indicators
                    if ("reply from" in out) or ("ttl=" in out):
                        success_count += 1
                else:
                    # Unix success indicators
                    if ("1 packets transmitted, 1 received" in out) or ("bytes from" in out) or (" 1 received" in out):
                        success_count += 1
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue

        # Return True if at least one ping succeeded
        return success_count > 0

    def discover_ping(self, targets: List[str]) -> List[str]:
        """
        Discover alive hosts using parallel ICMP ping.
        Suitable for IP/CIDR-expanded lists.
        Returns list of alive IPs.
        """
        if not targets:
            self.logger("No targets provided for ping discovery", "WARN")
            return []

        alive_ips: List[str] = []

        self.total = len(targets)
        self.done = 0
        self.finished.clear()

        def worker(ip: str):
            ok = self._ping_one(ip)
            with self._lock:
                self.done += 1
                if ok:
                    alive_ips.append(ip)
                    self.alive_queue.put(ip)
                if self.progress_cb:
                    try:
                        percent = int(self.done * 100 / self.total)
                        self.progress_cb("ping", percent)
                    except Exception:
                        pass

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=int(self.workers)) as ex:
            for ip in targets:
                ex.submit(worker, ip)

        self.alive_total = len(alive_ips)
        self.finished.set()

        self.logger(f"[PING] Hoàn tất: {len(alive_ips)} host đang hoạt động (from {self.total} targets)", "SUCCESS")
        return alive_ips
