# CVE Detail Modal - User Guide

## Feature Overview

The CVE Detail Modal provides an ASM (Attack Surface Management) style interface for exploring vulnerability details, directly integrated into the Vulnerabilities page. When you click on any host/IP or CVE ID in the vulnerability table, a detailed analysis modal appears showing:

- **CVE Information**: Title, description, affected products
- **CVSS Scores**: Full v2, v3, and v4 support with vectors
- **Security Standards Mapping**: 
  - OWASP Top 10 2021 categories
  - MITRE ATT&CK framework tactics & techniques
  - Secure Coding Practices recommendations
- **Risk Scoring**: Unified 0-10 risk assessment
- **Remediation Guidance**: Actionable steps to fix the vulnerability

## How to Use

### Opening the Modal

1. Navigate to **Vulnerabilities** page
2. Click on any **HOST/IP address** in the table (clickable host tag)
3. **OR** Click on any **CVE ID** link
4. The modal appears with a fade-in animation

### Understanding the Modal Tabs

#### **Tab 1: Overview**
- **CVE Information**: Full description of the vulnerability
- **CVSS Scores**: All available CVSS versions
  - Base score (numeric)
  - Vector string (technical details)
- **Affected Products**: CPE strings showing which products are vulnerable

#### **Tab 2: Security Standards**
Shows vulnerability mapped to three security frameworks:

**OWASP Top 10 2021 (A01-A10)**
- Category code and name
- Risk rating (CRITICAL, HIGH, MEDIUM, LOW)
- Framework description
- Examples: A03 (Injection), A01 (Access Control), A07 (Authentication)

**MITRE ATT&CK Framework**
- Organized by Tactics (Reconnaissance, Initial Access, Persistence, etc.)
- Techniques (T1190, T1595, etc.)
- Shows attack chain/methodology

**Secure Coding Practices**
- Categorized by practice area
- Severity levels (CRITICAL, HIGH, MEDIUM, LOW)
- Specific guidance for each practice

**Risk Score**
- Visual bar chart (0-10 scale)
- Combines all frameworks + CVSS severity
- Algorithm: 40% OWASP + 20% MITRE + 20% SCP + 20% CVSS

#### **Tab 3: Remediation**
- Step-by-step remediation guidance
- Specific to each framework's recommendations
- Actionable best practices
- Prioritized by risk level

### Closing the Modal

- Click the **X** button in the top-right corner
- Click the **Close** button at the bottom
- Click outside the modal (on the dark background)
- Press **Escape** key (if implemented)

## Examples

### Example 1: SQL Injection (CVE-2023-12345)

1. Click host "192.168.1.100" in table
2. Modal opens showing:
   - **Overview**: SQL Injection in login form
   - **OWASP**: A03 (Injection) - HIGH risk
   - **MITRE**: Initial Access → Exploit Public-Facing Application (T1190)
   - **SCP**: Input Validation category - use parameterized queries
   - **Risk**: 8.5/10 (HIGH)
   - **Action**: Implement input validation + parameterized queries

### Example 2: Outdated Component (CVE-2023-99999)

1. Click CVE-2023-99999 link
2. Modal displays:
   - **Overview**: Vulnerable npm package version
   - **OWASP**: A06 (Vulnerable Components) - MEDIUM risk
   - **MITRE**: Persistence → Exploit Library (various)
   - **SCP**: Third-party component dependency management
   - **Risk**: 6.2/10 (MEDIUM)
   - **Action**: Update package to latest secure version

## Security Framework Explanations

### OWASP Top 10 2021

The OWASP Top 10 is a standard awareness document for web application security risks:

| Code | Category | Focus |
|------|----------|-------|
| A01 | Broken Access Control | Authorization & permissions |
| A02 | Cryptographic Failures | Encryption & secure storage |
| A03 | Injection | Untrusted data to interpreters |
| A04 | Insecure Design | Missing security controls |
| A05 | Security Misconfiguration | Hardening & defaults |
| A06 | Vulnerable Components | Outdated/unsafe dependencies |
| A07 | Authentication Failures | Password/session security |
| A08 | Data Integrity Failures | Unsigned/unverified data |
| A09 | Logging/Monitoring | Detection & incident response |
| A10 | SSRF | Server-side request forgery |

### MITRE ATT&CK

Framework showing tactics (what) and techniques (how) used in cyber attacks:

