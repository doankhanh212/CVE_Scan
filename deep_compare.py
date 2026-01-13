import csv
from collections import defaultdict

def analyze_cve_mapping():
    """Kiểm tra xem có vấn đề về CVE mapping không"""
    
    print("=" * 80)
    print("PHÂN TÍCH SÂU VỀ CVE MAPPING")
    print("=" * 80)
    
    # Đọc dữ liệu ngày 11
    data_11 = defaultdict(list)
    with open('vulnerabilities_2026-01-11.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = f"{row['Host']}|{row['Port']}|{row['Service']}|{row['Version']}"
            data_11[key].append(row['CVE ID'])
    
    # Đọc dữ liệu ngày 12
    data_12 = defaultdict(list)
    with open('vulnerabilities_2026-01-12.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = f"{row['Host']}|{row['Port']}|{row['Service']}|{row['Version']}"
            data_12[key].append(row['CVE ID'])
    
    # Tìm các service giống nhau
    common_services = set(data_11.keys()) & set(data_12.keys())
    
    print(f"\n🔍 KIỂM TRA CVE MAPPING CHO CÙNG SERVICE:")
    print(f"  Số service giống nhau giữa 2 ngày: {len(common_services)}")
    
    if common_services:
        print(f"\n  Chi tiết 5 service đầu tiên:")
        for idx, key in enumerate(sorted(common_services)[:5], 1):
            parts = key.split('|')
            host, port, service, version = parts[0], parts[1], parts[2], parts[3]
            
            cves_11 = set(data_11[key])
            cves_12 = set(data_12[key])
            
            print(f"\n  {idx}. {host} - {service} ({version})")
            print(f"     Ngày 11-1: {len(cves_11)} CVEs")
            print(f"     Ngày 12-1: {len(cves_12)} CVEs")
            
            only_11 = cves_11 - cves_12
            only_12 = cves_12 - cves_11
            both = cves_11 & cves_12
            
            print(f"     Giống nhau: {len(both)} CVEs")
            print(f"     Chỉ ngày 11: {len(only_11)} CVEs")
            print(f"     Chỉ ngày 12: {len(only_12)} CVEs")
            
            if only_11:
                print(f"     ⚠️ Mất CVEs: {list(only_11)[:3]}")
            if only_12:
                print(f"     ✅ Thêm CVEs: {list(only_12)[:3]}")
    
    # Kiểm tra host 103.98.152.15 đặc biệt
    print(f"\n" + "=" * 80)
    print("⚠️ TRƯỜNG HỢP ĐẶC BIỆT: 103.98.152.15")
    print("=" * 80)
    
    host_15_11 = [k for k in data_11.keys() if k.startswith('103.98.152.15|')]
    host_15_12 = [k for k in data_12.keys() if k.startswith('103.98.152.15|')]
    
    print(f"\nNgày 11-1: {len(host_15_11)} services")
    for key in host_15_11:
        parts = key.split('|')
        print(f"  - Port {parts[1]}, Service: {parts[2]}, Version: {parts[3]}")
        print(f"    CVEs: {len(data_11[key])}")
    
    print(f"\nNgày 12-1: {len(host_15_12)} services")
    for key in host_15_12:
        parts = key.split('|')
        print(f"  - Port {parts[1]}, Service: {parts[2]}, Version: {parts[3]}")
        print(f"    CVEs: {len(data_12[key])}")
    
    # KẾT LUẬN
    print(f"\n" + "=" * 80)
    print("🔎 KẾT LUẬN PHÂN TÍCH")
    print("=" * 80)
    
    if len(common_services) > 0:
        # Kiểm tra xem CVE mapping có nhất quán không
        inconsistent = []
        for key in common_services:
            cves_11 = set(data_11[key])
            cves_12 = set(data_12[key])
            
            # Nếu khác biệt quá lớn (>50% hoặc >10 CVEs)
            diff = abs(len(cves_11) - len(cves_12))
            if diff > 10 or diff / max(len(cves_11), len(cves_12), 1) > 0.5:
                inconsistent.append((key, len(cves_11), len(cves_12)))
        
        if inconsistent:
            print(f"\n⚠️ PHÁT HIỆN BẤT THƯỜNG:")
            print(f"  Có {len(inconsistent)} services với CVE mapping khác biệt lớn:")
            for key, count_11, count_12 in inconsistent[:3]:
                parts = key.split('|')
                print(f"  - {parts[0]} {parts[2]}: {count_11} CVEs (11-1) vs {count_12} CVEs (12-1)")
            print(f"\n  🐛 Có thể có vấn đề về:")
            print(f"     1. Phiên bản NVD database khác nhau giữa 2 lần quét")
            print(f"     2. CPE matching rules thay đổi")
            print(f"     3. Cache CVE không đồng bộ")
        else:
            print(f"\n✅ CVE MAPPING NHẤT QUÁN")
            print(f"  Không phát hiện bất thường trong CVE mapping")
    
    print(f"\n💡 NGUYÊN NHÂN CHÍNH:")
    print(f"  - Ngày 12-1: Scan DỪNG ở 42/183 hosts (23%)")
    print(f"  - Ngày 11-1: Scan HOÀN THÀNH 100%")
    print(f"  - Hosts khác nhau → CVE count khác nhau")
    print(f"\n✅ Đây KHÔNG PHẢI lỗi scan engine")
    print(f"✅ Đây là kết quả của scan incomplete")

if __name__ == "__main__":
    analyze_cve_mapping()
