import sys
sys.path.insert(0, r'c:\Users\dhqkh\CVE_Scan')

from web.services.scan_service import scan_service

print("=" * 60)
print("Quick API Test")
print("=" * 60)

# Test 1: list_scans without results
print("\n[1] list_scans(include_results=False):")
scans = scan_service.list_scans(include_results=False)
print(f"  Total scans: {len(scans)}")
for i, s in enumerate(scans[:2]):
    print(f"  Scan {i+1}:")
    print(f"    - status: {s.get('status')}")
    print(f"    - has_summary: {'summary' in s}")
    print(f"    - has_results: {'results' in s}")
    if 'summary' in s:
        print(f"    - summary: {s['summary']}")

# Test 2: list_scans with results
print("\n[2] list_scans(include_results=True):")
scans_full = scan_service.list_scans(include_results=True)
print(f"  Total scans: {len(scans_full)}")
for i, s in enumerate(scans_full[:1]):
    print(f"  Scan {i+1}:")
    print(f"    - status: {s.get('status')}")
    print(f"    - has_summary: {'summary' in s}")
    print(f"    - has_results: {'results' in s}")
    if 'results' in s:
        print(f"    - results keys: {list(s['results'].keys())[:3]}")
