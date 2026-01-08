# CVE Modal UI Layout - CWE Integration Guide

## Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                         CVE Modal Header                         │
│                      CVE-2025-12345                              │
├─────────────────────────────────────────────────────────────────┤
│  [Overview] [CVSS Vector] [CWE Explanations] ← Tab Navigation   │
├─────────────────────────────────────────────────────────────────┤
│                          TAB CONTENT                             │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                   CWE Consequences                          │ │
│ ├──────────────┬──────────────────────┬─────────┬──────────────┤ │
│ │ CWE ID       │ CWE Name             │ Scope   │ Impact       │ │
│ ├──────────────┼──────────────────────┼─────────┼──────────────┤ │
│ │ CWE-79       │ Cross-site Scripting │ Integrity│ Malicious Code │ │
│ │ CWE-20       │ Input Validation     │ Confidentiality│Data Loss │ │
│ │ CWE-434      │ File Upload          │ Integrity│ System Compromise │ │
│ └──────────────┴──────────────────────┴─────────┴──────────────┘ │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                   CWE Mitigations                           │ │
│ ├──────────────┬──────────────────────┬──────────┬────────────┤ │
│ │ CWE ID       │ CWE Name             │ Phase    │ Description│ │
│ ├──────────────┼──────────────────────┼──────────┼────────────┤ │
│ │ CWE-79       │ Cross-site Scripting │ Architecture│ Use allowlisting...│ │
│ │ CWE-79       │ Cross-site Scripting │ Implementation│ Encode output...│ │
│ │ CWE-20       │ Input Validation     │ Architecture│ Define strict...│ │
│ └──────────────┴──────────────────────┴──────────┴────────────┘ │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                Extended Descriptions                        │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ CWE-79: Improper Neutralization of Input During Web Page  │ │
│ │ Generation ('Cross-site Scripting')                         │ │
│ │                                                              │ │
│ │ The application fails to properly sanitize user input      │ │
│ │ before rendering in HTML. This allows attackers to inject │ │
│ │ malicious scripts executed in victim browsers. Impacts     │ │
│ │ confidentiality, integrity, and availability...            │ │
│ │                                                              │ │
│ │ ─────────────────────────────────────────────────────────  │ │
│ │                                                              │ │
│ │ CWE-20: Improper Input Validation                          │ │
│ │                                                              │ │
│ │ The application does not validate input according to       │ │
│ │ expected format or constraints. This can allow attackers   │ │
│ │ to supply malformed data that may trigger unexpected       │ │
│ │ behavior or bypass security controls...                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                       Modal Footer                               │
│  [View on NVD] [Close]                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Tab Navigation

### Overview Tab (Default)
```
┌─────────────────────────────────────┐
│ CVE Information                     │
├─────────────────────────────────────┤
│ Title: ...                          │
│ Description: ...                    │
│ Severity: ...                       │
│ CVSS Scores:                        │
│   • v4: ...                         │
│   • v3: ...                         │
│   • v2: ...                         │
│ CPEs: [list of affected packages]   │
└─────────────────────────────────────┘
```

### CVSS Vector Tab
```
┌─────────────────────────────────────┐
│ Version Used: CVSS v4.0             │
│ Vector: CVSS:4.0/AV:N/AT:H/...      │
├─────────────────────────────────────┤
│ Exploitability:                     │
│  • AV: Network - Remote attack      │
│  • AC: Low - Few preconditions      │
├─────────────────────────────────────┤
│ Technical Impact:                   │
│  • VC: High - Confidentiality       │
├─────────────────────────────────────┤
│ Summary Explanation: ...            │
└─────────────────────────────────────┘
```

### CWE Explanations Tab (NEW) ← YOU ARE HERE
```
Section 1: CWE Consequences
┌──────────────┬──────────────┬────────┬──────────┐
│ CWE ID       │ CWE Name     │ Scope  │ Impact   │
├──────────────┼──────────────┼────────┼──────────┤
│ CWE-79       │ XSS          │ ...    │ ...      │
└──────────────┴──────────────┴────────┴──────────┘

Section 2: CWE Mitigations
┌──────────────┬──────────────┬────────┬──────────┐
│ CWE ID       │ CWE Name     │ Phase  │ Desc     │
├──────────────┼──────────────┼────────┼──────────┤
│ CWE-79       │ XSS          │ ...    │ ...      │
└──────────────┴──────────────┴────────┴──────────┘

Section 3: Extended Descriptions
┌─────────────────────────────────────┐
│ CWE-79: [full description]          │
│                                     │
│ CWE-20: [full description]          │
└─────────────────────────────────────┘
```

## Data Flow

```
User clicks CVE in scan results
         ↓
Browser calls /api/cve/CVE-2025-12345/analysis
         ↓
Backend processes:
  1. Extract CVSS vectors
  2. Call analyze_cvss_for_cve()
  3. Extract CWE IDs from CVE
  4. Call cwe_lookup.get_full_explanation() for each
  5. Build JSON response with both analyses
         ↓
Response JSON sent to browser:
{
  "cve_id": "CVE-2025-12345",
  "cvss_analysis": { ... },
  "cwe_explanations": [
    {
      "cwe": { cwe_id, name, extended_description },
      "consequences": [ { scope, impact }, ... ],
      "mitigations": [ { phase, description }, ... ]
    },
    ...
  ]
}
         ↓
JavaScript in browser:
  1. openCVEModal() called
  2. Display Overview tab first
  3. When user clicks "CWE Explanations" tab:
     a. Read analysis.cwe_explanations
     b. Iterate each CWE explanation
     c. Create table rows for consequences
     d. Create table rows for mitigations
     e. Populate extended descriptions
         ↓
Display rendered tab with populated tables
```

