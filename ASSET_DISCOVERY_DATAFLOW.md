# Asset Discovery - Complete Data Flow Diagram

## Flow Overview

```
INPUT
│
├─ "example.com" (Hostname)
├─ "192.168.1.1" (IP)
└─ "scanme.nmap.org" (FQDN)
│
└──────────┬──────────────────────────────────────────────────────────────────┐
           │                                                                  │
           ▼                                                                  │
    ╔══════════════════════════════════════════════════════════════════════╗ │
    ║ AssetDiscovery.discover([targets])                                   ║ │
    ║ ─────────────────────────────────────────────────────────────────── ║ │
    ║ Orchestrates all discovery steps                                    ║ │
    ╚══════════════════════════════════════════════════════════════════════╝ │
           │                                                                  │
           ▼                                                                  │
    ╔══════════════════════════════════════════════════════════════════════╗ │
    ║ STEP 1: DNS RESOLUTION (DNSResolver)                                ║ │
    ║ ─────────────────────────────────────────────────────────────────── ║ │
    ║ Input:  "example.com"                                              ║ │
    ║ Method: socket.getaddrinfo() [concurrent, 10 workers]             ║ │
    ║ Output: ["192.168.1.1", "192.168.1.2"]                            ║ │
    ║ Confidence: 1.0 (DNS resolved)                                     ║ │
    ║                                                                     ║ │
    ║ Failure: No resolution → empty list → skip target                  ║ │
    ╚══════════════════════════════════════════════════════════════════════╝ │
           │                                                                  │
           ▼                                                                  │
    ╔══════════════════════════════════════════════════════════════════════╗ │
    ║ STEP 2: WHOIS LOOKUP (WHOISLookup)                                 ║ │
    ║ ─────────────────────────────────────────────────────────────────── ║ │
    ║ Input:  ["192.168.1.1", "192.168.1.2"]                            ║ │
    ║ Method: ipwhois library [concurrent, 5 workers, timeout=10s]      ║ │
    ║                                                                     ║ │
    ║ For 192.168.1.1:                                                   ║ │
    ║   Output: {asn: "AS1234", cidr: "192.168.0.0/16", org: "...",    ║ │
    ║            success: True}                                          ║ │
    ║   Confidence: 0.95 (WHOIS success)                                 ║ │
    ║                                                                     ║ │
    ║ For 192.168.1.2:                                                   ║ │
    ║   WHOIS timeout after 10s!                                         ║ │
    ║   Output: {asn: None, cidr: None, org: None, success: False}     ║ │
    ║   Confidence: 0.70 (WHOIS timeout, but CONTINUE!)                 ║ │
    ║   ⚠️  KEY: Doesn't crash pipeline, reduces confidence instead      ║ │
    ║                                                                     ║ │
    ║ Failure: Timeout → success=False, continue anyway                  ║ │
    ╚══════════════════════════════════════════════════════════════════════╝ │
           │                                                                  │
           ▼                                                                  │
    ╔══════════════════════════════════════════════════════════════════════╗ │
    ║ STEP 3: REVERSE DNS (ReverseDNS)                                   ║ │
    ║ ─────────────────────────────────────────────────────────────────── ║ │
    ║ Input:  ["192.168.1.1", "192.168.1.2"]                            ║ │
    ║ Method: socket.gethostbyaddr() [concurrent]                       ║ │
    ║                                                                     ║ │
    ║ For 192.168.1.1:                                                   ║ │
    ║   Output: "www.example.com"                                        ║ │
    ║   Confidence boost: 0.95 → 0.95 (reverse DNS confirms forward)    ║ │
    ║                                                                     ║ │
    ║ For 192.168.1.2:                                                   ║ │
    ║   Output: None (no reverse DNS)                                    ║ │
    ║   Confidence stays: 0.70 (unchanged)                               ║ │
    ║                                                                     ║ │
    ║ Failure: Timeout → skip, use forward DNS results                   ║ │
    ╚══════════════════════════════════════════════════════════════════════╝ │
           │                                                                  │
           ▼                                                                  │
    ╔══════════════════════════════════════════════════════════════════════╗ │
    ║ STEP 4: CIDR EXPANSION (CIDRExpander)                              ║ │
    ║ ─────────────────────────────────────────────────────────────────── ║ │
    ║ Input: Assets with CIDR blocks from WHOIS                          ║ │
    ║        {192.168.0.0/16, 10.0.0.0/8}                               ║ │
    ║ Method: ipaddress.ip_network().hosts()                             ║ │
    ║ Limit: max_ips=256 per CIDR (prevent memory bomb)                 ║ │
    ║                                                                     ║ │
    ║ Output: Expanded IPs for asset inventory                           ║ │
    ║         - 192.168.1.1 through 192.168.1.254                        ║ │
    ║         - 10.0.0.1 through 10.0.0.254                              ║ │
    ║ Confidence: 0.75 (CIDR inferred, not directly discovered)          ║ │
    ║                                                                     ║ │
    ║ Failure: Invalid CIDR → skip, use original IP only                 ║ │
    ╚══════════════════════════════════════════════════════════════════════╝ │
           │                                                                  │
           ▼                                                                  │
    ╔══════════════════════════════════════════════════════════════════════╗ │
    ║ RESULT: Asset Dict                                                  ║ │
    ║ ─────────────────────────────────────────────────────────────────── ║ │
    ║                                                                     ║ │
    ║ {                                                                   ║ │
    ║   "192.168.1.1": Asset {                                            ║ │
    ║     ip: "192.168.1.1"                                              ║ │
    ║     hostnames: {"example.com", "www.example.com"}                 ║ │
    ║     asn: "AS1234"                                                  ║ │
    ║     cidr: "192.168.0.0/16"                                         ║ │
    ║     org: "Example Corp"                                            ║ │
    ║     confidence: 0.95      ← HIGH CONFIDENCE                        ║ │
    ║     source: ["dns", "whois", "reverse_dns"]                        ║ │
    ║     scan_priority: 1      ← SCAN IMMEDIATELY                       ║ │
    ║   },                                                                ║ │
    ║   "192.168.1.2": Asset {                                            ║ │
    ║     ip: "192.168.1.2"                                              ║ │
    ║     hostnames: {"example.com"}                                     ║ │
    ║     asn: None             ← WHOIS FAILED                           ║ │
    ║     cidr: None                                                      ║ │
    ║     org: None                                                       ║ │
    ║     confidence: 0.70      ← MEDIUM CONFIDENCE                      ║ │
    ║     source: ["dns", "whois_timeout"]                               ║ │
    ║     scan_priority: 50     ← SCAN WITH CAUTION                      ║ │
    ║   },                                                                ║ │
    ║   "192.168.1.3": Asset {                                            ║ │
    ║     ip: "192.168.1.3"     ← CIDR INFERRED                          ║ │
    ║     hostnames: {}                                                   ║ │
    ║     asn: "AS1234"                                                  ║ │
    ║     cidr: "192.168.0.0/16"                                         ║ │
    ║     org: "Example Corp"                                            ║ │
    ║     confidence: 0.75      ← MEDIUM-HIGH                            ║ │
    ║     source: ["cidr_inferred"]                                      ║ │
    ║     scan_priority: 50     ← OPTIONAL SCAN                          ║ │
    ║   },                                                                ║ │
    ║   ...                                                               ║ │
    ║   256 total IPs from /24 CIDR                                       ║ │
    ║ }                                                                   ║ │
    ║                                                                     ║ │
    ║ Total assets: 257 (primary + CIDR expanded)                        ║ │
    ╚══════════════════════════════════════════════════════════════════════╝ │
           │                                                                  │
           ▼                                                                  │
    ╔══════════════════════════════════════════════════════════════════════╗ │
    ║ FILTER FOR SCAN (filter_for_scan)                                  ║ │
    ║ ─────────────────────────────────────────────────────────────────── ║ │
    ║                                                                     ║ │
    ║ Confidence >= 0.85:  192.168.1.1     → Priority 1    (HIGH)       ║ │
    ║                                                                     ║ │
    ║ 0.70 <= Confidence < 0.85:                                         ║ │
    ║                      192.168.1.2     → Priority 50   (MEDIUM)     ║ │
    ║                      192.168.1.3     → Priority 50   (MEDIUM)     ║ │
    ║                      ... (other /24)                               ║ │
    ║                                                                     ║ │
    ║ Confidence < 0.70:   (NONE in this example)         (SKIP)        ║ │
    ║                                                                     ║ │
    ║ Result: [                                                           ║ │
    ║   "192.168.1.1",      ← Scan first                                 ║ │
    ║   "192.168.1.2",      ← Then these (if time permits)              ║ │
    ║   "192.168.1.3",                                                   ║ │
    ║   ...                                                               ║ │
    ║ ] (sorted by priority)                                             ║ │
    ╚══════════════════════════════════════════════════════════════════════╝ │
           │                                                                  │
           └────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          PRIMARY_IP = scan_ips[0]
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │  BASIC PIPELINE CONTINUES       │
                    │ ─────────────────────────────── │
                    │                                 │
                    │ 1. RustScan (primary_ip)        │
                    │ 2. Nmap -sV (primary_ip)        │
                    │ 3. Build CPE                    │
                    │ 4. Match CVE                    │
                    │ 5. Generate Report              │
                    │                                 │
                    └─────────────────────────────────┘
                                    │
                                    ▼
                          VULNERABILITY REPORT
                          (with ASN/CIDR context)
```

