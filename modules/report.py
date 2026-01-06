"""
Module ReportGenerator: Xuất kết quả quét ra file báo cáo text.
- Ghi kết quả quét (host, port, service) và CVE (ID, severity, score) vào file report.txt
"""

import datetime  # Thư viện xử lý ngày giờ (tạo timestamp)


class ReportGenerator:
    """
    Lớp xuất báo cáo quét vào file văn bản.
    - Ghi format: Host -> Port -> Service -> CVE -> Exploit URLs
    - Dễ đọc, dễ parse bằng text editor hoặc tools khác
    """

    def __init__(self, output_file='report.txt'):
        """
        Khởi tạo ReportGenerator instance.
        
        Tham số:
        - output_file (str): đường dẫn file output, mặc định 'report.txt'
        
        Hành động:
        - Lưu output_file path để dùng trong hàm write()
        """
        self.output_file = output_file

    def write(self, results):
        """
        Ghi kết quả quét và CVE vào file báo cáo text.

        Tham số:
        - results (dict): dữ liệu quét dạng:
            {
                ip_address: {
                    port_number: {
                        'service': str (ví dụ: 'http', 'ssh'),
                        'version': str (ví dụ: '1.18.0'),
                        'cves': [
                            {
                                'id': 'CVE-YYYY-XXXXX',
                                'severity': 'Critical|High|Medium|Low',
                                'score': float or 'N/A',
                                'desc': 'Mô tả lỗ hổng',
                                'exploits': ['url1', 'url2', ...]
                            },
                            ...
                        ]
                    }
                }
            }

        Quy trình:
        1. Tạo timestamp cho báo cáo (để biết khi nào quét)
        2. Nếu results rỗng, ghi thông báo "No scan results"
        3. Duyệt từng host -> port -> CVE, xây dựng list dòng text
        4. Ghi tất cả dòng vào file (một lần)
        5. Xử lý exception nếu có lỗi file I/O
        """
        # 1. Tạo timestamp báo cáo (format: YYYY-MM-DD HH:MM:SS)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Khởi tạo list dòng text (sẽ ghép và ghi vào file)
        lines = [f"Report generated: {now}\n\n"]

        # 2. Kiểm tra kết quả rỗng
        if not results:
            lines.append("No scan results to report.\n")

        # 3. Chuyển dict thành list để duyệt (để support while loop)
        # host_items: list các tuple [(ip1, ports_dict1), (ip2, ports_dict2), ...]
        host_items = list(results.items())
        i = 0
        # Duyệt từng host
        while i < len(host_items):
            ip, ports = host_items[i]
            # Thêm tiêu đề host vào báo cáo
            lines.append(f"Host: {ip}\n")

            # Chuyển port dict thành list để duyệt (hỗ trợ while loop)
            # port_items: list các tuple [(port1, info1), (port2, info2), ...]
            port_items = list(ports.items())
            j = 0
            # Duyệt từng port
            while j < len(port_items):
                port, info = port_items[j]
                # Lấy service name và version (fallback 'unknown' hoặc '' nếu thiếu)
                service = info.get('service') or 'unknown'
                version = info.get('version') or ''

                # Ghi dòng port: "  Port 80/http 2.4.49" hoặc "  Port 22/ssh "
                lines.append(f"  Port {port}/{service} {version}\n")

                # Xử lý CVE của port này
                cve_list = info.get('cves', [])
                k = 0
                # Duyệt từng CVE
                while k < len(cve_list):
                    cve = cve_list[k]

                    # Chuẩn bị score để hiển thị
                    # Nếu score là None, rỗng, hoặc 'N/A' thì hiển thị 'N/A'
                    score = cve['score'] if cve['score'] not in (None, '', 'N/A') else 'N/A'

                    # Ghi info CVE: ID, severity level, score, mô tả
                    # Ví dụ: "    - CVE-2023-50071 [High (Score: 7.5)]: Mô tả lỗ hổng"
                    lines.append(
                        f"    - {cve['id']} [{cve['severity']} (Score: {score})]: {cve['desc']}\n"
                    )

                    # Duyệt và ghi các exploit URLs (hoặc ghi "No exploits" nếu không có)
                    exploits = cve.get('exploits', [])
                    if exploits:
                        # Duyệt từng exploit URL
                        m = 0
                        while m < len(exploits):
                            lines.append(f"       * Exploit: {exploits[m]}\n")
                            m += 1
                    else:
                        # Không có exploit nào, ghi thông báo
                        lines.append("       * No exploits found on Exploit-DB\n")

                    k += 1

                # Thêm dòng trống để ngăn cách giữa các port (format đẹp)
                lines.append("\n")
                j += 1
            i += 1

        # 4. Ghi tất cả dòng vào file (một lần)
        try:
            # Mở file với encoding utf-8 (hỗ trợ ký tự tiếng Việt)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                # Ghi tất cả dòng cùng lúc (hiệu quả hơn ghi từng dòng)
                f.writelines(lines)
            # Log thành công trên console
            print(f"Report saved to {self.output_file}")
        except Exception as e:
            # Xử lý exception: lỗi quyền file, disk đầy, path invalid, v.v.
            print(f"[ERROR] Cannot write report: {e}")


# Entry point: khi chạy file này trực tiếp để test
if __name__ == "__main__":
    # Khởi tạo ReportGenerator instance
    rg = ReportGenerator()
    # Test với dict rỗng (sẽ ghi "No scan results to report")
    rg.write({})
