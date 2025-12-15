# gui.py
"""
GUI Controller (fixed hosts parsing + use NVDFetcherPRO.search_cve_keyword)
"""

import os
import datetime
import threading
import re
import csv
import queue
import ipaddress
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from PIL import Image, ImageTk
from collections import defaultdict

# imports attempt: prefer modules.* but fallback to local
try:
    from modules.scanner import Scanner, full_scan_pipeline
    from modules.nvd_fetcher import NVDFetcherPRO
    from modules.report import ReportGenerator
    from modules.config_manager import ConfigManager
    from modules.auth_linux_scanner import AuthLinuxScanner
    from modules.auth_windows_scanner import AuthWindowsScanner
    from modules.cpe_builder import build_cpe
except Exception:
    # fallback to local modules if not in package
    try:
        from modules.scanner import Scanner, full_scan_pipeline
    except Exception:
        from scanner import Scanner, full_scan_pipeline  # local fallback
    try:
        from modules.nvd_fetcher import NVDFetcherPRO
    except Exception:
        from nvd_fetcher import NVDFetcherPRO
    try:
        from modules.report import ReportGenerator
    except Exception:
        try:
            from report import ReportGenerator
        except Exception:
            ReportGenerator = None
    try:
        from modules.config_manager import ConfigManager
    except Exception:
        from config_manager import ConfigManager
    try:
        from modules.auth_linux_scanner import AuthLinuxScanner
    except Exception:
        from auth_linux_scanner import AuthLinuxScanner
    try:
        from modules.auth_windows_scanner import AuthWindowsScanner
    except Exception:
        from auth_windows_scanner import AuthWindowsScanner
    try:
        from modules.cpe_builder import build_cpe
    except Exception:
        from cpe_builder import build_cpe

# =====================================================================
# VALIDATION HOST/IP
# =====================================================================
def is_valid_host(host):
    """Check if host is valid IP or hostname"""
    ip_regex = r"^(?:\d{1,3}\.){3}\d{1,3}$"
    hostname_regex = (
        r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
        r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
    )
    return bool(re.match(ip_regex, host) or re.match(hostname_regex, host))


