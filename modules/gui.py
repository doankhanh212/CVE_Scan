# gui.py
"""
GUI Controller (fixed hosts parsing + use NVDFetcherPRO.search_cve_keyword)
"""


import os
import sys
import shutil
import subprocess
import threading
import re
import csv
import queue
import ipaddress
import socket
import datetime
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


# imports attempt: prefer modules.* but fallback to local
from modules.scan_manager import ScanManager
from modules.config_manager import ConfigManager
from modules.report import html_report
from modules.report import pdf_report

# =============================================================
# Filtering constants for UI/CSV noise reduction
# =============================================================
DEFAULT_MIN_SEVERITY = "LOW"
# Show all CVEs regardless of publish year by default
DEFAULT_MIN_YEAR = 0
HIDE_SCROLLBARS = True

# Skip platform/framework packages that tend to explode CVE volume
SKIP_KEYWORDS = [
    # .NET / VS / SDK noise
    ".net", "asp.net", "targeting pack", "desktop runtime", "host fx resolver",
    "workload", "manifest", "templates", "apphost pack", "runtime pack",
    "windows sdk", "winrt intellisense", "intellisense", "redistributable",
    "visual studio", "vs ", "visual c++", "maui", "xamarin", "toolset",
    "framework", "diagnostic pack",
    # Python bundle components (avoid dozens of subpackages)
    "python ", "python3", "pip", "tcl", "standard library", "development libraries",
    "core interpreter", "executables", "test suite", "documentation", "add to path",
    # Android/SDK extras
    "android runtime", "android.sdk", "android ref", "android.svc"
]

SEVERITY_RANK = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# =====================================================================
# VALIDATION HOST/IP
# =====================================================================
def is_valid_host(host):
    """Check if host is valid IP, CIDR, or hostname"""
    # Check for CIDR notation
    if "/" in host:
        try:
            ipaddress.ip_network(host, strict=False)
            return True
        except Exception:
            return False
    
    # Check for plain IP
    ip_regex = r"^(?:\d{1,3}\.){3}\d{1,3}$"
    if re.match(ip_regex, host):
        return True
    
    # Check for hostname
    hostname_regex = (
        r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
        r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
    )
    return bool(re.match(hostname_regex, host))


def _version_from_cpe(cpe: str | None) -> str:
    """Best-effort version extraction from a CPE 2.3 string."""
    if not cpe or not isinstance(cpe, str):
        return ""
    parts = cpe.split(":")
    # cpe:2.3:part:vendor:product:version:...
    if len(parts) >= 6:
        candidate = parts[5]
        if candidate and candidate not in {"*", "-"}:
            return candidate
    return ""


