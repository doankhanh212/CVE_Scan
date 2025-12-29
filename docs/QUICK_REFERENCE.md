# 🚀 CVE_Scan Quick Reference

**Version:** 1.0  
**Quick Start:** 5 minutes to scanning

---

## 📥 Installation (First Time)

### Option 1: Local Installation (Recommended)
```bash
# 1. Extract files
unzip cve_scan_1.0.zip
cd CVE_Scan

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python verify_installation.py

# 5. Run the app
python app.py
```

### Option 2: Docker (Easiest)
```bash
# 1. Build image
docker build -t cve-scan:1.0 .

# 2. Run container
docker-compose up

# 3. Access GUI
VNC: localhost:5900
noVNC: http://localhost:6080
```

### Option 3: Development Setup
```bash
# Clone from git
git clone <repository-url>
cd CVE_Scan
pip install -e .
python app.py
```

---

## 🎯 Running a Scan

### Via GUI (Easiest)
```bash
python app.py
```

1. **Select Mode:**
   - Unauthenticated: Basic nmap scan
   - Authenticated: SSH/WinRM credentials

2. **Enter Targets:**
   - Single IP: `192.168.1.100`
   - CIDR range: `192.168.1.0/24`
   - Multiple: One per line

3. **Configure (Optional):**
   - Click ⚙️ Settings
   - Add NVD API key for latest CVEs
   - Adjust severity filtering

4. **Run Scan:**
   - Click "Quét"
   - Watch progress in log
   - View results in table

5. **Export Results:**
   - Click "Xuất"
   - Choose format: CSV, HTML, PDF, JSON

### Via Command Line
```bash
# Quick test
python scripts/smoke_run_scan.py localhost

# Full pipeline test
python scripts/test_filtering.py

# Database operations
python scripts/rebuild_local_db.py
python scripts/download_nvd_feeds.py
```

---

## ⚙️ Configuration

### Basic Setup
```bash
# Edit config.json
{
  "nvd_api_key": "your_api_key_here",
  "use_local_db": true,
  "cve_year_window": 10,
  "cve_max_per_service": 20
}
```

### Get NVD API Key
1. Visit: https://nvd.nist.gov/developers/start-here
2. Register for free account
3. Copy API key to config.json

### Advanced Options
- `log_verbosity`: "normal" or "debug"
- `local_db_path`: Path to CVE database
- `use_local_db`: Use local database instead of API
- `cve_year_window`: Years of CVE history (default: 10)

---

## 🧪 Testing

### Run Test Suite
```bash
# All tests
python -m pytest -v

# Specific test
python -m pytest tests/test_host_discovery.py -v

# With coverage
python -m pytest --cov=modules tests/

# Quick verification
python verify_installation.py
```

### Available Tests
```
tests/test_host_discovery.py       - Host discovery (nmap -sn)
tests/test_gui.py                  - GUI helpers & CSV export
tests/test_csv_report.py           - Report generation
tests/test_fuzzy_matcher.py        - CVE matching
tests/test_scan_manager_progress.py - Progress callbacks
tests/test_auth_linux.py           - Linux authentication
tests/test_windows_mapping.py      - Windows mapping
```

---

## 📊 Scanning Features

### Host Discovery
- **Method:** nmap -sn (ARP, ICMP, TCP SYN/ACK, UDP)
- **Speed:** 5-10x faster than sequential ping
- **Supports:** Single IPs, IP ranges, CIDR notation

### Port & Service Detection
- **Tools:** Nmap + RustScan
- **Service Identification:** -sV flag
- **Version Detection:** Product and version extraction

### Authenticated Scanning
- **SSH (Linux):** Paramiko-based remote execution
- **WinRM (Windows):** pywinrm for PowerShell commands
- **Commands:** Software inventory, registry queries

### CVE Matching
- **Sources:** NVD API v2.0 or local SQLite database
- **Matching:** CPE-based with fuzzy product name matching
- **Filtering:** By severity (CRITICAL/HIGH/MEDIUM/LOW)
- **Deduplication:** Automatic removal of duplicate CVEs

---

## 📁 File Locations

### Important Directories
```
CVE_Scan/
├── config.json              ← Configuration (edit this)
├── modules/cve/nvd_cve.db  ← Local CVE database
├── reports/                 ← Generated scan reports
├── logs/                    ← Log files
└── backups/                 ← Scan result backups
```

### Generated Files
- **Reports:** `*.csv`, `*.html`, `*.pdf`, `*.json`
- **Database:** `modules/cve/nvd_cve.db` (auto-built)
- **Cache:** `nvd_cache.json` (API response cache)

