# CVE Scan Security Platform - Technical Report

## 1. Overview
- Desktop-driven security scanner with web dashboard (Flask) for host/service discovery, CVE mapping, likelihood scoring, and reporting.
- Supports unauthenticated and authenticated scans (SSH/WinRM), outputs CSV/HTML/PDF and interactive dashboard.

## 2. Core Architecture
- **Entry points**: `app.py` (GUI launcher), `web/app.py` (Flask dashboard server), `modules/scan_manager.py` (scan orchestration).
- **Pipelines**: `modules/pipelines/basic_pipeline.py` (no auth), `modules/pipelines/authenticated_pipeline.py` (SSH/WinRM via `auth_linux_scanner.py`, `auth_windows_scanner.py`).
- **Discovery & Scanning**:
  - Host discovery: `modules/discovery/host_discovery.py` using `nmap -sn`.
  - Port scan: `modules/scanners/rustscan_scanner.py` (fast SYN via WSL rustscan) and `modules/scanners/nmap_scanner.py` (service/version detection).
- **CVE/CWE/EPSS logic**:
  - CPE build & match: `modules/cve/cpe_builder.py`, `modules/cve/cve_matcher.py`, fuzzy via `fuzzy_matcher.py`.
  - CVE data: fetched from NVD API (`modules/cve/nvd_fetcher.py`) or local DB (`local_db_fetcher.py`, `cve.db`).
  - CWE data: `modules/cve/cwe_lookup.py` reading `cwe.db` (imported from `cwec_v4.19.xml` + `attack_mitigations.csv` for Common Consequences).
  - Likelihood/EPSS: `modules/cve/likelihood_calculator.py`, `likelihood_integration.py`, `build_epss_db.py`.
- **Reporting**: `modules/report/{csv_report,html_report,pdf_report,cpe_report}.py`; dashboard adapter `modules/report/dashboard_adapter.py`.
- **Web UI**: Flask routes under `web/routes/*`, templates under `web/templates/*`, JS/CSS under `web/static/js|css` (notably `cve_modal.js`, `dashboard.js`).

## 2.1. Scan Flows

