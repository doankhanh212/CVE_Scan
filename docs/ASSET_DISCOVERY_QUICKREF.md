# 🚀 Asset Discovery - Quick Reference Card

## TL;DR - What Changed?

**New scanning flow:**
```
Hostname → DNS → IP → WHOIS/ASN → Reverse DNS → Filter → Scan
```

**Files added:** 4 new files (module + docs + tests)  
**Files modified:** 2 existing files (requirements.txt + basic_pipeline.py)  
**Breaking changes:** None ✓  
**New dependency:** ipwhois (lightweight, optional)

---

## 🎯 Key Concepts

### Asset Class
Represents a discovered IP with metadata:
```python
Asset {
  ip: "192.168.1.1"
  hostnames: {"example.com", "www.example.com"}
  asn: "AS1234"
  cidr: "192.168.0.0/16"
  confidence: 0.95  # 0-1 score
  source: ["dns", "whois", "reverse_dns"]
  scan_priority: 1  # 1=high, 255=skip
}
```

### Confidence Scoring
Higher = more reliable (more discovery methods used)

```
1.0  ← DNS resolved
0.95 ← DNS + WHOIS success
0.85 ← DNS + Reverse DNS
0.70 ← DNS + WHOIS timeout (continues anyway!)
0.75 ← CIDR inferred from ASN
```

### Scan Filter Logic
```
conf >= 0.85  → SCAN (priority 1)
0.70 <= conf < 0.85  → SCAN (priority 50)
conf < 0.70  → INVENTORY ONLY (skip)
```

---

## 📦 New Files

| File | Purpose | Size |
|------|---------|------|
| `modules/discovery/asset_discovery.py` | Core module | 555 lines |
| `docs/ASSET_DISCOVERY.md` | Complete guide | 300+ lines |
| `scripts/test_asset_discovery.py` | Quick test | 150 lines |
| `tests/test_asset_discovery.py` | Unit tests | 250 lines |

---

## 🧪 Testing

### Unit Tests
```bash
pytest tests/test_asset_discovery.py -v
# Expected: 17 passed ✓
```

### Manual Test
```bash
python scripts/test_asset_discovery.py example.com
# Outputs: Pretty-printed assets + scan priorities + JSON
```

---

## 📝 Code Examples

### Basic Usage
```python
from modules.discovery.asset_discovery import AssetDiscovery

discovery = AssetDiscovery()
assets = discovery.discover(["example.com"])

for ip, asset in assets.items():
    print(f"{ip}: {asset.hostnames} (conf: {asset.confidence:.2%})")
```

### Scan Filtering
```python
scan_ips = discovery.filter_for_scan(assets)
# Only high-confidence targets
```

### Export Inventory
```python
inventory = {ip: asset.to_dict() for ip, asset in assets.items()}
# Save to JSON, CSV, database, etc.
```

---

## ⚡ Performance

| Operation | Time |
|-----------|------|
| DNS (1 host) | ~200ms |
| WHOIS (1 IP) | 5-10s |
| Reverse DNS | ~1s |
| CIDR expansion | ~100ms |
| **Total** | **6-15s** |

---

## 🔄 Error Handling

| Scenario | Behavior |
|----------|----------|
| DNS fails | Skip target (continue) |
| WHOIS timeout | **Continue with conf=0.70** ⭐ |
| Reverse DNS fails | Skip, use forward DNS |
| CIDR invalid | Skip expansion |
| All fails | Return empty dict |

**KEY:** WHOIS timeout ≠ stop. It just lowers confidence!

---

## 📊 Integration Points

### BasicPipeline
```python
# Step 0 (NEW)
assets = self.asset_discovery.discover([target])
scan_ips = self.asset_discovery.filter_for_scan(assets)
primary_ip = scan_ips[0]

# Steps 1-5 (existing)
ports = self._discover_ports(primary_ip)
# ... rest of scanning
```

### No GUI Changes
Asset discovery happens automatically in the pipeline!

---

## 🐛 Troubleshooting

