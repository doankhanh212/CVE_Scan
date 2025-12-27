#!/usr/bin/env python3
"""
Asset Discovery Quick Start Example

Usage:
    python scripts/test_asset_discovery.py example.com
    python scripts/test_asset_discovery.py google.com
    python scripts/test_asset_discovery.py 192.168.1.1
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from modules.discovery.asset_discovery import AssetDiscovery


def pretty_print_asset(ip: str, asset) -> None:
    """Pretty print a single asset"""
    asset_type = "IPv4" if asset.is_ipv4 else ("IPv6" if asset.is_ipv6 else "Unknown")
    print(f"\n{'='*60}")
    print(f"IP: {asset.ip} ({asset_type})")
    print(f"{'='*60}")
    
    if asset.hostnames:
        print(f"Hostnames: {', '.join(sorted(asset.hostnames))}")
    
    if asset.asn:
        print(f"ASN: {asset.asn}")
    
    if asset.cidr:
        print(f"CIDR: {asset.cidr}")
    
    if asset.org:
        print(f"Organization: {asset.org}")
    
    if asset.country:
        print(f"Country: {asset.country}")
    
    print(f"Confidence: {asset.confidence:.2%}")
    print(f"Sources: {', '.join(asset.source)}")
    print(f"Scan Priority: {asset.scan_priority} {'(SCAN)' if asset.scan_priority < 255 else '(INVENTORY ONLY)'}")


def pretty_print_assets(assets: dict) -> None:
    """Pretty print all assets"""
    if not assets:
        print("❌ No assets discovered")
        return
    
    print(f"\n✅ Discovered {len(assets)} asset(s)")
    
    for ip, asset in sorted(assets.items(), key=lambda x: x[1].confidence, reverse=True):
        pretty_print_asset(ip, asset)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <hostname|ip> [hostname2] [hostname3]")
        print(f"Examples:")
        print(f"  python {sys.argv[0]} example.com")
        print(f"  python {sys.argv[0]} google.com github.com")
        print(f"  python {sys.argv[0]} 192.168.1.1")
        sys.exit(1)
    
    targets = sys.argv[1:]
    
    print(f"\n🔍 Asset Discovery starting...")
    print(f"Targets: {', '.join(targets)}\n")
    
    # Create logger callback
    def logger_cb(msg: str, level: str = "INFO"):
        level_colors = {
            "INFO": "ℹ️",
            "SUCCESS": "✓",
            "WARN": "⚠️",
            "ERROR": "❌",
            "SYSTEM": "🔧"
        }
        print(f"{level_colors.get(level, '→')} [{level}] {msg}")
    
    # Run discovery
    try:
        discovery = AssetDiscovery(logger=logger_cb)
        assets = discovery.discover(targets)
        
        # Pretty print results
        pretty_print_assets(assets)
        
        # Show scan filtering
        scan_ips = discovery.filter_for_scan(assets)
        print(f"\n\n📊 SCAN FILTERING RESULTS")
        print(f"{'='*60}")
        print(f"Total assets: {len(assets)}")
        print(f"High-confidence (scan): {len(scan_ips)}")
        print(f"Inventory-only: {len(assets) - len(scan_ips)}")
        
        if scan_ips:
            print(f"\n🎯 IPs to scan (by priority):")
            for i, ip in enumerate(scan_ips, 1):
                asset = assets[ip]
                print(f"  {i}. {ip} (confidence: {asset.confidence:.2%}, priority: {asset.scan_priority})")
        
        # Export as JSON
        print(f"\n\n💾 EXPORTING TO inventory.json...")
        inventory = {ip: asset.to_dict() for ip, asset in assets.items()}
        with open("inventory.json", "w") as f:
            json.dump(inventory, f, indent=2)
        print("✓ Saved to inventory.json")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