---

## Error Handling Paths

```
┌─ DNS FAILS
│  └─→ Returns []
│  └─→ No assets → skip scan
│  └─→ Log warning
│  └─→ Continue (no crash)

┌─ WHOIS TIMEOUT (KEY PATH)
│  └─→ Returns success=False
│  └─→ Confidence reduced to 0.70
│  └─→ Asset still marked for scan
│  └─→ Continue pipeline (NO CRASH!)
│  └─→ Log warning

┌─ REVERSE DNS TIMEOUT
│  └─→ Returns None
│  └─→ Skip reverse DNS
│  └─→ Use forward DNS results
│  └─→ Continue (no crash)

┌─ CIDR EXPANSION INVALID
│  └─→ Returns []
│  └─→ Skip CIDR expansion
│  └─→ Use primary IP only
│  └─→ Continue (no crash)
```

---

## Data Structure - Asset Class

```python
class Asset:
    ip: str                      # "192.168.1.1"
    addr_obj: IPv4Address        # Parsed IP object
    is_ipv4: bool                # True
    is_ipv6: bool                # False
    
    hostnames: Set[str]          # {"example.com", "www.example.com"}
    asn: Optional[str]           # "AS1234"
    cidr: Optional[str]          # "192.168.0.0/16"
    country: Optional[str]       # "US"
    org: Optional[str]           # "Example Corporation"
    
    confidence: float            # 0.95 (0-1 scale)
    source: List[str]            # ["dns", "whois", "reverse_dns"]
    scan_priority: int           # 1 (higher priority) to 255 (skip)
    
    methods:
      to_dict()                  # Export as dictionary
      add_hostname()             # Add hostname to set
      add_source()               # Track discovery method
      update_confidence()        # Update confidence (use max)
```

