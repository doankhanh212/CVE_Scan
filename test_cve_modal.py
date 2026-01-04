#!/usr/bin/env python3
"""
Test script for CVE detail modal integration
Tests the /api/cve/{cve_id}/analysis endpoint
"""

import requests
import json
import sys

def test_cve_analysis():
    """Test CVE analysis API"""
    
    print("=" * 60)
    print("CVE Detail Modal Integration Test")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # First, fetch vulnerabilities to get a real CVE ID
    print("\n1. Fetching vulnerabilities list...")
    try:
        response = requests.get(f"{base_url}/api/vulnerabilities", timeout=5)
        if response.status_code != 200:
            print(f"❌ Failed to fetch vulnerabilities: {response.status_code}")
            return False
        
        vuln_data = response.json()
        vulnerabilities = vuln_data.get("vulnerabilities", [])
        
        if not vulnerabilities:
            print("❌ No vulnerabilities found in system")
            return False
        
        # Get first CVE
        first_cve = vulnerabilities[0]
        cve_id = first_cve.get("cve_id")
        print(f"✓ Found {len(vulnerabilities)} vulnerabilities")
        print(f"  Testing with: {cve_id}")
        
    except Exception as e:
        print(f"❌ Error fetching vulnerabilities: {e}")
        return False
    
    # Test CVE analysis endpoint
    print(f"\n2. Testing /api/cve/{cve_id}/analysis endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/cve/{cve_id}/analysis",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        analysis = response.json()
        
        # Validate response structure
        required_fields = ["cve_id", "title", "description", "cvss", "owasp", "mitre", "scp", "recommendations", "risk_score"]
        missing = [f for f in required_fields if f not in analysis]
        
        if missing:
            print(f"❌ Missing fields: {missing}")
            return False
        
        print("✓ Response structure valid")
        print(f"\n3. Response Details:")
        print(f"  • CVE ID: {analysis['cve_id']}")
        print(f"  • Title: {analysis['title'][:60]}...")
        print(f"  • Description: {analysis['description'][:60]}...")
        print(f"  • Risk Score: {analysis['risk_score']}/10")
        print(f"  • CVSS versions: {list(analysis['cvss'].keys())}")
        print(f"  • OWASP mappings: {len(analysis['owasp'])} category(ies)")
        print(f"  • MITRE tactics: {len(analysis['mitre'])} tactic(s)")
        print(f"  • Secure Coding Practices: {len(analysis['scp'])} practice(ies)")
        print(f"  • Recommendations: {len(analysis['recommendations'])} item(s)")
        
        # Validate OWASP format
        if analysis['owasp']:
            print(f"\n4. OWASP Mappings:")
            for owasp in analysis['owasp'][:3]:
                print(f"  • {owasp.get('category')} - {owasp.get('name')}")
                print(f"    Risk: {owasp.get('risk_rating')}")
        
        # Validate MITRE format
        if analysis['mitre']:
            print(f"\n5. MITRE ATT&CK Mappings:")
            for tactic, techniques in list(analysis['mitre'].items())[:2]:
                print(f"  • {tactic}:")
                for tech in techniques[:2]:
                    print(f"    - {tech}")
        
        # Validate SCP format
        if analysis['scp']:
            print(f"\n6. Secure Coding Practices:")
            for practice in analysis['scp'][:2]:
                print(f"  • {practice.get('practice')}")
                print(f"    Category: {practice.get('category')}")
                print(f"    Severity: {practice.get('severity')}")
        
        # Validate CVSS details
        print(f"\n7. CVSS Details:")
        for version, details in analysis['cvss'].items():
            if details:
                score = details.get('base_score', 'N/A')
                vector = details.get('vector', 'N/A')[:40]
                print(f"  • v{version}: Score={score}, Vector={vector}...")
        
        # Validate recommendations
        if analysis['recommendations']:
            print(f"\n8. Recommendations:")
            for rec in analysis['recommendations'][:3]:
                print(f"  • {rec[:70]}...")
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_cve_analysis()
    sys.exit(0 if success else 1)
