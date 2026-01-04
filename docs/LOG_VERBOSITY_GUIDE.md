# Log Verbosity Implementation Guide

## ✅ Tính năng đã hoàn thành

### 1. **Backend Filtering** 
- Log level priority system trong `scan_service.py`
- Chỉ ghi logs >= configured level
- Mapping: debug(0) < info(1) < warning(2) < error(3)

### 2. **Settings UI**
- Dropdown với icons rõ ràng:
  - 🔍 Debug (Most Detailed)
  - ℹ️ Info (Recommended)
  - ⚠️ Warning (Less Verbose)
  - ❌ Error (Least Detailed)
- Tooltip giải thích impact

### 3. **Live Logs Display**
- Real-time log streaming với icons
- Color-coded levels (debug/info/success/warning/error)
- Auto-scroll toggle
- Log counter hiển thị số entries

### 4. **Client-side Filtering**
- Dropdown filter: All / Debug / Info+ / Warning+ / Error Only
- Instant filtering không cần reload
- Filter được apply cho cả logs cũ và mới

### 5. **Performance Optimizations**
- Backend: Skip logs dưới threshold → save CPU/memory
- Frontend: Hidden CSS class thay vì remove DOM
- Keep only last 200 logs in DOM
- Batch rendering với DocumentFragment

---

## 🎨 UI Features

### Log Entry Format
```
[HH:MM:SS] [LEVEL] 🔍 Message text
```

### Interactive Controls
1. **Filter Dropdown**: Lọc theo mức độ
2. **Auto-scroll Button**: Toggle scroll behavior
3. **Clear Button**: Xóa display (confirm required)
4. **Footer Stats**: Show count + live indicator

### Visual Indicators
- Level badges với màu riêng
- Emoji icons cho dễ nhận diện
- Hover effects
- Smooth transitions

---

## 📊 Log Level Behavior

| Setting | Backend Logs | Frontend Display |
|---------|--------------|------------------|
| Debug   | All logs     | All logs         |
| Info    | Info+        | Can filter       |
| Warning | Warning+     | Can filter       |
| Error   | Error only   | Error only       |

**Example**: Nếu setting = "Info", backend sẽ skip debug logs (tiết kiệm RAM/CPU), nhưng user vẫn có thể filter Info/Warning/Error ở frontend.

---

## 🔧 Configuration

### Settings Page
```javascript
{
  "log_verbosity": "info"  // debug|info|warning|error
}
```

### Applied To
- Scan execution logs
- Progress updates
- Error messages
- System notifications

---

## 🚀 Usage Examples

### For Developers (Debug Mode)
```json
{"log_verbosity": "debug"}
```
→ See all internal operations, API calls, CPE matching details

### For Operators (Info Mode)
```json
{"log_verbosity": "info"}
```
→ See scan progress, hosts found, CVE counts

### For Production (Warning Mode)
```json
{"log_verbosity": "warning"}
```
→ Only see warnings and errors, minimal noise

---

## 💡 Best Practices

### When to use each level:

**Debug** 🔍
- Troubleshooting scan issues
- Understanding CVE matching logic
- Performance profiling

**Info** ℹ️ (Recommended)
- Normal operations
- Scan progress tracking
- General monitoring

**Warning** ⚠️
- Production environments
- Minimal log volume
- Focus on issues only

**Error** ❌
- Critical systems
- Alert-only mode
- Minimal overhead

---

## 🧪 Testing

### Test Log Filtering
1. Set verbosity to "Debug" in Settings
2. Start a scan
3. Observe all log levels appear
4. Change filter dropdown to "Warning+"
5. Only warning/error logs visible

### Test Auto-scroll
1. Start scan with many hosts
2. Watch logs auto-scroll
3. Click "Auto-scroll" to pause
4. Scroll up to read old logs
5. Re-enable to jump to bottom

### Test Clear Logs
1. Accumulate some logs
2. Click "Clear"
3. Confirm dialog
4. Display clears (backend logs preserved)

---

## 📁 Files Modified

1. `web/services/scan_service.py` - Backend filtering logic
2. `web/templates/result.html` - Live logs UI + JS filtering
3. `web/templates/settings.html` - Verbosity dropdown
4. `web/static/css/logs.css` - Log styling (NEW)
5. `web/templates/base.html` - Include logs.css

---

## 🎯 Next Steps (Optional Enhancements)

- [ ] Export logs to file (txt/json)
- [ ] Search/regex filter in logs
- [ ] Highlight specific keywords
- [ ] Log timestamps in different timezones
- [ ] Persist filter preference in localStorage
- [ ] Add "Copy logs" button
- [ ] WebSocket for real-time push (vs polling)

---

**Status**: ✅ Fully Implemented & Production Ready
**Version**: 1.0
**Last Updated**: 2026-01-03
