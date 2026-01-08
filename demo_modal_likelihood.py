#!/usr/bin/env python3
"""
Demo: Likelihood tính toán trong CVE Modal
"""

from modules.cve.likelihood_calculator import LikelihoodCalculator

print("\n" + "="*70)
print("DEMO: LIKELIHOOD TRONG CVE MODAL")
print("="*70 + "\n")

calc = LikelihoodCalculator()

# Example CVE
cve_id = "CVE-2021-44228"
print(f"User clicks CVE: {cve_id}")
print("-" * 70)

# Step 1: Assume CVSS from modal (from NVD API)
cvss_scores = {
    "v4": None,
    "v3": {"base_score": 10.0, "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"},
    "v2": {"base_score": 10.0, "vector": "AV:N/AC:L/Au:N/C:C/I:C/A:C"}
}

print("\n🔹 BƯỚC 1: Chọn CVSS_base 'tốt nhất'")
print("Ưu tiên: CVSS 4.0 → CVSS 3.1 → CVSS 3.0 → CVSS 2.0\n")

if cvss_scores["v4"]:
    cvss_base = cvss_scores["v4"]["base_score"]
    cvss_version = "CVSS 4.0"
elif cvss_scores["v3"]:
    cvss_base = cvss_scores["v3"]["base_score"]
    cvss_version = "CVSS 3.1"
elif cvss_scores["v2"]:
    cvss_base = cvss_scores["v2"]["base_score"]
    cvss_version = "CVSS 2.0"
else:
    cvss_base = None
    cvss_version = "N/A"

print(f"  ✓ Selected: {cvss_version}")
print(f"  ✓ CVSS Base: {cvss_base:.2f}\n")

# Step 2: Get EPSS
print("🔹 BƯỚC 2: Lấy EPSS theo CVE ID")
print(f"epss, percentile = get_epss('{cve_id}')\n")

epss, percentile = calc.get_epss_from_db(cve_id)

percentile_str = f"{percentile:.5f}" if percentile else "N/A"
print(f"  ✓ EPSS: {epss:.5f}")
print(f"  ✓ Percentile: {percentile_str}")
if percentile:
    print(f"    (This CVE is more exploitable than {percentile*100:.2f}% of all CVEs)\n")
else:
    print(f"    (Percentile data not available)\n")

# Calculate likelihood
likelihood_score = cvss_base * epss
if likelihood_score >= 7.0:
    level = "HIGH"
    color = "🔴"
elif likelihood_score >= 4.0:
    level = "MEDIUM"
    color = "🟠"
else:
    level = "LOW"
    color = "🟢"

print("-" * 70)
print("CALCULATION:")
print(f"  Formula: Likelihood = CVSS × EPSS")
print(f"  Result:  {cvss_base:.2f} × {epss:.5f} = {likelihood_score:.5f}")
print(f"  Level:   {color} {level}")
print("-" * 70)

print("\n" + "="*70)
print("MODAL DISPLAY:")
print("="*70)

percentile_display = f"{percentile*100:.2f}%" if percentile else "N/A"
print(f"""
┌──────────────────────────────────────────────────────────────────┐
│ CVE-2025-26465                                                   │
├──────────────────────────────────────────────────────────────────┤
│ OVERVIEW   SECURITY STANDARDS   REMEDIATION                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Exploitation Likelihood                                          │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │  LIKELIHOOD SCORE                              {color} {level:7s}│  │
│ │                                                             │  │
│ │                      {likelihood_score:.5f}                              │  │
│ │                                                             │  │
│ │  Formula: Likelihood = CVSS × EPSS                          │  │
│ │                                                             │  │
│ │  CVSS Base:    {cvss_base:.2f} ({cvss_version})                     │  │
│ │  EPSS:         {epss:.5f}                                        │  │
│ │  Percentile:   {percentile_display:7s}                                      │  │
│ │                                                             │  │
│ │  ℹ Likelihood combines CVSS severity with EPSS              │  │
│ │    exploitation probability to show real-world risk         │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
""")

print("="*70)
print("✅ READY TO DISPLAY IN MODAL")
print("="*70 + "\n")