---

## Confidence Score Breakdown

```
Asset 192.168.1.1:

DNS Resolution:     ✓ PASS    → Confidence: 1.0
WHOIS Lookup:       ✓ PASS    → Confidence: 0.95 (success override 1.0 max is 1.0)
Reverse DNS:        ✓ PASS    → Confidence: 0.85 (no change, already 0.95)
─────────────────────────────
Final Confidence:            → 0.95 (max of all steps)
Scan Priority:               → 1 (HIGH - >= 0.85)


Asset 192.168.1.2:

DNS Resolution:     ✓ PASS    → Confidence: 1.0
WHOIS Lookup:       ✗ TIMEOUT → Confidence: 0.70 (reduced but continue!)
Reverse DNS:        ✗ None    → Confidence: (no change, stays 0.70)
─────────────────────────────
Final Confidence:            → 0.70 (max = 0.70)
Scan Priority:               → 50 (MEDIUM - 0.70-0.85)


Asset 192.168.1.3 (CIDR Inferred):

DNS Resolution:     ✗ N/A     → Confidence: 0 (not directly discovered)
WHOIS Lookup:       ✓ PARENT  → Confidence: 0.75 (inferred from CIDR)
Reverse DNS:        ✗ None    → Confidence: (no change)
─────────────────────────────
Final Confidence:            → 0.75 (CIDR inferred)
Scan Priority:               → 50 (MEDIUM - 0.70-0.85)
```

---

## Timeline - Single Hostname Discovery

```
Time    Event
───────────────────────────────────────────────────────────────────
 0ms    Start discovery for "example.com"
        │
 100ms  └─ DNS resolution complete (concurrent):
        │    example.com → 192.168.1.1, 192.168.1.2
        │
 5000ms └─ WHOIS lookup complete (concurrent):
        │    192.168.1.1 → ASN=AS1234, CIDR=192.168.0.0/16 ✓
        │    192.168.1.2 → TIMEOUT ⚠️  (continues anyway!)
        │
 6000ms └─ Reverse DNS complete (concurrent):
        │    192.168.1.1 → www.example.com ✓
        │    192.168.1.2 → (no PTR record)
        │
 6100ms └─ CIDR expansion:
        │    256 IPs enumerated from 192.168.0.0/16
        │
 6200ms └─ Asset inventory created: 258 total IPs
        │
 6210ms └─ Scan filtering:
        │    High-confidence: 1 IP (priority 1)
        │    Medium-confidence: 257 IPs (priority 50)
        │    Low-confidence: 0 IPs (skip)
        │
 6220ms Discovery complete! Pass assets to scanner
```

---

## Integration Point

```
BasicPipeline.execute(target="example.com")
│
├─ 0️⃣  [NEW] Asset Discovery
│   ├─ assets = discover([target])
│   ├─ scan_ips = filter_for_scan(assets)
│   └─ primary_ip = scan_ips[0]
│
├─ 1️⃣  RustScan(primary_ip)
├─ 2️⃣  Nmap(primary_ip)
├─ 3️⃣  CPE Building
├─ 4️⃣  CVE Matching
└─ 5️⃣  Report Generation

Result: Asset metadata available in scan context!
```

---

This diagram shows exactly how asset discovery integrates and the **critical WHOIS timeout path** that allows graceful degradation instead of pipeline crashes.
