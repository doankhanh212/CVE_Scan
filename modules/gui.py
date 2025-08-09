import tkinter as tk  # Thư viện giao diện người dùng Tkinter
from tkinter import filedialog, messagebox  # Hộp thoại chọn file và thông báo
from modules.scanner import Scanner  # Module quét port sử dụng nmap
from modules.nvd_fetcher import NVDFetcher  # Module lấy thông tin CVE từ NVD và PoC từ Exploit-DB
from modules.report import ReportGenerator  # Module tạo báo cáo định dạng TXT
import csv  # Thư viện xử lý CSV cho chức năng xuất dữ liệu

class GUIController:
    def __init__(self):
        # Khởi tạo cửa sổ chính của ứng dụng
        self.root = tk.Tk()
        self.root.title("Công cụ quét lỗ hổng CVE")

        # --- Các đối tượng xử lý nghiệp vụ phía sau GUI ---
        self.scanner = Scanner()  # Đối tượng để quét port host
        self.nvd = NVDFetcher(api_key="b869e2cd-3a86-4cb0-bf38-88a10671c3c4")  # Đối tượng để lấy CVE
        self.reporter = ReportGenerator()  # Đối tượng để ghi báo cáo TXT

        # --- B1: Tạo khung nhập hosts ---
        # Label hướng dẫn nhập nhiều host, mỗi dòng một host
        tk.Label(self.root, text="Nhập IP/Host (mỗi dòng 1 host):")\
            .grid(row=0, column=0, columnspan=3, sticky='w')
        # Text widget cho phép nhập nhiều dòng
        self.hosts_text = tk.Text(self.root, height=5, width=60)
        self.hosts_text.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

        # --- B2: Nút điều khiển ---
        # Nút bắt đầu quá trình quét
        tk.Button(self.root, text="Run Scan", command=self.run_scan)\
            .grid(row=2, column=0, pady=5)
        # Nút xuất kết quả cuối cùng sang file CSV
        tk.Button(self.root, text="Export CSV", command=self.export_csv)\
            .grid(row=2, column=1, pady=5)

        # --- B3: Vùng hiển thị log ---
        # Text widget để hiển thị dòng lệnh tiến trình quét
        self.log = tk.Text(self.root, height=15, width=70)
        self.log.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

        # Khởi tạo biến lưu kết quả scan cuối cùng để xuất CSV
        self.last_results = {}

    def run_scan(self):
        """
        Hàm xử lý khi người dùng nhấn nút "Run Scan".
        1. Đọc danh sách hosts từ GUI
        2. Quét từng host, lấy port và gọi NVD
        3. Ghi log tiến trình và lưu kết quả
        4. Gọi ReportGenerator để xuất file TXT
        """
        # 1. Đọc toàn bộ nội dung nhập và tách thành danh sách dòng
        raw = self.hosts_text.get('1.0', tk.END).strip()
        host_lines = raw.splitlines()
        hosts = []
        idx_host = 0
        # Duyệt từng dòng, loại bỏ dòng rỗng
        while idx_host < len(host_lines):
            line = host_lines[idx_host].strip()
            if line:
                hosts.append(line)
            idx_host += 1

        # Nếu không có host nào, cảnh báo và dừng
        if not hosts:
            messagebox.showwarning("Warning", "Vui lòng nhập ít nhất một host.")
            return

        # 2. Xóa log cũ và khởi tạo kết quả trống
        self.log.delete('1.0', tk.END)
        results = {}

        idx_host = 0
        # Duyệt lần lượt từng host để quét
        while idx_host < len(hosts):
            host = hosts[idx_host]
            # Ghi log: bắt đầu quét host
            self.log.insert(tk.END, f"Scanning {host}...\n")
            # Gọi Scanner quét port
            ports = self.scanner.scan_host(host)
            # Ghi log: port tìm được
            self.log.insert(tk.END, f"  Found ports: {list(ports.keys())}\n")
            results[host] = {}

            # --- Duyệt từng port ---
            port_items = list(ports.items())
            idx_port = 0
            while idx_port < len(port_items):
                port, svc = port_items[idx_port]
                # Lấy tên service và version (hoặc 'unknown' nếu trống)
                service = svc.get('service') or 'unknown'
                version = svc.get('version') or ''
                info = {'service': service, 'version': version, 'cves': []}

                # 3. Gọi NVD để tìm CVE theo keyword 'service version'
                keyword = f"{service} {version}".strip()
                if keyword:
                    self.log.insert(tk.END, f"  Query NVD for: {keyword}\n")
                    cves = self.nvd.search_cves(keyword)
                    # Nếu không tìm thấy CVE nào
                    if not cves:
                        self.log.insert(tk.END, f"    No CVEs found for {keyword}\n")
                    # Duyệt danh sách CVE và ghi log
                    idx_cve = 0
                    while idx_cve < len(cves):
                        cve = cves[idx_cve]
                        self.log.insert(
                            tk.END,
                            f"    Found CVE: {cve['id']} (Score: {cve.get('score')})\n"
                        )
                        info['cves'].append(cve)
                        idx_cve += 1

                # Lưu thông tin port vào kết quả
                results[host][port] = info
                idx_port += 1

            # Ghi log: hoàn thành host
            self.log.insert(tk.END, f"Done {host}.\n\n")
            idx_host += 1

        # 4. Gọi ReportGenerator xuất file TXT
        self.reporter.write(results)
        # Lưu kết quả cho xuất CSV
        self.last_results = results
        messagebox.showinfo("Info", "Scan hoàn tất và lưu report.txt")

    def export_csv(self):
        """
        Hàm xử lý xuất kết quả scan sang CSV khi nhấn nút.
        1. Kiểm tra tồn tại kết quả
        2. Chọn file lưu
        3. Ghi dữ liệu host-port-CVE vào CSV
        """
        # 1. Kiểm tra đã scan hay chưa
        if not self.last_results:
            messagebox.showwarning("Warning", "Chưa có kết quả để xuất CSV.")
            return

        # 2. Mở hộp thoại chọn nơi lưu file CSV
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')]
        )
        # Nếu hủy thì dừng
        if not path:
            return

        # 3. Ghi file CSV
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Ghi header
            writer.writerow([
                'Host', 'Port', 'Service', 'Version',
                'CVE ID', 'Severity', 'Score', 'Description', 'Exploit URLs'
            ])
            # Duyệt kết quả lưu trái cây tổ chức ra dòng CSV
            hosts_items = list(self.last_results.items())
            i = 0
            while i < len(hosts_items):
                host, ports = hosts_items[i]
                port_items = list(ports.items())
                j = 0
                while j < len(port_items):
                    port, info = port_items[j]
                    service = info['service']
                    version = info['version']
                    cve_list = info.get('cves', [])
                    # Nếu có CVEs, ghi mỗi CVE một dòng
                    if cve_list:
                        k = 0
                        while k < len(cve_list):
                            cve = cve_list[k]
                            writer.writerow([
                                host, port, service, version,
                                cve['id'], cve['severity'], cve.get('score') or '',
                                cve['desc'], ';'.join(cve.get('exploits', []))
                            ])
                            k += 1
                    else:
                        # Không có CVE, ghi trống phần CVE
                        writer.writerow([host, port, service, version, '', '', '', '', ''])
                    j += 1
                i += 1

        # Thông báo đã xuất xong
        messagebox.showinfo("Info", f"Đã xuất CSV: {path}")

    def run(self):
        # Bắt đầu vòng lặp sự kiện của GUI
        self.root.mainloop()
        