# =====================================================================
# MAIN GUI CONTROLLER
# =====================================================================
class GUIController:

    def __init__(self):

        # =======================
        # ROOT WINDOW (CHỈ 1 LẦN)
        # =======================
        try:
            # try to create a real Tk root; this will fail in environments
            # where Tcl/Tk is not installed (e.g., some CI or headless tests)
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
            self._has_tk = True
        except Exception as e:
            # Running without a usable Tk installation (headless/test mode).
            # Avoid building GUI or scheduling periodic callbacks that assume widgets.
            print("Tk initialization failed; running in headless mode:", e)
            self.root = None
            self._has_tk = False

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
        # =======================
        # STATE
        # =======================
        self.last_results = {}
        self.scanning = False
        self.stop_event = threading.Event()
        self.stopping = False
        # Ensure progress counters exist even in headless mode
        self._ping_percent = 0
        self._scan_percent = 0
        self._alive_count = 0

        # =======================
        # BUILD GUI (LUÔN PHẢI CHẠY)
        # =======================
        if self._has_tk:
            self.build_gui()

            # apply initial layout based on default scan mode
            try:
                self._on_mode_change()
            except Exception:
                pass

            # =======================
            # START LOG POLLING
            # =======================
            self.root.after(120, self._poll_queue)
        else:
            # Headless mode: create minimal stubs so tests can interact
            # with controller without real Tk widgets.
            class _HostBoxStub:
                def __init__(self):
                    self._text = ""
                def delete(self, start, end=None):
                    self._text = ""
                def insert(self, start, text):
                    self._text += str(text or "")
                def get(self, start, end):
                    return self._text

            class _SimpleVar:
                def __init__(self, value=None):
                    self._val = value
                def get(self):
                    return self._val
                def set(self, v):
                    self._val = v

            self.host_box = _HostBoxStub()
            # Defaults mirror GUI options but remain flexible for tests
            self.scan_mode_var = _SimpleVar("Quét không xác thực")
            self.input_mode_var = _SimpleVar("IP/CIDR")
            # Do not build the full GUI or schedule polling in headless mode

    def on_progress(self, phase, percent, message=None):
        """
        phase: 'ping' | 'scan'
        NOTE: Only `scan` updates the main overall progress bar that the user sees.
        Ping progress is kept for internal use but is not shown in the overall bar.
        """

        def _update():
            if phase == "ping":
                # keep ping percent internally but do not update the overall UI
                self._ping_percent = int(percent)
                # update Hosts Alive KPI if message carries alive count
                try:
                    if isinstance(message, dict) and "alive" in message:
                        alive_count = int(message.get("alive", 0))
                        self._alive_count = alive_count
                        self.kpi_cards["hosts_alive"].config(text=str(alive_count))
                except Exception:
                    pass
                return

            elif phase == "scan":
                self._scan_percent = int(percent)

            # compute overall percent based on scan progress only
            overall = int(self._scan_percent)
            self.overall_var.set(overall)
            self.overall_label.config(text=f"{overall}%")

            # enable export when complete
            if overall >= 100:
                try:
                    if hasattr(self, "export_menu_btn"):
                        self.export_menu_btn.config(state=tk.NORMAL)
                except Exception:
                    pass

        # schedule UI update safely
        try:
            self.root.after(0, _update)
        except Exception:
            # if root.after isn't available (tests), call inline
            _update()

    
    # =================================================================
    # BUILD GUI
    # =================================================================
    def build_gui(self):
        # Dark SOC theme palette
        self.theme = {
            "bg": "#0b1220",
            "panel": "#0f172a",
            "card": "#111827",
            "text": "#e5e7eb",
            "sub": "#9ca3af",
            "accent": "#38bdf8",
            "accent2": "#22d3ee",
            "muted": "#1f2937",
            "button": "#1f2937",
            "button_fg": "#e5e7eb"
        }

        # Apply base colors
        self.root.configure(bg=self.theme["bg"])
        self.root.option_add("*Background", self.theme["bg"])
        self.root.option_add("*Foreground", self.theme["text"])
        self.root.option_add("*Font", ("Segoe UI", 10))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Treeview",
            background=self.theme["panel"],
            fieldbackground=self.theme["panel"],
            foreground=self.theme["text"],
            rowheight=22,
            bordercolor=self.theme["muted"],
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=self.theme["card"],
            foreground=self.theme["text"],
            bordercolor=self.theme["muted"],
            borderwidth=1
        )
        style.map("Treeview", background=[("selected", "#1d4ed8")])
        style.configure(
            "Blue.Horizontal.TProgressbar",
            troughcolor=self.theme["panel"],
            background=self.theme["accent"]
        )

        # =======================
        # MAIN CANVAS + SCROLLBAR
        # =======================
        container = tk.Frame(self.root, bg=self.theme["bg"])
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0, bg=self.theme["bg"], borderwidth=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        if not HIDE_SCROLLBARS:
            scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.main_frame = tk.Frame(self.canvas, bg=self.theme["bg"])
        self._main_window = self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        def on_configure(event):
            # keep scrollregion and stretch inner frame to canvas width for responsive resize
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            try:
                self.canvas.itemconfigure(self._main_window, width=event.width)
            except Exception:
                pass

        self.main_frame.bind("<Configure>", on_configure)

        # ensure width syncs when the outer canvas resizes (e.g., window resize)
        def on_canvas_configure(event):
            try:
                self.canvas.itemconfigure(self._main_window, width=event.width)
            except Exception:
                pass

        self.canvas.bind("<Configure>", on_canvas_configure)

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Bind globally to allow scrolling anywhere
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
            text="Developed by Đoàn Khánh • Security Assessment Tool",
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
            font=("Arial", 11, "bold"),
            bg=self.theme["bg"],
            fg=self.theme["text"]
        ).pack(anchor="w", padx=10, pady=8)

        # container to allow side-by-side host input and credentials when authenticated
        self.host_auth_container = tk.Frame(self.main_frame, bg=self.theme["bg"])
        self.host_auth_container.pack(fill="both", expand=True, padx=10)
        self.host_auth_container.rowconfigure(0, weight=1)
        self.host_auth_container.columnconfigure(0, weight=1)
        self.host_auth_container.columnconfigure(1, weight=0)

        self.host_box_frame = tk.Frame(self.host_auth_container, bg=self.theme["panel"], bd=1, relief="solid")
        self.host_box_frame.grid(row=0, column=0, sticky="nsew")

        self.host_box = tk.Text(self.host_box_frame, height=3, width=50, bg=self.theme["panel"], fg=self.theme["text"], insertbackground=self.theme["accent"], borderwidth=0, relief="flat")
        host_scrollbar = tk.Scrollbar(self.host_box_frame, command=self.host_box.yview)
        self.host_box.configure(yscrollcommand=host_scrollbar.set)
        self.host_box.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        if not HIDE_SCROLLBARS:
            host_scrollbar.pack(side="right", fill="y")

        # Scan mode and Input mode
        mode_frame = tk.Frame(self.main_frame, bg=self.theme["bg"])
        mode_frame.pack(padx=10, pady=6, anchor="w")

        # Input mode (IP/CIDR vs Hostname)
        tk.Label(mode_frame, text="Input Mode:", font=("Arial", 10), bg=self.theme["bg"], fg=self.theme["text"]).grid(row=0, column=0, sticky="w", padx=(0,6))
        self.input_mode_var = tk.StringVar(self.root, value="IP/CIDR")
        self.input_mode_cb = ttk.Combobox(
            mode_frame,
            textvariable=self.input_mode_var,
            state="readonly",
            width=20
        )
        self.input_mode_cb["values"] = ("IP/CIDR", "Hostname (Domain)")
        self.input_mode_cb.grid(row=0, column=1, padx=6)

        # Scan mode (Authenticated vs Unauthenticated)
        tk.Label(mode_frame, text="Scan Mode:", font=("Arial", 10), bg=self.theme["bg"], fg=self.theme["text"]).grid(row=0, column=2, sticky="w", padx=(12,6))
        self.scan_mode_var = tk.StringVar(self.root, value="Quét không xác thực")
        self.scan_mode_cb = ttk.Combobox(
            mode_frame,
            textvariable=self.scan_mode_var,
            state="readonly",
            width=24
        )
        self.scan_mode_cb["values"] = ("Quét không xác thực", "Quét có xác thực")
        self.scan_mode_cb.grid(row=0, column=3, padx=6)
        self.scan_mode_cb.bind("<<ComboboxSelected>>", lambda e: self._on_mode_change())

        # =======================
        # AUTH FRAME (initially hidden; shown side-by-side on Authenticated mode)
        self.auth_wrapper = tk.Frame(self.host_auth_container, bg=self.theme["bg"])
        self.auth_frame = tk.LabelFrame(self.auth_wrapper, text="Thông tin xác thực", bg=self.theme["panel"], fg=self.theme["text"], bd=1, relief="solid")
        self.auth_frame.pack(fill="both", expand=True, padx=6, pady=2)

        tk.Label(self.auth_frame, text="Username:", bg=self.theme["panel"], fg=self.theme["text"]).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.auth_user = tk.Entry(self.auth_frame, width=26)
        self.auth_user.grid(row=0, column=1, padx=6, pady=4)

        tk.Label(self.auth_frame, text="Password:", bg=self.theme["panel"], fg=self.theme["text"]).grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.auth_pass = tk.Entry(self.auth_frame, width=26, show="*")
        self.auth_pass.grid(row=1, column=1, padx=6, pady=4)

        tk.Label(self.auth_frame, text="Private Key (optional):", bg=self.theme["panel"], fg=self.theme["text"]).grid(row=2, column=0, sticky="w", padx=6, pady=4)
        key_frame = tk.Frame(self.auth_frame, bg=self.theme["panel"])
        key_frame.grid(row=2, column=1, padx=6, pady=4, sticky="w")
        self.auth_key = tk.Entry(key_frame, width=24)
        self.auth_key.pack(side="left")
        tk.Button(key_frame, text="Browse", command=self._browse_key, bg=self.theme["button"], fg=self.theme["button_fg"], activebackground=self.theme["muted"], relief="flat").pack(side="left", padx=4)

        tk.Label(self.auth_frame, text="Port:", bg=self.theme["panel"], fg=self.theme["text"]).grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self.auth_port = tk.Entry(self.auth_frame, width=8)
        self.auth_port.insert(0, "22")
        self.auth_port.grid(row=3, column=1, padx=6, pady=4, sticky="w")

        tk.Label(self.auth_frame, text="Target OS:", bg=self.theme["panel"], fg=self.theme["text"]).grid(row=4, column=0, sticky="w", padx=6, pady=4)
        self.auth_os_var = tk.StringVar(self.root, value="Auto")
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
        btn_frame = tk.Frame(self.main_frame, bg=self.theme["bg"])
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Bắt đầu quét", command=self.start_scan_thread,
              bg="#2563eb", fg="white", activebackground="#1d4ed8", width=12, relief="flat").grid(row=0, column=0, padx=6)

        # Export menu (CSV/HTML/PDF)
        self.export_menu_btn = tk.Menubutton(btn_frame, text="Xuất báo cáo", bg=self.theme["button"], fg=self.theme["button_fg"], activebackground=self.theme["muted"], relief="flat", width=11)
        self.export_menu = tk.Menu(self.export_menu_btn, tearoff=0, bg=self.theme["panel"], fg=self.theme["text"], activebackground=self.theme["muted"], activeforeground=self.theme["text"])
        self.export_menu.add_command(label="Xuất CSV", command=self.export_csv)
        self.export_menu.add_command(label="Xuất HTML", command=self.export_html)
        self.export_menu.add_command(label="Xuất PDF", command=self.export_pdf)
        self.export_menu_btn.config(menu=self.export_menu)
        self.export_menu_btn.grid(row=0, column=1, padx=6)
        self.export_menu_btn.config(state=tk.DISABLED)

        tk.Button(btn_frame, text="Xóa log",
              command=lambda: self.log_box.delete("1.0", tk.END),
              bg="#e67e22", fg="white", activebackground="#d97706", width=11, relief="flat").grid(row=0, column=2, padx=6)

        # Use a safe handler so missing attributes won't raise during button creation
        tk.Button(btn_frame, text="⚙ Cài đặt", command=self._handle_open_settings,
              width=9, bg=self.theme["button"], fg=self.theme["button_fg"], activebackground=self.theme["muted"], relief="flat").grid(row=0, column=3, padx=6)

        # One-click setup (auto install required tools)
        tk.Button(
            btn_frame,
            text="🛠 Tự động cài đặt",
            command=self.start_auto_setup_thread,
            width=16,
            bg=self.theme["button"],
            fg=self.theme["button_fg"],
            activebackground=self.theme["muted"],
            relief="flat"
        ).grid(row=0, column=4, padx=6)

        # Help / guide button
        tk.Button(
            btn_frame,
            text="❔ Hướng dẫn",
            command=self.open_help_dialog,
            width=11,
            bg=self.theme["button"],
            fg=self.theme["button_fg"],
            activebackground=self.theme["muted"],
            relief="flat"
        ).grid(row=0, column=5, padx=6)

        
        # =======================
        # KPI SUMMARY & HOSTS / SERVICES VIEW
        # =======================
        # KPI cards
        summary_frame = tk.Frame(self.main_frame, bg=self.theme["bg"])
        summary_frame.pack(fill="x", padx=10, pady=(8, 4))

        # KPI cards
        self.kpi_cards = {}
        for idx, (title, var_name) in enumerate([
            ("Tổng host", "hosts_alive"),
            ("Host đã quét", "hosts_scanned"),
            ("Dịch vụ mở", "open_services"),
            ("CVE phát hiện", "cves_found")
        ]):
            card = tk.Frame(summary_frame, bd=1, relief="ridge", padx=12, pady=8, bg=self.theme["card"], highlightbackground=self.theme["muted"], highlightcolor=self.theme["muted"], highlightthickness=1)
            card.grid(row=0, column=idx, padx=6, sticky="nsew")
            summary_frame.grid_columnconfigure(idx, weight=1)
            tk.Label(card, text=title, font=("Segoe UI", 9), bg=self.theme["card"], fg=self.theme["sub"]).pack(anchor="w")
            val = tk.Label(card, text="0", font=("Segoe UI", 16, "bold"), bg=self.theme["card"], fg=self.theme["text"])
            val.pack(anchor="w", pady=(6,0))
            self.kpi_cards[var_name] = val

        # CVE Severity summary
        severity_frame = tk.Frame(self.main_frame, bg=self.theme["bg"])
        severity_frame.pack(fill="x", padx=10, pady=(4, 8))
        for idx, (label_text, color) in enumerate([("CRITICAL","#ef4444"), ("HIGH","#f97316"), ("MEDIUM","#f59e0b"), ("LOW","#10b981")]):
            sf = tk.Frame(severity_frame, bd=1, relief="groove", padx=8, pady=6, bg=self.theme["card"], highlightbackground=self.theme["muted"], highlightcolor=self.theme["muted"], highlightthickness=1)
            sf.grid(row=0, column=idx, padx=6, sticky="w")
            tk.Label(sf, text=label_text, fg=color, font=("Segoe UI", 9, "bold"), bg=self.theme["card"]).pack(anchor="w")
            cnt = tk.Label(sf, text="0", font=("Segoe UI", 12), bg=self.theme["card"], fg=self.theme["text"])
            cnt.pack(anchor="w")
            setattr(self, f"sev_{label_text.lower()}", cnt)

        # Hosts & Services TreeView
        hosts_frame = tk.Frame(self.main_frame, bg=self.theme["bg"])
        hosts_frame.pack(fill="both", expand=True, padx=10, pady=(6,8))
        tk.Label(hosts_frame, text="Hosts & Services:", font=("Arial", 11, "bold"), bg=self.theme["bg"], fg=self.theme["text"]).pack(anchor="w")
        # Columns: Host (IP), Thiết bị, Port, Product, Version, Severity, CVE count
        columns = ("host", "device", "port_proto", "product", "version", "severity", "cve_count")
        table_container = tk.Frame(hosts_frame, bg=self.theme["bg"]) 
        table_container.pack(fill="both", expand=True, pady=6)
        
        self.hosts_tree = ttk.Treeview(table_container, columns=columns, show="headings", height=10)
        yscroll = ttk.Scrollbar(table_container, orient="vertical", command=self.hosts_tree.yview)
        self.hosts_tree.configure(yscrollcommand=yscroll.set)
        self.hosts_tree.pack(side="left", fill="both", expand=True)
        if not HIDE_SCROLLBARS:
            yscroll.pack(side="right", fill="y")
        # Headers
        self.hosts_tree.heading("host", text="Host (IP)", anchor="w")
        self.hosts_tree.heading("device", text="Thiết bị", anchor="w")
        self.hosts_tree.heading("port_proto", text="Port", anchor="center")
        self.hosts_tree.heading("product", text="Service", anchor="center")
        self.hosts_tree.heading("version", text="Version", anchor="center")
        self.hosts_tree.heading("severity", text="Severity", anchor="center")
        self.hosts_tree.heading("cve_count", text="CVEs", anchor="center")
        # column widths
        self.hosts_tree.column("host", width=180, anchor="w")
        self.hosts_tree.column("device", width=140, anchor="w")
        self.hosts_tree.column("port_proto", width=90, anchor="center")
        self.hosts_tree.column("product", width=150, anchor="w")
        self.hosts_tree.column("version", width=110, anchor="center")
        self.hosts_tree.column("severity", width=90, anchor="center")
        self.hosts_tree.column("cve_count", width=60, anchor="center")

        # Row tag colors for severity
        self.hosts_tree.tag_configure("CRITICAL", foreground="#ef4444")
        self.hosts_tree.tag_configure("HIGH", foreground="#f97316")
        self.hosts_tree.tag_configure("MEDIUM", foreground="#f59e0b")
        self.hosts_tree.tag_configure("LOW", foreground="#10b981")
        self.hosts_tree.tag_configure("NONE", foreground="#64748b")

        # Enable clickable headers for sorting
        for idx, col in enumerate(columns):
            self.hosts_tree.heading(col, text=self.hosts_tree.heading(col, "text"), command=lambda c=col: self._sort_tree_by_column(c))

        # =======================
        # OVERALL PROGRESS (Merged Ping + Scan)
        # =======================
        overall_frame = tk.Frame(self.main_frame, bg=self.theme["bg"])
        overall_frame.pack(fill="x", padx=10, pady=(2, 8))
        ttk.Label(overall_frame, text="Tiến độ:").pack(side="left")
        self.overall_var = tk.IntVar(self.root, value=0)
        self.overall_bar = ttk.Progressbar(overall_frame, variable=self.overall_var, maximum=100, length=420, style="Blue.Horizontal.TProgressbar")
        self.overall_bar.pack(side="left", padx=6)
        self.overall_label = tk.Label(overall_frame, text="0%", width=10, anchor="w", bg=self.theme["bg"], fg=self.theme["text"])
        self.overall_label.pack(side="left")

        # Stop scan button (Cancel & Save Progress)
        def _stop_scan():
            self.stop_event.set()
            self.stopping = True
            self.log("Dừng scan — sẽ hoàn thành IP hiện tại rồi dừng...", "WARN")
            # Jump progress bar to 100% immediately
            try:
                self.overall_var.set(100)
                self.overall_label.config(text="100%")
                # Enable export when stopping
                if hasattr(self, "export_menu_btn"):
                    self.export_menu_btn.config(state=tk.NORMAL)
            except Exception:
                pass

        tk.Button(overall_frame, text="Dừng", command=_stop_scan, bg="#ef4444", fg="white").pack(side="left", padx=6)

        # internal per-phase tracking
        self._ping_percent = 0
        self._scan_percent = 0
        self._alive_count = 0

        # Export button will be enabled only when overall reaches 100%
        try:
            self.export_btn.config(state=tk.DISABLED)
        except Exception:
            pass
        

        # =======================
        # LOG OUTPUT
        # =======================
        tk.Label(
            self.main_frame,
            text="Nhật ký:",
            font=("Arial", 11, "bold"),
            bg=self.theme["bg"],
            fg=self.theme["text"]
        ).pack(anchor="w", padx=10)

        self.log_box = scrolledtext.ScrolledText(
            self.main_frame,
            width=110,
            height=18,
            bg=self.theme["panel"],
            fg=self.theme["text"],
            insertbackground=self.theme["accent"],
            borderwidth=1,
            relief="solid"
        )
        # Use a monospaced font for easier scanning
        try:
            self.log_box.configure(font=("Consolas", 10))
        except Exception:
            pass
        self.log_box.pack(padx=10, pady=5, fill="both", expand=True)
        # =======================
        # LOG STYLES (COLOR LEVELS)
        # =======================
        self.log_box.tag_config("INFO", foreground="#60a5fa")     # xanh dương
        self.log_box.tag_config("SUCCESS", foreground="#34d399")  # xanh lá
        self.log_box.tag_config("WARN", foreground="#fbbf24")     # cam
        self.log_box.tag_config("ERROR", foreground="#f87171")    # đỏ
        self.log_box.tag_config("SYSTEM", foreground="#94a3b8")   # xám

        # NOTE: removed demo/mock data population to start with a clean UI

    # =================================================================
    # QUEUE LOGGING
    # =================================================================
    def enqueue_log(self, text):
        try:
            self.log_queue.put_nowait(text)
        except queue.Full:
            pass

    def log(self, message, level="INFO"):
        # Skip verbose technical logs unless in debug mode
        verbosity = self.config.get("log_verbosity", "normal")
        if verbosity == "normal":
            # Filter out overly detailed technical messages
            skip_patterns = [
                "[AUTH] Auth keys:",
                "[AUTH] ENTERING",
                "[AUTH] BEFORE",
                "[AUTH] AFTER",
                "[AUTH] WinRM connecting to",
                "[AUTH] Trying username=",
                "[AUTH] Executing PowerShell",
                "[AUTH] PowerShell exit code:",
                "[AUTH] PowerShell stdout:",
                "[AUTH] PowerShell stderr:",
                "[AUTH] Registry output length:",
                "[AUTH] Registry output (first",
                "[AUTH] Registry output has",
                "[AUTH] Parsed:",
                "[AUTH] Final software list:",
                "[AUTH] Software returned:",
                "[AUTH] Sample software:",
                "[AUTH] Final result - os_info:",
                "[PIPELINE] Raw data",
                "[PIPELINE] Software count:",
                "[PIPELINE] OS info:",
                ">>> ENTER",
                "ScanManager initialized",
                "Start scan with",
                "AuthenticatedScanner initialized",
                "AuthenticatedPipeline initialized"
            ]
            
            # Check if message should be filtered
            msg_lower = message.lower()
            for pattern in skip_patterns:
                if pattern.lower() in msg_lower:
                    return  # Skip this log entry

        # If stop was requested, suppress all further logs except stop notice and SUMMARY
        if getattr(self, "stopping", False):
            if "Dừng scan" not in message and level != "SYSTEM":
                return
        
        icons = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅ ",
            "WARN": "⚠️ ",
            "ERROR": "❌ ",
            "SYSTEM": "🖥️ "
        }

        tag = level if level in icons else "INFO"
        prefix = icons.get(tag, "")
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{ts}] {prefix}{message}"
        self.enqueue_log((text, tag))

    # ==================================================
    # PROGRESS CALLBACK (PING + SCAN PIPELINE)
    # ==================================================

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
        if mode == "Quét có xác thực":
            if not getattr(self.auth_wrapper, "_packed", False):
                self.auth_wrapper.grid(row=0, column=1, sticky="nsew", padx=8)
                self.auth_wrapper._packed = True
            # give host and auth reasonable split (host wider)
            try:
                # host narrower, still enough for ~2 IPv4 entries side-by-side
                self.host_auth_container.columnconfigure(0, weight=1)
                self.host_auth_container.columnconfigure(1, weight=2)
            except Exception:
                pass
        else:
            if getattr(self.auth_wrapper, "_packed", False):
                self.auth_wrapper.grid_forget()
                self.auth_wrapper._packed = False
            # host takes full width when auth hidden
            try:
                self.host_auth_container.columnconfigure(0, weight=1)
                self.host_auth_container.columnconfigure(1, weight=0)
            except Exception:
                pass

        self.root.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # =================================================================
    # SETTINGS HANDLER (in-class)
    # =================================================================
    def _open_settings_wrapper(self):
        """Wrapper to open settings with logging and graceful error handling."""
        try:
            self.log("Opening settings...", "INFO")
            self.open_settings()
        except Exception as e:
            self.log(f"Failed to open settings: {e}", "ERROR")
            try:
                # bind exception into default arg so the callback can run later without NameError
                self._safe_after(lambda _e=e: messagebox.showerror("Error", f"Cannot open settings: {_e}"))
            except Exception:
                # best-effort: swallow
                pass

    def _handle_open_settings(self):
        """Call the best available settings opener safely.

        This avoids evaluating attributes at button creation time which can raise
        AttributeError in some testing or partial-init scenarios.
        """
        handler = getattr(self, "_open_settings_wrapper", None) or getattr(self, "open_settings", None)
        if not handler:
            # Nothing to call; log and show an inline error if possible
            self.log("No settings handler available", "ERROR")
            try:
                self._safe_after(lambda: messagebox.showerror("Error", "Settings are not available"))
            except Exception:
                pass
            return

        try:
            handler()
        except Exception as e:
            self.log(f"Error when opening settings: {e}", "ERROR")
            try:
                # bind exception into default arg so the callback can run later without NameError
                self._safe_after(lambda _e=e: messagebox.showerror("Error", f"Cannot open settings: {_e}"))
            except Exception:
                pass

    # =================================================================
    # HELP DIALOG
    # =================================================================
    def open_help_dialog(self):
        """Open a simple help viewer showing installation & usage guide.

        Prioritize Vietnamese docs; fallback to English if missing.
        """
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates = [
                os.path.join(base_dir, "QUICK_REFERENCE_vi.md"),
                os.path.join(base_dir, "QUICK_REFERENCE.md"),
                os.path.join(base_dir, "START_HERE_vi.txt"),
                os.path.join(base_dir, "START_HERE.txt"),
            ]

            file_path = None
            for p in candidates:
                if os.path.exists(p):
                    file_path = p
                    break

            content = "Hướng dẫn chưa sẵn sàng. Vui lòng xem tài liệu đi kèm." if not file_path else open(file_path, "r", encoding="utf-8", errors="ignore").read()

            win = tk.Toplevel(self.root)
            win.title("Hướng dẫn cài đặt & sử dụng")
            win.configure(bg=self.theme["bg"])
            win.geometry("720x540")

            txt = scrolledtext.ScrolledText(win, wrap="word", bg=self.theme["panel"], fg=self.theme["text"], insertbackground=self.theme["accent"], borderwidth=1, relief="solid")
            try:
                txt.configure(font=("Segoe UI", 10))
            except Exception:
                pass
            txt.pack(fill="both", expand=True, padx=10, pady=10)
            txt.insert("1.0", content)
            txt.configure(state="disabled")

            # Ensure scrolling the help does NOT scroll the main GUI
            def _help_mousewheel(event, widget=txt):
                try:
                    widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except Exception:
                    pass
                return "break"  # stop propagation to global <MouseWheel> binding

            try:
                txt.bind("<MouseWheel>", _help_mousewheel)
            except Exception:
                pass
        except Exception as e:
            self.log(f"Không mở được hướng dẫn: {e}", "ERROR")
            try:
                messagebox.showerror("Lỗi", f"Không mở được hướng dẫn: {e}")
            except Exception:
                pass

    # =================================================================
    # ONE-CLICK AUTO SETUP
    # =================================================================
    def start_auto_setup_thread(self):
        """Start auto setup in background to keep UI responsive."""
        t = threading.Thread(target=self._run_auto_setup_wrapper, daemon=True)
        t.start()

    def _run_auto_setup_wrapper(self):
        try:
            self.auto_setup()
        except Exception as e:
            self.log(f"Lỗi cài đặt tự động: {e}", "ERROR")
            try:
                self._safe_after(lambda m=str(e): messagebox.showerror("Lỗi", f"Cài đặt thất bại: {m}"))
            except Exception:
                pass

    def _exec_cmd(self, cmd, shell=False):
        """Execute a command and stream output to log."""
        self.log(f"Chạy lệnh: {' '.join(cmd) if isinstance(cmd, (list, tuple)) else cmd}", "SYSTEM")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=shell)
            for line in proc.stdout or []:
                self.log(line.strip(), "SYSTEM")
            rc = proc.wait()
            if rc != 0:
                raise RuntimeError(f"Lệnh trả về mã lỗi {rc}")
        except Exception as e:
            raise

    def auto_setup(self):
        """Automate common setup steps: dependencies, Nmap check, verification."""
        self.log("Bắt đầu cài đặt tự động…", "SYSTEM")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        req_path = os.path.join(base_dir, "requirements.txt")
        verify_path = os.path.join(base_dir, "verify_installation.py")

        # 1) Install Python dependencies
        if os.path.exists(req_path):
            self.log("Cài đặt phụ thuộc Python từ requirements.txt", "INFO")
            # Use the current Python executable to ensure correct environment
            py = sys.executable or "python"
            self._exec_cmd([py, "-m", "pip", "install", "-r", req_path])
        else:
            self.log("Không tìm thấy requirements.txt", "WARN")

        # 2) Check Nmap presence; attempt install on Windows via winget if missing
        self.log("Kiểm tra Nmap…", "INFO")
        nmap_path = shutil.which("nmap")
        if nmap_path:
            self.log(f"Đã tìm thấy Nmap: {nmap_path}", "SUCCESS")
        else:
            self.log("Không tìm thấy Nmap trong PATH", "WARN")
            if os.name == "nt":
                # Try winget
                winget = shutil.which("winget")
                if winget:
                    self.log("Thử cài đặt Nmap qua winget", "INFO")
                    try:
                        self._exec_cmd([winget, "install", "-e", "--id", "Nmap.Nmap"])
                    except Exception as e:
                        self.log(f"Winget cài đặt Nmap thất bại: {e}", "ERROR")
                else:
                    self.log("Winget không khả dụng. Vui lòng tải Nmap tại https://nmap.org/download.", "WARN")
            else:
                self.log("Vui lòng cài Nmap (apt/brew/yum hoặc https://nmap.org/download)", "WARN")

        # 3) Verify installation script
        if os.path.exists(verify_path):
            self.log("Chạy xác minh cài đặt", "INFO")
            py = sys.executable or "python"
            try:
                self._exec_cmd([py, verify_path])
                self.log("Xác minh cài đặt hoàn tất", "SUCCESS")
            except Exception as e:
                self.log(f"Xác minh cài đặt báo lỗi: {e}", "ERROR")
        else:
            self.log("Không tìm thấy verify_installation.py", "WARN")

        # 4) Optional: rebuild local CVE DB if configured
        cfg = ConfigManager.load()
        if cfg.get("use_local_db"):
            rebuild_script = os.path.join(base_dir, "scripts", "rebuild_local_db.py")
            if os.path.exists(rebuild_script):
                self.log("Tái xây dựng CSDL CVE cục bộ (tuỳ chọn)", "INFO")
                py = sys.executable or "python"
                try:
                    self._exec_cmd([py, rebuild_script])
                except Exception as e:
                    self.log(f"Không thể xây dựng DB cục bộ: {e}", "WARN")

        self.log("Cài đặt tự động đã hoàn tất.", "SUCCESS")

    # (Removed easy wizard: guidance moved to Help and docs)
    

    # =================================================================
    # SCAN THREAD CONTROL
    # =================================================================
    def start_scan_thread(self):
        # reset overall progress
        self._ping_percent = 0
        self._scan_percent = 0
        try:
            # Guard for headless/tests where these widgets are absent
            if hasattr(self, "overall_var"):
                self.overall_var.set(0)
            if hasattr(self, "overall_label"):
                self.overall_label.config(text="0%")
        except Exception:
            pass

        # disable export during scan
        try:
            if hasattr(self, "export_menu_btn"):
                self.export_menu_btn.config(state=tk.DISABLED)
        except Exception:
            pass

        with self.scan_lock:
            if self.scanning:
                self.root.after(0, lambda: messagebox.showwarning("Warning", "Đang chạy scan. Vui lòng chờ."))
                return
            self.scanning = True
            self.last_results = {}

        t = threading.Thread(target=self.run_scan_wrapper, daemon=True)
        t.start()

        # Testing helper: when tests patch Thread to execute synchronously (no is_alive),
        # ensure scanning gets cleared if the run completed inline but _on_scan_complete
        # could not be scheduled on the Tk mainloop.
        if self.scanning and not hasattr(t, "is_alive"):
            # Thread-like object executed synchronously (tests). Ensure completion handler runs.
            try:
                self._on_scan_complete()
            except Exception:
                # best-effort: don't let test crash
                pass


    def _safe_after(self, func):
        """Schedule `func` to run on the Tk mainloop if available, else call it inline."""
        try:
            self.root.after(0, func)
        except Exception:
            try:
                func()
            except Exception:
                pass

    def run_scan_wrapper(self):
        try:
            self.run_scan()
        except Exception as e:
            msg = str(e)
            self._safe_after(lambda m=msg: messagebox.showerror("Error", f"Lỗi scan: {m}"))
        finally:
            self._safe_after(self._on_scan_complete)

    # Simple run method (ensures GUI can be started even if later definitions were moved)
    def run(self):
        """Start the Tk main loop (keeps compatibility with `app.py`)."""
        try:
            self.root.mainloop()
        except Exception:
            pass

    def _on_scan_complete(self):
        self.scanning = False
        try:
            messagebox.showinfo("Hoàn tất", "Scan đã hoàn tất!")
        except Exception:
            pass

    # =================================================================
    # FULL PIPELINE ADDON (CPE → CVE → REPORT)
    # =================================================================
    
    # =================================================================
    # SCAN LOGIC
    # =================================================================
    def process_host_result(self, host, result, sync=False):
        """Process a single host result (safe to call from background thread).
        If `sync=True` the update is applied synchronously (useful for tests).
        """
        def _do():
            try:
                self.last_results[host] = result
                # small summary log
                ports = result.get("gui", {}).get("ports", [])
                cve_count = sum(1 for p in ports for c in p.get("cves", []) if c.get("id"))
                self.log(f"Scanned {host} ({len(ports)} services, {cve_count} CVE)", "INFO")
                self._update_ui_from_results(sync=True)
            except Exception as e:
                self.log(f"Error processing host result for {host}: {e}", "ERROR")

        if sync:
            _do()
        else:
            try:
                self.root.after(0, _do)
            except Exception:
                # fallback if root is not available
                _do()

    def run_scan(self):
        raw = self.host_box.get("1.0", tk.END).strip()
        hosts = []
    
        # ==========================
        # PARSE HOSTS
        # ==========================
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
                
            if not is_valid_host(line):
                self.log(f"Host/IP không hợp lệ: {line}", "WARN")
                continue
            
            hosts.append(line)
    
        if not hosts:
            self.log("Không có host hợp lệ để quét", "ERROR")
            self.scanning = False
            return
    
        self._scan_start = time.time()
        self.log("🖥️ Bắt đầu quá trình quét", "SYSTEM")
        self.stop_event.clear()
        self.stopping = False
        
        # Reload config from disk to catch any updates (e.g., scan_policy change in Settings)
        self.config = ConfigManager.load()
    
        # Instantiate ScanManager; support test doubles that may not accept all args
        try:
            manager = ScanManager(
                self.config,
                logger=self.log,
                progress_cb=self.on_progress,
                stop_event=self.stop_event
            )
        except TypeError:
            manager = ScanManager(
                self.config,
                logger=self.log,
                progress_cb=self.on_progress
            )

        # Resolve hostnames to IPv4 for scanners that expect numeric IPs
        resolved_targets = []
        alias_map = {}
        input_mode = self.input_mode_var.get()  # "IP/CIDR" or "Hostname (Domain)"

        for h in hosts:
            resolved_ip = None
            display = h
            
            if input_mode == "IP/CIDR":
                # ===== IP/CIDR MODE =====
                # Pass through IP and CIDR without DNS resolution
                if "/" in h:
                    # Check if it's valid CIDR
                    try:
                        ipaddress.ip_network(h, strict=False)
                        resolved_targets.append(h)
                        alias_map[h] = display
                        self.log(f"CIDR detected: {h} (will be expanded by pipeline)", "INFO")
                        continue
                    except Exception:
                        self.log(f"Input Mode is IP/CIDR but '{h}' is not valid CIDR", "WARN")
                        continue
                
                # Check if it's a plain IP address
                try:
                    ipaddress.ip_address(h)
                    resolved_ip = h
                    self.log(f"IP detected: {h}", "INFO")
                except Exception:
                    self.log(f"Input Mode is IP/CIDR but '{h}' is not valid IP/CIDR", "WARN")
                    continue
            else:
                # ===== HOSTNAME MODE =====
                # Check if it's CIDR notation - pass through directly
                if "/" in h:
                    try:
                        ipaddress.ip_network(h, strict=False)
                        resolved_targets.append(h)
                        alias_map[h] = display
                        self.log(f"CIDR detected: {h} (will be expanded by pipeline)", "INFO")
                        continue
                    except Exception:
                        pass
                
                # Check if it's a plain IP address
                try:
                    ipaddress.ip_address(h)
                    resolved_ip = h
                except Exception:
                    # It's a hostname - try to resolve
                    try:
                        resolved_ip = socket.gethostbyname(h)
                        display = f"{h} ({resolved_ip})"
                        self.log(f"Resolved hostname {h} -> {resolved_ip}", "INFO")
                    except Exception as e:
                        self.log(f"Không resolve được hostname: {h} ({e})", "WARN")
                        continue

            if resolved_ip:
                if resolved_ip not in alias_map:
                    alias_map[resolved_ip] = display
                resolved_targets.append(resolved_ip)

        if not resolved_targets:
            self.log("Không có host hợp lệ sau khi resolve", "ERROR")
            self.scanning = False
            return

        # provide a host-level callback so UI updates as each host finishes
        def _host_cb(host, result, sync=None):
            label = alias_map.get(host, host)
            # Always apply synchronously for deterministic updates in tests/UI
            self.process_host_result(label, result, sync=True)
        host_cb = _host_cb

        # NOTE: actual call to manager.scan happens after determining scan mode and auth_data
        # (avoids referencing `authenticated`/`auth_data` before they are defined)


    
        # ==========================
        # CHỌN MODE
        # ==========================
        scan_mode = self.scan_mode_var.get()
        authenticated = scan_mode == "Quét có xác thực"
    
        auth_data = None
    
        # ==========================
        # AUTHENTICATED SCAN
        # ==========================
        if authenticated:
            os_ui = self.auth_os_var.get()
    
            if os_ui == "Auto":
                self.log(
                    "Authenticated scan yêu cầu chọn OS (Linux hoặc Windows)",
                    "ERROR"
                )
                self.scanning = False
                return
    
            auth_data = {
                "os": os_ui.lower(),  # linux | windows
                "username": self.auth_user.get().strip(),
                "password": self.auth_pass.get().strip(),
                "keyfile": self.auth_key.get().strip() or None,
                "port": int(
                    self.auth_port.get()
                    or (22 if os_ui == "Linux" else 5985)
                )
            }
    
        # ==========================
        # RUN ENGINE
        # ==========================
        try:
            results = manager.scan(
                targets=resolved_targets,
                authenticated=authenticated,
                auth_data=auth_data,
                host_result_cb=host_cb,
                input_mode=input_mode  # Pass mode to pipeline
            )
        except TypeError:
            results = manager.scan(
                targets=resolved_targets,
                authenticated=authenticated,
                auth_data=auth_data,
                host_result_cb=host_cb
            )
    
        # ==========================
        # SAVE + LOG
        # ==========================
        self.last_results = {}

        scanned_hosts = 0
        total_cve_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for item in results:
            host_ip = item["host"]
            host_label = alias_map.get(host_ip, host_ip)
            
            # DEBUG: log what we got from results loop
            ports = item["result"].get("gui", {}).get("ports", [])
            cve_count = 0
            for p in ports:
                for c in p.get("cves", []):
                    if c.get("id"):
                        cve_count += 1
                        # severity may be dict or label
                        sev = c.get("severity")
                        label = sev if isinstance(sev, str) else (sev.get("label") if isinstance(sev, dict) else "INFO")
                        if label in total_cve_counts:
                            total_cve_counts[label] += 1

            scanned_hosts += 1
            
            # DEBUG: log what we got from results loop
            self.log(f"[FINAL LOOP] {host_label}: {len(ports)} ports, {cve_count} CVEs from manager.scan()", "SYSTEM")
            
            # IMPORTANT: DO NOT overwrite self.last_results here
            # It was already populated by host_result_cb during scan
            # Only use this loop for CVE counting and logging
            # If the key doesn't exist (no callback), add it
            if host_label not in self.last_results:
                self.last_results[host_label] = item["result"]
                self.log(f"[FINAL LOOP] {host_label} missing from callbacks, adding from manager.scan()", "WARN")

            if cve_count > 0:
                self.log(f"✅ Hoàn tất host: {host_label}", "SUCCESS")
            # else: suppress logs for hosts with no CVEs to reduce noise

        # ---------------------
        # SUMMARY
        # ---------------------
        elapsed = int(time.time() - self._scan_start)
        mins = elapsed // 60
        secs = elapsed % 60

        self.log("==================== SUMMARY ====================", "SYSTEM")
        self.log(f"🖥️ Tổng host nhập:        {len(hosts)}", "SYSTEM")
        self.log(f"🖥️ Host hoạt động:        {len(results)}", "SYSTEM")
        self.log(f"🖥️ Host đã quét:          {scanned_hosts}", "SYSTEM")
        self.log("", "SYSTEM")
        self.log("❗ CVE phát hiện:", "SYSTEM")
        for lvl, icon in [("CRITICAL", "🔴"), ("HIGH", "🟠"), ("MEDIUM", "🟡"), ("LOW", "🟢")]:
            self.log(f"   {icon} {lvl}: {total_cve_counts[lvl]}", "SYSTEM")
        self.log("", "SYSTEM")
        self.log(f"⏱️ Thời gian scan: {mins}m {secs}s", "SYSTEM")
        self.log("================================================", "SYSTEM")

        # update UI from results (safe for background thread)
        try:
            self._update_ui_from_results()
        except Exception:
            pass

        # mark overall progress complete and enable export
        try:
            self.overall_var.set(100)
            self.overall_label.config(text="100%")
            if hasattr(self, "export_menu_btn"):
                self.export_menu_btn.config(state=tk.NORMAL)
        except Exception:
            pass
    

    # =================================================================
    # UI helpers / mock data
    # =================================================================
    def _populate_mock_data(self):
        """No-op: demo/mock data has been removed to start the UI in a clean state."""
        return

    def _update_ui_from_results(self, sync=False):
        """Update KPI cards and hosts table from self.last_results.
        If `sync` is True, apply updates synchronously (useful for tests).
        """
        def _do():
            try:
                # In headless/test mode there is no tree or KPI widgets
                if not hasattr(self, "hosts_tree"):
                    return
                # Skip updating tree if we're stopping (to prevent flickering)
                if self.stopping:
                    return

                # clear hosts table
                for i in self.hosts_tree.get_children():
                    self.hosts_tree.delete(i)

                rows, kpi_counts, sev_counts = results_to_rows(self.last_results)

                for r in rows:
                    # rows: (host, port, service, product, version, severity, cve_count, device)
                    display = (r[0], r[7], r[1], r[3], r[4], r[5], r[6])
                    sev = r[5] if len(r) > 5 and r[5] else "NONE"
                    self.hosts_tree.insert("", "end", values=display, tags=(sev,))

                alive_display = self._alive_count if self._alive_count else kpi_counts["hosts"]
                self.kpi_cards["hosts_alive"].config(text=str(alive_display))
                self.kpi_cards["hosts_scanned"].config(text=str(kpi_counts["scanned"]))
                self.kpi_cards["open_services"].config(text=str(kpi_counts["open_services"]))
                self.kpi_cards["cves_found"].config(text=str(kpi_counts["cves_found"]))

                self.sev_critical.config(text=str(sev_counts["CRITICAL"]))
                self.sev_high.config(text=str(sev_counts["HIGH"]))
                self.sev_medium.config(text=str(sev_counts["MEDIUM"]))
                self.sev_low.config(text=str(sev_counts["LOW"]))
            except Exception:
                pass

        if sync:
            _do()
        else:
            try:
                self.root.after(0, _do)
            except Exception:
                _do()

    def _sort_rows(self, rows, col, reverse=False):
        return results_sort_rows(rows, col, reverse)

    def _sort_tree_by_column(self, col):
        """Sort the TreeView by column name (toggles asc/desc)."""
        rows, _, _ = results_to_rows(self.last_results)
        if not hasattr(self, "_sort_state"):
            self._sort_state = {}
        cur = self._sort_state.get(col, False)
        new_rows = self._sort_rows(rows, col, reverse=not cur)
        self._sort_state[col] = not cur

        for i in self.hosts_tree.get_children():
            self.hosts_tree.delete(i)
        for r in new_rows:
            display = (r[0], r[7], r[1], r[3], r[4], r[5], r[6])
            sev = r[5] if len(r) > 5 and r[5] else "NONE"
            self.hosts_tree.insert("", "end", values=display, tags=(sev,))

    # =================================================================
    # CSV EXPORT (refactored for testability)
    # =================================================================
    def export_csv_to_path(self, path):
        if not path:
            raise ValueError("No path provided")
        return write_scan_results_to_csv(self.last_results, path)

    def export_csv(self):
        if getattr(self, "overall_var", None) and self.overall_var.get() < 100:
            self._safe_after(lambda: messagebox.showwarning(
                "Warning", "Scan chưa hoàn tất — CSV chỉ có thể xuất khi tiến trình đạt 100%"
            ))
            return

        if not self.last_results:
            self._safe_after(lambda: messagebox.showwarning(
                "Warning", "Chưa có kết quả để xuất CSV."
            ))
            return

        path = None
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialdir=os.getcwd(),
                filetypes=[("CSV file", "*.csv")]
            )
        except Exception:
            path = None

        if not path:
            return

        try:
            self.export_csv_to_path(path)
            self._safe_after(lambda: messagebox.showinfo(
                "Success", f"Đã xuất CSV: {path}"
            ))
        except Exception as e:
            self._safe_after(lambda _e=e: messagebox.showerror(
                "Error", f"Lỗi ghi CSV: {_e}"
            ))

    def export_html(self):
        if getattr(self, "overall_var", None) and self.overall_var.get() < 100:
            self._safe_after(lambda: messagebox.showwarning(
                "Warning", "Scan chưa hoàn tất — HTML chỉ có thể xuất khi tiến trình đạt 100%"
            ))
            return

        if not self.last_results:
            self._safe_after(lambda: messagebox.showwarning(
                "Warning", "Chưa có kết quả để xuất HTML."
            ))
            return

        path = None
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".html",
                initialdir=os.getcwd(),
                filetypes=[("HTML file", "*.html")]
            )
        except Exception:
            path = None

        if not path:
            return

        try:
            if html_report.export_html(self.last_results, path):
                self._safe_after(lambda: messagebox.showinfo(
                    "Success", f"Đã xuất HTML: {path}"
                ))
            else:
                self._safe_after(lambda: messagebox.showerror(
                    "Error", "Xuất HTML thất bại"
                ))
        except Exception as e:
            self.log(f"HTML export error: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            self._safe_after(lambda _e=e: messagebox.showerror(
                "Error", f"Lỗi ghi HTML: {_e}"
            ))

    def export_pdf(self):
        if getattr(self, "overall_var", None) and self.overall_var.get() < 100:
            self._safe_after(lambda: messagebox.showwarning(
                "Warning", "Scan chưa hoàn tất — PDF chỉ có thể xuất khi tiến trình đạt 100%"
            ))
            return

        if not self.last_results:
            self._safe_after(lambda: messagebox.showwarning(
                "Warning", "Chưa có kết quả để xuất PDF."
            ))
            return

        path = None
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialdir=os.getcwd(),
                filetypes=[("PDF file", "*.pdf"), ("All files", "*.*")]
            )
        except Exception:
            path = None

        if not path:
            return

        try:
            if pdf_report.export_pdf(self.last_results, path):
                self._safe_after(lambda: messagebox.showinfo(
                    "Success", f"Đã xuất PDF: {path}"
                ))
            else:
                self._safe_after(lambda: messagebox.showerror(
                    "Error", "Xuất PDF thất bại. Yêu cầu thư viện 'reportlab'.\nCài đặt: pip install reportlab"
                ))
        except Exception as e:
            self._safe_after(lambda _e=e: messagebox.showerror(
                "Error", f"Lỗi ghi PDF: {_e}"
            ))



    def open_settings(self):
        try:
            win = tk.Toplevel(self.root)
            win.title("Cài đặt")
            win.geometry("600x450")
        except Exception as e:
            raise RuntimeError(f"Cannot open settings window: {e}")

        tk.Label(win, text="NVD API Key:", font=("Arial", 12)).pack(pady=(10, 2))
        entry = tk.Entry(win, width=60)
        entry.insert(0, self.api_key)
        entry.pack()

        use_local_var = tk.BooleanVar(win, value=self.config.get("use_local_db", False))
        local_frame = tk.Frame(win)
        local_frame.pack(fill="x", padx=12, pady=(10, 4))
        tk.Checkbutton(local_frame, text="Use local CVE DB (SQLite)", variable=use_local_var).pack(side="left")
        
        # Log verbosity option
        verbosity_frame = tk.Frame(win)
        verbosity_frame.pack(fill="x", padx=12, pady=(4, 4))
        tk.Label(verbosity_frame, text="Log verbosity:", font=("Arial", 10)).pack(side="left")
        verbosity_var = tk.StringVar(win, value=self.config.get("log_verbosity", "normal"))
        verbosity_cb = ttk.Combobox(
            verbosity_frame,
            textvariable=verbosity_var,
            state="readonly",
            width=15
        )
        verbosity_cb["values"] = ("normal", "debug")
        verbosity_cb.pack(side="left", padx=6)

        tk.Label(win, text="Local DB Path:", font=("Arial", 10)).pack(pady=(6, 2))
        db_frame = tk.Frame(win)
        db_frame.pack(fill="x", padx=12)
        db_entry = tk.Entry(db_frame, width=48)
        db_entry.insert(0, self.config.get("local_db_path", "modules/cve/nvd_cve.db"))
        db_entry.pack(side="left")

        def _browse_db():
            p = filedialog.askopenfilename(title="Select SQLite DB", filetypes=[("SQLite DB", "*.db *.sqlite3"), ("All files", "*")])
            if p:
                db_entry.delete(0, tk.END)
                db_entry.insert(0, p)

        tk.Button(db_frame, text="Browse", command=_browse_db).pack(side="left", padx=6)

        # Max concurrent scans setting
        tk.Label(win, text="Max concurrent scans:", font=("Arial", 10)).pack(pady=(6, 2))
        mcs_entry = tk.Entry(win, width=10)
        mcs_entry.insert(0, str(self.config.get("max_concurrent_scans", 4)))
        mcs_entry.pack()

        # CVE cap per service
        tk.Label(win, text="CVE cap per service:", font=("Arial", 10)).pack(pady=(6, 2))
        cve_cap_entry = tk.Entry(win, width=10)
        cve_cap_entry.insert(0, str(self.config.get("cve_max_per_service", 50)))
        cve_cap_entry.pack()

        def _rebuild():
            import threading

            def _job():
                self.log("Starting DB rebuild from feeds...", "SYSTEM")
                feed_path = "modules/cve/nvd_data"
                db_path = db_entry.get().strip() or "modules/cve/nvd_cve.db"
                try:
                    from modules.cve.local_db_fetcher import LocalDBFetcher
                    # Ensure destination folder exists
                    import os
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)

                    fetcher = LocalDBFetcher(db_path=db_path)

                    def _progress(filename, idx, total):
                        if filename:
                            self.log(f"Importing {filename} ({idx}/{total})", "SYSTEM")
                        else:
                            self.log(f"Finished file {idx}/{total}", "SYSTEM")

                    fetcher.rebuild_db_from_feeds(feed_path, progress_cb=_progress)

                    self.log("DB rebuild completed.", "SUCCESS")
                    self._safe_after(lambda: messagebox.showinfo("Success", "DB rebuild completed."))
                except Exception as e:
                    self.log(f"DB rebuild failed: {e}", "ERROR")
                    self._safe_after(lambda _e=e: messagebox.showerror("Error", f"DB rebuild failed: {_e}"))

            threading.Thread(target=_job, daemon=True).start()

        btn_frame2 = tk.Frame(win)
        btn_frame2.pack(pady=(6, 10))
        tk.Button(btn_frame2, text="Rebuild Local DB from Feeds", command=_rebuild).pack(side="left", padx=6)

        def save():
            new_key = entry.get().strip()
            self.config["nvd_api_key"] = new_key
            self.config["use_local_db"] = bool(use_local_var.get())
            self.config["local_db_path"] = db_entry.get().strip()
            self.config["log_verbosity"] = verbosity_var.get()
            try:
                self.config["max_concurrent_scans"] = int(mcs_entry.get().strip() or 4)
            except Exception:
                self.config["max_concurrent_scans"] = 4
            try:
                self.config["cve_max_per_service"] = int(cve_cap_entry.get().strip() or 50)
            except Exception:
                self.config["cve_max_per_service"] = 50

            ConfigManager.save(self.config)

            self.api_key = new_key

            self._safe_after(lambda: messagebox.showinfo("Success", "Đã lưu cấu hình!"))

            win.destroy()

        tk.Button(win, text="Lưu", command=save).pack(pady=14)

    # =================================================================
    # RUN GUI
    # =================================================================
    def run(self):
        if self.root:
            try:
                self.root.mainloop()
            except Exception:
                pass


