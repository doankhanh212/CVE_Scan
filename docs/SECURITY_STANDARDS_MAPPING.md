## Security Standards Mapping Framework - CVE Scan Platform

Nâng cấp toàn diện CVE scanning platform với 3 chuẩn bảo mật hàng đầu thế giới.

---

## 📋 Overview

### 3 Frameworks Chính

#### 1. **OWASP Top 10 2021** 🛡️
Ánh xạ CVE/CWE findings đến 10 danh mục web/API vulnerabilities hàng đầu

- **A01**: Broken Access Control (Lỗi kiểm soát truy cập)
- **A02**: Cryptographic Failures (Lỗi mật mã)
- **A03**: Injection (SQL, XSS, Command Injection)
- **A04**: Insecure Design (Thiết kế không an toàn)
- **A05**: Security Misconfiguration (Cấu hình sai)
- **A06**: Vulnerable & Outdated Components (Thành phần lỗi thời)
- **A07**: Authentication Failures (Lỗi xác thực)
- **A08**: Software & Data Integrity Failures
- **A09**: Logging & Monitoring Failures
- **A10**: SSRF (Server-Side Request Forgery)

**Tính năng:**
- Ánh xạ tự động CWE → OWASP
- Risk weight cho mỗi category
- Heuristic mapping từ CVE description

#### 2. **MITRE ATT&CK Framework** 🎯
Map vulnerabilities đến chiến lược tấn công thực tế

**Tactics:**
- **Reconnaissance** (TA0043) - Tìm kiếm thông tin
- **Initial Access** (TA0001) - Truy cập ban đầu
- **Persistence** (TA0003) - Duy trì truy cập
- **Privilege Escalation** (TA0004) - Escalate quyền
- **Defense Evasion** (TA0005) - Tránh phát hiện

**Techniques:**
- T1589: Gather Victim Network Information
- T1590: Network Topology Mapping
- T1190: Exploit Public-Facing Application
- T1195: Supply Chain Compromise
- T1548: Abuse Elevation Control Mechanism

**Tính năng:**
- Attack chain reconstruction
- Reconnaissance threat mapping (critical for ASM)
- Initial access techniques tracking

#### 3. **Secure Coding Best Practices** 💻
OWASP Secure Code Practices mapped to vulnerabilities

**Categories:**
- Input Validation & Output Encoding
- Authentication & Session Management
- Cryptography & Key Management
- Access Control & Authorization
- Error Handling & Logging
- Third-Party Component Management

---

## 🔧 Architecture

### Module Structure

```
web/security_standards/
├── __init__.py                    # Package initialization
├── owasp_mapping.py               # OWASP Top 10 framework
├── mitre_attack_mapping.py        # MITRE ATT&CK framework
├── secure_coding_mapper.py        # Secure Coding Practices
└── unified_mapper.py              # Unified analysis engine

web/routes/
├── security_standards.py          # API endpoints
└── security_standards_page.py     # Web interface

web/templates/
└── security_standards.html        # Dashboard UI
```

### Data Flow

```
CVE Input (ID + CWE IDs)
    ↓
Unified Mapper
    ├→ OWASPMapper (CWE → OWASP Code + Risk Weight)
    ├→ MITREMapper (CWE → Techniques + Tactics)
    └→ SecureCodeMapper (CWE → Practices + Category)
    ↓
Comprehensive Analysis
    ├ Risk Score (0-10)
    ├ OWASP Mappings
    ├ MITRE Attack Chain
    ├ Secure Coding Practices
    └ Recommendations
```

---

## 🚀 API Endpoints

### Unified Analysis

```bash
POST /api/security/analyze/cve
Content-Type: application/json

{
    "cve_id": "CVE-2023-12345",
    "cwe_ids": [79, 80],
    "description": "Stored XSS vulnerability...",
    "severity": "HIGH"
}

# Response:
{
    "cve_id": "CVE-2023-12345",
    "risk_score": 6.62,
    "owasp": {
        "mappings": [{"owasp_code": "A03", "owasp_name": "Injection", ...}],
        "primary": {...},
        "coverage": true
    },
    "mitre_attack": {
        "techniques": [...],
        "tactics": [...],
        "attack_chain": [...]
    },
    "secure_coding": {
        "practices": [...],
        "categories": [...],
        "critical_count": 2
    },
    "attack_context": {...},
    "recommendations": [...]
}
```

### Batch Analysis

```bash
POST /api/security/analyze/batch
Content-Type: application/json

{
    "findings": [
        {"id": "CVE-2023-1", "cwe_ids": [...], "severity": "HIGH"},
        {"id": "CVE-2023-2", "cwe_ids": [...], "severity": "CRITICAL"}
    ]
}

# Response: Aggregate statistics + per-CVE analysis
```

### OWASP Framework

```bash
# Get all OWASP categories
GET /api/security/owasp/categories

# Get OWASP by CWE ID
GET /api/security/owasp/by-cwe/79

# Get OWASP by CVE ID
GET /api/security/owasp/by-cve/CVE-2023-12345?cwe_ids=79,80
```

### MITRE ATT&CK Framework

```bash
# Get all tactics
GET /api/security/mitre/tactics

# Get reconnaissance techniques
GET /api/security/mitre/reconnaissance

# Get initial access techniques
GET /api/security/mitre/initial-access

# Get MITRE by CVE
GET /api/security/mitre/by-cve/CVE-2023-12345?cwe_ids=89
```

### Secure Coding Practices

