# web/utils/scan_persistence.py
"""
JSON-based Scan Persistence Layer
Lưu scan state vào file, reload lại khi server start
"""

import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class ScanPersistence:
    """
    Quản lý lưu/tải scan data từ JSON files
    
    Structure:
    data/
     ├── scans/
     │    ├── scan_<uuid>.json
     │    └── scan_<uuid>.json
     └── index.json
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.scans_dir = self.data_dir / "scans"
        self.index_file = self.data_dir / "index.json"
        self.lock = threading.RLock()
        
        # Create directories if not exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.scans_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize index if not exist
        if not self.index_file.exists():
            self._save_index({})
    
    def _load_index(self) -> Dict[str, Any]:
        """Load scan index from index.json"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f) or {}
        except Exception as e:
            print(f"[WARNING] Error loading index: {e}")
        return {}
    
    def _save_index(self, index: Dict[str, Any]):
        """Save scan index to index.json"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Error saving index: {e}")
    
    def _load_scan_file(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Load individual scan file"""
        scan_file = self.scans_dir / f"scan_{scan_id}.json"
        try:
            if scan_file.exists():
                with open(scan_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[WARNING] Error loading scan {scan_id}: {e}")
        return None
    
    def _save_scan_file(self, scan_id: str, scan_data: Dict[str, Any]):
        """Save individual scan file"""
        scan_file = self.scans_dir / f"scan_{scan_id}.json"
        try:
            with open(scan_file, 'w', encoding='utf-8') as f:
                json.dump(scan_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Error saving scan {scan_id}: {e}")
    
    def save_scan(self, scan_id: str, scan_data: Dict[str, Any]):
        """Save scan to disk (both file and index)"""
        with self.lock:
            # Save individual scan file
            self._save_scan_file(scan_id, scan_data)
            
            # Update index
            index = self._load_index()
            index[scan_id] = {
                "scan_id": scan_id,
                "status": scan_data.get("status", "unknown"),
                "hosts": scan_data.get("hosts", []),
                "authenticated": scan_data.get("authenticated", False),
                "input_mode": scan_data.get("input_mode", "IP/CIDR"),
                "progress": scan_data.get("progress", 0),
                "message": scan_data.get("message", ""),
                "start_time": scan_data.get("start_time"),
                "end_time": scan_data.get("end_time"),
                "cve_count": self._count_cves(scan_data.get("results", {})),
                "host_count": len(scan_data.get("results", {}))
            }
            self._save_index(index)
    
    def load_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Load specific scan from disk"""
        with self.lock:
            return self._load_scan_file(scan_id)
    
    def load_all_scans(self) -> Dict[str, Dict[str, Any]]:
        """Load all scans from index"""
        with self.lock:
            index = self._load_index()
            scans = {}
            for scan_id in index.keys():
                scan_data = self._load_scan_file(scan_id)
                if scan_data:
                    scans[scan_id] = scan_data
            return scans
    
    def delete_scan(self, scan_id: str):
        """Delete scan file and update index"""
        with self.lock:
            # Delete scan file
            scan_file = self.scans_dir / f"scan_{scan_id}.json"
            if scan_file.exists():
                try:
                    scan_file.unlink()
                except Exception as e:
                    print(f"❌ Error deleting scan file {scan_id}: {e}")
            
            # Update index
            index = self._load_index()
            if scan_id in index:
                del index[scan_id]
                self._save_index(index)
    
    def cleanup_old_scans(self, keep_count: int = 100):
        """Cleanup old scans, keep only recent ones"""
        with self.lock:
            index = self._load_index()
            
            # Sort by start_time descending
            sorted_scans = sorted(
                index.items(),
                key=lambda x: x[1].get("start_time", ""),
                reverse=True
            )
            
            # Delete old ones
            for scan_id, _ in sorted_scans[keep_count:]:
                self.delete_scan(scan_id)
    
    @staticmethod
    def _count_cves(results: Dict[str, Any]) -> int:
        """Count total CVEs in results"""
        total = 0
        for result in results.values():
            if isinstance(result, dict):
                gui_data = result.get("gui", {})
                ports = gui_data.get("ports", [])
                for port in ports:
                    cves = port.get("cves", [])
                    total += len(cves)
        return total