# =============================================================
# Filtering helpers
# =============================================================
def _score_to_severity_label(score):
    try:
        s = float(score)
    except Exception:
        return "INFO"

    if s >= 9.0:
        return "CRITICAL"
    if s >= 7.0:
        return "HIGH"
    if s >= 4.0:
        return "MEDIUM"
    if s > 0:
        return "LOW"
    return "INFO"


def _normalize_severity(cve: dict) -> str:
    sev = cve.get("severity")
    score = None

    if isinstance(sev, str):
        return sev.upper()
    if isinstance(sev, dict):
        lbl = (sev.get("label") or "").upper()
        score = sev.get("score")
        if lbl:
            return lbl

    for key in ("cvss_v3", "cvss_v4", "cvss_v2"):
        if key in cve and cve.get(key) not in (None, ""):
            score = cve.get(key)
            break

    return _score_to_severity_label(score) if score is not None else "INFO"


def _cve_year_from_id(cve_id: str | None) -> int | None:
    if not cve_id or not isinstance(cve_id, str):
        return None
    try:
        parts = cve_id.split("-")
        if len(parts) >= 2:
            return int(parts[1])
    except Exception:
        return None
    return None


def _filter_cves(cves, min_sev: str = DEFAULT_MIN_SEVERITY, min_year: int = DEFAULT_MIN_YEAR):
    min_rank = SEVERITY_RANK.get(min_sev.upper(), 0)
    seen = set()
    filtered = []

    for cve in cves or []:
        cid = cve.get("id")
        if cid and cid in seen:
            continue

        label = _normalize_severity(cve)
        rank = SEVERITY_RANK.get(label, 0)
        if rank < min_rank:
            continue

        year = _cve_year_from_id(cid)
        if min_year and year and year < min_year:
            continue

        if cid:
            seen.add(cid)

        # ensure severity label is present for downstream rendering
        if not cve.get("severity"):
            cve = dict(cve)
            cve["severity"] = label

        filtered.append(cve)

    return filtered


