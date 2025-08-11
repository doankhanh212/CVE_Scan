import datetime  # Thư viện xử lý ngày giờ

class ReportGenerator:
    """
    Lớp ReportGenerator: ghi kết quả quét vào file văn bản (report.txt theo mặc định).

    - output_file: đường dẫn file đầu ra, mặc định 'report.txt'.
    - write(results): ghi cấu trúc kết quả vào file theo định dạng dễ đọc.
    """

    def __init__(self, output_file='report.txt'):
        # Thiết lập đường dẫn file đầu ra (có thể thay đổi khi khởi tạo instance)
        self.output_file = output_file

    def write(self, results):
        """
        Ghi kết quả quét và CVE vào file văn bản.

        Tham số:
        results: dict dạng:
            {
                ip_address: {
                    port_number: {
                        'service': str,
                        'version': str,
                        'cves': [
                            {'id', 'severity', 'score', 'desc', 'exploits'}
                        ]
                    }
                }
            }

        Quy trình:
        1. Tạo timestamp cho báo cáo
        2. Nếu results rỗng -> ghi thông báo
        3. Duyệt mỗi host -> mỗi port -> mỗi CVE, ghi chi tiết
        4. Xử lý ngoại lệ khi ghi file
        """
        # 1. Tạo timestamp cho báo cáo (format: YYYY-MM-DD HH:MM:SS)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # lines là list các dòng sẽ ghép và ghi vào file
        lines = [f"Report generated: {now}\n\n"]

        # 2. Nếu không có kết quả, thêm dòng tương ứng
        if not results:
            lines.append("No scan results to report.\n")

        # 3. Chuyển dict thành list để dùng while 
        # host_items sẽ là list các tuple: [(ip, ports_dict), ...]
        host_items = list(results.items())
        i = 0
        # Dùng while để duyệt từng host
        while i < len(host_items):
            ip, ports = host_items[i]
            # Thêm tiêu đề host vào báo cáo
            lines.append(f"Host: {ip}\n")

            # 4. Xử lý từng port (chuyển sang list để dùng while/index)
            port_items = list(ports.items())
            j = 0
            while j < len(port_items):
                port, info = port_items[j]
                # Lấy service/version với fallback nếu thiếu
                service = info.get('service') or 'unknown'
                version = info.get('version') or ''

                # Ghi dòng port: ví dụ "  Port 80/http 2.4.49"
                lines.append(f"  Port {port}/{service} {version}\n")

                # 5. Xử lý từng CVE ứng với port đó
                cve_list = info.get('cves', [])
                k = 0
                while k < len(cve_list):
                    cve = cve_list[k]

                    # Chọn score để hiển thị: nếu score có giá trị hợp lệ thì dùng,
                    # nếu là 'N/A' hoặc '', hiển thị 'N/A'
                    score = cve['score'] if cve['score'] not in (None, '', 'N/A') else 'N/A'

                    # Ghi thông tin CVE: ID, severity, score, mô tả
                    # Ví dụ: "    - CVE-2023-xxxxx [High (Score: 7.5)]: Mô tả"
                    lines.append(
                        f"    - {cve['id']} [{cve['severity']} (Score: {score})]: {cve['desc']}\n"
                    )

                    # 6. Ghi các exploit URL nếu có, hoặc ghi thông báo không có exploit
                    exploits = cve.get('exploits', [])
                    if exploits:
                        # Dùng while để duyệt exploit list
                        m = 0
                        while m < len(exploits):
                            lines.append(f"       * Exploit: {exploits[m]}\n")
                            m += 1
                    else:
                        # Nếu không có exploit, ghi dòng thông báo
                        lines.append("       * No exploits found on Exploit-DB\n")

                    k += 1

                # Thêm dòng trống để ngăn cách giữa các port
                lines.append("\n")
                j += 1
            i += 1

        # 7. Ghi file và xử lý ngoại lệ
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                # Ghi tất cả dòng vào file cùng lúc
                f.writelines(lines)
            # In thông báo trên console khi ghi thành công
            print(f"Report saved to {self.output_file}")
        except Exception as e:
            # Nếu có lỗi khi ghi file (quyền, disk full, path invalid), in lỗi
            print(f"[ERROR] Cannot write report: {e}")


# Nếu file này chạy đơn lẻ để test, tạo instance và gọi write với dict rỗng
if __name__ == "__main__":
    rg = ReportGenerator()
    rg.write({})
