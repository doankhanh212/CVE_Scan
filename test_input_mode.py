#!/usr/bin/env python3
"""
Quick test for Input Mode (IP/CIDR vs Hostname)
"""

import ipaddress

def test_cidr_expansion():
    cidr = "192.168.100.0/24"
    
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        ips = [str(ip) for ip in network.hosts()]
        print(f"✅ CIDR {cidr} expanded to {len(ips)} IPs")
        print(f"First 5: {ips[:5]}")
        print(f"Last 5: {ips[-5:]}")
    except Exception as e:
        print(f"❌ Failed to expand CIDR: {e}")

def test_input_validation():
    test_inputs = [
        "192.168.1.1",
        "192.168.100.0/24",
        "google.com",
        "10.0.0.0/8",
        "invalid_input"
    ]
    
    for inp in test_inputs:
        is_ip = False
        is_cidr = False
        is_hostname = False
        
        # Check IP
        try:
            ipaddress.ip_address(inp)
            is_ip = True
        except:
            pass
        
        # Check CIDR
        if "/" in inp:
            try:
                ipaddress.ip_network(inp, strict=False)
                is_cidr = True
            except:
                pass
        
        # Hostname if neither IP nor CIDR
        if not is_ip and not is_cidr:
            is_hostname = True
        
        print(f"{inp:20s} → IP:{is_ip}, CIDR:{is_cidr}, Hostname:{is_hostname}")

if __name__ == "__main__":
    print("="*60)
    print("Test CIDR Expansion")
    print("="*60)
    test_cidr_expansion()
    
    print("\n" + "="*60)
    print("Test Input Validation")
    print("="*60)
    test_input_validation()