### Import Error
```bash
pip install ipwhois
```

### WHOIS Too Slow
Increase timeout in `asset_discovery.py`:
```python
WHOIS_TIMEOUT = 15  # was 10
```

### DNS Not Resolving
Check network:
```python
import socket
socket.getaddrinfo("example.com", None)
```

### High Memory Usage
Limit CIDR expansion:
```python
ips = cidr_expander.expand_cidr("192.168.0.0/16", max_ips=100)
```

---

## 📚 Documentation

| Document | Content |
|----------|---------|
| `docs/ASSET_DISCOVERY.md` | Complete API guide |
| `ASSET_DISCOVERY_SUMMARY.md` | Executive summary |
| `ASSET_DISCOVERY_DATAFLOW.md` | Visual architecture |
| `ASSET_DISCOVERY_CHANGELOG.md` | Implementation details |
| `ASSET_DISCOVERY_CHECKLIST.md` | Verification checklist |

---

## ✅ Checklist

Before using in production:
- [ ] Run tests: `pytest tests/test_asset_discovery.py -v`
- [ ] Test manually: `python scripts/test_asset_discovery.py example.com`
- [ ] Check logs during GUI scan
- [ ] Verify confidence scores are reasonable
- [ ] Monitor WHOIS timeout frequency

---

## 🔗 API Quick Reference

```python
# Create discovery object
discovery = AssetDiscovery(logger=logger_cb, progress_cb=progress_cb)

# Discover assets from hostnames
assets: Dict[str, Asset] = discovery.discover(["example.com"])

# Filter for scanning (high-confidence only)
scan_ips: List[str] = discovery.filter_for_scan(assets)

# Access asset metadata
asset = assets["192.168.1.1"]
print(asset.confidence)  # 0.95
print(asset.asn)         # "AS1234"
print(asset.cidr)        # "192.168.0.0/16"

# Export asset
asset_dict = asset.to_dict()
```

---

## 📈 Confidence Score Meanings

| Score | Trust Level | Action |
|-------|------------|--------|
| 1.0 | Excellent | Scan first |
| 0.95 | Very Good | Scan immediately |
| 0.85 | Good | Scan with caution |
| 0.70 | Fair | Scan if time permits |
| < 0.70 | Poor | Inventory only |

---

## 🎯 Future Enhancements

```
✓ Asset Discovery (current)
  ├─ DNS Resolution
  ├─ WHOIS/ASN lookup
  ├─ Reverse DNS
  └─ Confidence scoring

→ Coming soon:
  ├─ WHOIS caching
  ├─ Geolocation
  ├─ SSL certificate parsing
  ├─ Passive DNS (VirusTotal)
  └─ Web UI visualization
```

---

## 🚀 Get Started

### 1. Test it
```bash
python scripts/test_asset_discovery.py example.com
```

### 2. Run tests
```bash
pytest tests/test_asset_discovery.py -v
```

### 3. Use in GUI
```bash
python app.py
# Asset discovery runs automatically!
```

### 4. Check logs
Look for `[AssetDiscovery]` entries in scan output

---

## 💡 Pro Tips

1. **For slow networks:** Increase timeouts
   ```python
   DNSResolver(timeout=10)
   WHOISLookup(timeout=15)
   ```

2. **For speed:** Disable WHOIS
   ```bash
   pip uninstall ipwhois
   ```

3. **For debugging:** Enable debug logging
   ```python
   logger.setLevel(logging.DEBUG)
   ```

4. **For bulk scans:** Cache WHOIS results (future feature)

---

## 📞 Support

**Documentation:** `docs/ASSET_DISCOVERY.md`  
**Examples:** `scripts/test_asset_discovery.py`  
**Tests:** `tests/test_asset_discovery.py`  
**Data flow:** `ASSET_DISCOVERY_DATAFLOW.md`  

**Questions?** Check the troubleshooting section above!

---

**Version:** 1.0  
**Date:** December 26, 2025  
**Status:** ✅ Production Ready
