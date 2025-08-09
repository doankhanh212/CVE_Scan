# GUI cho công cụ quét CVE (tkinter)
# Mỗi dòng comment bằng # giải thích mục đích dòng lệnh/khối code

# Thư viện GUI từ Python chuẩn
import tkinter as tk  # Thao tác GUI cơ bản (cửa sổ, widget, v.v.)
from tkinter import filedialog, messagebox, scrolledtext
# - filedialog: mở hộp thoại lưu/mở file
# - messagebox: hiển thị hộp thoại thông báo/warning/error
# - scrolledtext: widget Text có scrollbar tích hợp (dùng cho log)

# Module nội bộ của dự án (modules/)
from modules.scanner import Scanner  # module quét port/service (phải có hàm scan_host)
from modules.nvd_fetcher import NVDFetcher  # module tìm CVE từ NVD
from modules.report import ReportGenerator  # module xuất report (report.txt, v.v.)

# Các thư viện chuẩn hữu ích
import csv        # ghi/đọc CSV
import threading  # chạy background thread để không block GUI
import os         # truy xuất biến môi trường, thao tác file
import re         # regex: kiểm tra định dạng IP/hostname
import queue      # queue để truyền message thread-safe từ background -> GUI
import time       # (tuỳ chọn) dùng cho sleep/delay nếu cần; có thể bỏ nếu không dùng

# ----------------------------------------
# Hàm kiểm tra IP hoặc hostname hợp lệ
# ----------------------------------------
def is_valid_host(host):
    """
    Kiểm tra xem input có phải IP (dạng x.x.x.x) hoặc hostname hợp lệ không.
    Trả về True nếu hợp lệ, False nếu không.
    """
    # Regex đơn giản cho IPv4 (không kiểm tra 0-255 chặt chẽ ở đây)
    ip_regex = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    # Regex cho hostname theo RFC-ish (độ dài tổng <=253, các label 1-63 ký tự, không bắt đầu/ket thúc bằng '-')
    hostname_regex = (
        r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
        r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
    )
    # Dùng bool(...) để đảm bảo trả về True/False, không phải match object
    return bool(re.match(ip_regex, host) or re.match(hostname_regex, host))