### Flow A: Basic Unauthenticated Scan (BasicPipeline)
**Trigger**: User provides IP/CIDR/hostname without credentials.

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INPUT PROCESSING (ScanManager)                               │
│    - Accept targets: single IP, CIDR (192.168.1.0/24), hostname │
│    - Determine input_mode: "IP/CIDR" or "Hostname (Domain)"     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. ASSET DISCOVERY (modules/discovery/asset_discovery.py)       │
│    IF input_mode = "Hostname (Domain)":                         │
│      - DNS A/AAAA record lookup → extract IPs                   │
│      - WHOIS query → organization/contact info                  │
│      - ASN lookup → network owner details                       │
│      - Reverse DNS → PTR records for discovered IPs             │
│    IF input_mode = "IP/CIDR":                                   │
│      - CIDR expansion: 192.168.1.0/24 → 192.168.1.1-254         │
│      - Cap at max_cidr_ips (default 1024) for large ranges      │
│    OUTPUT: List of IP addresses to scan                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. HOST DISCOVERY (modules/discovery/host_discovery.py)         │
│    - Run: nmap -sn <IP list> (ping sweep)                       │
│    - Techniques: ICMP Echo, TCP SYN to common ports, ARP        │
│    - Parallel workers (default 100) for speed                   │
│    - Parse output: extract only "Host is up" IPs                │
│    OUTPUT: Filtered list of alive hosts                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. PARALLEL IP SCANNING (ThreadPoolExecutor)                    │
│    - Max concurrent: max_concurrent_scans (default 4 IPs)       │
│    - For EACH alive IP:                                         │
└─────────────────────────────────────────────────────────────────┘
       ↓                      ↓                      ↓
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │  IP 1   │           │  IP 2   │    ...    │  IP N   │
   └─────────┘           └─────────┘           └─────────┘
        │
        ├──→ 4a. PORT DISCOVERY (RustScan)
        │    └─ Run: rustscan -a <IP> --ulimit 5000 --timeout 1500
        │    └─ Fast TCP SYN scan on all 65535 ports
        │    └─ Parse: extract open port list [22, 80, 443, ...]
        │
        ├──→ 4b. SERVICE DETECTION (Nmap)
        │    └─ Run: nmap -sV -p <port list> <IP>
        │    └─ Connect to each port, send probes
        │    └─ Parse: service name, product, version, extrainfo
        │    └─ Heuristic parsing for version extraction
        │
        ├──→ 4c. CPE CONSTRUCTION (modules/cve/cpe_builder.py)
        │    └─ For each service (port):
        │         - Map product+version → CPE 2.3 format
        │         - Examples:
        │           • OpenSSH 8.2p1 → cpe:2.3:a:openbsd:openssh:8.2p1
        │           • Apache 2.4.49 → cpe:2.3:a:apache:http_server:2.4.49
        │         - Use remote NVD CPE API if use_local_db=false
        │         - Use offline heuristics if use_local_db=true
        │
        ├──→ 4d. CVE MATCHING (modules/cve/cve_matcher.py)
        │    └─ For each CPE:
        │         - Query NVD API or local SQLite DB
        │         - Fuzzy matching via fuzzy_matcher.py if exact fails
        │         - Return CVEs: id, description, CVSS, severity, CWE
        │         - Apply filters:
        │           • cve_year_window: limit to recent years (0=all)
        │           • cve_max_per_service: cap at 50 CVEs per port
        │
        ├──→ 4e. LIKELIHOOD SCORING (modules/cve/likelihood_calculator.py)
        │    └─ For each CVE:
        │         - Fetch EPSS score (exploit probability)
        │         - Calculate composite likelihood (CVSS + EPSS)
        │         - Rank CVEs by exploitability
        │
        └──→ 4f. RESULT NORMALIZATION
             └─ Build per-IP result dict:
                  {
                    "host": "192.168.1.100",
                    "ports": [
                      {
                        "port": 22,
                        "service": "ssh",
                        "product": "OpenSSH",
                        "version": "8.2p1",
                        "cpe": "cpe:2.3:a:openbsd:openssh:8.2p1",
                        "cves": [
                          {
                            "id": "CVE-2024-1234",
                            "description": "...",
                            "cvss": 9.8,
                            "severity": "CRITICAL",
                            "cwe": ["CWE-79"],
                            "epss": 0.85,
                            "likelihood": "HIGH"
                          }
                        ]
                      }
                    ]
                  }
             └─ Invoke host_result_cb(ip, result) → GUI update
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. AGGREGATION & OUTPUT (ScanManager)                           │
│    - Collect all per-IP results                                 │
│    - Generate reports: CSV, HTML, PDF (modules/report/*)        │
│    - Persist to data/scans/<scan_id>.json                       │
│    - Return to GUI/Dashboard for display                        │
└─────────────────────────────────────────────────────────────────┘
```

### Flow B: Authenticated Scan (AuthenticatedPipeline)
**Trigger**: User provides credentials (SSH for Linux, WinRM for Windows).

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INPUT PROCESSING (ScanManager)                               │
│    - Skip host discovery (no ping) - assumes hosts are up       │
│    - Accept: target IP + auth_data {username, password, type}   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. AUTHENTICATED CONNECTION                                     │
│    (modules/scanners/authenticated_scanner.py)                  │
│                                                                  │
│    IF platform = Linux:                                         │
│      → modules/scanners/auth_linux_scanner.py                   │
│         - SSH connect via paramiko (port 22)                    │
│         - Commands:                                             │
│           • dpkg -l (Debian/Ubuntu) → package list              │
│           • rpm -qa (RedHat/CentOS) → package list              │
│           • cat /etc/os-release → OS info                       │
│         - Parse package names + versions                        │
│                                                                  │
│    IF platform = Windows:                                       │
│      → modules/scanners/auth_windows_scanner.py                 │
│         - WinRM connect via pywinrm (port 5985/5986)            │
│         - Commands:                                             │
│           • Get-WmiObject Win32_Product → installed software    │
│           • Get-ItemProperty HKLM:\Software\... → registry      │
│           • systeminfo → OS version                             │
│         - Parse software names + versions                       │
│                                                                  │
│    OUTPUT: {os: {...}, software: [{name, version, vendor}]}     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. CPE CONSTRUCTION (modules/cve/cpe_builder.py)                │
│    - For OS: build OS CPE                                       │
│      • Ubuntu 20.04 → cpe:2.3:o:canonical:ubuntu_linux:20.04    │
│      • Windows Server 2019 → cpe:2.3:o:microsoft:windows:2019   │
│    - For each software package:                                 │
│      • nginx 1.18.0 → cpe:2.3:a:nginx:nginx:1.18.0              │
│      • mysql 8.0.25 → cpe:2.3:a:oracle:mysql:8.0.25             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. CVE MATCHING (modules/cve/cve_matcher.py)                    │
│    - Query NVD API or local DB for each CPE                     │
│    - OS-level CVEs (kernel, system libraries)                   │
│    - Application-level CVEs (nginx, mysql, etc.)                │
│    - Fuzzy matching for version variants                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. LIKELIHOOD SCORING & NORMALIZATION                           │
│    - Calculate EPSS/likelihood per CVE                          │
│    - Organize by service/package                                │
│    - Return structured result:                                  │
│      {                                                           │
│        "os": {cpe, cves: [...]},                                │
│        "services": {                                            │
│          "nginx": {port: null, cpe, cves: [...]},               │
│          "mysql": {port: 3306, cpe, cves: [...]}                │
│        }                                                         │
│      }                                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. OUTPUT (ScanManager)                                         │
│    - Reports: CSV, HTML, PDF                                    │
│    - Persist to data/scans/<scan_id>.json                       │
│    - Display in Dashboard                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Flow C: Dashboard API Request (Runtime)
**Trigger**: User clicks CVE in web dashboard.

```
Frontend (cve_modal.js)
    ↓ GET /api/cve/<cve_id>/cwe-data
web/routes/dashboard.py
    ↓ Parse CVE ID, fetch CWE from NVD API
    ↓ Query modules/cve/cwe_lookup.py
modules/cve/cwe.db (SQLite)
    ↓ SELECT plain_text FROM cwe_consequence_plain WHERE cwe_id=?
    ↓ Apply parser: _parse_consequence_text()
    ↓   • ::SCOPE: → **SCOPE:**
    ↓   • ::IMPACT: → •
    ↓   • ::NOTE: → paragraph break
    ↓ Return JSON: {cwe_id, plain_text, consequences}
Frontend
    ↓ Render in modal with white-space: pre-line
```

### Scan Configuration Tunables
| Parameter | Default | Impact |
|-----------|---------|--------|
| `max_concurrent_scans` | 4 | Parallel IP scans (CPU/network) |
| `rustscan_ulimit` | 5000 | Max concurrent sockets (NAT stress) |
| `rustscan_timeout` | 1500ms | Port scan speed vs accuracy |
| `ping_workers` | 100 | Host discovery parallelism |
| `nmap_timeout` | 60s | Service detection depth |
| `cve_max_per_service` | 50 | Limit CVEs to avoid overload |
| `use_local_db` | false | Use local DB vs NVD API calls |

## 3. Data Sources
- **NVD CVE**: Remote API (requires `nvd_api_key`) or local SQLite (`modules/cve/cve.db`, `modules/cve/nvd_data/*`).
- **CWE**: `modules/cve/cwe.db` built from `cwec_v4.19.xml` plus `attack_mitigations.csv` (Common Consequences column imported as-is).
- **EPSS / Likelihood**: Built via `build_epss_db.py`, integrated in likelihood calculators.

## 4. Configuration
- Main config: `config.json` (API keys, local DB toggle, paths).
- Scanner behavior (timeouts, workers, ulimit) defined in scanner/discovery classes; can be tuned to reduce network impact.
- I18n: `web/static/i18n/en.json`, `vi.json` for UI text.

## 5. Runtime Behavior & Resources
- **Network**: Host discovery (ICMP/ARP/TCP probes), port scanning (SYN to many ports), service probing (TCP connects). Can stress NAT/router if scanning large CIDRs or using aggressive settings (rustscan ulimit).
- **CPU**: CPE/CVE matching, likelihood scoring, report generation; moderate load during large scans or PDF export.
- **Storage**: SQLite DBs for CVE/CWE/EPSS; scan results in `data/scans/`.

## 6. Outputs
- Interactive dashboard (Flask) with CVE details, CWE consequences (from Common Consequences CSV), NIST R5 recommendations, and MITRE ATT&CK mapping.
- Export formats: CSV, HTML, PDF reports; scan artifacts persisted in `data/scans/`.

## 7. Key Files by Responsibility
- Orchestration: `modules/scan_manager.py`, `modules/scan_manager_storage.py` (if present), `modules/report/dashboard_adapter.py`.
- Discovery/Scanning: `modules/discovery/host_discovery.py`, `modules/scanners/{rustscan_scanner,nmap_scanner,authenticated_scanner}.py`.
- Vulnerability Intelligence: `modules/cve/{nvd_fetcher,local_db_fetcher,cwe_lookup,cve_matcher,fuzzy_matcher,likelihood_calculator}.py`.
- Web UI: `web/routes/dashboard.py`, templates `web/templates/dashboard.html`, modal logic `web/static/js/cve_modal.js`.

## 8. Notes & Considerations
- Ensure rustscan (via WSL) and nmap are installed for full scan capability.
- For low-impact scans, reduce concurrency/ulimit and narrow target ranges.
- CWE “Common Consequences” shown in UI come directly from `attack_mitigations.csv` via `cwe_consequence_plain` table and parsed for readability.