def _should_skip_product(name: str | None) -> bool:
    n = (name or "").lower()
    for kw in SKIP_KEYWORDS:
        if kw in n:
            return True
    return False


def _filter_and_dedupe_ports(ports):
    deduped = {}

    for port in ports or []:
        product = port.get("product") or port.get("service") or ""
        version = port.get("version") or ""

        if _should_skip_product(product):
            continue

        # Keep ports even if there are no CVEs; just sanitize CVE list
        filtered_cves = _filter_cves(port.get("cves", []))

        key = (product.lower(), version.lower())
        if key not in deduped:
            new_port = dict(port)
            new_port["cves"] = filtered_cves
            deduped[key] = new_port
        else:
            existing = deduped[key]
            existing.setdefault("cves", [])
            existing_ids = {c.get("id") for c in existing.get("cves", []) if c.get("id")}
            for c in filtered_cves:
                cid = c.get("id")
                if cid and cid in existing_ids:
                    continue
                existing["cves"].append(c)
                if cid:
                    existing_ids.add(cid)

    return list(deduped.values())


def _filtered_results(results):
    filtered = {}
    if results is None:
        return filtered

    for host, host_result in results.items():
        gui_data = host_result.get("gui", {}) if isinstance(host_result, dict) else {}
        ports = gui_data.get("ports", [])
        cleaned_ports = _filter_and_dedupe_ports(ports)

        new_gui = dict(gui_data)
        new_gui["ports"] = cleaned_ports

        new_host_result = dict(host_result)
        new_host_result["gui"] = new_gui
        filtered[host] = new_host_result

    return filtered