# ----------------------------------------
# Lớp điều khiển GUI
# ----------------------------------------
class GUIController:
    def __init__(self):
        # Khởi tạo cửa sổ chính
        self.root = tk.Tk()
        self.root.title("Công cụ quét lỗ hổng CVE")

        # Khởi tạo các module logic: Scanner, NVDFetcher, ReportGenerator
        self.scanner = Scanner()

        # Lấy NVD API key từ biến môi trường để bảo mật.
        # KHÔNG đặt API key trong code nguồn; nếu không có ENV, NVDFetcher có thể hoạt động ở chế độ không-auth tuỳ implementation.
        api_key = os.environ.get("b869e2cd-3a86-4cb0-bf38-88a10671c3c4")
        self.nvd = NVDFetcher(api_key=api_key)

        # Module xuất báo cáo (viết report.txt)
        self.reporter = ReportGenerator()

        # Queue dùng để gửi log messages từ background thread về main thread (thread-safe)
        self.log_queue = queue.Queue()

        # Widget nhập danh sách host (mỗi dòng 1 host)
        tk.Label(self.root, text="Nhập IP/Host (mỗi dòng 1 host):")\
            .grid(row=0, column=0, columnspan=4, sticky='w')
        # Text widget để người dùng nhập nhiều dòng host
        self.hosts_text = tk.Text(self.root, height=5, width=60)
        self.hosts_text.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

        # Nút chạy, xuất CSV, xóa log
        # Lưu reference button để sau này enable/disable khi scan
        self.run_button = tk.Button(self.root, text="Run Scan", command=self.run_scan_thread)
        self.run_button.grid(row=2, column=0, pady=5)

        self.export_button = tk.Button(self.root, text="Export CSV", command=self.export_csv)
        self.export_button.grid(row=2, column=1, pady=5)

        self.clear_button = tk.Button(self.root, text="Clear Log", command=self.clear_log)
        self.clear_button.grid(row=2, column=2, pady=5)

        # ScrolledText để hiển thị log (chỉ cập nhật từ main thread)
        self.log = scrolledtext.ScrolledText(self.root, height=15, width=70, state='normal')
        self.log.grid(row=3, column=0, columnspan=4, padx=5, pady=5)

        # Lưu kết quả lần cuối để export CSV sau này
        self.last_results = {}

        # Flag theo dõi đang quét hay không (tránh chạy chồng)
        self.scanning = False

        # Bắt đầu polling queue để cập nhật log (sẽ gọi _poll_log_queue mỗi 200ms)
        self.root.after(200, self._poll_log_queue)

    # -----------------------------
    # Queue log helper
    # -----------------------------
    def enqueue_log(self, message):
        """
        Đưa message vào queue từ thread background.
        Thêm newline nếu message chưa có.
        """
        if not message.endswith("\n"):
            message = message + "\n"
        self.log_queue.put(message)

    def _poll_log_queue(self):
        """
        Hàm chạy trên main thread (được gọi định kỳ bằng root.after).
        Nó lấy các message từ queue và chèn vào ScrolledText.
        Điều này đảm bảo GUI chỉ được cập nhật từ main thread (an toàn).
        """
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log.insert(tk.END, msg)
                self.log.see(tk.END)  # scroll xuống cuối
        except queue.Empty:
            pass
        # Lên lịch gọi lại sau 200ms
        self.root.after(200, self._poll_log_queue)

    # -----------------------------
    # Các hành động UI cơ bản
    # -----------------------------
    def clear_log(self):
        """Xóa nội dung log (chạy trên main thread)."""
        self.log.delete('1.0', tk.END)

    def run_scan_thread(self):
        """
        Khởi động background thread để chạy scan.
        - Kiểm tra flag self.scanning để tránh chạy đồng thời nhiều thread.
        - Disable nút khi đang quét.
        """
        if self.scanning:
            messagebox.showwarning("Warning", "Đang quét rồi, vui lòng chờ.")
            return

        # Disable nút để tránh click tiếp
        self.run_button.config(state='disabled')
        self.export_button.config(state='disabled')
        self.scanning = True

        # Tạo thread daemon để tự kết thúc khi ứng dụng đóng
        t = threading.Thread(target=self.run_scan, daemon=True)
        t.start()

    # -----------------------------
    # Quét và thu thập kết quả
    # -----------------------------
    def scan_and_collect(self, hosts):
        """
        Quét từng host bằng Scanner.scan_host và thu thập thông tin port/service.
        Trả về dict kết quả có cấu trúc:
        { host: { port: { 'service': ..., 'version': ..., 'cves': [ ... ] } } }
        """
        results = {}
        for host in hosts:
            # Gửi log từ background thread bằng enqueue_log
            self.enqueue_log(f"Scanning {host}...")
            try:
                # scan_host nên trả về dict kiểu {port: {'service':..., 'version':...}, ...}
                ports = self.scanner.scan_host(host)
            except Exception as e:
                # Khi có lỗi quét host, log rồi tiếp tục host khác
                self.enqueue_log(f"  Scan error: {e}")
                continue

            # Log danh sách port tìm được
            self.enqueue_log(f"  Found ports: {list(ports.keys())}")
            # Thu thập thông tin từng port (gọi hàm phụ)
            results[host] = self.collect_port_info(host, ports)
            self.enqueue_log(f"Done {host}.\n")
        return results

    def collect_port_info(self, host, ports):
        """
        Với mỗi port, lấy thông tin service/version và truy vấn NVDFetcher để tìm CVE.
        Trả về dict port_results cho host đó.
        """
        port_results = {}
        for port, svc in ports.items():
            # Lấy service/version, nếu thiếu thì gán 'unknown' hoặc rỗng
            service = svc.get('service') or 'unknown'
            version = svc.get('version') or ''
            info = {'service': service, 'version': version, 'cves': []}

            # Tạo keyword tìm kiếm như "nginx 1.18.0" hoặc "ssh"
            keyword = f"{service} {version}".strip()
            if keyword:
                self.enqueue_log(f"  Query NVD for: {keyword}")
                try:
                    # search_cves có thể gọi API/IO và trả về list các dict CVE
                    cves = self.nvd.search_cves(keyword)
                except Exception as e:
                    # Nếu NVDFetcher lỗi, log và tiếp
                    self.enqueue_log(f"    NVD error: {e}")
                    cves = []

                if not cves:
                    self.enqueue_log(f"    No CVEs found for {keyword}")

                # Thêm từng CVE vào info và log
                for cve in cves:
                    # cve kỳ vọng là dict với keys: 'id', 'severity', 'score', 'desc', 'exploits'
                    self.enqueue_log(f"    Found CVE: {cve.get('id')} (Score: {cve.get('score')})")
                    info['cves'].append(cve)
            # Lưu kết quả port
            port_results[port] = info
        return port_results

    # -----------------------------
    # Hàm chạy scan trong background thread
    # -----------------------------
    def run_scan(self):
        """
        Hàm này chạy trong background thread:
        - Đọc hosts từ Text widget (ở một số cấu hình có thể lấy trước, nhưng đọc ở đây thông thường OK)
        - Validate host, build host list
        - Gọi scan_and_collect để quét
        - Ghi report bằng ReportGenerator (I/O) trong background
        - Đưa thông báo hoàn tất lên main thread bằng root.after
        - Cleanup: enable lại các nút
        """
        # Lấy raw text (các thao tác GUI đơn giản thường an toàn để đọc trong thread, nhưng tốt nhất lấy trước)
        raw = self.hosts_text.get('1.0', tk.END).strip()
        host_lines = raw.splitlines()
        hosts = []
        for line in host_lines:
            line = line.strip()
            if line:
                if not is_valid_host(line):
                    # Lưu log host không hợp lệ (không show dialog từ background)
                    self.enqueue_log(f"Host không hợp lệ: {line}")
                    continue
                hosts.append(line)

        if not hosts:
            # Hiển thị message box từ main thread qua root.after
            self.root.after(0, lambda: messagebox.showwarning("Warning", "Vui lòng nhập ít nhất một host hợp lệ."))
            # Enable lại nút qua main thread
            self.root.after(0, self._scan_finished_cleanup)
            return

        # Xóa log (thực hiện trên main thread)
        self.root.after(0, lambda: self.log.delete('1.0', tk.END))

        # Thực hiện quét
        results = self.scan_and_collect(hosts)

        # Ghi report (I/O) — an toàn thực hiện trong background thread
        try:
            self.reporter.write(results)
            self.enqueue_log("Report saved to report.txt")
        except Exception as e:
            self.enqueue_log(f"Error writing report: {e}")

        # Lưu kết quả để export CSV
        self.last_results = results

        # Thông báo hoàn tất — show dialog trên main thread
        self.root.after(0, lambda: messagebox.showinfo("Info", "Scan hoàn tất và lưu report.txt"))

        # Cleanup trên main thread (bật lại nút, reset flag)
        self.root.after(0, self._scan_finished_cleanup)

    def _scan_finished_cleanup(self):
        """
        Chạy trên main thread để enable lại các nút và reset flag self.scanning.
        Dùng root.after để schedule từ background nếu cần.
        """
        self.run_button.config(state='normal')
        self.export_button.config(state='normal')
        self.scanning = False

    # -----------------------------
    # Export CSV
    # -----------------------------
    def export_csv(self):
        """
        Lấy self.last_results và ghi ra CSV theo cấu trúc:
        Host, Port, Service, Version, CVE ID, Severity, Score, Description, Exploit URLs
        """
        if not self.last_results:
            messagebox.showwarning("Warning", "Chưa có kết quả để xuất CSV.")
            return

        # Hỏi đường dẫn lưu file
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')]
        )
        if not path:
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Header CSV
                writer.writerow([
                    'Host', 'Port', 'Service', 'Version',
                    'CVE ID', 'Severity', 'Score', 'Description', 'Exploit URLs'
                ])
                # Viết từng dòng
                for host, ports in self.last_results.items():
                    self.write_csv_rows(writer, host, ports)
            messagebox.showinfo("Info", f"Đã xuất CSV: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi ghi CSV: {e}")

    def write_csv_rows(self, writer, host, ports):
        """
        Ghi các dòng CSV cho một host:
        - Nếu port có nhiều CVE thì ghi nhiều dòng (1 dòng / 1 CVE)
        - Nếu không có CVE, ghi 1 dòng với các trường CVE rỗng
        """
        for port, info in ports.items():
            service = info.get('service', '')
            version = info.get('version', '')
            cve_list = info.get('cves', [])
            if cve_list:
                for cve in cve_list:
                    writer.writerow([
                        host, port, service, version,
                        cve.get('id', ''), cve.get('severity', ''), cve.get('score', '') or '',
                        cve.get('desc', ''), ';'.join(cve.get('exploits', []))
                    ])
            else:
                writer.writerow([host, port, service, version, '', '', '', '', ''])

    # -----------------------------
    # Chạy GUI
    # -----------------------------
    def run(self):
        """Bắt đầu vòng lặp chính của Tkinter."""
        self.root.mainloop()


# -----------------------------
# Nếu file này được chạy trực tiếp
# -----------------------------
if __name__ == "__main__":
    app = GUIController()
    app.run()
