import subprocess
import logging
import re
from typing import List

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class RustScanScanner:
    """
    RustScan wrapper (WSL)
    ---------------------
    - Fast port discovery
    - Parse text output (Windows + WSL compatible)
    """

    def __init__(self, timeout=1500, ulimit=5000):
        self.timeout = timeout
        self.ulimit = ulimit

    # ==================================================
    def scan(self, target: str) -> List[int]:
        cmd = [
            "wsl",
            "rustscan",
            "-a", target,
            "--ulimit", str(self.ulimit),
            "--timeout", str(self.timeout)
        ]
    
        logger.info("Running RustScan: %s", " ".join(cmd))
    
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout + 10
            )
        except Exception as e:
            logger.error("RustScan execution failed: %s", e)
            return []
    
        output = ""
        if proc.stdout:
            output = proc.stdout.decode("utf-8", errors="ignore")
    
        return self._parse_output(output)
    

    # ==================================================
    def _parse_output(self, output: str) -> List[int]:
        """
        Parse RustScan text output:
        Example line:
        Open 192.168.100.1:22
        """

        ports = set()

        for line in output.splitlines():
            line = line.strip()

            # Match: Open IP:PORT
            match = re.search(r"Open\s+\S+:(\d+)", line)
            if match:
                try:
                    ports.add(int(match.group(1)))
                except ValueError:
                    continue

        if ports:
            logger.info("RustScan found %d open ports", len(ports))
        else:
            logger.warning("RustScan found no open ports")

        return sorted(ports)
