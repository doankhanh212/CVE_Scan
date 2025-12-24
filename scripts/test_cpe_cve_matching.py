"""
Test CPE building and CVE matching for Windows software enumeration results
"""
import sys
sys.path.insert(0, "c:\\Users\\dhqkh\\Documents\\CVE_Scan")

from modules.cve.cpe_builder import build_cpe
from modules.cve.cve_matcher import CVEMatcher
from modules.config_manager import ConfigManager

# Sample software from your scan
test_software = [
    ("VLC media player", "3.0.16"),
    ("Git", "2.50.1"),
    ("Python", "3.13.3"),
    ("VMware Workstation", "17.6.3"),
    ("WinRAR 6.24 (64-bit)", "6.24.0"),
    ("Wireshark", "4.4.9"),
    ("Node.js", "24.12.0"),
    ("Google Chrome", "143.0.7499.148"),
    ("Mozilla Firefox", "14.0.1"),
    ("Nmap", "7.95"),
]

# Load config
config = ConfigManager.load()

# Initialize CVE matcher
matcher = CVEMatcher(
    api_key=config.get("nvd_api_key"),
    local_db_path=(config.get("local_db_path") if config.get("use_local_db") else None)
)

use_remote = not bool(config.get("use_local_db", False))

print(f"Testing CPE building and CVE matching")
print(f"Using remote CPE API: {use_remote}")
print(f"Using local DB: {config.get('use_local_db', False)}")
print(f"Local DB path: {config.get('local_db_path', 'N/A')}")
print("=" * 80)

for name, version in test_software:
    print(f"\n[TEST] {name} v{version}")
    
    # Build CPE
    cpe = build_cpe(name, version, use_remote=use_remote)
    print(f"  CPE: {cpe}")
    
    if not cpe or cpe == "N/A":
        print(f"  ❌ CPE build failed")
        continue
    
    # Match CVE
    cves = matcher.match_by_cpe(cpe)
    if cves:
        print(f"  ✅ Found {len(cves)} CVE(s)")
        # Show first 3 CVEs
        for idx, cve in enumerate(cves[:3]):
            cve_id = cve.get("id", "N/A")
            severity = cve.get("severity")
            if isinstance(severity, dict):
                severity = severity.get("label", "N/A")
            print(f"     {idx+1}. {cve_id} ({severity})")
        if len(cves) > 3:
            print(f"     ... and {len(cves) - 3} more")
    else:
        print(f"  ⚠️  No CVEs found")

print("\n" + "=" * 80)
print("Test completed")
