#!/usr/bin/env python3
"""Debug WHOIS lookup để tìm ra tại sao fail"""

import sys
sys.path.insert(0, '.')

print("=" * 60)
print("TEST WHOIS LOOKUP - DEBUG")
print("=" * 60)

# Test 1: Check ipwhois library
print("\n1️⃣ Check ipwhois library...")
try:
    from ipwhois import IPWhois
    print("   ✅ ipwhois có sẵn")
except ImportError as e:
    print(f"   ❌ Lỗi import: {e}")
    sys.exit(1)

# Test 2: WHOIS lookup trực tiếp
ip = '103.98.152.188'
print(f"\n2️⃣ Test WHOIS lookup cho IP: {ip}")
try:
    print("   ⏳ Đang lookup (timeout=10s)...")
    whois = IPWhois(ip, timeout=10)
    result = whois.lookup()
    
    print("   ✅ WHOIS lookup thành công!")
    print(f"      ASN: {result.get('asn')}")
    print(f"      CIDR: {result.get('cidr')}")
    print(f"      Org: {result.get('org')}")
    
except Exception as e:
    print(f"   ❌ Lỗi: {type(e).__name__}")
    print(f"   Chi tiết: {str(e)[:200]}")

# Test 3: Test qua AssetDiscovery
print(f"\n3️⃣ Test qua WHOISLookup class...")
try:
    from modules.discovery.asset_discovery import WHOISLookup
    
    whois_lookup = WHOISLookup(timeout=15)
    asn, cidr, org, success = whois_lookup.lookup_ip(ip)
    
    print(f"   Result: success={success}")
    print(f"   ASN: {asn}")
    print(f"   CIDR: {cidr}")
    print(f"   Org: {org}")
    
except Exception as e:
    print(f"   ❌ Lỗi: {e}")

print("\n" + "=" * 60)