def _split_host_label(label: str):
    """Tách nhãn host thành (hostname, ip)."""
    if not label:
        return "", ""
    lbl = str(label).strip()
    if "(" in lbl and lbl.endswith(")"):
        base, rest = lbl.rsplit("(", 1)
        host = base.strip()
        ip = rest[:-1].strip()
        if host and host != ip:
            return host, ip
        return "", ip or lbl
    return "", lbl


def results_to_rows(results):
    """Convert `results` dict to rows for the TreeView and KPI counts.
    Host keys are already formatted as 'hostname (ip)' or just 'ip' from pipeline.
    Display chúng tách riêng cột Thiết bị và Host (IP).
    """
    filtered = _filtered_results(results)

    rows = []
    hosts = len(filtered)
    scanned = len(filtered)
    open_services = 0
    cves_found = 0
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for host, host_result in filtered.items():
        # host key là "hostname (ip)" hoặc chỉ "ip"
        device_name, ip_only = _split_host_label(host)
        display_host = ip_only or host
        display_device = device_name
        
        ports = host_result.get("gui", {}).get("ports", [])
        open_services += len(ports)
        for p in ports:
            cves = p.get("cves", [])
            p_cve_count = sum(1 for c in cves if c.get("id"))
            cves_found += p_cve_count

            highest_sev = "NONE"
            highest_rank = 0
            for c in cves:
                label = _normalize_severity(c)
                if label in sev_counts:
                    sev_counts[label] += 1
                rank = SEVERITY_RANK.get(label, 0)
                if rank > highest_rank:
                    highest_rank = rank
                    highest_sev = label

            port = p.get('port') if p.get('port') is not None else ""
            port_proto = f"{port}"
            version = p.get("version") or ""
            if not version and cves:
                version = _version_from_cpe((cves[0] or {}).get("cpe"))

            # Keep legacy ordering for host/port (tests), append device at the end
            rows.append((display_host, port_proto, p.get("service") or "", p.get("product") or "", version, highest_sev, p_cve_count, display_device))

    kpi_counts = {"hosts": hosts, "scanned": scanned, "open_services": open_services, "cves_found": cves_found}
    return rows, kpi_counts, sev_counts


