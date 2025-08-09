import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from modules.scanner import Scanner
from modules.nvd_fetcher import NVDFetcher
from modules.report import ReportGenerator
import csv
import threading
import os
import re

def is_valid_host(host):
    # Kiểm tra IP hoặc hostname hợp lệ
    ip_regex = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    hostname_regex = r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
    return re.match(ip_regex, host) or re.match(hostname_regex, host)

class GUIController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Công cụ quét lỗ hổng CVE")

        self.scanner = Scanner()
        api_key = os.environ.get("NVD_API_KEY", "b869e2cd-3a86-4cb0-bf38-88a10671c3c4")
        self.nvd = NVDFetcher(api_key=api_key)
        self.reporter = ReportGenerator()

        tk.Label(self.root, text="Nhập IP/Host (mỗi dòng 1 host):")\
            .grid(row=0, column=0, columnspan=4, sticky='w')
        self.hosts_text = tk.Text(self.root, height=5, width=60)
        self.hosts_text.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

        tk.Button(self.root, text="Run Scan", command=self.run_scan_thread)\
            .grid(row=2, column=0, pady=5)
        tk.Button(self.root, text="Export CSV", command=self.export_csv)\
            .grid(row=2, column=1, pady=5)
        tk.Button(self.root, text="Clear Log", command=self.clear_log)\
            .grid(row=2, column=2, pady=5)

        # Thêm scrolledtext cho log
        self.log = scrolledtext.ScrolledText(self.root, height=15, width=70)
        self.log.grid(row=3, column=0, columnspan=4, padx=5, pady=5)

        self.last_results = {}

    def clear_log(self):
        self.log.delete('1.0', tk.END)

    def run_scan_thread(self):
        # Chạy scan ở thread phụ để không treo GUI
        t = threading.Thread(target=self.run_scan)
        t.daemon = True
        t.start()

    def scan_and_collect(self, hosts):
        """Quét các host và thu thập kết quả, trả về dict kết quả."""
        results = {}
        for host in hosts:
            self.log.insert(tk.END, f"Scanning {host}...\n")
            self.log.see(tk.END)
            try:
                ports = self.scanner.scan_host(host)
            except Exception as e:
                self.log.insert(tk.END, f"  Scan error: {e}\n")
                continue
            self.log.insert(tk.END, f"  Found ports: {list(ports.keys())}\n")
            results[host] = self.collect_port_info(host, ports)
            self.log.insert(tk.END, f"Done {host}.\n\n")
            self.log.see(tk.END)
        return results

    def collect_port_info(self, host, ports):
        """Thu thập thông tin từng port và CVE cho một host."""
        port_results = {}
        for port, svc in ports.items():
            service = svc.get('service') or 'unknown'
            version = svc.get('version') or ''
            info = {'service': service, 'version': version, 'cves': []}
            keyword = f"{service} {version}".strip()
            if keyword:
                self.log.insert(tk.END, f"  Query NVD for: {keyword}\n")
                self.log.see(tk.END)
                try:
                    cves = self.nvd.search_cves(keyword)
                except Exception as e:
                    self.log.insert(tk.END, f"    NVD error: {e}\n")
                    cves = []
                if not cves:
                    self.log.insert(tk.END, f"    No CVEs found for {keyword}\n")
                for cve in cves:
                    self.log.insert(
                        tk.END,
                        f"    Found CVE: {cve['id']} (Score: {cve.get('score')})\n"
                    )
                    info['cves'].append(cve)
            port_results[port] = info
        return port_results

    def run_scan(self):
        raw = self.hosts_text.get('1.0', tk.END).strip()
        host_lines = raw.splitlines()
        hosts = []
        for line in host_lines:
            line = line.strip()
            if line:
                if not is_valid_host(line):
                    self.log.insert(tk.END, f"Host không hợp lệ: {line}\n")
                    continue
                hosts.append(line)

        if not hosts:
            messagebox.showwarning("Warning", "Vui lòng nhập ít nhất một host hợp lệ.")
            return

        self.log.delete('1.0', tk.END)
        results = self.scan_and_collect(hosts)
        self.reporter.write(results)
        self.last_results = results
        messagebox.showinfo("Info", "Scan hoàn tất và lưu report.txt")

    def export_csv(self):
        if not self.last_results:
            messagebox.showwarning("Warning", "Chưa có kết quả để xuất CSV.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')]
        )
        if not path:
            return

        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Host', 'Port', 'Service', 'Version',
                'CVE ID', 'Severity', 'Score', 'Description', 'Exploit URLs'
            ])
            for host, ports in self.last_results.items():
                self.write_csv_rows(writer, host, ports)
        messagebox.showinfo("Info", f"Đã xuất CSV: {path}")

    def write_csv_rows(self, writer, host, ports):
        """Ghi các dòng CSV cho một host."""
        for port, info in ports.items():
            service = info['service']
            version = info['version']
            cve_list = info.get('cves', [])
            if cve_list:
                for cve in cve_list:
                    writer.writerow([
                        host, port, service, version,
                        cve['id'], cve['severity'], cve.get('score') or '',
                        cve['desc'], ';'.join(cve.get('exploits', []))
                    ])
            else:
                writer.writerow([host, port, service, version, '', '', '', '', ''])

    def run(self):
        self.root.mainloop()