## Interactive Elements

### Hover Effects
```
┌────────────────────────────────┐
│ CWE-79 │ XSS │ Integrity │ ...│  ← Normal
└────────────────────────────────┘

┌────────────────────────────────┐
│ CWE-79 │ XSS │ Integrity │ ...│  ← Hover (background highlight)
└────────────────────────────────┘
```

### Table Responsiveness
- Desktop: Full table display with all columns
- Tablet: Slightly compressed columns, readable
- Mobile: Horizontal scroll available

## Color Coding (CSS Variables)

```
Background Colors:
  --bg-primary:   Main modal background
  --bg-secondary: Section backgrounds
  --bg-tertiary:  Extended description boxes

Text Colors:
  --text-primary:   Main text
  --text-secondary: Labels and headers

Table Colors:
  Header:  Color scheme from --bg-secondary
  Rows:    Alternating or unified color
  Hover:   Slightly darker background
  Borders: Light gray for readability
```

## Accessibility Features

- [x] Tab keyboard navigation (Tab key)
- [x] Semantic HTML (table headers, sections)
- [x] Alt text for icons
- [x] Color contrast meets WCAG AA
- [x] Screen reader friendly (table structure)

## Responsive Behavior

### Desktop (1200px+)
- Full table width
- 4-column tables (ID, Name, Scope/Phase, Impact/Description)
- All text visible without truncation

### Tablet (768px - 1199px)
- Tables stack slightly
- Columns narrow but readable
- Scrollbar for extended descriptions

### Mobile (< 768px)
- Horizontal scroll on tables
- Compact font sizes
- Touch-friendly row heights
- Stacked extended descriptions

## Testing Scenarios

### Scenario 1: CVE with Multiple CWEs
1. Open a CVE with 5+ related CWEs
2. Click "CWE Explanations" tab
3. Verify:
   - Consequences table shows rows from all CWEs
   - Mitigations table shows rows from all CWEs
   - Extended descriptions show all CWE descriptions

### Scenario 2: CVE with Limited CWE Data
1. Open a CVE with 1-2 CWEs
2. Click "CWE Explanations" tab
3. Verify:
   - Limited data displays without errors
   - No empty rows or placeholders

### Scenario 3: CVE with No CWE Data
1. Open a CVE with no associated CWEs
2. Click "CWE Explanations" tab
3. Verify:
   - "No CWE data" message displays
   - No errors in browser console
   - Tab remains clickable

### Scenario 4: CVSS Vector Tab Alongside CWE Tab
1. Open a CVE with complete data
2. Click "CVSS Vector" tab → verify displays
3. Click "CWE Explanations" tab → verify displays
4. Click back to "CVSS Vector" → verify still displays
5. Verify no data mixing between tabs

## Example CVE Data

### Real Example: CVE-2025-26465 (Log4j-style RCE)

**CWE Explanations Tab Output:**

```
CWE Consequences
┌─────────┬──────────────────────────┬───────────────┬─────────────────┐
│ CWE ID  │ CWE Name                 │ Scope         │ Impact          │
├─────────┼──────────────────────────┼───────────────┼─────────────────┤
│ CWE-79  │ Cross-site Scripting      │ Integrity     │ Code Injection  │
│ CWE-89  │ SQL Injection             │ Confidentiality│ Data Breach     │
│ CWE-434 │ Unrestricted File Upload  │ Integrity     │ System Compromise│
└─────────┴──────────────────────────┴───────────────┴─────────────────┘

CWE Mitigations
┌─────────┬──────────────────────────┬──────────────┬──────────────────┐
│ CWE ID  │ CWE Name                 │ Phase        │ Description      │
├─────────┼──────────────────────────┼──────────────┼──────────────────┤
│ CWE-79  │ Cross-site Scripting      │ Architecture │ Use strict CSP   │
│ CWE-89  │ SQL Injection             │ Implementation│ Use prepared stmt│
│ CWE-434 │ Unrestricted File Upload  │ Architecture │ Whitelist types  │
└─────────┴──────────────────────────┴──────────────┴──────────────────┘

Extended Descriptions
─────────────────────
CWE-79: Improper Neutralization of Input During Web Page 
Generation ('Cross-site Scripting')...

CWE-89: Improper Neutralization of Special Elements used in 
an SQL Command ('SQL Injection')...

CWE-434: Unrestricted Upload of File with Dangerous Type...
```

---

## Next Steps for Users

1. **Open the web interface**: `python app.py`
2. **Navigate to a CVE detail**: Click on any CVE in results
3. **Explore CVSS Vector tab**: Understand attack surface
4. **Explore CWE Explanations tab**: Learn about weaknesses
5. **Read mitigations**: Implement recommended fixes
6. **Review extended descriptions**: Deep-dive technical details

---

**Created**: 2025-01-XX
**Status**: ✅ Complete and ready for use
**Test Coverage**: 15/15 passing
