# API Key Usage Verification Guide

## ✅ Luồng hoạt động của API Key

### 1. **Lưu Settings**
```
User nhập API key → Click "Save Settings" 
→ POST /api/settings 
→ ConfigManager.save(config) 
→ Ghi vào config.json
```

### 2. **Khởi tạo Scan**
```
User start scan 
→ POST /api/scan 
→ scan_service.create_and_start_scan()
→ Reload config: ConfigManager.load() ✅
→ Pass config to ScanManager
```

### 3. **Trong Pipeline**
```python
# basic_pipeline.py line 87
self.matcher = CVEMatcher(
    api_key=config.get("nvd_api_key"),  # ✅ Lấy từ config đã reload
    local_db_path=(config.get("local_db_path") if config.get("use_local_db") else None),
    year_window=self.cve_year_window
)
```

### 4. **CVE Matching**
```python
# cve_matcher.py
def __init__(self, api_key: Optional[str] = None, ...):
    # Prefer local DB if provided
    if local_db_path:
        self.fetcher = LocalDBFetcher(db_path=local_db_path)
    else:
        # Use NVD API with key
        self.fetcher = NVDFetcherPRO(api_key=api_key)  # ✅ Key được truyền vào
```

### 5. **NVD API Call**
```python
# nvd_fetcher.py
def _api_call(self, params: dict) -> dict:
    headers = {"User-Agent": "CVE-Scanner/1.0"}
    
    if self.api_key:  # ✅ Key được dùng trong request
        headers["apiKey"] = self.api_key.strip()
    
    response = requests.get(NVD_API_URL, headers=headers, params=params, timeout=30)
```

---

## 🔍 Cách kiểm tra API Key có hoạt động

### Method 1: Check Logs (Recommended)
1. Save API key trong Settings
2. Start một scan mới
3. Xem Live Logs, tìm dòng:
   ```
   🎯 Scan initialized - API key: ✓, Local DB: false, Log level: info
   ✅ Using NVDFetcherPRO with API key: Yes
   ```

### Method 2: Test API Button
1. Nhập API key
2. Click **"Test API Connection"**
3. Thấy: `✓ Valid` → Key hoạt động

### Method 3: Check Config File
```bash
cat config.json | grep nvd_api_key
```
Nếu thấy key → đã được lưu.

### Method 4: Monitor Network
- Dùng DevTools Network tab
- Filter requests đến `services.nvd.nist.gov`
- Check request headers có `apiKey` không

---

## ⚠️ Common Issues

### Issue 1: Key không hoạt động sau save
**Nguyên nhân**: Scan đang chạy dùng config cũ  
**Fix**: 
- Scans mới sẽ dùng key mới
- Hoặc restart server để force reload

### Issue 2: Vẫn hit rate limit dù có key
**Nguyên nhân**: 
- Key không valid
- Key đã hết quota
- Syntax sai (có space thừa)

**Fix**:
```bash
# Test key manually
curl -H "apiKey: YOUR_KEY" \
  "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=1"
```

### Issue 3: Local DB được ưu tiên
**Nguyên nhân**: Setting `use_local_db = true`  
**Result**: NVD API key **KHÔNG được dùng** (by design)

**To use API key**:
- Set `use_local_db = false`
- Hoặc xóa `local_db_path`

---

## 📊 Rate Limits

| Key Type | Requests/30s | Daily Limit |
|----------|--------------|-------------|
| **No Key** | 5 | ~7,200 |
| **With Key** | 50 | ~720,000 |

**Recommendation**: Always use API key cho production.

---

## 🧪 Test Script

```python
# test_api_key.py
import requests
import json

# Load config
with open('config.json') as f:
    config = json.load(f)

api_key = config.get('nvd_api_key')
print(f"API Key: {api_key[:10]}..." if api_key else "No API key")

# Test call
headers = {"apiKey": api_key} if api_key else {}
resp = requests.get(
    "https://services.nvd.nist.gov/rest/json/cves/2.0",
    headers=headers,
    params={"resultsPerPage": 1}
)

print(f"Status: {resp.status_code}")
print(f"Rate limit remaining: {resp.headers.get('X-RateLimit-Remaining', 'N/A')}")

if resp.status_code == 200:
    print("✅ API key working!")
elif resp.status_code == 403:
    print("❌ Invalid API key")
elif resp.status_code == 429:
    print("⚠️ Rate limit exceeded")
```

---

## ✅ Confirmed Working

**Files Modified**:
1. `scan_service.py` - Log API key status on scan start
2. `settings.js` - Better test feedback
3. `settings.py` - Better save message

**Verification**:
- ✅ Config reload before each scan
- ✅ API key passed to CVEMatcher
- ✅ NVDFetcherPRO uses key in headers
- ✅ Logs show key status

**Status**: Fully functional. API key **IS** being used when:
1. Saved in settings
2. `use_local_db = false`
3. New scan started (not existing scans)

---

**Last Updated**: 2026-01-03  
**Version**: 1.0
