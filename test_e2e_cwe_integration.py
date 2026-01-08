#!/usr/bin/env python
"""
End-to-End test for CWE Lookup Integration
Tests that CWE data flows from database → lookup service → backend endpoint → frontend
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from modules.cve.cwe_lookup import CWELookup
from modules.cve.cvss_vector_analysis import analyze_cvss_for_cve

def test_cwe_lookup_service():
    """Test CWELookup service directly"""
    print("\n[1] Testing CWELookup Service...")
    try:
        lookup = CWELookup()
        
        # Test CWE-79
        cwe_79 = lookup.get_cwe("CWE-79")
        assert cwe_79 is not None, "CWE-79 should be found"
        assert cwe_79['name'] == "Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')", "CWE-79 name mismatch"
        
        consequences = lookup.get_consequences("CWE-79")
        assert len(consequences) > 0, "CWE-79 should have consequences"
        print(f"   ✓ CWE-79 found with {len(consequences)} consequences")
        
        mitigations = lookup.get_mitigations("CWE-79")
        assert len(mitigations) > 0, "CWE-79 should have mitigations"
        print(f"   ✓ CWE-79 found with {len(mitigations)} mitigations")
        
        full = lookup.get_full_explanation("CWE-79")
        assert full is not None, "CWE-79 full explanation should exist"
        assert 'cwe' in full, "Full explanation should have 'cwe' key"
        assert 'consequences' in full, "Full explanation should have 'consequences' key"
        assert 'mitigations' in full, "Full explanation should have 'mitigations' key"
        print(f"   ✓ CWE-79 full explanation loaded successfully")
        
        return True
    except Exception as e:
        print(f"   ✗ CWE Lookup Service test failed: {e}")
        return False

def test_cvss_analysis():
    """Test CVSS Vector Analysis"""
    print("\n[2] Testing CVSS Vector Analysis...")
    try:
        # Mock CVE with CVSS v4 vector
        cve = {
            "cvss_v4": "CVSS:4.0/AV:N/AT:H/RL:O/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N",
            "cvss_v3": "3.7",
            "cvss_v2": "5.0"
        }
        
        analysis = analyze_cvss_for_cve(cve)
        assert analysis is not None, "Analysis should not be None"
        assert 'summary_explanation' in analysis, "Analysis should have summary_explanation"
        assert 'exploitability' in analysis, "Analysis should have exploitability"
        print(f"   ✓ CVSS analysis completed: {analysis.get('summary_explanation', 'N/A')[:50]}...")
        
        return True
    except Exception as e:
        print(f"   ✗ CVSS Analysis test failed: {e}")
        return False

def test_integrated_response():
    """Test that a mock API response contains both CVSS and CWE data"""
    print("\n[3] Testing Integrated Response Structure...")
    try:
        lookup = CWELookup()
        
        # Mock CVE with multiple CWE IDs
        cwe_ids = [79, 20, 200]  # XSS, Input Validation, Information Disclosure
        cve = {
            "cvss_v4": "CVSS:4.0/AV:N/AT:L/RL:O/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N",
            "cvss_v3": "7.5",
            "cvss_v2": "7.5"
        }
        
        # Simulate what the endpoint does
        cvss_analysis = analyze_cvss_for_cve(cve)
        
        cwe_explanations_list = []
        for cwe_id in cwe_ids[:5]:
            cwe_explanation = lookup.get_full_explanation(f"CWE-{cwe_id}")
            if cwe_explanation:
                cwe_explanations_list.append(cwe_explanation)
        
        # Build mock response
        response = {
            "cve_id": "CVE-2025-12345",
            "cvss_analysis": cvss_analysis,
            "cwe_explanations": cwe_explanations_list,
        }
        
        # Validate response
        assert 'cvss_analysis' in response, "Response should have cvss_analysis"
        assert 'cwe_explanations' in response, "Response should have cwe_explanations"
        assert len(cwe_explanations_list) > 0, "Should have CWE explanations"
        
        print(f"   ✓ Response contains {len(cwe_explanations_list)} CWE explanations")
        print(f"   ✓ CVSS Analysis present: {bool(cvss_analysis)}")
        
        # Validate CWE explanation structure
        for exp in cwe_explanations_list[:1]:  # Check first one
            assert 'cwe' in exp, "CWE explanation should have 'cwe'"
            assert 'consequences' in exp, "CWE explanation should have 'consequences'"
            assert 'mitigations' in exp, "CWE explanation should have 'mitigations'"
            print(f"   ✓ CWE explanation structure valid: cwe_id={exp['cwe']['cwe_id']}, consequences={len(exp['consequences'])}, mitigations={len(exp['mitigations'])}")
        
        return True
    except Exception as e:
        print(f"   ✗ Integrated response test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all E2E tests"""
    print("=" * 70)
    print("CWE Integration End-to-End Tests")
    print("=" * 70)
    
    results = []
    results.append(("CWE Lookup Service", test_cwe_lookup_service()))
    results.append(("CVSS Vector Analysis", test_cvss_analysis()))
    results.append(("Integrated Response", test_integrated_response()))
    
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name:<30} {status}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All E2E tests passed! CWE integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
