# CVE Likelihood Integration - Quick Reference Guide

## What is Likelihood?

**Likelihood** = CVSS Score × EPSS (Exploit Prediction Scoring System)

The likelihood score represents the probability that a CVE will be exploited in the wild. It combines:
- **CVSS** (Severity): How bad the vulnerability is (0-10 scale)
- **EPSS** (Exploitability): How likely to be exploited (0-1 scale)

**Result**: A 0-10 scale showing actual risk

## Where to Find It

**Navigate to**: `/vulnerabilities` page in CVE_Scan web interface

The LIKELIHOOD column appears in the vulnerability table with:
- **Score**: Calculated value with 5 decimal precision
- **Badge**: Color-coded severity indicator

## Understanding the Colors

| Badge Color | Score Range | Meaning |
|------------|-------------|---------|
| 🔴 **HIGH** | ≥ 7.0 | Critical - High likelihood of exploitation |
| 🟠 **MEDIUM** | 4.0 - 6.99 | Important - Moderate exploitation risk |
| 🟢 **LOW** | < 4.0 | Minor - Low exploitation probability |

## How to Use It

### 1. **Quick Prioritization**
- Look at the LIKELIHOOD column to see actual risk
- High scores = higher priority for patching
- Better than CVSS alone (CVSS might be high but unlikely to be exploited)

### 2. **Hover for Details**
- Hover your mouse over the likelihood score
- Tooltip shows the EPSS value
- Example: "EPSS: 0.94358"

### 3. **Click CVE for Full Details**
- Click CVE ID to open detail modal
- View all CVSS versions, EPSS, and other data
- See remediation guidance

### 4. **Export Data**
- Export vulnerabilities to CSV
- Includes likelihood scores for analysis
- Can be used in risk reports

## Real-World Example

**Scenario**: You have 2 CVEs discovered:

| CVE | CVSS | EPSS | Likelihood | Decision |
|-----|------|------|------------|----------|
| CVE-A | 9.0 | 0.15 | 1.35 (LOW) | Lower priority - less likely to be exploited |
| CVE-B | 5.0 | 0.95 | 4.75 (MEDIUM) | Higher priority - more likely to be exploited |

**Insight**: CVE-B should be patched first because it's more likely to be exploited, even though it has a lower CVSS score.

## Key Features

✅ **Automatic Calculation**
- Likelihood automatically calculated for each CVE
- No manual input needed

✅ **5 Decimal Precision**
- Scores like 7.07685 show exact calculation
- Useful for detailed analysis

✅ **Color-Coded Badges**
- Immediate visual indication of risk level
- Easy scanning of large vulnerability lists

✅ **EPSS Integration**
- Combines NVD vulnerability data with EPSS
- 309,301 CVE records in database

## Technical Details

### Calculation Process
1. System receives CVE from scan
2. Extracts CVSS score (prioritizes v4 > v3 > v2)
3. Looks up EPSS in database
4. Multiplies: CVSS × EPSS = Likelihood
5. Classifies into HIGH/MEDIUM/LOW
6. Displays in table with color badge

### Data Sources
- **CVSS**: From NVD (National Vulnerability Database)
- **EPSS**: From EPSS database (modules/cve/epss.db)
- **Updated**: Database automatically synced with NVD

## Troubleshooting

### Q: Why does a CVE show "-" for likelihood?
**A**: The EPSS database doesn't have data for that CVE (possibly very new). System uses conservative estimate (0.01 EPSS).

### Q: How often is EPSS data updated?
**A**: Run `scripts/rebuild_local_db.py` to refresh EPSS database with latest data.

### Q: Can I export vulnerabilities with likelihood?
**A**: Yes! Use the "Export to CSV" button - includes likelihood scores.

### Q: What if CVSS is high but likelihood is low?
**A**: It's a severe vulnerability but rarely exploited in practice. Depends on your risk tolerance.

## Best Practices

1. **Sort by Likelihood**
   - Focus on HIGH likelihood vulnerabilities first
   - These pose immediate exploitation risk

2. **Monitor EPSS Changes**
   - EPSS scores change as exploits become available
   - Review critical CVEs regularly

3. **Balance with CVSS**
   - Use both CVSS and likelihood for decisions
   - High CVSS + Low EPSS = lower immediate priority
   - Low CVSS + High EPSS = higher immediate priority

4. **Regular Reviews**
   - Re-scan weekly to catch new vulnerabilities
   - Check updated EPSS scores for existing CVEs
   - Update patches based on likelihood changes

5. **Report Findings**
   - Include likelihood scores in security reports
   - Helps stakeholders understand real risk
   - Justifies prioritization decisions

## Integration Points

### API Endpoint
```
GET /api/vulnerabilities
```

Returns JSON with likelihood data:
```json
{
  "cve_id": "CVE-2021-44228",
  "cvss_v3": 10.0,
  "likelihood": {
    "epss": 0.94358,
    "score": 9.43580,
    "level": "HIGH"
  }
}
```

### HTML Table
- Column header: "LIKELIHOOD"
- Shows score (5 decimals) + colored badge
- Sortable and filterable

### Backend Route
- Location: `web/routes/vulnerabilities.py`
- Automatically enriches CVE data with likelihood
- Uses `LikelihoodCalculator` class

## Advanced Usage

### Filter by Likelihood Level
(Feature in development)
- Filter: Show only HIGH risk
- Filter: Show only MEDIUM risk
- Filter: Show only LOW risk

### Sort by Likelihood
(Feature in development)
- Sort ascending: LOW → MEDIUM → HIGH
- Sort descending: HIGH → MEDIUM → LOW

### Likelihood Trends
(Feature in development)
- Chart likelihood over time
- Identify newly exploitable CVEs
- Predict future exploitation risk

## FAQ

**Q: Is likelihood the same as CVSS severity?**
A: No. CVSS measures vulnerability severity (impact/exploitability of the bug). Likelihood measures probability of real-world exploitation (based on EPSS). CVSS = potential impact, Likelihood = actual risk.

**Q: Should I ignore LOW likelihood CVEs?**
A: Not completely, but they can be lower priority. If they have high CVSS (severe), still worth patching. But exploit risk is lower.

**Q: How is EPSS calculated?**
A: EPSS uses machine learning on historical CVE data to predict which vulnerabilities will be exploited. Developed by Cyentia Institute.

**Q: Can likelihood change over time?**
A: Yes! EPSS scores update as new exploitation data becomes available. Re-run database refresh to get latest scores.

**Q: Why is this better than CVSS alone?**
A: CVSS is static (doesn't change). Likelihood is dynamic and reflects actual threat landscape. Many high-CVSS vulnerabilities are never exploited in practice.

## Getting Help

- Check logs in web interface: Settings → Logs
- Run test suite: `python test_likelihood_web_integration.py`
- Review database: `sqlite3 modules/cve/epss.db`
- Contact support with CVE ID for specific issues

## Summary

The Likelihood feature transforms how you prioritize CVE patching:
- **Before**: Patch all high-CVSS CVEs (many never exploited)
- **After**: Patch high-likelihood CVEs first (actual risk)

Result: Better resource allocation and faster response to real threats.

---
**Last Updated**: January 2024
**Version**: 1.0
**Status**: Production Ready ✅