# =====================================================================
# MAIN GUI CONTROLLER
# =====================================================================
class GUIController:

    def __init__(self):

        # =======================
        # ROOT WINDOW (CHỈ 1 LẦN)
        # =======================
        self.root = tk.Tk()
        self.root.title("Công cụ quét lỗ hổng CVE")
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_dir, "images", "HQG.ico")
    
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                print("Không tìm thấy icon:", icon_path)
    
        except Exception as e:
            print("Không load được icon HQG:", e)
    
        self.root.geometry("880x760")

        # =======================
        # THREADING + QUEUE
        # =======================
        self.scan_lock = threading.Lock()
        self.log_queue = queue.Queue()

        # =======================
        # LOAD CONFIG + API KEY
        # =======================
        self.config = ConfigManager.load()
        self.api_key = self.config.get("nvd_api_key", "")

        # =======================
        # ENGINE MODULES
        # =======================
        self.scanner = Scanner()
        self.nvd = NVDFetcherPRO(api_key=self.api_key)
        self.reporter = ReportGenerator() if ReportGenerator else None

        # =======================
        # STATE
        # =======================
        self.last_results = {}
        self.scanning = False

        # =======================
        # BUILD GUI (LUÔN PHẢI CHẠY)
        # =======================
        self.build_gui()

        # =======================
        # START LOG POLLING
        # =======================
        self.root.after(120, self._poll_queue)

    
    # =================================================================
    # BUILD GUI
    # =================================================================
    def build_gui(self):

        # =======================
        # MAIN CANVAS + SCROLLBAR
        # =======================
        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.main_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        def on_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.main_frame.bind("<Configure>", on_configure)

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # =======================
        # HEADER (LOGO + TITLE)
        # =======================
        header = tk.Frame(self.main_frame, bg="#0b1220", height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg="#0b1220")
        header_inner.pack(fill="both", padx=24)

        # ---- LEFT: LOGO ----
        logo_frame = tk.Frame(header_inner, bg="#0b1220")
        logo_frame.pack(side="left", fill="y")

        try:
            logo_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "images", "HQG.png"
            )
            img = Image.open(logo_path)
            img.thumbnail((165, 50), Image.LANCZOS)  # giữ tỉ lệ
            self.logo_img = ImageTk.PhotoImage(img)

            tk.Label(
                logo_frame,
                image=self.logo_img,
                bg="#0b1220"
            ).pack(anchor="center", pady=20)

        except Exception:
            tk.Label(
                logo_frame,
                text="HQG",
                font=("Segoe UI", 26, "bold"),
                fg="#38bdf8",
                bg="#0b1220"
            ).pack(anchor="center", pady=18)

        # ---- RIGHT: TEXT ----
        text_frame = tk.Frame(header_inner, bg="#0b1220")
        text_frame.pack(side="left", fill="y", padx=(18, 0))

        tk.Label(
            text_frame,
            text="CÔNG CỤ QUÉT LỖ HỔNG CVE",
            font=("Segoe UI Semibold", 18),
            fg="white",
            bg="#0b1220"
        ).pack(anchor="w", pady=(20, 2))

        tk.Label(
            text_frame,
            text="NVD • CPE • CVSS • Authenticated Scan",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#0b1220"
        ).pack(anchor="w")

        ttk.Separator(self.main_frame, orient="horizontal").pack(fill="x")

        # =======================
        # CONTENT
        # =======================
        tk.Label(
            self.main_frame,
            text="Nhập IP/Host (mỗi dòng 1 host hoặc CIDR):",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=10, pady=8)

        self.host_box = tk.Text(self.main_frame, height=6, width=100)
        self.host_box.pack(padx=10)

        # Scan mode
        mode_frame = tk.Frame(self.main_frame)
        mode_frame.pack(padx=10, pady=6, anchor="w")

        tk.Label(mode_frame, text="Scan Mode:", font=("Arial", 10)).grid(row=0, column=0, sticky="w")
        self.scan_mode_var = tk.StringVar(value="Basic Scan")
        self.scan_mode_cb = ttk.Combobox(
            mode_frame,
            textvariable=self.scan_mode_var,
            state="readonly",
            width=24
        )
        self.scan_mode_cb["values"] = ("Basic Scan", "Authenticated Scan")
        self.scan_mode_cb.grid(row=0, column=1, padx=6)
        self.scan_mode_cb.bind("<<ComboboxSelected>>", lambda e: self._on_mode_change())

        # =======================
        # AUTH FRAME
        # =======================
        self.auth_frame = tk.LabelFrame(self.main_frame, text="Authenticated Scan Credentials")

        tk.Label(self.auth_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.auth_user = tk.Entry(self.auth_frame, width=30)
        self.auth_user.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(self.auth_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.auth_pass = tk.Entry(self.auth_frame, width=30, show="*")
        self.auth_pass.grid(row=1, column=1, padx=6, pady=4)

        tk.Label(self.auth_frame, text="Private Key (optional):").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        key_frame = tk.Frame(self.auth_frame)
        key_frame.grid(row=2, column=1, padx=6, pady=4, sticky="w")
        self.auth_key = tk.Entry(key_frame, width=32)
        self.auth_key.pack(side="left")
        tk.Button(key_frame, text="Browse", command=self._browse_key).pack(side="left", padx=4)

        tk.Label(self.auth_frame, text="Port:").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self.auth_port = tk.Entry(self.auth_frame, width=8)
        self.auth_port.insert(0, "22")
        self.auth_port.grid(row=3, column=1, padx=6, pady=4, sticky="w")

        tk.Label(self.auth_frame, text="Target OS:").grid(row=4, column=0, sticky="w", padx=6, pady=4)
        self.auth_os_var = tk.StringVar(value="Auto")
        self.auth_os_cb = ttk.Combobox(
            self.auth_frame,
            textvariable=self.auth_os_var,
            state="readonly",
            width=18
        )
        self.auth_os_cb["values"] = ("Auto", "Linux", "Windows")
        self.auth_os_cb.grid(row=4, column=1, padx=6, pady=4, sticky="w")

        # =======================
        # BUTTONS
        # =======================
        btn_frame = tk.Frame(self.main_frame)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Run Scan", command=self.start_scan_thread,
                  bg="#0ea5e9", fg="white", width=14).grid(row=0, column=0, padx=6)

        tk.Button(btn_frame, text="Export CSV", command=self.export_csv,
                  bg="#2563eb", fg="white", width=14).grid(row=0, column=1, padx=6)

        tk.Button(btn_frame, text="Clear Log",
                  command=lambda: self.log_box.delete("1.0", tk.END),
                  bg="#e67e22", fg="white", width=14).grid(row=0, column=2, padx=6)

        tk.Button(btn_frame, text="⚙ Settings", command=self.open_settings,
                  width=12).grid(row=0, column=3, padx=6)
        
        # =======================
        # PROGRESS BAR
        # =======================
        progress_frame = tk.Frame(self.main_frame)
        progress_frame.pack(fill="x", padx=10, pady=(8, 2))

        self.progress_var = tk.IntVar(value=0)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=280,         
            mode="determinate"
        )
        self.progress_bar.pack(side="left")

        self.progress_label = tk.Label(
            progress_frame,
            text="0%",
            font=("Arial", 9),
            width=4,
            anchor="w"
        )
        self.progress_label.pack(side="left", padx=(6, 0))
        

        # =======================
        # LOG OUTPUT
        # =======================
        tk.Label(
            self.main_frame,
            text="Log Output:",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=10)

        self.log_box = scrolledtext.ScrolledText(
            self.main_frame,
            width=110,
            height=18
        )
        self.log_box.pack(padx=10, pady=5)
        # =======================
        # LOG STYLES (COLOR LEVELS)
        # =======================
        self.log_box.tag_config("INFO", foreground="#1e40af")     # xanh dương
        self.log_box.tag_config("SUCCESS", foreground="#15803d")  # xanh lá
        self.log_box.tag_config("WARN", foreground="#b45309")     # cam
        self.log_box.tag_config("ERROR", foreground="#b91c1c")    # đỏ
        self.log_box.tag_config("SYSTEM", foreground="#475569")   # xám

    # =================================================================
    # QUEUE LOGGING
    # =================================================================
    def enqueue_log(self, text):
        try:
            self.log_queue.put_nowait(text)
        except queue.Full:
            pass

    def log(self, message, level="INFO"):
        icons = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅ ",
            "WARN": "⚠️ ",
            "ERROR": "❌ ",
            "SYSTEM": "🖥️ "
        }

        tag = level if level in icons else "INFO"
        prefix = icons.get(tag, "")
        self.enqueue_log((prefix + message, tag))


    def _poll_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()

                if isinstance(item, tuple):
                    text, tag = item
                    self.log_box.insert(tk.END, text + "\n", tag)
                else:
                    self.log_box.insert(tk.END, item)

                self.log_box.see(tk.END)
        except queue.Empty:
            pass

        self.root.after(120, self._poll_queue)

    def _browse_key(self):
        path = filedialog.askopenfilename(title="Select private key", filetypes=[("PEM files", "*.pem"), ("All files", "*.*")])
        if path:
            self.auth_key.delete(0, tk.END)
            self.auth_key.insert(0, path)

    def _on_mode_change(self):
        mode = self.scan_mode_var.get()
        if mode == "Authenticated Scan":
            if not getattr(self.auth_frame, "_packed", False):
                self.auth_frame.pack(fill="x", padx=10, pady=6)
                self.auth_frame._packed = True
        else:
            if getattr(self.auth_frame, "_packed", False):
                self.auth_frame.pack_forget()
                self.auth_frame._packed = False

        self.root.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    

    # =================================================================
    # SCAN THREAD CONTROL
    # =================================================================
    def start_scan_thread(self):
        self.progress_var.set(0)
        self.progress_label.config(text="0%")

        with self.scan_lock:
            if self.scanning:
                self.root.after(0, lambda: messagebox.showwarning("Warning", "Đang chạy scan. Vui lòng chờ."))
                return
            self.scanning = True
            self.last_results = {}

        t = threading.Thread(target=self.run_scan_wrapper, daemon=True)
        t.start()

    def run_scan_wrapper(self):
        try:
            self.run_scan()
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Lỗi scan: {e}"))
        finally:
            self.root.after(0, self._on_scan_complete)

    def _on_scan_complete(self):
        self.scanning = False
        try:
            messagebox.showinfo("Hoàn tất", "Scan đã hoàn tất!")
        except Exception:
            pass

    # =================================================================
    # FULL PIPELINE ADDON (CPE → CVE → REPORT)
    # =================================================================
    def run_full_pipeline(self, host, software_list=None):
        """
        Authenticated Scan:
        - Nhận danh sách software
        - Build CPE
        - Query CVE
        - Hiển thị log dạng tóm tắt (user-friendly)
        - Trả về raw results để export/report
        """
        try:
            # ===============================
            # HEADER
            # ===============================
            self.enqueue_log("\n" + "=" * 30)
            self.log(f"Phân tích CVE cho {host}", "SYSTEM")
            self.enqueue_log("=" * 30)

            # Fallback demo software (chỉ dùng khi test)
            if software_list is None:
                software_list = [
                    {"name": "nginx", "version": "1.18.0"},
                    {"name": "openssh", "version": "8.2"}
                ]

            # ===============================
            # RUN CORE PIPELINE
            # ===============================
            results = full_scan_pipeline(host, software_list)

            if not results:
                self.log(f"Không phát hiện CVE cho {host}", "SUCCESS")
                return None

            # ===============================
            # GROUP & SUMMARY
            # ===============================
            summary = defaultdict(list)

            for item in results:
                sw = item.get("software")
                ver = item.get("version")
                cid = item.get("cve_id")
                score = item.get("cvss_v3") or item.get("cvss_v2")

                if cid:
                    summary[(sw, ver)].append((cid, score))

            # ===============================
            # USER-FRIENDLY LOG OUTPUT
            # ===============================
            for (sw, ver), cves in summary.items():
                scores = [s for _, s in cves if isinstance(s, (int, float))]
                max_score = max(scores) if scores else "N/A"

                self.log(f"🧩 {sw} {ver}", "INFO")
                self.log(f"   ↳ Tổng số CVE: {len(cves)}", "WARN")
                self.log(f"   ↳ CVSS cao nhất: {max_score}", "WARN")

                # Show max 3 CVE để không spam
                for cid, score in cves[:3]:
                    score_txt = score if score is not None else "N/A"
                    self.log(f"      • {cid} (CVSS {score_txt})", "SYSTEM")

            # ===============================
            # FOOTER
            # ===============================
            self.log(f"Hoàn tất phân tích CVE cho {host}", "SUCCESS")
            self.enqueue_log("")
    
            return results
    
        except Exception as e:
            self.log(f"Lỗi khi phân tích CVE cho {host}: {e}", "ERROR")
            return None


    # =================================================================
    # SCAN LOGIC
    # =================================================================
    def run_scan(self):
        raw = self.host_box.get("1.0", tk.END).strip()
        hosts = []

        # =======================
        # PARSE HOSTS / CIDR
        # =======================
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            if "/" in line:
                try:
                    net = ipaddress.ip_network(line, strict=False)
                    hosts.extend([str(ip) for ip in net.hosts()])
                    continue
                except Exception:
                    self.log(f"CIDR không hợp lệ: {line}", "WARN")
                    continue

            if not is_valid_host(line):
                self.log(f"Host/IP không hợp lệ: {line}", "WARN")
                continue

            hosts.append(line)

        if not hosts:
            self.log("Không có host hợp lệ để quét", "ERROR")
            self.scanning = False
            return

        # =======================
        # INIT PROGRESS
        # =======================
        total_hosts = len(hosts)
        done_hosts = 0

        self.root.after(0, lambda: (
            self.progress_var.set(0),
            self.progress_label.config(text="0%")
        ))

        # =======================
        # HEADER LOG (ONCE)
        # =======================
        self.log("Bắt đầu quá trình quét lỗ hổng CVE", "SYSTEM")
        self.log(f"Tổng số host cần quét: {total_hosts}", "INFO")

        # =======================
        # MAIN LOOP
        # =======================
        for host in hosts:
            self.log(f"Đang quét host: {host}", "INFO")
            softwares = []

            # ==================================================
            # AUTHENTICATED SCAN
            # ==================================================
            if self.scan_mode_var.get() == "Authenticated Scan":
                user = self.auth_user.get().strip()
                pwd = self.auth_pass.get().strip()
                key = self.auth_key.get().strip() or None

                try:
                    port = int(self.auth_port.get().strip() or 22)
                except Exception:
                    port = 22

                target_os = self.auth_os_var.get()

                # -------- Linux --------
                if target_os in ("Auto", "Linux"):
                    try:
                        lscanner = AuthLinuxScanner(
                            host,
                            username=user,
                            password=pwd or None,
                            keyfile=key,
                            port=port
                        )
                        if lscanner.connect():
                            for pkg, ver in lscanner.get_installed_packages():
                                softwares.append({"name": pkg, "version": ver})
                            lscanner.close()
                    except Exception as e:
                        self.log(f"Không thể kết nối SSH tới {host}: {e}", "ERROR")

                # -------- Windows --------
                if target_os in ("Auto", "Windows") and not softwares:
                    try:
                        wscanner = AuthWindowsScanner(
                            host,
                            username=user,
                            password=pwd or None
                        )
                        if wscanner.connect():
                            for name, ver in wscanner.get_installed_software():
                                softwares.append({"name": name, "version": ver})
                    except Exception as e:
                        self.log(f"Lỗi kết nối WinRM tới {host}: {e}", "ERROR")

                # -------- PIPELINE --------
                if softwares:
                    self.run_full_pipeline(host, softwares)
                else:
                    self.log(f"Không thu thập được danh sách phần mềm từ {host}", "WARN")


            # ==================================================
            # BASIC SCAN (PORT → SERVICE → VERSION → CPE → CVE)
            # ==================================================
            else:
                try:
                    scan_result = self.scanner.basic_scan_with_cve(host)
                except Exception as e:
                    self.log(f"Lỗi khi quét host {host}: {e}", "ERROR")
                    continue

                self.last_results[host] = scan_result
                
                for port, info in scan_result.items():
                    service = info.get("service") or "unknown"
                    version = info.get("version") or "không rõ"

                    # 1️⃣ Log port/service/version
                    self.log(
                        f"{host} | port {port} | {service} | version {version}",
                        "INFO"
                    )

                    # 2️⃣ Log CVE nếu có
                    cves = info.get("cves", [])
                    if cves:
                        for cve in cves[:5]:  # giới hạn tránh spam
                            cve_id = (
                                cve.get("cve", {}).get("id")
                                or cve.get("cve_id")
                                or cve.get("id")
                            )
                            if cve_id:
                                self.log(
                                    f"    ↳ CVE phát hiện: {cve_id}",
                                    "WARN"
                                )


            # =======================
            # LOG FINISH HOST
            # =======================
            self.log(
                f"Đã quét xong host {host} ({done_hosts + 1}/{total_hosts})",
                level="SUCCESS"
            )

            # =======================
            # UPDATE PROGRESS
            # =======================
            done_hosts += 1
            percent = int((done_hosts / total_hosts) * 100)

            self.root.after(
                0,
                lambda p=percent: (
                    self.progress_var.set(p),
                    self.progress_label.config(text=f"{p}%")
                )
            )
        

        # =======================
        # FINISH
        # =======================
        self.root.after(0, lambda: (
            self.progress_var.set(100),
            self.progress_label.config(text="100%")
        ))

        self.scanning = False
    

    # =================================================================
    # EXPORT CSV
    # =================================================================
    def export_csv(self):
        if not self.last_results:
            self.root.after(0, lambda: messagebox.showwarning("Warning", "Chưa có kết quả để xuất CSV."))
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=os.getcwd(),
            filetypes=[("CSV file", "*.csv")]
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                writer.writerow([
                    "Host", "Port", "Service", "Version",
                    "CVE ID", "Severity", "Score", "Description", "Exploit URLs"
                ])

                for host, ports in self.last_results.items():
                    for port, info in ports.items():
                        if info.get("cves"):
                            for cve in info["cves"]:
                                writer.writerow([
                                    host, port,
                                    info.get("service"), info.get("version"),
                                    cve.get("id", ""),
                                    cve.get("severity", ""),
                                    cve.get("score", ""),
                                    cve.get("desc", ""),
                                    ";".join(cve.get("exploits", []))
                                ])
                        else:
                            writer.writerow([host, port, info.get("service"), info.get("version"), "", "", "", "", ""])

            self.root.after(0, lambda: messagebox.showinfo("Success", f"Đã xuất CSV: {path}"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Lỗi ghi CSV: {e}"))

    # =================================================================
    # SETTINGS
    # =================================================================
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Cài đặt API Key")
        win.geometry("400x200")

        tk.Label(win, text="NVD API Key:", font=("Arial", 12)).pack(pady=10)

        entry = tk.Entry(win, width=45)
        entry.insert(0, self.api_key)
        entry.pack()

        def save():
            new_key = entry.get().strip()
            if len(new_key) < 10:
                messagebox.showerror("Error", "API key không hợp lệ.")
                return

            self.config["nvd_api_key"] = new_key
            ConfigManager.save(self.config)

            self.api_key = new_key
            self.nvd = NVDFetcherPRO(api_key=self.api_key)

            self.root.after(0, lambda: messagebox.showinfo("Success", "Đã lưu API key!"))

            win.destroy()

        tk.Button(win, text="Lưu", command=save).pack(pady=15)

    # =================================================================
    # RUN GUI
    # =================================================================
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    GUIController().run()
