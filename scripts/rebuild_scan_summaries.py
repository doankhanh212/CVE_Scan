"""
Rebuild summary cho tất cả scans đã hoàn thành nhưng thiếu summary field
"""

import json
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.utils.result_normalizer import normalize_for_api


def rebuild_summaries():
    """Rebuild summary cho tất cả scan files"""
    scans_dir = project_root / "data" / "scans"
    
    if not scans_dir.exists():
        print(f"[ERROR] Scans directory not found: {scans_dir}")
        return
    
    scan_files = list(scans_dir.glob("scan_*.json"))
    
    if not scan_files:
        print("[INFO] No scan files found")
        return
    
    print(f"[INFO] Found {len(scan_files)} scan files")
    print("=" * 60)
    
    rebuilt = 0
    skipped = 0
    errors = 0
    
    for scan_file in scan_files:
        try:
            # Load scan data
            with open(scan_file, 'r', encoding='utf-8') as f:
                scan_data = json.load(f)
            
            scan_id = scan_data.get("scan_id", "unknown")
            status = scan_data.get("status", "unknown")
            
            # Skip if not completed
            if status != "completed":
                print(f"[SKIP] {scan_id[:8]}... - Status: {status}")
                skipped += 1
                continue
            
            # Skip if already has summary
            if scan_data.get("summary"):
                print(f"[SKIP] {scan_id[:8]}... - Already has summary")
                skipped += 1
                continue
            
            # Get results
            results = scan_data.get("results", {})
            
            if not results:
                print(f"[SKIP] {scan_id[:8]}... - No results")
                skipped += 1
                continue
            
            # Normalize and extract summary
            print(f"[REBUILD] {scan_id[:8]}... - Rebuilding summary...")
            
            normalized = normalize_for_api(results)
            summary = normalized["summary"]
            
            # Update scan data with summary
            scan_data["summary"] = summary
            
            # Also update results with normalized hosts structure
            for label, host_data in normalized["hosts"].items():
                scan_data["results"][label] = host_data
            
            # Save back to file
            with open(scan_file, 'w', encoding='utf-8') as f:
                json.dump(scan_data, f, indent=2, ensure_ascii=False)
            
            # Print summary info
            print(f"  ✓ Hosts: {summary['hosts_scanned']}")
            print(f"  ✓ Ports: {summary['open_ports']}")
            print(f"  ✓ CVEs: {summary['total_cves']}")
            print(f"  ✓ Critical: {summary['severity']['critical']}")
            
            rebuilt += 1
            
        except Exception as e:
            print(f"[ERROR] {scan_file.name} - {e}")
            errors += 1
    
    print("=" * 60)
    print(f"[SUMMARY]")
    print(f"  Rebuilt: {rebuilt}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total: {len(scan_files)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Rebuild Scan Summaries")
    print("=" * 60)
    rebuild_summaries()
    print("\n[DONE] Rebuild complete. Restart web app to see changes.")
