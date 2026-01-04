# Web Platform - Data Persistence Guide

## Tổng Quan

Web platform của CVE_Scan giờ có **JSON-based persistence** để lưu scan state vào file. Điều này cho phép:

✅ **Reload page** → Vẫn thấy scan đang chạy  
✅ **Dashboard hiển thị lại** các scans lịch sử  
✅ **Progress lưu lại** khi page bị đóng/reload  

⚠️ **Limitation**: Restart server → mất dữ liệu (chấp nhận được cho internal use)

## Cấu Trúc Thư Mục

```
CVE_Scan/
└── data/
    ├── scans/
    │   ├── scan_<uuid>.json      # Mỗi scan lưu trong 1 file
    │   ├── scan_<uuid>.json
    │   └── ...
    └── index.json               # Danh sách tất cả scans
```

## Cách Hoạt Động

### 1. **Khởi động Server**
```bash
python app.py --web
```

→ Tự động load tất cả scans từ `data/scans/` vào memory  
→ Dashboard sẽ hiển thị scan lịch sử

### 2. **Chạy Scan**
- Scan data được lưu vào file **mỗi 10% progress**
- Khi host hoàn tất, kết quả được lưu **immediately**
- Khi scan hoàn tất, final result được lưu **immediately**

### 3. **Reload Page**
- Frontend gọi `/api/scans` → Server trả về tất cả scans (từ memory)
- Progress bar, results vẫn hiển thị đúng
- Logs vẫn được lưu

### 4. **Restart Server**
- Tất cả scans trong `data/scans/` được load lại
- Scans `running` → state vẫn là `running` (nhưng không thực sự chạy)
- Scans `completed` → vẫn thấy results

## API Endpoints

### GET `/api/scans` - Danh sách tất cả scans
```json
{
  "scans": [
    {
      "scan_id": "abc-123",
      "status": "running",
      "progress": 45,
      "hosts": ["192.168.1.1", "192.168.1.2"],
      "authenticated": false,
      "start_time": "2026-01-01T10:00:00",
      "cve_count": 125
    }
  ]
}
```

### GET `/api/scan/<scan_id>` - Chi tiết scan
```json
{
  "scan_id": "abc-123",
  "status": "completed",
  "progress": 100,
  "hosts": ["192.168.1.1"],
  "results": { ... },
  "logs": [ ... ]
}
```

## JSON File Format

### `data/index.json`
```json
{
  "abc-123": {
    "scan_id": "abc-123",
    "status": "completed",
    "hosts": ["192.168.1.1"],
    "authenticated": false,
    "input_mode": "IP/CIDR",
    "progress": 100,
    "start_time": "2026-01-01T10:00:00",
    "end_time": "2026-01-01T10:05:30",
    "cve_count": 125,
    "host_count": 1
  }
}
```

### `data/scans/scan_<uuid>.json`
```json
{
  "scan_id": "abc-123",
  "status": "completed",
  "hosts": ["192.168.1.1"],
  "results": {
    "192.168.1.1": {
      "gui": {
        "ports": [ ... ]
      },
      "services": { ... },
      "vulnerabilities": { ... }
    }
  },
  "logs": [
    {
      "timestamp": "2026-01-01T10:00:00",
      "level": "INFO",
      "message": "Bắt đầu scan..."
    }
  ],
  "progress": 100,
  "message": "Hoàn tất (5m 30s)",
  "start_time": "2026-01-01T10:00:00",
  "end_time": "2026-01-01T10:05:30"
}
```

## Cleanup

### Tự động cleanup
Server sẽ tự động giữ lại **100 scan gần nhất** (tùy chỉnh):

```python
# Trong scan_service.py
self.persistence.cleanup_old_scans(keep_count=100)
```

### Xóa thủ công
Xóa folder `data/scans/` → Tất cả scans sẽ bị xóa:

```bash
rm -rf data/scans
rm data/index.json
```

## Performance Notes

- **Memory**: Tất cả scans load vào memory khi startup
- **Disk**: JSON files được lưu synchronously
- **Concurrency**: Thread-safe với `threading.RLock()`
- **Scalability**: 1000+ scans OK, nhưng nên cleanup

## Development Notes

### Thêm feature mới
Nếu bạn muốn thêm field mới vào scan data:

```python
# 1. Thêm vào scan_info dict
self.scans[scan_id]["new_field"] = value

# 2. Khi có thay đổi, save to disk
self.persistence.save_scan(scan_id, self.scans[scan_id])

# 3. Khi load, field sẽ tự động load từ JSON
```

### Testing
```python
from web.utils.scan_persistence import ScanPersistence

p = ScanPersistence("data")
scans = p.load_all_scans()
print(len(scans))  # Số scans đã lưu
```

## Troubleshooting

### Q: Mở server lại mà không thấy scan cũ?
A: Kiểm tra folder `data/scans/` có tồn tại không. Nếu không, tạo bằng `mkdir -p data/scans`

### Q: Sao progress không lưu khi đang chạy?
A: Progress được lưu mỗi 10%, bạn có thể reload page sẽ thấy cập nhật

### Q: Sao host result không lưu immediately?
A: `host_result_cb` được gọi khi host hoàn tất, lúc đó sẽ save to disk

### Q: Làm sao upgrade sang database?
A: Implement interface tương tự như `ScanPersistence`, swap trong `scan_service.__init__`

---

**Last Updated**: 2026-01-01  
**Status**: ✅ Production Ready (Internal Use)
