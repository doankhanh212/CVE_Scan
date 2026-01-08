#!/usr/bin/env python3
"""
Quick test to verify likelihood calculation works
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from modules.cve.likelihood_calculator import LikelihoodCalculator

calc = LikelihoodCalculator()

# Test with CVE-2025-26466
cve_id = "CVE-2025-26466"
print(f"\nTesting {cve_id}:")
print("="*60)

# Step 2: Get EPSS
epss, percentile = calc.get_epss_from_db(cve_id)
print(f"✓ EPSS: {epss:.5f}")
percentile_str = f"{percentile:.5f}" if percentile else "None"
print(f"✓ Percentile: {percentile_str}")

# Assume CVSS from scan (vulnData.cvss_v3 = 5.3)
cvss_from_scan = 5.3
likelihood = cvss_from_scan * epss
level = "HIGH" if likelihood >= 7.0 else "MEDIUM" if likelihood >= 4.0 else "LOW"

print(f"\n Calculation:")
print(f"CVSS: {cvss_from_scan} (from scan data)")
print(f"EPSS: {epss:.5f}")
print(f"Likelihood: {cvss_from_scan} × {epss:.5f} = {likelihood:.5f}")
print(f"Level: {level}")

print("\n" + "="*60)
print("This should appear in modal!")
