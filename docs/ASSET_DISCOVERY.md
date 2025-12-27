# Asset Discovery Module - Implementation Guide

## Overview

The **Asset Discovery** module enhances CVE_Scan with comprehensive asset reconnaissance:

```
Domain/Hostname
    ↓
DNS Resolution (A/AAAA records, concurrent)
    ↓
IP + WHOIS → ASN → CIDR (with fallback on timeout)
    ↓
Reverse DNS (IP → Hostname)
    ↓
Asset Inventory: {IP, CIDR, ASN, Hostname, Confidence}
    ↓
Scan Filter (only high-confidence targets)
```

---

## Architecture

### Module Structure

```
modules/discovery/
├── host_discovery.py       (Existing: ICMP ping)
└── asset_discovery.py      (NEW: DNS + WHOIS + ASN + RevDNS)
```

### Core Classes

#### 1. **Asset**
Represents a single discovered asset with metadata:

```python
asset = Asset("192.168.1.1")
asset.add_hostname("example.com")
asset.asn = "AS1234"
asset.cidr = "192.168.1.0/24"
asset.confidence = 0.95  # Confidence score (0-1)

# Export
asset_dict = asset.to_dict()
# {
#   "ip": "192.168.1.1",
#   "type": "IPv4",
#   "hostnames": ["example.com"],
#   "asn": "AS1234",
#   "cidr": "192.168.1.0/24",
#   "confidence": 0.95,
#   "source": ["dns", "whois", "reverse_dns"],
#   "scan_priority": 1
# }
```

**Attributes:**
- `ip`: IP address
- `hostnames`: Set of associated hostnames
- `asn`: Autonomous System Number
- `cidr`: CIDR block
- `org`: Organization name
- `country`: Country code
- `confidence`: Confidence score (0-1, higher = more reliable)
- `source`: List of discovery methods used
- `scan_priority`: Priority for scanning (1=highest)

#### 2. **DNSResolver**
Concurrent DNS resolution with timeout handling:

```python
resolver = DNSResolver(timeout=5, max_workers=10)

# Single hostname
ips = resolver.resolve_hostname("example.com")
# Returns: ["192.168.1.1", "192.168.1.2"]

# Multiple hostnames (concurrent)
results = resolver.resolve_many(["host1.com", "host2.com"])
# Returns: {"host1.com": ["192.168.1.1"], "host2.com": ["192.168.1.2"]}
```

**Features:**
- ✅ Supports IPv4 + IPv6
- ✅ Concurrent lookup (ThreadPoolExecutor)
- ✅ Timeout handling
- ✅ Deduplicates IPs

#### 3. **WHOISLookup**
WHOIS/ASN lookup with graceful timeout fallback:

```python
whois = WHOISLookup(timeout=10)

# Single IP
asn, cidr, org, success = whois.lookup_ip("192.168.1.1")
# Returns: ("AS1234", "192.168.0.0/16", "Example Corp", True)

# Multiple IPs (concurrent)
results = whois.lookup_many(["192.168.1.1", "192.168.1.2"])
# Returns: {
#   "192.168.1.1": {"asn": "AS1234", "cidr": "192.168.0.0/16", "org": "...", "success": True},
#   "192.168.1.2": {"asn": None, "cidr": None, "org": None, "success": False}  # Timeout
# }
```

