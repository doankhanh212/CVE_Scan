# CVE Detail Modal Integration - Group-IB ASM Style

## Overview
Integratedcomplete CVE detail modal into the Vulnerabilities page, allowing users to click on hosts/IPs to view security standards mapping (OWASP, MITRE ATT&CK, Secure Coding Practices) alongside CVSS details.

## Files Modified/Created

### 1. **web/templates/vulnerabilities.html** (Updated)
- Added CVE detail modal HTML structure with 3 tabs:
  - **Overview**: CVE info, CVSS scores (v2, v3, v4), affected products
  - **Security Standards**: OWASP Top 10, MITRE ATT&CK, Secure Coding Practices with risk score
  - **Remediation**: Detailed remediation guidance and recommendations
- Added comprehensive modal CSS styling (dark theme, card-based layout)
- Updated JavaScript to:
  - Add click handlers to host/IP cells and CVE links
  - Fetch `/api/cve/{cve_id}/analysis` when modal opens
  - Populate modal with security frameworks data
  - Handle tab switching and modal lifecycle

### 2. **web/routes/cve_detail.py** (Updated)
Added new POST endpoint:
```
POST /api/cve/{cve_id}/analysis
```

**Response Format:**
```json
{
  "cve_id": "CVE-2023-12345",
  "title": "Vulnerability Title",
  "description": "Full CVE description",
  "cvss": {
    "v2": { "base_score": 7.5, "vector": "AV:N/AC:L/..." },
    "v3": { "base_score": 8.8, "vector": "CVSS:3.1/AV:N/AC:L/..." },
    "v4": { "base_score": null, "vector": null }
  },
  "owasp": [
    {
      "category": "A03:2021 – Injection",
      "name": "Injection",
      "risk_rating": "HIGH",
      "description": "..."
    }
  ],
  "mitre": {
    "Reconnaissance": ["T1595 - Active Scanning", "..."],
    "Initial Access": ["T1190 - Exploit Public-Facing Application", "..."]
  },
  "scp": [
    {
      "category": "Input Validation",
      "practice": "Validate all input",
      "severity": "CRITICAL",
      "description": "..."
    }
  ],
  "affected_cpes": ["cpe:2.3:a:vendor:product:version:...", "..."],
  "recommendations": [
    "Implement input validation whitelist...",
    "Use parameterized queries...",
    "..."
  ],
  "risk_score": 7.5
}
```

### 3. **web/app.py** (Updated)
- Imported `cve_detail_bp` from `web.routes.cve_detail`
- Registered blueprint: `app.register_blueprint(cve_detail_bp)`

## User Interaction Flow

1. **User opens Vulnerabilities page** → Table loads with all CVEs
2. **User clicks on host/IP or CVE ID** → Modal opens and fetches data
3. **Modal fetches** `/api/cve/{cve_id}/analysis`:
   - UnifiedSecurityMapper analyzes CVE
   - Returns OWASP, MITRE, SCP mappings
   - Includes risk score (0-10 scale)
4. **Modal displays** 3 tabs:
   - Overview: CVSS scores, affected products
   - Standards: Security frameworks with detailed cards
   - Remediation: Step-by-step guidance
5. **User can**:
   - Switch between tabs
   - Click "View on NVD" to open external link
   - Close modal to return to table

## Security Standards Integration

### OWASP Top 10 2021
- **Display**: Category cards with risk rating
- **Mapping**: Automatic from CWE IDs
- **Data**: 155+ CWE to OWASP mappings

### MITRE ATT&CK Framework (ASM-focused)
- **Display**: Tactic → Techniques cards
- **Coverage**: Reconnaissance, Initial Access, Persistence, Privilege Escalation
- **Tactics**: T0001-T0006 mapped to CVE characteristics

### Secure Coding Practices
- **Display**: Practice cards with severity
- **Categories**: Input Validation, Authentication, Cryptography, Access Control, Error Handling, Third-party
- **Details**: Remediation steps for each practice

### Risk Scoring
- **Algorithm**: 0-10 scale
  - OWASP: 40% weight
  - MITRE: 20% weight
  - SCP: 20% weight
  - CVSS: 20% weight
- **Display**: Filled progress bar in Standards tab

## Modal Features

### Styling
- Dark theme (matching Group-IB ASM)
- Smooth animations (fade-in, slide-up)
- Card-based layout for frameworks
- Responsive grid for CVSS cards

### Interactive Elements
- Tab switching with visual indicator
- Hover effects on buttons
- Modal close button and background click close
- External link to NVD

### Data Validation
- Handles missing CVSS versions
- Gracefully displays "N/A" for unavailable data
- Empty state messages for missing mappings
- Automatic fallback to empty arrays

## Technical Details

### Helper Functions (cve_detail.py)
```python
_find_cve_in_scans()          # Find CVE in completed scans
_extract_cwe_ids()             # Extract CWE IDs from CVE data
_extract_severity_label()      # Get severity as string
_extract_cvss_details()        # Parse CVSS v2, v3, v4 scores
_extract_severity()            # Get full severity object
_extract_cvss_vector()         # Get CVSS vector string
_get_owasp_guidance()          # Get remediation per OWASP category
```

### JavaScript Functions (vulnerabilities.html)
```javascript
loadVulnerabilities()           // Fetch initial vulnerability list
renderTable()                   // Render table rows with click handlers
openCVEModal(cveId, vulnData)  // Fetch analysis and display modal
closeCVEModal()                 // Close modal
applyFilters()                  // Filter by severity/host/search
```

## API Integration

**Endpoint Chain:**
```
User clicks host → openCVEModal()
  ↓
POST /api/cve/{cve_id}/analysis
  ↓
cve_detail_bp.cve_analysis()
  ↓
UnifiedSecurityMapper.analyze_cve()
  ↓
Returns: {cve_id, title, description, cvss, owasp, mitre, scp, affected_cpes, recommendations, risk_score}
  ↓
Modal populates tabs with results
```

## Testing

To test the integration:

1. **Run the app**: `python web/app.py`
2. **Navigate to**: `http://localhost:5000/vulnerabilities`
3. **Click on a host/IP** or CVE ID
4. **Modal should open** with:
   - CVE ID and title
   - 3 tabs (Overview, Standards, Remediation)
   - Populated data from `/api/cve/{cve_id}/analysis`
5. **Switch tabs** to see different frameworks
6. **Click "View on NVD"** to verify external link
7. **Click outside modal** or close button to close

## Compliance with Group-IB ASM

✅ **Modal-based CVE exploration** - Click host → Detail view  
✅ **Security frameworks** - OWASP, MITRE, SCP integration  
✅ **CVSS details** - Full v2/v3/v4 support with vectors  
✅ **Professional UI** - Dark theme, card layout, smooth animations  
✅ **Risk scoring** - 0-10 unified risk assessment  
✅ **Remediation guidance** - Actionable steps per framework  
✅ **Enterprise ready** - Handles missing data gracefully  

## Future Enhancements

- [ ] Export CVE analysis to PDF
- [ ] Advanced filtering by framework (show only A01 vulnerabilities)
- [ ] CVE comparison (side-by-side modal)
- [ ] Custom remediation templates per organization
- [ ] Integration with ticketing system (auto-create tickets)
- [ ] Security metrics dashboard with framework stats
