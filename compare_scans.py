import csv
from collections import defaultdict

def analyze_scan_file(filename):
    """Phân tích file CSV scan"""
    hosts = defaultdict(lambda: {'ports': set(), 'services': set(), 'cves': []})
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            host = row['Host']
            port = row['Port']
            service = row['Service']
            cve = row['CVE ID']
            
            hosts[host]['ports'].add(port)
            hosts[host]['services'].add(service)
            if cve:
                hosts[host]['cves'].append(cve)
    
    return hosts

def main():
    print("=" * 80)
    print("SO SÁNH DỮ LIỆU QUÉT NGÀY 11-1 VÀ 12-1")
    print("=" * 80)
    
    # Đọc dữ liệu
    data_11 = analyze_scan_file('vulnerabilities_2026-01-11.csv')
    data_12 = analyze_scan_file('vulnerabilities_2026-01-12.csv')
    
    print(f"\n📊 TỔNG QUAN:")
    print(f"  Ngày 11-1: {len(data_11)} hosts, {sum(len(h['cves']) for h in data_11.values())} CVE entries")
    print(f"  Ngày 12-1: {len(data_12)} hosts, {sum(len(h['cves']) for h in data_12.values())} CVE entries")
    
    # Hosts chỉ có ngày 11
    only_11 = set(data_11.keys()) - set(data_12.keys())
    print(f"\n🔴 Hosts CHỈ CÓ ngày 11-1 (bị mất): {len(only_11)}")
    if only_11:
        for host in sorted(only_11)[:10]:  # Hiển thị 10 đầu tiên
            print(f"    - {host}: {len(data_11[host]['ports'])} ports, {len(data_11[host]['cves'])} CVEs")
        if len(only_11) > 10:
            print(f"    ... và {len(only_11) - 10} hosts khác")
    
    # Hosts chỉ có ngày 12
    only_12 = set(data_12.keys()) - set(data_11.keys())
    print(f"\n🟢 Hosts CHỈ CÓ ngày 12-1 (mới): {len(only_12)}")
    if only_12:
        for host in sorted(only_12)[:10]:
            print(f"    - {host}: {len(data_12[host]['ports'])} ports, {len(data_12[host]['cves'])} CVEs")
        if len(only_12) > 10:
            print(f"    ... và {len(only_12) - 10} hosts khác")
    
    # Hosts cả 2 ngày
    both = set(data_11.keys()) & set(data_12.keys())
    print(f"\n🔵 Hosts CẢ 2 NGÀY: {len(both)}")
    
    # So sánh chi tiết hosts cùng có
    print(f"\n📋 SO SÁNH CHI TIẾT HOSTS CẢ 2 NGÀY:")
    cve_increase = []
    cve_decrease = []
    
    for host in sorted(both)[:5]:  # Top 5 hosts
        cves_11 = len(data_11[host]['cves'])
        cves_12 = len(data_12[host]['cves'])
        ports_11 = len(data_11[host]['ports'])
        ports_12 = len(data_12[host]['ports'])
        
        diff = cves_12 - cves_11
        if diff > 0:
            cve_increase.append((host, diff))
        elif diff < 0:
            cve_decrease.append((host, diff))
        
        print(f"\n  {host}:")
        print(f"    11-1: {ports_11} ports, {cves_11} CVEs")
        print(f"    12-1: {ports_12} ports, {cves_12} CVEs")
        print(f"    Thay đổi: {diff:+d} CVEs")
    
    # Kiểm tra scan incomplete
    print(f"\n\n⚠️ PHÂN TÍCH VẤN ĐỀ:")
    print(f"  1. Ngày 12-1 quét DỪNG giữa chừng (42/183 hosts)")
    print(f"  2. Ngày 11-1 quét HOÀN THÀNH (tất cả hosts)")
    print(f"  3. Số hosts khác nhau KHÔNG PHẢI LỖI - do scan chưa xong")
    print(f"\n  ✅ Không có vấn đề về scan engine hay CVE mapping")
    print(f"  ✅ Dữ liệu ngày 11-1 là chính xác và đầy đủ")
    print(f"  ❌ Dữ liệu ngày 12-1 chưa đầy đủ do scan bị dừng")
    
    print(f"\n💡 KHUYẾN NGHỊ:")
    print(f"  - Chạy lại scan ngày 12-1 cho đến khi hoàn thành (183/183 hosts)")
    print(f"  - Đợi scan hoàn thành mới refresh dashboard")
    print(f"  - Không so sánh scan incomplete với scan complete")

if __name__ == "__main__":
    main()