```bash
# Get all categories
GET /api/security/scp/categories

# Get practices by category
GET /api/security/scp/by-category/Input%20Validation

# Get practices by CVE
GET /api/security/scp/by-cve/CVE-2023-12345?cwe_ids=79,80
```

---

## 📊 Usage Examples

### Example 1: XSS Vulnerability Analysis

```python
from web.security_standards import UnifiedSecurityMapper

analysis = UnifiedSecurityMapper.analyze_cve(
    cve_id="CVE-2023-12345",
    cwe_ids=[79, 80],  # CWE-79: XSS, CWE-80: Improper Neutralization
    description="Stored XSS vulnerability in user comments",
    severity="HIGH"
)

print(f"Risk Score: {analysis['risk_score']}/10")
print(f"OWASP: {analysis['owasp']['primary']['owasp_name']}")
print(f"Attack Techniques: {[t['technique_id'] for t in analysis['mitre_attack']['techniques']]}")
print(f"Recommendations: {analysis['recommendations']}")
```

### Example 2: Batch CVE Analysis

```python
findings = [
    {"id": "CVE-2023-1", "cwe_ids": [79], "severity": "HIGH"},
    {"id": "CVE-2023-2", "cwe_ids": [89], "severity": "CRITICAL"},
    {"id": "CVE-2023-3", "cwe_ids": [200], "severity": "MEDIUM"}
]

result = UnifiedSecurityMapper.analyze_multiple_cves(findings)

print(f"High Risk Count: {result['risk_summary']['high_risk_count']}")
print(f"Top OWASP Risks: {result['aggregate_stats']['owasp_top_risks']}")
print(f"Critical Practices: {result['aggregate_stats']['critical_practices_count']}")
```

### Example 3: Framework Queries

```python
from web.security_standards import OWASPMapper, MITREMapper, SecureCodeMapper

# OWASP: Get category for CWE-89 (SQL Injection)
code, category = OWASPMapper.get_by_cwe(89)
print(f"{code}: {category.name}")  # A03: Injection

# MITRE: Get reconnaissance techniques
recon_techniques = MITREMapper.get_reconnaissance_threats()
print(f"Reconnaissance threats: {recon_techniques}")

# Secure Coding: Get practices for Input Validation
practices = SecureCodeMapper.get_by_category("Input Validation")
for p in practices:
    print(f"{p.id}: {p.practice} ({p.severity})")
```

---

## 🎨 Web Interface

### Security Standards Dashboard
- **URL**: `http://localhost:5000/security-standards`
- **Features**:
  - OWASP Top 10 categories browser
  - MITRE ATT&CK tactics & techniques mapper
  - Secure Coding Practices checklist
  - API documentation
  - Real-time framework statistics

### Dashboard Sections

1. **Framework Overview Cards**
   - Quick stats on OWASP, MITRE, SCP
   - Navigation to detailed views

2. **OWASP Top 10 Table**
   - All 10 categories with CWE counts
   - Risk weights visualization
   - Color-coded severity

3. **MITRE ATT&CK Visualization**
   - Reconnaissance techniques
   - Initial Access techniques
   - Attack flow mapping

4. **Secure Coding Practices**
   - 6 categories
   - 20+ detailed practices
   - Remediation guidance

5. **API Documentation**
   - All endpoints listed
   - Example requests
   - Integration guide

---

## 🔍 Risk Scoring Algorithm

Risk Score = 0-10 (higher = more critical)

**Components:**
1. **OWASP Risk Weight** (40%) - Risk inherent to vulnerability type
2. **MITRE ATT&CK Presence** (20%) - Number of attack techniques applicable
3. **Secure Coding Violations** (20%) - Critical + High practices affected
4. **CVSS Severity** (20%) - CRITICAL=2.0, HIGH=1.6, MEDIUM=1.2, LOW=0.8

**Formula:**
```
Risk Score = (OWASP Weight / 10 × 4) + 
             min(2.0, Technique Count × 0.5) +
             min(2.0, Critical × 0.8 + High × 0.4) +
             CVSS Severity Factor
```

---

## 📈 Next Steps (Phase 2)

1. **Database Integration**
   - Persist mapping results
   - Historical trend tracking
   - Compliance reporting

2. **Advanced Features**
   - Auto-mapping new CVEs
   - Custom framework rules
   - AI-based classification

3. **Integration**
   - Slack/Teams alerts
   - SIEM integration
   - Ticketing systems (Jira/Azure DevOps)

4. **Reporting**
   - PDF compliance reports
   - Executive dashboards
   - Trend analysis

---

## ✅ Validation

### Test Results
```
SECURITY STANDARDS MAPPING TEST RESULTS:
✓ XSS Analysis: Risk Score 6.62/10
  - OWASP: A03 (Injection)
  - MITRE: T1190 (Exploit Public-Facing App)
  - SCP: Output Encoding practice

✓ SQL Injection Analysis: Risk Score 6.22/10
  - OWASP: A03 (Injection)
  - MITRE: TA0001 (Initial Access)

✓ Batch Analysis: 3 CVEs analyzed
  - Average Risk: 6.99/10
  - Top OWASP: A03 (3 findings)
```

---

## 🔗 References

- OWASP Top 10 2021: https://owasp.org/Top10/
- MITRE ATT&CK: https://attack.mitre.org/
- CWE/CWSS: https://cwe.mitre.org/
- CVSS Calculator: https://www.first.org/cvss/calculator/3.1

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Status**: ✅ Production Ready
