# CVE Scan Platform - Web Interface

## 🎯 Overview

Web-based vulnerability scanning platform with professional dark theme UI/UX, inspired by OpenVAS. Features real-time scanning, vulnerability management, and comprehensive reporting.

## ✨ Features

### 1. **Dashboard** (`/`)
- **Statistics Cards**:
  - Total Hosts Scanned
  - Open Ports
  - Total CVEs Found
  - Critical CVEs
  - Change indicators from last scan

- **CVE Severity Distribution**:
  - Critical (CVSS 9.0-10.0)
  - High (CVSS 7.0-8.9)
  - Medium (CVSS 4.0-6.9)
  - Low (CVSS 0.1-3.9)

- **Recent Vulnerability Findings Table**:
  - Host/IP, Port, Service, Version
  - CVE ID (linked to NVD)
  - CVSS Score
  - Severity Badge
  - Description
  - Export to CSV
  - Filter functionality

### 2. **Scan Targets** (`/scan`)
- **Configuration Options**:
  - Multiple target input (IP, CIDR, hostnames)
  - Input mode selection (IP/CIDR or Hostname)
  - Authenticated scan support (SSH/WinRM)
  - Credential management

- **Real-time Progress Tracking**:
  - Progress bar with percentage
  - Status messages
  - Scan logs
  - Stop scan capability

### 3. **Vulnerabilities** (`/vulnerabilities`)
- **Filtering**:
  - By severity (Critical, High, Medium, Low)
  - By host
  - By search (CVE, service, description)

- **Features**:
  - Full vulnerability table
  - Export filtered results to CSV
  - Reset filters
  - Real-time vulnerability count

## 🎨 UI/UX Design

### Color Scheme (Dark Theme)
```css
--bg-primary: #0b0f1a       /* Main background */
--bg-secondary: #12182b      /* Cards/panels */
--bg-tertiary: #1a2332       /* Inputs/hover */
--bg-card: #1e2943           /* Interactive elements */

--text-primary: #e8eaed      /* Main text */
--text-secondary: #9aa0a6    /* Secondary text */

--primary: #3b82f6           /* Primary actions */
--success: #10b981           /* Success states */
--warning: #f59e0b           /* Warnings */
--danger: #ef4444            /* Errors/Critical */

--critical: #dc2626          /* Critical CVEs */
--high: #ea580c              /* High CVEs */
--medium: #d97706            /* Medium CVEs */
--low: #2563eb               /* Low CVEs */
```

### Layout
- **Sidebar Navigation** (260px):
  - Dashboard
  - Scan Targets
  - Scan Results
  - Vulnerabilities
  - Reports
  - Settings

- **Top Bar**:
  - Page title
  - Last scan timestamp
  - Notifications (badge)
  - User profile

- **Content Area**:
  - Responsive grid layouts
  - Professional cards with hover effects
  - Interactive tables
  - Real-time updates

## 🚀 Quick Start

### 1. Start Web Server
```bash
cd c:\Users\dhqkh\CVE_Scan
$env:PYTHONPATH="c:\Users\dhqkh\CVE_Scan"
python web\app.py
```

### 2. Access Application
Open browser: `http://localhost:5000`

### 3. Start a Scan
1. Navigate to "Scan Targets"
2. Enter targets (one per line):
   ```
   192.168.1.10
   192.168.1.0/24
   example.com
   ```
3. Select input mode
4. (Optional) Enable authenticated scan
5. Click "Start Scan"

### 4. View Results
- Dashboard automatically updates
- Navigate to "Vulnerabilities" for detailed view
- Export results to CSV

## 📡 API Endpoints

### Scan Management
- `POST /api/scan` - Create and start new scan
  ```json
  {
    "hosts": ["192.168.1.0/24"],
    "input_mode": "IP/CIDR",
    "authenticated": false,
    "auth_data": null
  }
  ```

- `GET /api/scan/<scan_id>` - Get scan status
- `DELETE /api/scan/<scan_id>` - Stop scan
- `GET /api/scans` - List all scans

### Vulnerabilities
- `GET /api/vulnerabilities` - Get all vulnerabilities
  ```json
  {
    "scan_id": "...",
    "generated_at": "2026-01-01T...",
    "total": 892,
    "vulnerabilities": [...]
  }
  ```

### Export
- CSV export available via frontend buttons

## 🔧 Configuration

### Database (config.json)
```json
{
  "use_local_db": true,
  "local_db_path": "modules/cve/nvd_cve.db",
  "cve_max_per_service": 20,
  "cve_year_window": 10,
  ...
}
```

### Scan Settings
- Max concurrent scans: 2
- CIDR expansion: configurable
- Ping timeout: 1s
- Nmap timeout: 60s

## 📊 Features Detail

### Real-time Updates
- Dashboard auto-refreshes every 30 seconds
- Scan progress updates every 2 seconds
- Live vulnerability table updates

### Export Functionality
- CSV export with full vulnerability details
- Filtered export (exports current filter results)
- Timestamp in filename

### Filter System
- Multi-criteria filtering
- Search across all fields
- Instant results update
- Reset to default state

## 🎯 User Workflow

1. **Initial Setup**
   - Configure local CVE database
   - Review settings

2. **Scan Execution**
   - Define targets
   - Configure scan parameters
   - Monitor progress

3. **Results Analysis**
   - Review dashboard statistics
   - Analyze severity distribution
   - Examine individual vulnerabilities

4. **Remediation**
   - Export filtered critical vulnerabilities
   - Share reports with security team
   - Track fixes over time

## 🔐 Security Features

- Credential management for authenticated scans
- Secure password fields
- CVE validation against NVD
- CVSS scoring integration

## 📈 Performance

- Concurrent scanning (configurable workers)
- Database caching (323,869+ CVEs)
- Fuzzy CVE matching for better coverage
- Efficient CIDR expansion

## 🛠️ Troubleshooting

### No CVEs Found
1. Check local DB exists: `modules/cve/nvd_cve.db`
2. Verify config: `use_local_db: true`
3. Review service detection logs
4. Ensure version information available

### Scan Not Starting
1. Check target format
2. Verify network connectivity
3. Review console logs
4. Check authentication credentials (if enabled)

### Web Interface Issues
1. Clear browser cache
2. Check console for JavaScript errors
3. Verify Flask server running
4. Check PYTHONPATH set correctly

## 📝 Future Enhancements

- [ ] User authentication/authorization
- [ ] Multiple scan profiles
- [ ] Scheduled scans
- [ ] Email notifications
- [ ] PDF report generation
- [ ] Vulnerability remediation tracking
- [ ] Integration with ticketing systems
- [ ] API authentication
- [ ] WebSocket for real-time updates
- [ ] Scan history comparison

## 🤝 Contributing

See main project README for development guidelines.

## 📄 License

See LICENSE file in project root.

---

**Professional vulnerability scanning, made accessible.**

Built with Flask, Python, and modern web technologies.
Inspired by OpenVAS and enterprise security tools.
