"""
Test Security Standards Mapping
"""
import sys
sys.path.insert(0, r'c:\Users\dhqkh\CVE_Scan')

from web.security_standards import UnifiedSecurityMapper

# Example CVE analysis
print("=" * 70)
print("SECURITY STANDARDS MAPPING - CVE ANALYSIS")
print("=" * 70)

# Analyze XSS vulnerability
xss_analysis = UnifiedSecurityMapper.analyze_cve(
    cve_id="CVE-2023-12345",
    cwe_ids=[79, 80],  # XSS and Improper Neutralization
    description="Stored XSS vulnerability in web application",
    severity="HIGH"
)

print("\n[1] XSS Vulnerability Analysis:")
print(f"    Risk Score: {xss_analysis['risk_score']}/10")
print(f"\n    OWASP Top 10:")
for mapping in xss_analysis['owasp']['mappings']:
    print(f"      - {mapping['owasp_code']}: {mapping['owasp_name']}")

print(f"\n    MITRE ATT&CK:")
for technique in xss_analysis['mitre_attack']['techniques'][:3]:
    print(f"      - {technique['technique_id']}: {technique['technique_name']}")

print(f"\n    Secure Coding Practices:")
for practice in xss_analysis['secure_coding']['practices'][:3]:
    print(f"      - {practice['practice']}")

# Analyze SQL Injection
print("\n" + "=" * 70)
sql_analysis = UnifiedSecurityMapper.analyze_cve(
    cve_id="CVE-2024-54321",
    cwe_ids=[89],  # SQL Injection
    description="SQL injection in user login endpoint",
    severity="CRITICAL"
)

print("\n[2] SQL Injection Analysis:")
print(f"    Risk Score: {sql_analysis['risk_score']}/10")
print(f"    Primary OWASP: {sql_analysis['owasp']['primary']['owasp_code']} - {sql_analysis['owasp']['primary']['owasp_name']}")
print(f"    Attack Phases: {', '.join(sql_analysis['mitre_attack']['tactics'])}")

# Batch analysis
print("\n" + "=" * 70)
print("\n[3] Batch Analysis (Multiple CVEs):")

batch_findings = [
    {"id": "CVE-2023-12345", "cwe_ids": [79, 80], "severity": "HIGH", "description": "XSS"},
    {"id": "CVE-2024-54321", "cwe_ids": [89], "severity": "CRITICAL", "description": "SQL Injection"},
    {"id": "CVE-2024-11111", "cwe_ids": [200, 201], "severity": "HIGH", "description": "Information Disclosure"},
]

batch_result = UnifiedSecurityMapper.analyze_multiple_cves(batch_findings)

print(f"    Total Findings: {batch_result['total_findings']}")
print(f"    Average Risk Score: {batch_result['risk_summary']['average_risk_score']}/10")
print(f"    Critical Risk Count: {batch_result['risk_summary']['critical_risk_count']}")
print(f"\n    Top OWASP Risks:")
for code, count in batch_result['aggregate_stats']['owasp_top_risks']:
    print(f"      - {code}: {count} findings")

print("\n" + "=" * 70)
print("✓ Security Standards Mapping Test Complete")
print("=" * 70)
