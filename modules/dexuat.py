import json
import pandas as pd
from tabulate import tabulate

def load_keywords(file_path):
    """Tải bộ quy tắc từ file JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def map_cve_to_nist_only(mitigation_text, rules):
    """Thuật toán mapping chỉ giữ lại các cột NIST và Hành động"""
    text = mitigation_text.lower()
    aggregated_results = {}

    for control_id, info in rules.items():
        # Tìm kiếm từ khóa để xác định Control phù hợp
        if any(kw in text for kw in info['keywords']):
            if control_id not in aggregated_results:
                aggregated_results[control_id] = {
                    'Mã NIST R5': control_id,
                    'Nhóm Control': info['group'],
                    'Kế hoạch hành động cụ thể': info['action']
                }
    
    return list(aggregated_results.values())

# --- THỰC THI ---
# 1. Nạp quy tắc từ keywords.json
rules = load_keywords('keywords.json')

# 2. Nội dung Mitigation mẫu
sample_mitigation = (
    "Recommendation: Apply security patches. Deploy a Web Application Firewall (WAF) "
    "to filter SQL injection. Enforce multi-factor authentication (MFA)."
)

# 3. Chạy mapping
results = map_cve_to_nist_only(sample_mitigation, rules)
df = pd.DataFrame(results)

if not df.empty:
    print("\n" + "="*90)
    print(f"{'BẢNG ĐỀ XUẤT XỬ LÝ LỖ HỔNG THEO TIÊU CHUẨN NIST':^90}")
    print("="*90)
    
    # Xuất bảng với khung 'grid' để cố định hàng cột ngay ngắn
    # Đã loại bỏ hoàn toàn cột ISO và Từ khóa khớp theo yêu cầu
    print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
    
    print("="*90 + "\n")
else:
    print("Không tìm thấy dữ liệu phù hợp.")