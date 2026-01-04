# web/services/scan_service.py
"""
ScanService - TRÁI TIM của Flask
Thay thế toàn bộ logic trong gui.run_scan()
"""

import os
import sys
import socket
import ipaddress
import re
import threading
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# Add parent directory to path để import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from modules.scan_manager import ScanManager
from modules.config_manager import ConfigManager
from modules.progress_tracker import ProgressTracker
from web.utils.result_normalizer import normalize_for_api
from web.utils.scan_persistence import ScanPersistence
  

# =====================================================================
# VALIDATION HOST/IP (từ gui.py)
# =====================================================================
def is_valid_host(host):
    """Check if host is valid IP, CIDR, or hostname"""
    # Check for CIDR notation
    if "/" in host:
        try:
            ipaddress.ip_network(host, strict=False)
            return True
        except Exception:
            return False
    
    # Check for plain IP
    ip_regex = r"^(?:\d{1,3}\.){3}\d{1,3}$"
    if re.match(ip_regex, host):
        return True
    
    # Check for hostname
    hostname_regex = (
        r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
        r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
    )
    return bool(re.match(hostname_regex, host))


# =====================================================================
# SCAN SERVICE - TRÁI TIM CỦA FLASK
# =====================================================================
class ScanService:
    """
    Service layer để gọi ScanManager
    Quản lý scan jobs, progress, và results
    """
    
    MAX_CONCURRENT_SCANS = 3  # Limit concurrent scans to prevent overload
    MAX_LOGS_PER_SCAN = 500   # Limit log entries per scan
    
    # Log level priority mapping (lower = more verbose)
    LOG_LEVELS = {
        "debug": 0,
        "info": 1,
        "warning": 2,
        "error": 3
    }
    
    def __init__(self):
        self.scans: Dict[str, Dict[str, Any]] = {}  # scan_id -> scan_info
        self.lock = threading.RLock()  # Use RLock for nested locking
        self.config = ConfigManager.load()
        
        # Initialize persistence layer
        self.persistence = ScanPersistence(data_dir="data")
        
        # Load existing scans from disk
        self._load_persisted_scans()
    
    def reload_scans_from_disk(self):
        """Reload all scans from disk (useful after external modifications)"""
        print("[INFO] Reloading scans from disk...")
        self._load_persisted_scans()
        self._invalidate_cache()
        print(f"[SUCCESS] Reloaded {len(self.scans)} scans from disk")
    
    def _load_persisted_scans(self):
        """Load all scans from disk into memory"""
        try:
            all_scans = self.persistence.load_all_scans()
            fixed = 0
            with self.lock:
                self.scans = all_scans
                # Heal scans that were marked running but have no thread (e.g., after restart)
                for sid, scan in self.scans.items():
                    status = scan.get("status")
                    progress = int(scan.get("progress", 0))
                    results_present = bool(scan.get("results"))

                    if status == "running":
                        # If we have results or already reached the end, treat as completed
                        if scan.get("end_time") or progress >= 100 or results_present:
                            scan["status"] = "completed"
                            scan["progress"] = 100
                            scan["end_time"] = scan.get("end_time") or datetime.now().isoformat()
                            scan["message"] = scan.get("message") or "Completed (restored)"
                        else:
                            # Otherwise mark as stopped to avoid stuck running state
                            scan["status"] = "stopped"
                            scan["message"] = scan.get("message") or "Stopped (restored)"
                        fixed += 1

                    # Upgrade previously restored stopped scans that clearly finished
                    elif status == "stopped" and scan.get("message") == "Stopped (restored)" and results_present:
                        scan["status"] = "completed"
                        scan["progress"] = 100
                        scan["end_time"] = scan.get("end_time") or datetime.now().isoformat()
                        scan["message"] = "Completed (restored)"
                        fixed += 1
            if fixed:
                # Persist healed states
                for sid in list(self.scans.keys()):
                    self._save_scan_to_disk(sid, force=True)
            print(f"[SUCCESS] Loaded {len(all_scans)} scans from disk (healed {fixed} orphaned runs)")
        except Exception as e:
            print(f"[WARNING] Error loading persisted scans: {e}")
    
    def create_scan(
        self,
        hosts: List[str],
        authenticated: bool = False,
        auth_data: Optional[Dict[str, Any]] = None,
        input_mode: str = "IP/CIDR"
    ) -> str:
        """
        Tạo scan job mới
        
        Returns:
            scan_id: UUID của scan job
        """
        scan_id = str(uuid.uuid4())
        
        # Validate hosts
        valid_hosts = []
        for h in hosts:
            h = h.strip()
            if not h:
                continue
            if not is_valid_host(h):
                continue
            valid_hosts.append(h)
        
        if not valid_hosts:
            raise ValueError("Không có host hợp lệ để quét")
        
        # Resolve hostnames to IPv4
        resolved_targets = []
        alias_map = {}
        
        for h in valid_hosts:
            resolved_ip = None
            display = h
            
            if input_mode == "IP/CIDR":
                # IP/CIDR MODE - pass through IP and CIDR without DNS resolution
                if "/" in h:
                    try:
                        ipaddress.ip_network(h, strict=False)
                        resolved_targets.append(h)
                        alias_map[h] = display
                        continue
                    except Exception:
                        continue
                
                # Check if it's a plain IP address
                try:
                    ipaddress.ip_address(h)
                    resolved_ip = h
                except Exception:
                    continue
            else:
                # HOSTNAME MODE - resolve hostnames
                if "/" in h:
                    try:
                        ipaddress.ip_network(h, strict=False)
                        resolved_targets.append(h)
                        alias_map[h] = display
                        continue
                    except Exception:
                        pass
                
                # Check if it's a plain IP address
                try:
                    ipaddress.ip_address(h)
                    resolved_ip = h
                except Exception:
                    # It's a hostname - try to resolve
                    try:
                        resolved_ip = socket.gethostbyname(h)
                        display = f"{h} ({resolved_ip})"
                    except Exception:
                        continue
            
            if resolved_ip:
                if resolved_ip not in alias_map:
                    alias_map[resolved_ip] = display
                resolved_targets.append(resolved_ip)
        
        if not resolved_targets:
            raise ValueError("Không có host hợp lệ sau khi resolve")
        
        # Tạo scan job
        scan_info = {
            "scan_id": scan_id,
            "status": "pending",  # pending, running, completed, failed
            "hosts": resolved_targets,
            "alias_map": alias_map,
            "authenticated": authenticated,
            "auth_data": auth_data,
            "input_mode": input_mode,
            "progress": 0,
            "message": "Đang chờ bắt đầu...",
            "results": {},
            "start_time": None,
            "end_time": None,
            "error": None,
            "thread": None,
            "stop_event": threading.Event()
        }
        
        with self.lock:
            self.scans[scan_id] = scan_info
        
        # Save to disk (non-serializable objects excluded)
        self._save_scan_to_disk(scan_id)
        
        return scan_id
    
    def start_scan(self, scan_id: str):
        """
        Bắt đầu scan trong background thread
        """
        with self.lock:
            if scan_id not in self.scans:
                raise ValueError(f"Scan {scan_id} không tồn tại")
            
            scan_info = self.scans[scan_id]
            if scan_info["status"] != "pending":
                raise ValueError(f"Scan {scan_id} đã được chạy hoặc đang chạy")
            
            # Check concurrent scan limit
            running_count = sum(1 for s in self.scans.values() if s["status"] == "running")
            if running_count >= self.MAX_CONCURRENT_SCANS:
                raise ValueError(f"Đã đạt giới hạn {self.MAX_CONCURRENT_SCANS} scan đồng thời. Vui lòng đợi.")
            
            scan_info["status"] = "running"
            scan_info["start_time"] = datetime.now().isoformat()
        
        # Chạy scan trong background thread
        thread = threading.Thread(
            target=self._run_scan,
            args=(scan_id,),
            daemon=True
        )
        thread.start()
        
        with self.lock:
            self.scans[scan_id]["thread"] = thread
    
    def _save_scan_to_disk(self, scan_id: str, force=False):
        """
        Helper: Save scan to disk, excluding non-serializable objects
        force=True: Save regardless, False: Save only if status changed
        """
        with self.lock:
            if scan_id not in self.scans:
                return
            
            scan_info = self.scans[scan_id].copy()
            # Remove non-JSON-serializable objects
            scan_info.pop("thread", None)
            scan_info.pop("stop_event", None)
        
        # Save outside of lock to avoid blocking
        try:
            self.persistence.save_scan(scan_id, scan_info)
        except Exception as e:
            print(f"[ERROR] Error saving scan {scan_id}: {e}")
    
    def _run_scan(self, scan_id: str):
        """
        Chạy scan thực tế (trong background thread)
        Gọi ScanManager.scan() - TRÁI TIM
        """
        try:
            with self.lock:
                scan_info = self.scans[scan_id]
                resolved_targets = scan_info["hosts"]
                alias_map = scan_info["alias_map"]
                authenticated = scan_info["authenticated"]
                auth_data = scan_info["auth_data"]
                input_mode = scan_info["input_mode"]
                stop_event = scan_info["stop_event"]
            
            # Reload config để lấy settings mới nhất (bao gồm API key)
            self.config = ConfigManager.load()
            
            # Get configured log verbosity level
            log_verbosity = self.config.get("log_verbosity", "info").lower()
            verbosity_threshold = self.LOG_LEVELS.get(log_verbosity, 1)
            
            # Log config status for troubleshooting
            has_api_key = bool(self.config.get('nvd_api_key'))
            use_local_db = self.config.get('use_local_db', False)
            
            # Tạo logger callback - không khóa lock để tránh block API
            def logger(msg, level="INFO"):
                # Filter logs based on verbosity setting
                level_normalized = level.upper()
                level_key = level.lower()
                
                # Map log levels to priority
                level_priority = self.LOG_LEVELS.get(level_key, 1)
                
                # Skip logs below verbosity threshold
                if level_priority < verbosity_threshold:
                    return
                
                # Append log outside of lock to avoid blocking API requests
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": level_normalized,
                    "message": msg
                }
                
                with self.lock:
                    if scan_id in self.scans:
                        if "logs" not in self.scans[scan_id]:
                            self.scans[scan_id]["logs"] = []
                        # Keep only last MAX_LOGS_PER_SCAN to prevent memory bloat
                        logs = self.scans[scan_id]["logs"]
                        if len(logs) >= self.MAX_LOGS_PER_SCAN:
                            # Remove oldest 20% when limit reached
                            del logs[:self.MAX_LOGS_PER_SCAN // 5]
                        logs.append(log_entry)
            
            # Initialize Progress Tracker
            progress_tracker = ProgressTracker(
                scan_type="authenticated" if authenticated else "basic",
                input_mode=input_mode or "Hostname (Domain)"
            )
            logger(f"🎯 Scan initialized - API key: {'✓' if has_api_key else '✗'}, Local DB: {use_local_db}, Log level: {log_verbosity}", "SYSTEM")
            
            # Tạo progress callback sử dụng ProgressTracker
            def progress_cb(phase, percent, message=None):
                with self.lock:
                    if scan_id in self.scans:
                        overall = progress_tracker.get_overall_percent(phase, percent)
                        self.scans[scan_id]["progress"] = int(overall)
                        if message:
                            self.scans[scan_id]["message"] = str(message)
                
                # Save progress to disk periodically (outside lock)
                if scan_id and percent % 10 == 0:
                    self._save_scan_to_disk(scan_id)
            
            # Tạo host result callback
            def host_result_cb(host, result):
                with self.lock:
                    if scan_id in self.scans:
                        label = self.scans[scan_id]["alias_map"].get(host, host)
                        self.scans[scan_id]["results"][label] = result
                
                # Don't save to disk on every host - too frequent during CVE mapping
                # Will be saved on completion instead
            
            # Instantiate ScanManager
            try:
                manager = ScanManager(
                    self.config,
                    logger=logger,
                    progress_cb=progress_cb,
                    stop_event=stop_event
                )
            except TypeError:
                manager = ScanManager(
                    self.config,
                    logger=logger,
                    progress_cb=progress_cb
                )
            
            # GỌI SCANMANAGER.SCAN() - TRÁI TIM
            logger("🖥️ Bắt đầu quá trình quét", "SYSTEM")
            start_time = time.time()
            
            try:
                results = manager.scan(
                    targets=resolved_targets,
                    authenticated=authenticated,
                    auth_data=auth_data,
                    host_result_cb=host_result_cb,
                    input_mode=input_mode
                )
            except TypeError:
                results = manager.scan(
                    targets=resolved_targets,
                    authenticated=authenticated,
                    auth_data=auth_data,
                    host_result_cb=host_result_cb
                )
            
            # Xử lý results
            elapsed = int(time.time() - start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            
            logger(f"Scan completed, processing {len(results)} result(s)", "INFO")
            
            # Đảm bảo tất cả results được lưu
            with self.lock:
                if scan_id in self.scans:
                    # Results đã được lưu qua host_result_cb
                    # Nhưng đảm bảo không bị mất
                    for item in results:
                        host_ip = item["host"]
                        label = scan_info["alias_map"].get(host_ip, host_ip)
                        if label not in self.scans[scan_id]["results"]:
                            self.scans[scan_id]["results"][label] = item["result"]
                    
                    # Normalize all results at once
                    try:
                        import traceback
                        logger("Normalizing results...", "INFO")
                        normalized = normalize_for_api(self.scans[scan_id]["results"])
                        # Update each host with normalized data
                        for label, host_data in normalized["hosts"].items():
                            self.scans[scan_id]["results"][label] = host_data
                        self.scans[scan_id]["summary"] = normalized["summary"]
                        logger("Results normalized successfully", "SUCCESS")
                    except Exception as norm_err:
                        import traceback
                        logger(f"⚠️ Normalization warning: {norm_err}", "WARN")
                        logger(f"Normalization traceback: {traceback.format_exc()}", "DEBUG")
                        # Keep raw results if normalization fails
                        pass
                    
                    self.scans[scan_id]["status"] = "completed"
                    self.scans[scan_id]["progress"] = 100
                    self.scans[scan_id]["message"] = f"Hoàn tất ({mins}m {secs}s)"
                    self.scans[scan_id]["end_time"] = datetime.now().isoformat()
            
            logger(f"Scan status set to completed", "SUCCESS")
            
            # Save final result to disk (outside lock)
            self._save_scan_to_disk(scan_id)
            
            logger("==================== SUMMARY ====================", "SYSTEM")
            logger(f"Host đã quét: {len(results)}", "SYSTEM")
            logger(f"Thời gian scan: {mins}m {secs}s", "SYSTEM")
            logger("================================================", "SYSTEM")
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            with self.lock:
                if scan_id in self.scans:
                    self.scans[scan_id]["status"] = "failed"
                    self.scans[scan_id]["error"] = error_msg
                    self.scans[scan_id]["end_time"] = datetime.now().isoformat()
            
            # Save error state to disk (outside lock)
            self._save_scan_to_disk(scan_id)
            
            logger(f"Lỗi scan: {error_msg}", "ERROR")
            logger(error_trace, "ERROR")
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Lấy status của scan"""
        with self.lock:
            if scan_id not in self.scans:
                return None
            
            scan_info = self.scans[scan_id].copy()
            # Không trả về thread object
            scan_info.pop("thread", None)
            scan_info.pop("stop_event", None)
            return scan_info
    
    def get_scan_results(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Lấy results của scan (chỉ khi completed)"""
        with self.lock:
            if scan_id not in self.scans:
                return None
            
            scan_info = self.scans[scan_id]
            if scan_info["status"] != "completed":
                return None
            
            return scan_info["results"]
    
    def stop_scan(self, scan_id: str):
        """Dừng scan"""
        with self.lock:
            if scan_id not in self.scans:
                raise ValueError(f"Scan {scan_id} không tồn tại")
            
            scan_info = self.scans[scan_id]
            if scan_info["status"] not in ["pending", "running"]:
                return
            
            scan_info["stop_event"].set()
            scan_info["status"] = "stopped"
            scan_info["end_time"] = datetime.now().isoformat()

    def delete_scan(self, scan_id: str):
        """Xóa scan khỏi bộ nhớ và tệp lưu trữ"""
        with self.lock:
            if scan_id in self.scans:
                # cố gắng dừng trước nếu còn chạy
                scan_info = self.scans[scan_id]
                try:
                    scan_info.get("stop_event").set()
                except Exception:
                    pass
                self.scans.pop(scan_id, None)
        
        # Invalidate cache for this scan
        self._invalidate_cache()
        
        # xóa khỏi đĩa (không giữ lock để tránh block)
        try:
            self.persistence.delete_scan(scan_id)
        except Exception as e:
            print(f"[WARN] Delete scan {scan_id} failed: {e}")
    
    def list_scans(self, include_results: bool = False) -> List[Dict[str, Any]]:
        """List tất cả scans (lightweight by default)"""
        with self.lock:
            scans_list = []
            for scan_id, scan_info in self.scans.items():
                info = scan_info.copy()
                info.pop("thread", None)
                info.pop("stop_event", None)
                
                # Exclude heavy results by default to reduce memory/bandwidth
                # But keep summary (lightweight and useful for stats)
                if not include_results:
                    info.pop("results", None)
                    info.pop("logs", None)  # Also exclude logs from list view
                
                scans_list.append(info)
            return scans_list
    
    def create_and_start_scan(
        self,
        hosts: List[str],
        authenticated: bool = False,
        auth_data: Optional[Dict[str, Any]] = None,
        input_mode: str = "IP/CIDR"
    ) -> str:
        """Convenience method: create and immediately start scan."""
        scan_id = self.create_scan(hosts, authenticated, auth_data, input_mode)
        self.start_scan(scan_id)
        return scan_id
    
    def get_scan_logs(self, scan_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get logs for a specific scan."""
        with self.lock:
            if scan_id not in self.scans:
                return None
            return self.scans[scan_id].get("logs", [])
    
    def _invalidate_cache(self):
        """Invalidate caches when scans change"""
        try:
            from web.utils.cache import stats_cache, list_cache
            stats_cache.clear()
            list_cache.clear()
        except ImportError:
            pass  # Cache module not available
    
    def get_running_count(self) -> int:
        """Get count of currently running scans"""
        with self.lock:
            return sum(1 for s in self.scans.values() if s["status"] == "running")


# Global instance
scan_service = ScanService()