**Tactics** (phases of attack):
- **Reconnaissance** (T0001): Gather information before attack
- **Initial Access** (T0002): Gain initial foothold
- **Persistence** (T0003): Maintain access
- **Privilege Escalation** (T0004): Gain higher permissions
- **Defense Evasion** (T0005): Avoid detection
- **Lateral Movement** (T0006): Move through network

### Secure Coding Practices (OWASP SCP)

Six categories of secure development practices:

1. **Input Validation** - Validate all user input
2. **Authentication** - Secure identity verification
3. **Cryptography** - Proper encryption implementation
4. **Access Control** - Role-based permissions
5. **Error Handling** - Safe error messaging
6. **Third-party** - Manage external dependencies

## Risk Score Calculation

The **Risk Score** combines four factors into a 0-10 scale:

```
Risk Score = (OWASP weight × 0.4) + (MITRE presence × 0.2) + 
             (SCP violations × 0.2) + (CVSS severity × 0.2)
```

**Score Interpretation:**
- **0-2**: Low risk (informational)
- **2-5**: Medium risk (should address)
- **5-7**: High risk (prioritize fixing)
- **7-10**: Critical risk (urgent attention)

## Technical Data Structure

The modal displays data returned from the API endpoint `/api/cve/{cve_id}/analysis`:

```json
{
  "cve_id": "CVE-2023-12345",
  "title": "SQL Injection in Login",
  "description": "Full vulnerability description...",
  "cvss": {
    "v2": { "base_score": 7.5, "vector": "AV:N/AC:L/..." },
    "v3": { "base_score": 8.8, "vector": "CVSS:3.1/AV:N/AC:L/..." },
    "v4": { "base_score": null, "vector": null }
  },
  "owasp": [
    { "category": "A03", "name": "Injection", "risk_rating": "HIGH", "description": "..." }
  ],
  "mitre": {
    "Reconnaissance": ["T1595 - Active Scanning", "..."],
    "Initial Access": ["T1190 - Exploit Public-Facing Application", "..."]
  },
  "scp": [
    { "category": "Input Validation", "practice": "Validate all input", "severity": "CRITICAL", "description": "..." }
  ],
  "affected_cpes": ["cpe:2.3:a:vendor:product:version:...", "..."],
  "recommendations": ["Use parameterized queries", "Implement input validation whitelist", "..."],
  "risk_score": 7.5
}
```

## Filtering & Navigation

From the Vulnerabilities page, you can:

1. **Filter by Severity** - Show only Critical/High/Medium/Low
2. **Filter by Host** - Focus on specific system
3. **Search** - Find by CVE ID, service, or description
4. **Export** - Download filtered results as CSV

Then click any result to open the detail modal.

## Tips & Best Practices

✅ **Do:**
- Click multiple CVEs to compare risk scores
- Use OWASP categories to group similar vulnerabilities
- Check remediation guidance before patching
- Monitor risk score trends over time

❌ **Don't:**
- Ignore CRITICAL risk scores
- Skip reading the description
- Deploy patches without testing
- Close the modal without noting recommendations

## Troubleshooting

**Q: Modal won't open when I click a host**
A: Make sure vulnerabilities are fully loaded (check browser console for errors)

**Q: Missing CVSS vectors**
A: Some CVEs may not have all versions (v2, v3, v4). Only available data is shown.

**Q: Empty OWASP mappings**
A: If no CWE IDs are in the CVE data, OWASP mapping won't be available.

**Q: Risk score seems wrong**
A: Risk score combines multiple factors. Check individual CVSS + framework mappings.

## Related Pages

- **Dashboard**: Overview of scan results and statistics
- **Security Standards**: Detailed framework definitions and mappings
- **Results**: Raw scan data and JSON export
- **Settings**: Configuration and scan preferences

## API Reference

### Endpoint
```
POST /api/cve/{cve_id}/analysis
```

### Example Request
```bash
curl -X POST http://localhost:5000/api/cve/CVE-2023-12345/analysis \
  -H "Content-Type: application/json"
```

### Response
See JSON structure above

### Error Responses
```json
// CVE not found
{ "error": "CVE CVE-2023-12345 not found" }
HTTP 404
```

## Version History

**v1.0** (Initial Release)
- Basic modal with 3 tabs
- OWASP Top 10 mapping
- MITRE ATT&CK framework
- Secure Coding Practices
- Risk scoring algorithm
- CVSS v2, v3, v4 support