**Key Feature: Graceful Degradation**
- ✅ On timeout → returns `success=False` but continues (doesn't crash)
- ✅ Confidence score reduced but asset still scanned
- ✅ Library: `ipwhois` (lightweight, no external API key needed)

#### 4. **ReverseDNS**
Reverse DNS lookup with concurrent execution:

```python
reverse = ReverseDNS(timeout=5)

# Single IP
hostname = reverse.reverse_lookup("192.168.1.1")
# Returns: "www.example.com" or None

# Multiple IPs (concurrent)
results = reverse.reverse_lookup_many(["192.168.1.1", "192.168.1.2"])
# Returns: {"192.168.1.1": "www.example.com", "192.168.1.2": None}
```

#### 5. **CIDRExpander**
Expand CIDR blocks to IP list for asset inventory:

```python
expander = CIDRExpander()

# Expand /24 to individual IPs (max 256)
ips = expander.expand_cidr("192.168.1.0/24", max_ips=256)
# Returns: ["192.168.1.1", "192.168.1.2", ..., "192.168.1.254"]
```

#### 6. **AssetDiscovery** (Main Orchestrator)
Coordinates all discovery steps:

```python
discovery = AssetDiscovery(logger=logger_cb, progress_cb=progress_cb)

# Discover assets from hostnames
assets = discovery.discover(["example.com", "192.168.1.1"])
# Returns: {"192.168.1.1": Asset(...), "192.168.1.2": Asset(...), ...}

# Filter which assets to scan (high confidence only)
scan_ips = discovery.filter_for_scan(assets)
# Returns: ["192.168.1.1", "192.168.1.2"]  (sorted by priority)
```

---

## Confidence Scoring

Assets are scored based on discovery method:

| Method | Score | Notes |
|--------|-------|-------|
| **DNS Resolved** | 1.0 | Found via DNS A/AAAA record |
| **WHOIS Success** | 0.95 | WHOIS lookup succeeded |
| **Reverse DNS** | 0.85 | Reverse DNS found |
| **WHOIS Timeout** | 0.70 | WHOIS failed, but continue |
| **CIDR Inferred** | 0.75 | Inferred from ASN CIDR |

**Scan Filter Logic:**
- **Score ≥ 0.85**: High priority (SCAN immediately)
- **0.70 ≤ Score < 0.85**: Medium priority (SCAN with caution)
- **Score < 0.70**: Inventory only (no scan)

---

## Integration with BasicPipeline

The **BasicPipeline** now includes asset discovery as step 0:

```python
class BasicPipeline:
    def __init__(self, config, logger, progress_cb):
        self.asset_discovery = AssetDiscovery(logger, progress_cb)
        # ... other components ...

    def execute(self, target: str) -> Dict[str, Any]:
        # Step 0: Asset Discovery
        assets = self.asset_discovery.discover([target])
        scan_ips = self.asset_discovery.filter_for_scan(assets)
        primary_ip = scan_ips[0]
        
        # Step 1-4: Port scan, service detection, CPE, CVE matching
        # (using primary_ip instead of target)
```

**Benefits:**
- ✅ Resolves hostnames to IPs automatically
- ✅ Collects ASN/CIDR for context
- ✅ Filters unreliable targets
- ✅ Provides asset inventory alongside vulnerabilities

---

## Error Handling & Fallbacks

### DNS Resolution Fails
→ Continue with empty asset list (silent skip)

### WHOIS Timeout
→ **Continue with lower confidence** (NOT a pipeline blocker)
- Confidence score reduced to 0.70
- Asset still marked for scan
- Source logged as `"whois_timeout"`

### Reverse DNS Timeout
→ Skip reverse DNS, continue with forward DNS results

### All discovery fails
→ Return empty asset dict, skip scan

---

## Usage Examples

### Example 1: Single Hostname Discovery

```python
from modules.discovery.asset_discovery import AssetDiscovery

discovery = AssetDiscovery()
assets = discovery.discover(["example.com"])

for ip, asset in assets.items():
    print(f"IP: {asset.ip}")
    print(f"  Hostnames: {asset.hostnames}")
    print(f"  ASN: {asset.asn}")
    print(f"  CIDR: {asset.cidr}")
    print(f"  Confidence: {asset.confidence}")
    print(f"  Sources: {asset.source}")
```

### Example 2: Scan Filtering

```python
discovery = AssetDiscovery()
assets = discovery.discover(["example.com"])

# Only scan high-confidence assets
scan_ips = discovery.filter_for_scan(assets)
print(f"Will scan {len(scan_ips)} assets (out of {len(assets)} discovered)")

for ip in scan_ips:
    asset = assets[ip]
    print(f"{ip} (priority: {asset.scan_priority}, conf: {asset.confidence})")
```

### Example 3: Asset Inventory Report

```python
discovery = AssetDiscovery()
assets = discovery.discover(["example.com"])

# Export for inventory
inventory = {ip: asset.to_dict() for ip, asset in assets.items()}

# Can be saved to JSON, CSV, or database
import json
with open("inventory.json", "w") as f:
    json.dump(inventory, f, indent=2)
```

---

## Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| DNS resolution (1 hostname) | 100-500ms | Concurrent, 10 workers |
| WHOIS lookup (1 IP) | 2-10s | Can timeout after 10s |
| Reverse DNS (1 IP) | 500ms-2s | Can timeout after 5s |
| CIDR expansion (/24) | 100ms | 256 IPs enumerated |
| **Total (1 hostname → assets)** | **3-15s** | Depends on WHOIS latency |

**Optimization Tips:**
- Use `max_workers` parameter to increase concurrency
- Reduce `timeout` if you expect fast network
- Cache WHOIS results if doing bulk scans

---

## Testing

Run asset discovery tests:

```bash
pytest tests/test_asset_discovery.py -v
```

**Test Coverage:**
- ✓ Asset class creation (IPv4/IPv6)
- ✓ DNS resolution (success/failure)
- ✓ WHOIS timeout fallback
- ✓ Reverse DNS
- ✓ CIDR expansion
- ✓ Confidence scoring
- ✓ Scan filtering

---

## Configuration

No additional config needed! Asset discovery uses:
- Standard library: `socket`, `ipaddress`, `threading`
- Third-party: `ipwhois` (lightweight, no auth required)

To disable WHOIS lookups temporarily:
```python
# Uninstall ipwhois or patch _HAVE_IPWHOIS
# discovery will still work with DNS + reverse DNS only
```

---

## Logging Output

Asset discovery logs operations for debugging:

```
[AssetDiscovery] Starting with 1 targets                  # SYSTEM
[AssetDiscovery] Step 1/4: DNS Resolution...             # INFO
  ✓ example.com → 192.168.1.1, 192.168.1.2              # SUCCESS
[AssetDiscovery] Step 2/4: WHOIS lookup for 2 IPs...     # INFO
  ✓ 192.168.1.1 → ASN=AS1234, CIDR=192.168.0.0/16       # SUCCESS
  ⚠ 192.168.1.2 → WHOIS failed, continuing with lower conf # WARN
[AssetDiscovery] Step 3/4: Reverse DNS for 2 IPs...     # INFO
  ✓ 192.168.1.1 → www.example.com                       # SUCCESS
[AssetDiscovery] Step 4/4: Asset Inventory from CIDR...  # INFO
[AssetDiscovery] Complete: 256 assets discovered         # SUCCESS
```

---

## Future Enhancements

- [ ] SNMP MIB enumeration (software inventory)
- [ ] SSL certificate parsing (SubjectAlternativeName)
- [ ] IP geolocation mapping
- [ ] Passive DNS (VirusTotal, SecurityTrails)
- [ ] Shodan/Censys integration (optional)
- [ ] Cached WHOIS results (SQLite)

---

## Summary

The **Asset Discovery** module:
1. ✅ Discovers IP addresses from hostnames (DNS)
2. ✅ Collects metadata (WHOIS, ASN, CIDR)
3. ✅ Performs reverse DNS lookups
4. ✅ Creates asset inventory with confidence scores
5. ✅ Filters targets for scanning (high-confidence only)
6. ✅ **Gracefully handles timeouts** (no pipeline crashes)

This significantly improves the quality and context of CVE scanning by:
- Ensuring we're scanning the right IPs
- Providing infrastructure context (ASN, CIDR)
- Reducing false positives (confidence filtering)
- Creating a complete asset inventory