---

## 🔄 Common Workflows

### Workflow 1: Quick Network Scan
```bash
python app.py
→ Enter: 192.168.1.0/24
→ Click Quét
→ Wait for results
→ Click Xuất → CSV
```

### Workflow 2: Authenticated Scanning
```bash
python app.py
→ Select "Authenticated"
→ Enter: username, password
→ Enter: targets (one per line)
→ Click Quét
→ Get detailed software inventory
```

### Workflow 3: Rebuild CVE Database
```bash
python scripts/rebuild_local_db.py
→ Downloads latest NVD data
→ Imports into local database
→ Ready for offline scanning
```

### Workflow 4: Validate Installation
```bash
python verify_installation.py
→ Checks Python version
→ Verifies all dependencies
→ Tests core modules
→ Confirms nmap installed
```

---

## 🐛 Troubleshooting

### "nmap not found"
```bash
# Install nmap
# Ubuntu/Debian
sudo apt-get install nmap

# Mac
brew install nmap

# Windows
# Download from https://nmap.org/download.html
```

### "Module not found" error
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Slow API lookups
```bash
# Use local database instead
# Edit config.json:
{
  "use_local_db": true
}

# Rebuild database if needed
python scripts/rebuild_local_db.py
```

### Permission denied (scanning)
```bash
# Windows: Run as Administrator
# Linux: Use sudo
# Mac: May require sudo for some operations
```

---

## 📈 Performance Tips

1. **Use nmap -sn for discovery**
   - Automatic in this version
   - 5-10x faster than ping

2. **Local database for scanning**
   - No API rate limits
   - Faster CVE lookups
   - Set `use_local_db: true`

3. **Adjust scan timing**
   - Edit config.json
   - Tune parallelism for your network

4. **Filter by severity**
   - Reduces processing
   - Focuses on high-risk CVEs

---

## 🔐 Security Best Practices

1. **API Key Management**
   - Never commit config.json to git
   - Use environment variables in production
   - Regenerate keys periodically

2. **Network Scanning**
   - Ensure you have authorization
   - Scan during maintenance windows
   - Monitor for detection by IDS/IPS

3. **Report Handling**
   - Store reports securely
   - Implement access controls
   - Encrypt sensitive scans

4. **Credential Management**
   - Use service accounts for scanning
   - Rotate credentials regularly
   - Log all authenticated access

---

## 📞 Getting Help

### Built-in Help
```bash
# Installation verification
python verify_installation.py

# Run tests
python -m pytest tests/ -v

# Check configuration
cat config.json
```

### Documentation Files
- **BUG_AUDIT_REPORT.md** - Quality assurance details
- **PACKAGING_GUIDE.md** - Complete setup guide
- **ANALYSIS.md** - Technical deep dive
- **README_ASSET_DISCOVERY.md** - Feature explanation
- **.github/copilot-instructions.md** - Developer guide

### Diagnostic Commands
```bash
# Check version
python app.py --version

# Test connectivity
python scripts/smoke_run_scan.py

# Validate configuration
python -c "from modules.config_manager import ConfigManager; ConfigManager()"
```

---

## 🎯 Quick Scan Examples

### Scan Single Host
```
Target: 192.168.1.100
Mode: Unauthenticated
Expected: ~5-10 minutes
Output: CSV with CVEs
```

### Scan Network Subnet
```
Target: 192.168.1.0/24 (256 IPs)
Mode: Unauthenticated
Expected: ~15-30 minutes
Output: Summary report of all CVEs
```

### Authenticated Linux Scan
```
Target: 10.0.0.1-10.0.0.10
Mode: Authenticated (SSH)
Credentials: domain\\user, password
Expected: ~20-30 minutes (detailed)
Output: Software inventory + CVEs
```

### Docker Scanning
```
docker run -it cve-scan:1.0
→ Access VNC at localhost:5900
→ Same workflow as local GUI
→ Reports saved to mounted volume
```

---

## ✅ Verification Checklist

After installation, verify:
```bash
✅ python verify_installation.py        # Should pass all checks
✅ python -m pytest tests/ -q          # Should show 100% pass
✅ python app.py                       # Should launch GUI
✅ nmap --version                      # Should show version
✅ cat config.json                     # Should show valid config
```

---

## 🎓 Learn More

- **Documentation:** See ANALYSIS.md for comprehensive guide
- **Source Code:** Read modules/ for implementation details
- **Tests:** See tests/ for usage examples
- **Scripts:** Check scripts/ for utility operations

---

**Ready to scan?** Run `python app.py` and start discovering vulnerabilities! 🚀
