# modules/progress_tracker.py
"""
Progress Tracker - Quản lý progress cho các giai đoạn khác nhau
Hỗ trợ 2 chế độ đầu vào (IP/CIDR vs Hostname) và 2 chế độ quét (Basic vs Authenticated)
"""


class ProgressTracker:
    """
    PROGRESS MAPPING STRATEGIES
    
    ===== BASIC SCAN (UNAUTHENTICATED) =====
    
    Mode 1: IP/CIDR Input (skip asset discovery)
    ├─ 0-20%:    Host Discovery (Ping)
    ├─ 20-80%:   Port Scanning + Service Detection
    └─ 80-100%:  CVE Mapping + Report Generation
    
    Mode 2: Hostname Input (with asset discovery)
    ├─ 0-15%:    Asset Discovery (DNS, WHOIS, Reverse DNS, CIDR expansion)
    ├─ 15-35%:   Host Discovery (Ping)
    ├─ 35-80%:   Port Scanning + Service Detection
    └─ 80-100%:  CVE Mapping + Report Generation
    
    ===== AUTHENTICATED SCAN =====
    
    Mode 1: IP/CIDR Input
    ├─ 0-30%:    SSH/WinRM connection + Software inventory
    ├─ 30-70%:   CPE building + CVE Matching
    └─ 70-100%:  Report Generation
    
    Mode 2: Hostname Input
    ├─ 0-10%:    Asset Discovery
    ├─ 10-40%:   SSH/WinRM connection + Software inventory
    ├─ 40-80%:   CPE building + CVE Matching
    └─ 80-100%:  Report Generation
    """
    
    def __init__(self, scan_type: str = "basic", input_mode: str = "IP/CIDR"):
        """
        Args:
            scan_type: "basic" | "authenticated"
            input_mode: "IP/CIDR" | "Hostname (Domain)"
        """
        self.scan_type = scan_type
        self.input_mode = input_mode
        self.current_phase = None
        self.current_percent = 0
    
    def get_overall_percent(self, phase: str, phase_percent: int) -> int:
        """
        Convert phase progress to overall progress
        
        Args:
            phase: phase name (asset_discovery, ping, scan, cve_mapping, report)
            phase_percent: 0-100 within the phase
            
        Returns:
            overall_percent: 0-100 overall
        """
        if self.scan_type == "authenticated":
            return self._auth_progress(phase, phase_percent)
        else:
            return self._basic_progress(phase, phase_percent)
    
    def _basic_progress(self, phase: str, phase_percent: int) -> int:
        """Progress for basic (unauthenticated) scan"""
        
        if self.input_mode == "IP/CIDR":
            # Skip asset discovery
            # 0-20%:    Host Discovery (Ping)
            # 20-80%:   Port Scanning + Service Detection
            # 80-100%:  CVE Mapping + Report Generation
            ranges = {
                "ping": (0, 20),
                "scan": (20, 80),
                "cve_mapping": (80, 100),
                "report": (90, 100),
            }
        else:
            # With asset discovery
            # 0-15%:    Asset Discovery (DNS, WHOIS, Reverse DNS, CIDR expansion)
            # 15-35%:   Host Discovery (Ping)
            # 35-80%:   Port Scanning + Service Detection
            # 80-100%:  CVE Mapping + Report Generation
            ranges = {
                "asset_discovery": (0, 15),
                "ping": (15, 35),
                "scan": (35, 80),
                "cve_mapping": (80, 100),
                "report": (90, 100),
            }
        
        if phase not in ranges:
            return self.current_percent
        
        start, end = ranges[phase]
        range_size = end - start
        overall = int(start + (phase_percent / 100.0) * range_size)
        self.current_percent = overall
        return overall
    
    def _auth_progress(self, phase: str, phase_percent: int) -> int:
        """Progress for authenticated scan"""
        
        if self.input_mode == "IP/CIDR":
            # Skip asset discovery
            # 0-30%:    SSH/WinRM connection + Software inventory
            # 30-70%:   CPE building + CVE Matching
            # 70-100%:  Report Generation
            ranges = {
                "auth": (0, 30),
                "cve_mapping": (30, 70),
                "report": (70, 100),
            }
        else:
            # With asset discovery
            # 0-10%:    Asset Discovery
            # 10-40%:   SSH/WinRM connection + Software inventory
            # 40-80%:   CPE building + CVE Matching
            # 80-100%:  Report Generation
            ranges = {
                "asset_discovery": (0, 10),
                "auth": (10, 40),
                "cve_mapping": (40, 80),
                "report": (80, 100),
            }
        
        if phase not in ranges:
            return self.current_percent
        
        start, end = ranges[phase]
        range_size = end - start
        overall = int(start + (phase_percent / 100.0) * range_size)
        self.current_percent = overall
        return overall
    
    def report_progress(self, phase: str, phase_percent: int, progress_cb=None, message: str = None) -> int:
        """
        Calculate and report progress
        
        Args:
            phase: phase name
            phase_percent: 0-100 within phase
            progress_cb: callback function(phase, percent, message)
            message: optional message
            
        Returns:
            overall_percent
        """
        overall = self.get_overall_percent(phase, phase_percent)
        
        if progress_cb:
            try:
                # Report with phase name and overall percent
                progress_cb("progress", overall, message or f"{phase}: {phase_percent}%")
            except Exception:
                pass
        
        return overall