class _ResultsHelpers:
    @staticmethod
    def results_to_rows_instance(results):
        return results_to_rows(results)


def results_sort_rows(rows, col, reverse=False):
    """Return sorted rows by column name (helper for tests)."""
    col_map = {"host": 0, "port_proto": 1, "service": 2, "product": 3, "version": 4, "severity": 5, "cve_count": 6, "device": 7}
    idx = col_map.get(col, 0)

    def _key(r):
        v = r[idx]
        try:
            return int(v) if isinstance(v, int) or (isinstance(v, str) and v.isdigit()) else str(v).lower()
        except Exception:
            return str(v)

    return sorted(rows, key=_key, reverse=reverse)


def write_scan_results_to_csv(results, path):
    """Write `results` dict to CSV path. This helper is independent of GUI objects and suitable for tests."""
    if not path:
        raise ValueError("No path provided")

    filtered = _filtered_results(results)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Include Device column next to Host
        writer.writerow([
            "Host", "Device", "Service/Product", "Version", "Port", "CPE", "CVE ID", "Severity", "Description", "CVSS v2", "CVSS v3", "CVSS v4"
        ])

        for host, host_result in filtered.items():
            device_name, ip_only = _split_host_label(host)
            for port_info in host_result.get("gui", {}).get("ports", []):
                port = port_info.get("port")
                service = port_info.get("service")
                product = port_info.get("product") or ""
                version = port_info.get("version")

                cves = port_info.get("cves", [])
                version = port_info.get("version") or ""
                if not version and cves:
                    try:
                        version = _version_from_cpe((cves[0] or {}).get("cpe"))
                    except Exception:
                        version = version
                if cves:
                    for cve in cves:
                        sev = cve.get("severity") if isinstance(cve.get("severity"), str) else (
                            cve.get("severity", {}).get("label") if isinstance(cve.get("severity"), dict) else ""
                        )
                        writer.writerow([
                            ip_only or host,
                            device_name or "",
                            product or service,
                            version,
                            port,
                            cve.get("cpe") or "",
                            cve.get("id") or "",
                            sev or "",
                            cve.get("description") or "",
                            cve.get("cvss_v2") if cve.get("cvss_v2") is not None else "",
                            cve.get("cvss_v3") if cve.get("cvss_v3") is not None else "",
                            cve.get("cvss_v4") if cve.get("cvss_v4") is not None else ""
                        ])
                else:
                    writer.writerow([ip_only or host, device_name or "", product or service, version, port, "", "", "", "", "", ""])


if __name__ == "__main__":
    GUIController().run()
