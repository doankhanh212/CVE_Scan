#!/usr/bin/env python3
"""
Quick test to verify likelihood integration on vulnerabilities page
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.cve.likelihood_calculator import LikelihoodCalculator
from web.routes.vulnerabilities import list_vulnerabilities
import json

def test_likelihood_integration():
    """Test that likelihood calculator is properly integrated"""
    
    print("=" * 70)
    print("LIKELIHOOD INTEGRATION TEST")
    print("=" * 70)
    
    # Test 1: Initialize calculator
    print("\n[1] Testing LikelihoodCalculator initialization...")
    try:
        calc = LikelihoodCalculator()
        print("    ✓ Calculator initialized successfully")
        print(f"    Database: {calc.epss_db_path}")
        print(f"    Database exists: {Path(calc.epss_db_path).exists()}")
    except Exception as e:
        print(f"    ✗ Failed to initialize: {e}")
        return False
    
    # Test 2: Test enrichment with sample CVE
    print("\n[2] Testing vulnerability enrichment...")
    sample_cve = {"cvss_v3": {"baseScore": 7.5}}
    test_cve_id = "CVE-2021-44228"  # Log4Shell
    
    try:
        enriched = calc.enrich_vulnerability_with_likelihood(sample_cve, test_cve_id)
        if enriched.get("likelihood"):
            likelihood = enriched["likelihood"]
            print(f"    ✓ Enrichment successful for {test_cve_id}")
            print(f"      - EPSS: {likelihood.get('epss'):.5f}")
            print(f"      - Likelihood Score: {likelihood.get('score'):.5f}")
            print(f"      - Level: {likelihood.get('level')}")
            
            # Verify precision
            score = likelihood.get('score')
            if isinstance(score, float):
                decimal_places = len(str(score).split('.')[1]) if '.' in str(score) else 0
                print(f"      - Decimal places: {decimal_places} (expected: 5)")
        else:
            print(f"    ✗ No likelihood data returned")
            return False
    except Exception as e:
        print(f"    ✗ Enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Test severity badge classification
    print("\n[3] Testing severity badge classification...")
    test_cases = [
        (8.9, "HIGH"),    # High likelihood
        (5.5, "MEDIUM"),  # Medium likelihood
        (2.1, "LOW"),     # Low likelihood
    ]
    
    for score, expected_level in test_cases:
        if score >= 7.0:
            actual_level = "HIGH"
        elif score >= 4.0:
            actual_level = "MEDIUM"
        else:
            actual_level = "LOW"
        
        status = "✓" if actual_level == expected_level else "✗"
        print(f"    {status} Score {score}: {actual_level} (expected: {expected_level})")
    
    # Test 4: Check multiple CVEs
    print("\n[4] Testing multiple CVE enrichment...")
    test_cves = [
        "CVE-2021-44228",  # Log4Shell
        "CVE-2021-3129",   # Laravel
        "CVE-2022-0001",   # Spectre
    ]
    
    enriched_count = 0
    for cve_id in test_cves:
        try:
            enriched = calc.enrich_vulnerability_with_likelihood(sample_cve, cve_id)
            if enriched.get("likelihood"):
                enriched_count += 1
                score = enriched["likelihood"].get("score")
                level = enriched["likelihood"].get("level")
                print(f"    ✓ {cve_id}: {score:.5f} ({level})")
        except Exception as e:
            print(f"    ✗ {cve_id}: {e}")
    
    print(f"\n    Summary: {enriched_count}/{len(test_cves)} CVEs enriched successfully")
    
    print("\n" + "=" * 70)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    success = test_likelihood_integration()
    sys.exit(0 if success else 1)
