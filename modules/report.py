import datetime  # Thư viện xử lý ngày giờ

class ReportGenerator:
    def __init__(self, output_file='report.txt'):
        # Thiết lập đường dẫn file đầu ra
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
        """
        # 1. Tạo timestamp cho báo cáo
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [f"Report generated: {now}\n\n"]

        # 2. Chuyển dict thành list để dùng while
        host_items = list(results.items())  # [(ip, ports_dict), ...]
        i = 0
        while i < len(host_items):
            ip, ports = host_items[i]
            lines.append(f"Host: {ip}\n")

            # 3. Xử lý từng port
            port_items = list(ports.items())  # [(port, info_dict), ...]
            j = 0
            while j < len(port_items):
                port, info = port_items[j]
                service = info.get('service') or 'unknown'
                version = info.get('version') or ''
                # Ghi thông tin port
                lines.append(f"  Port {port}/{service} {version}\n")

                # 4. Xử lý từng CVE
                cve_list = info.get('cves', [])
                k = 0
                while k < len(cve_list):
                    cve = cve_list[k]
                    # Chọn score hoặc N/A
                    score = cve['score'] if cve['score'] not in (None, '', 'N/A') else 'N/A'
                    # Ghi CVE line
                    lines.append(
                        f"    - {cve['id']} [{cve['severity']} (Score: {score})]: {cve['desc']}\n"
                    )

                    # 5. Ghi exploit URL hoặc thông báo không có
                    exploits = cve.get('exploits', [])
                    if exploits:
                        m = 0
                        while m < len(exploits):
                            lines.append(f"       * Exploit: {exploits[m]}\n")
                            m += 1
                    else:
                        lines.append("       * No exploits found on Exploit-DB\n")

                    k += 1
                lines.append("\n")  # ngăn cách các port
                j += 1
            i += 1

        # 6. Ghi file và thông báo
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Report saved to {self.output_file}")
