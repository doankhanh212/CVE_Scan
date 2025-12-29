# 🚀 CVE_Scan - Hướng Dẫn Nhanh (Tiếng Việt)

**Phiên bản:** 1.0  
**Bắt đầu nhanh:** 5 phút là quét được

---

## 🌟 Dành cho người mới (Siêu đơn giản)

1) Mở ứng dụng: `python app.py` hoặc `RUN_CVESCAN.bat` (Windows)
2) Bấm "🛠 Tự động cài đặt" để cài thư viện Python và kiểm tra/cài Nmap
3) Nhập mục tiêu (ví dụ: `192.168.1.0/24`) → bấm "Quét"
4) Xuất báo cáo: chọn "CSV/HTML/PDF" khi tiến trình đạt 100%

Nếu là Windows “máy trống”: chạy `RUN_INSTALLER.bat` để mở trình cài đặt GUI, cài Python/Nmap và phụ thuộc tự động.

---

## 📥 Cài đặt (lần đầu)

### Cách 1: Cài đặt cục bộ (Khuyến nghị)
```bash
# 1. Giải nén gói phân phối
unzip cve_scan_1.0.zip
cd CVE_Scan

# 2. Tạo môi trường ảo
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Cài đặt phụ thuộc
pip install -r requirements.txt

# 4. Xác minh cài đặt
python verify_installation.py

# 5. Chạy ứng dụng GUI
python app.py
```

#### Trình cài đặt GUI (Windows)
Bạn có thể dùng trình cài đặt chuyên dụng:
```bat
RUN_INSTALLER.bat
```
- Trình cài đặt sẽ:
   - Cài Python (qua winget nếu thiếu)
   - Tạo venv và cài `requirements.txt`
   - Kiểm tra/cài Nmap (qua winget)
   - Chạy `verify_installation.py`
Sau khi hoàn tất, mở ứng dụng bằng `python app.py` hoặc `RUN_CVESCAN.bat`.

### Cách 2: Docker (Dễ nhất)
```bash
# 1. Build image
docker build -t cve-scan:1.0 .

# 2. Chạy container
docker-compose up

# 3. Truy cập GUI
VNC: localhost:5900
noVNC: http://localhost:6080
```

### Cách 3: Môi trường phát triển
```bash
# Clone từ Git
git clone <repository-url>
cd CVE_Scan
pip install -e .
python app.py
```

---

## 🎯 Chạy một lần quét

### Qua GUI (Dễ nhất)
```bash
python app.py
```

1. **Chọn chế độ:**
   - Không xác thực: quét cơ bản bằng nmap
   - Có xác thực: dùng thông tin SSH/WinRM

2. **Nhập mục tiêu:**
   - IP đơn: `192.168.1.100`
   - Phạm vi CIDR: `192.168.1.0/24`
   - Nhiều mục tiêu: mỗi dòng một địa chỉ

3. **Cấu hình (Tuỳ chọn):**
   - Bấm ⚙️ Settings (Cài đặt)
   - Thêm NVD API key để lấy CVE mới nhất
   - Tuỳ chỉnh bộ lọc mức độ nghiêm trọng

4. **Chạy quét:**
   - Bấm "Quét"
   - Theo dõi tiến trình ở nhật ký
   - Xem kết quả trên bảng

5. **Xuất kết quả:**
   - Bấm "Xuất"
   - Chọn định dạng: CSV, HTML, PDF, JSON

### Qua dòng lệnh
```bash
# Thử nhanh
python scripts/smoke_run_scan.py localhost

# Kiểm thử pipeline đầy đủ
python scripts/test_filtering.py

# Tác vụ cơ sở dữ liệu
python scripts/rebuild_local_db.py
python scripts/download_nvd_feeds.py
```

---

## ⚙️ Cấu hình

- File cấu hình: `config.json`
- Khoá chính:
  - `nvd_api_key`: Khoá API NVD (tuỳ chọn, dùng để lấy dữ liệu mới)
  - `use_local_db`: Dùng cơ sở dữ liệu CVE cục bộ (true/false)
  - `local_db_path`: Đường dẫn DB CVE cục bộ (mặc định: `modules/cve/nvd_cve.db`)
- Thay đổi qua GUI: ⚙️ Settings → Lưu cài đặt

---

## 📦 Kết quả quét & báo cáo

- Dữ liệu nội bộ dạng: `host → result` với `result['gui']['ports']` là danh sách cổng
- Mỗi cổng có `cves` (danh sách CVE: `id`, `severity`, `description`, `cvss_v2|v3|v4`, `cpe`)
- Xuất báo cáo: CSV/HTML/PDF/JSON từ GUI

---

## ❓ Khắc phục sự cố

- Không thấy GUI: đảm bảo đã chạy `python app.py` trong môi trường ảo
- Quét không trả về cổng: kiểm tra Nmap đã cài và có trong PATH
- Không lấy được CVE mới: kiểm tra `nvd_api_key` hoặc bật `use_local_db`
- Lỗi quyền trên Linux/Mac: chạy với quyền phù hợp hoặc dùng Docker

---

## 📚 Tài liệu liên quan

- `START_HERE.txt` – Hướng dẫn bắt đầu nhanh cho mọi hệ điều hành
- `PACKAGING_GUIDE.md` – Hướng dẫn đóng gói & phân phối
- `DOCUMENTATION_INDEX.md` – Mục lục tài liệu
- `BUG_AUDIT_REPORT.md` – Báo cáo chất lượng & kiểm thử

---

## 🆘 Hỗ trợ

- Vui lòng đính kèm file `verify_installation.py` đầu ra khi yêu cầu hỗ trợ
- Môi trường khuyến nghị: Python 3.11+, Nmap mới nhất, Windows/Linux/Mac hoặc Docker
