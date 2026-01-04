# OWASP, MITRE, SCP Data Flow - Chi Tiết Mapping

## 📊 Luồng Dữ Liệu

### 1. **OWASP Mapping - Dữ liệu từ đâu?**

**File:** `web/security_standards/owasp_mapping.py`

- **OWASP Top 10** được định nghĩa sẵn trong file
- **Mapping logic:** CWE ID → OWASP Category
- **Được gọi ở:** `UnifiedSecurityMapper.analyze_cve()` → `OWASPMapper.get_by_cve_id(cve_id, cwe_ids)`

**Quy trình:**
```
CVE Data (có CWE IDs) 
  ↓
OWASPMapper.get_by_cve_id(cve_id, cwe_ids)
  ↓
Khớp CWE với OWASP Category
  ↓
Trả về owasp_mappings[]
```

---

### 2. **MITRE ATT&CK Mapping - Dữ liệu từ đâu?**

**File:** `web/security_standards/mitre_attack_mapping.py`

- **MITRE Tactics** (TA0043, TA0001, TA0003, ...) được định nghĩa sẵn
- **MITRE Techniques** (T1592, T1589, ...) được định nghĩa với danh sách CWE IDs liên quan
- **Mapping logic:** CWE ID → MITRE Technique → MITRE Tactic
- **Được gọi ở:** `UnifiedSecurityMapper.analyze_cve()` → `MITREMapper.get_by_cve(cve_id, cwe_ids)`

**Quy trình:**
```
CVE Data (có CWE IDs)
  ↓
MITREMapper.get_by_cve(cve_id, cwe_ids)
  ↓
Duyệt từng CWE:
   → Tìm Technique có CWE đó (via get_by_cwe())
   → Lấy Tactic từ Technique
  ↓
Trả về techniques[], tactics[], attack_chain[]
```

---

### 3. **Secure Coding Practices (SCP) - Dữ liệu từ đâu?**

**File:** `web/security_standards/secure_coding_mapper.py`

- **SCP Practices** được định nghĩa sẵn
- **Mapping logic:** CWE ID → SCP Practice Category
- **Được gọi ở:** `UnifiedSecurityMapper.analyze_cve()` → `SecureCodeMapper.get_by_cve(cve_id, cwe_ids)`

**Quy trình:**
```
CVE Data (có CWE IDs)
  ↓
SecureCodeMapper.get_by_cve(cve_id, cwe_ids)
  ↓
Khớp CWE với SCP Practice
  ↓
Trả về practices[]
```

---

## ⚠️ **Vấn đề: Tại sao "No MITRE ATT&CK mapping available"?**

### Nguyên nhân chính:

1. **CVE không có CWE IDs** (hoặc CWE rỗng)
   - Nếu `cwe_ids = []` → `MITREMapper.get_by_cve()` không tìm thấy téchnique nào
   - Kết quả: `techniques = []`, `mitre_dict = {}`

2. **CWE không có trong MITRE_TECHNIQUES**
   - MITRE_TECHNIQUES chỉ định nghĩa một số CWE nhất định
   - Nếu CVE có CWE nhưng CWE đó không trong danh sách MITRE → không match

3. **CVE data structure sai**
   - CVE từ scan có thể không chứa `cwe` field
   - Hoặc `cwe` field có tên khác (ví dụ: `cwe_ids`, `weaknesses`, ...)

---

## 🔍 **Cách Debug:**

### Bước 1: Check CVE data có CWE không
Trong `cve_detail.py` line 103-110:
```python
def _extract_cwe_ids(cve_data: dict) -> list:
    cwe_ids = cve_data.get('cwe')  # ← Check xem field này có dữ liệu không
    if not cwe_ids:
        cwe_ids = cve_data.get('cwe_ids')
    # ...
```

**Kiểm tra:** Log `cwe_ids` để xem nó có giá trị không

### Bước 2: Kiểm tra MITRE_TECHNIQUES có CWE đó không
Trong browser DevTools → Network → `/api/cve/CVE-XXX/analysis` → Response → `"mitre"`

Nếu `"mitre": {}` → CWE không match

### Bước 3: Thêm debug logging vào `mitre_attack_mapping.py`
```python
@staticmethod
def get_by_cve(cve_id: str, cwe_ids: List[int] = None, vulnerability_type: str = None) -> Dict:
    if not cwe_ids:
        cwe_ids = []
    
    print(f"[DEBUG] CVE {cve_id}, CWE IDs: {cwe_ids}")  # ← Thêm dòng này
    
    matched_techniques = {}
    for cwe_id in cwe_ids:
        techniques = MITREMapper.get_by_cwe(cwe_id)
        print(f"[DEBUG] CWE {cwe_id} → Techniques: {techniques}")  # ← Thêm dòng này
```

---

## 📋 **Dữ liệu được lấy từ đâu:**

| Framework | Nguồn | Lưu trữ | Cách gọi |
|-----------|-------|--------|---------|
| **OWASP** | Scan CVE data | `owasp_mapping.py` (constants) | `OWASPMapper.get_by_cve_id()` |
| **MITRE** | Scan CVE data | `mitre_attack_mapping.py` (constants) | `MITREMapper.get_by_cve()` |
| **SCP** | Scan CVE data | `secure_coding_mapper.py` (constants) | `SecureCodeMapper.get_by_cve()` |

---

## 💡 **Giải pháp:**

### Nếu CVE không có CWE → Thêm fallback mapping:
Có thể thêm mapping theo tên CVE hoặc description thay vì chỉ dựa vào CWE.

### Nếu muốn thêm CWE mapping cho MITRE:
Cập nhật `MITRE_TECHNIQUES` dictionary trong `mitre_attack_mapping.py` để bao gồm thêm CWE IDs.

### Để test mapping:
Có thể gọi trực tiếp endpoint POST `/api/cve/CVE-2021-45956/analysis` (từ screenshot bạn gửi)
