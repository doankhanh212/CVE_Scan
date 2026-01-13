# 🔍 Cách Thức Quét Domain/Hostname trong CVE_Scan

## 📌 Tổng Quan

Hệ thống hỗ trợ **2 chế độ quét khác nhau**:

### 1️⃣ Chế độ IP/CIDR (Direct Scan)
- Input: IP addresses hoặc CIDR ranges
- Flow: IP → Ping → Scan
- **BỎ QUA** Asset Discovery

### 2️⃣ Chế độ Domain/Hostname (Full Asset Discovery)
- Input: Domain names hoặc hostnames
- Flow: Domain → DNS → WHOIS → ASN → CIDR → Ping → Scan
- **SỬ DỤNG** Asset Discovery đầy đủ

---

## 🔄 Flow Chi Tiết - Quét Domain/Hostname

### Bước 0: Asset Discovery (DNS + WHOIS + ASN)

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: example.com, mail.example.com, api.example.com     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: DNS Resolution (Concurrent)                        │
│  ------------------------------------------------            │
│  • Resolve A records (IPv4)                                 │
│  • Resolve AAAA records (IPv6)                              │
│  • socket.getaddrinfo() với timeout                         │
│  • Concurrent với ThreadPoolExecutor                        │
│                                                              │
│  example.com → [103.98.152.1, 103.98.152.2]                │
│  mail.example.com → [103.98.152.15]                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: WHOIS Lookup (ASN + CIDR + Organization)          │
│  ------------------------------------------------            │
│  • IPWhois library (hoặc RIPEstat API fallback)            │
│  • Lấy ASN (Autonomous System Number)                       │
│  • Lấy CIDR block (network range)                           │
│  • Lấy Organization info                                    │
│  • Timeout: 10 giây                                         │
│                                                              │
│  103.98.152.1 → ASN: AS1234, CIDR: 103.98.152.0/24         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Reverse DNS (Optional)                             │
│  ------------------------------------------------            │
│  • socket.gethostbyaddr(ip)                                 │
│  • Lấy hostname canonical từ IP                             │
│  • Thêm vào danh sách hostnames của asset                   │
│                                                              │
│  103.98.152.1 → ["example.com", "www.example.com"]         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Asset Enrichment                                   │
│  ------------------------------------------------            │
│  • Tạo Asset object cho mỗi IP                              │
│  • Gắn metadata: ASN, CIDR, Org, Country, Hostnames        │
│  • Tính confidence score (0.0 - 1.0)                        │
│  • Ưu tiên scan (scan_priority)                             │
│                                                              │
│  Asset {                                                     │
│    ip: "103.98.152.1",                                      │
│    hostnames: ["example.com", "www.example.com"],          │
│    asn: "AS1234",                                           │
│    cidr: "103.98.152.0/24",                                 │
│    confidence: 0.95,                                        │
│    scan_priority: 1                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: CIDR Expansion (Optional)                          │
│  ------------------------------------------------            │
│  • Config: scan_cidr_expansion = True/False                 │
│  • Nếu bật: Expand CIDR block thành list IPs               │
│  • Ví dụ: 103.98.152.0/24 → [103.98.152.1..254]           │
│  • Cap: max_cidr_ips (default 1024)                        │
│  • Policy:                                                  │
│    - "fixed": Scan top N IPs                                │
│    - "cidr_full": Scan tất cả trong CIDR                   │
│    - "adaptive": Tự động dựa trên prefix length            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: Filter for Scan                                    │
│  ------------------------------------------------            │
│  • Lọc IPs để quét dựa trên:                                │
│    - Confidence score (ưu tiên cao trước)                   │
│    - Scan priority                                          │
│    - max_scan_ips limit                                     │
│                                                              │
│  Output: [103.98.152.1, 103.98.152.15, ...]               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: ICMP Ping Discovery                                │
│  ------------------------------------------------            │
│  • Nmap -sn (ping scan)                                     │
│  • Parallel với ThreadPoolExecutor                          │
│  • Filter chỉ lấy IPs còn sống                              │
│                                                              │
│  [103.98.152.1, 103.98.152.15] → alive_ips                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 8: Port & Service Scan                                │
│  ------------------------------------------------            │
│  1. RustScan: Phát hiện open ports (fast)                   │
│  2. Nmap -sV: Service version detection                     │
│  3. Build CPE: Tạo CPE từ service info                      │
│  4. CVE Matching: Map CPE → CVEs                            │
│                                                              │
│  Kết quả:                                                    │
│  • Host label: "example.com (103.98.152.1)"                │
│  • Ports: [22, 80, 443]                                     │
│  • Services: ssh, http, https                               │
│  • CVEs: [CVE-2024-xxxx, ...]                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Điểm Khác Biệt Giữa 2 Chế độ

| Feature | IP/CIDR Mode | Domain/Hostname Mode |
|---------|-------------|---------------------|
| DNS Resolution | ❌ Skip | ✅ Concurrent DNS |
| WHOIS Lookup | ❌ Skip | ✅ ASN + CIDR |
| Reverse DNS | ❌ Skip | ✅ Optional |
| CIDR Expansion | ✅ Manual | ✅ Auto (from WHOIS) |
| Asset Enrichment | ❌ None | ✅ Full metadata |
| Host Label | IP only | Domain + IP |
| Ping Discovery | ✅ Nmap -sn | ✅ Nmap -sn |
| Port Scan | ✅ RustScan+Nmap | ✅ RustScan+Nmap |

---

## 🔧 Cấu Hình Liên Quan

### config.json
```json
{
  "scan_cidr_expansion": false,      // Bật CIDR expansion
  "max_cidr_ips": 1024,               // Giới hạn IPs từ CIDR
  "max_scan_ips": 64,                 // Giới hạn tổng IPs scan
  "scan_policy": "fixed",             // "fixed" | "cidr_full" | "adaptive"
  "adaptive_full_scan_prefixlen": 24, // Prefix length cho adaptive
  "reverse_dns_pre_scan": false,      // Bật Reverse DNS
  "ping_timeout": 1,                  // Timeout ping (giây)
  "ping_retries": 3,                  // Số lần retry ping
  "ping_workers": 100                 // Workers concurrent ping
}
```

---

## 💡 Ví Dụ Thực Tế

### Ví dụ 1: Quét 1 domain
**Input:**
```
example.com
```

**Flow:**
1. DNS: `example.com` → `103.98.152.1`
2. WHOIS: `103.98.152.1` → ASN: AS1234, CIDR: `103.98.152.0/24`
3. Reverse DNS: `103.98.152.1` → `www.example.com`
4. Asset: `103.98.152.1` với hostnames [`example.com`, `www.example.com`]
5. Ping: Check if alive
6. Scan: Ports + Services + CVEs
7. **Output label:** `example.com (103.98.152.1)`

### Ví dụ 2: Quét nhiều subdomains
**Input:**
```
example.com
mail.example.com
api.example.com
```

**Flow:**
1. Concurrent DNS cho 3 domains
2. Có thể cùng IP hoặc khác IP
3. WHOIS cho mỗi unique IP
4. Merge hostnames nếu cùng IP
5. Scan tất cả unique IPs
6. **Output:**
   - `example.com (103.98.152.1)`
   - `mail.example.com (103.98.152.15)`
   - `api.example.com (103.98.152.20)`

### Ví dụ 3: CIDR Expansion
**Input:**
```
example.com
```
**WHOIS result:** CIDR = `103.98.152.0/24`

**Với `scan_cidr_expansion = true`:**
- Expand: `103.98.152.0/24` → 254 IPs
- Ping all 254 IPs
- Scan alive IPs (ví dụ: 42 alive)
- **Output:** 42 hosts trong report

**Với `scan_cidr_expansion = false`:**
- Chỉ scan `103.98.152.1` (IP resolved từ DNS)
- **Output:** 1 host trong report

---

## 📊 Confidence Scores

Asset Discovery tính confidence score để ưu tiên scan:

| Source | Confidence Score | Ý nghĩa |
|--------|-----------------|---------|
| dns_resolved | 1.0 | IP từ DNS resolution |
| whois_success | 0.95 | WHOIS lookup thành công |
| reverse_dns | 0.85 | Có reverse DNS |
| cidr_inferred | 0.75 | IP từ CIDR expansion |
| whois_timeout | 0.70 | WHOIS timeout nhưng có IP |

**Scan priority:** Confidence càng cao, scan càng sớm.

---

## ⚠️ Lưu Ý Quan Trọng

### 1. Timeout và Performance
- **DNS timeout:** 5 giây/hostname
- **WHOIS timeout:** 10 giây/IP
- **Concurrent:** Max 10 DNS workers
- **Recommendation:** Dùng local DB để tránh timeout NVD API

### 2. CIDR Expansion Risk
- CIDR /16 = **65,534 IPs** → Rất lâu!
- CIDR /24 = **254 IPs** → Chấp nhận được
- CIDR /28 = **14 IPs** → Nhanh
- **Giải pháp:** Dùng `max_scan_ips` để cap

### 3. Scan Policy
- **fixed:** An toàn, scan top N IPs (default)
- **cidr_full:** Nguy hiểm, scan hết CIDR
- **adaptive:** Thông minh, tự động quyết định dựa trên CIDR size

### 4. Asset Metadata trong Report
Khi quét domain, CSV report sẽ có:
- **Host column:** `example.com (103.98.152.1)`
- **Metadata:** ASN, CIDR info (nếu có)
- **Hostname resolution:** Được preserve trong kết quả

---

## 🚀 Ưu Điểm của Domain Scan

1. ✅ **Hiểu rõ infrastructure:** ASN, CIDR, Organization
2. ✅ **Phát hiện related assets:** Scan cả CIDR block
3. ✅ **Hostname tracking:** Giữ domain name trong report
4. ✅ **Intelligent prioritization:** Scan IPs quan trọng trước
5. ✅ **Metadata enrichment:** ASN, Country, Org info

---

## 📝 Kết Luận

**Khi nào dùng Domain Mode?**
- Cần hiểu rõ về infrastructure target
- Muốn phát hiện assets liên quan
- Có nhiều subdomains
- Cần metadata đầy đủ trong report

**Khi nào dùng IP/CIDR Mode?**
- Đã có danh sách IPs cụ thể
- Cần scan nhanh, không cần metadata
- Không quan tâm đến WHOIS/ASN
- Tránh DNS lookup overhead

**Recommendation:**
- Scan production: Dùng **Domain Mode** để có thông tin đầy đủ
- Scan test/internal: Dùng **IP/CIDR Mode** để nhanh hơn
