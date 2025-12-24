"""
Module AuthWindowsScanner: Quét phần mềm cài đặt trên Windows qua WinRM (Windows Remote Management).
- Kết nối tới Windows host qua WinRM (port 5985/5986)
- Chạy PowerShell script để lấy danh sách phần mềm cài đặt
- Parse registry uninstall keys hoặc WMI Win32_Product
"""

import logging                # Thư viện logging
from typing import List, Tuple  # Type hints

# Thiết lập logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Optional: import winrm library (dùng cho WinRM connection)
try:
    import winrm  # Thư viện Python cho WinRM protocol (kết nối remote Windows)
except Exception:
    # Nếu không cài đặt, set None (fallback sẽ xảy ra)
    winrm = None


class AuthWindowsScanner:
    r"""
    Lớp quét phần mềm cài đặt trên Windows qua WinRM.
    
    WinRM là giao thức cho phép remote command execution trên Windows.
    - Yêu cầu: WinRM service chạy trên target (port 5985/5986)
    - Authentication: NTLM, Basic, Kerberos (tùy config)
    
    Phương pháp:
    1. Kết nối tới endpoint WinRM (scheme://host:port/wsman)
    2. Chạy PowerShell script để enumerate phần mềm:
       - Registry: HKLM\Software\...\Uninstall\* (64-bit và 32-bit)
       - WMI: Get-WmiObject Win32_Product (slower, fallback)
    3. Parse output, extract name và version
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str = None,
        transport: str = "ntlm",
        port: int = 5985,
        use_ssl: bool = False,
        timeout: int = 30,
        logger_cb=None
    ):
        """
        Khởi tạo AuthWindowsScanner instance.
        
        Tham số:
        - host (str): địa chỉ IP/hostname của Windows target (ví dụ: "192.168.1.100")
        - username (str): tên user để kết nối WinRM (ví dụ: "Administrator", "DOMAIN\\user")
        - password (str|None): mật khẩu (có thể None nếu dùng kerberos hoặc prompt)
        - transport (str): loại authentication
          - "ntlm": NTLM (default, phổ biến trong mạng Windows)
          - "basic": Basic auth (HTTP)
          - "kerberos": Kerberos (domain network)
        - port (int): cổng WinRM (5985=HTTP, 5986=HTTPS, mặc định 5985)
        - use_ssl (bool): dùng HTTPS hay HTTP (mặc định False = HTTP)
        - timeout (int): timeout cho connection (giây, mặc định 30)
        - logger_cb (callable|None): callback(msg, level) để output logs tới GUI
        
        Hành động:
        - Lưu các tham số kết nối
        - Khởi tạo self.session = None (sẽ được set khi connect())
        """
        self.host = host
        self.username = username
        self.password = password
        self.transport = transport
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.session = None  # WinRM session object (khởi tạo sau khi connect)
        # 🔥 LOGGER CALLBACK (GUI)
        self.logger_cb = logger_cb or (lambda msg, lvl="INFO": None)

    def connect(self) -> bool:
        if winrm is None:
            self.logger_cb("pywinrm not installed", "ERROR")
            return False

        scheme = "https" if self.use_ssl else "http"
        endpoint = f"{scheme}://{self.host}:{self.port}/wsman"

        self.logger_cb(f"[AUTH] WinRM connecting to {endpoint}", "SYSTEM")

        def attempt(username: str, transport: str) -> bool:
            try:
                # WinRM requires: read_timeout_sec > operation_timeout_sec
                operation_timeout = max(self.timeout, 30)
                read_timeout = operation_timeout + 10

                self.logger_cb(
                    f"[AUTH] Trying username='{username}' transport='{transport}' (operation={operation_timeout}s, read={read_timeout}s)",
                    "INFO"
                )

                sess = winrm.Session(
                    endpoint,
                    auth=(username, self.password),
                    transport=transport,
                    server_cert_validation='ignore',
                    read_timeout_sec=read_timeout,
                    operation_timeout_sec=operation_timeout
                )

                # test hostname
                r = sess.run_ps("hostname")
                if getattr(r, "status_code", 1) == 0:
                    self.session = sess
                    self.logger_cb("[AUTH] WinRM PowerShell test OK", "SUCCESS")
                    return True

                self.logger_cb("[AUTH] PowerShell failed → trying CMD hostname", "WARN")
                r2 = sess.run_cmd("hostname")
                if getattr(r2, "status_code", 1) == 0:
                    self.session = sess
                    self.logger_cb("[AUTH] WinRM CMD test OK", "SUCCESS")
                    return True

                self.logger_cb("[AUTH] WinRM hostname test failed", "ERROR")
                return False
            except Exception as e:
                self.logger_cb(f"[AUTH] WinRM attempt failed (user='{username}', transport='{transport}'): {e}", "ERROR")
                return False

        # Build candidate usernames and transports
        user_candidates = [self.username]
        if "\\" not in self.username and not self.username.lower().startswith(".\\"):
            user_candidates.append(f".\\{self.username}")
            # also try host\username if user provided plain name
            try:
                user_candidates.append(f"{self.host}\\{self.username}")
            except Exception:
                pass

        transport_candidates = [self.transport]
        if self.transport != "basic":
            transport_candidates.append("basic")

        # Try combinations until one succeeds
        for u in user_candidates:
            for t in transport_candidates:
                if attempt(u, t):
                    return True

        self.logger_cb("[AUTH] All WinRM connection attempts failed", "ERROR")
        return False


    def run_ps(self, ps_script: str) -> str:
        """
        Chạy PowerShell script trên remote Windows host.
        
        Tham số:
        - ps_script (str): PowerShell script code (ví dụ: "Get-Item C:\\")
        
        Trả về: str - stdout output từ script (hoặc "" nếu lỗi)
        
        Quy trình:
        1. Kiểm tra session tồn tại (đã connect)
        2. Chạy script qua self.session.run_ps()
        3. Parse stdout output (có thể là bytes hoặc str)
        4. Decode bytes to string (hoặc str already)
        5. Handle decode errors gracefully (ignore mode)
        6. Return output string (hoặc "" nếu lỗi)
        
        Note: stdout có thể là bytes hoặc str tùy winrm version
        """
        # Nếu session chưa khởi tạo, return rỗng
        if not self.session:
            self.logger_cb("WinRM session not initialized", "WARN")
            return ""
        
        try:
            # Chạy PowerShell script qua WinRM
            self.logger_cb("[AUTH] Executing PowerShell script...", "INFO")
            r = self.session.run_ps(ps_script)
            out = ""
            
            # Log status code
            status = getattr(r, "status_code", None)
            self.logger_cb(f"[AUTH] PowerShell exit code: {status}", "INFO")
            
            # Parse stdout từ result object
            if hasattr(r, "std_out"):
                try:
                    # Kiểm tra std_out là bytes hay str
                    out = r.std_out.decode(errors="ignore") if isinstance(r.std_out, (bytes, bytearray)) else str(r.std_out)
                    self.logger_cb(f"[AUTH] PowerShell stdout: {len(out)} bytes", "INFO")
                except Exception as e:
                    # Fallback nếu decode fail
                    out = str(r.std_out)
                    self.logger_cb(f"[AUTH] PowerShell decode error: {e}, using str fallback", "WARN")
            else:
                # Fallback: một số phiên bản winrm có cách khác
                try:
                    out = r.std_out.decode(errors="ignore")
                    self.logger_cb(f"[AUTH] PowerShell stdout (alt): {len(out)} bytes", "INFO")
                except Exception:
                    out = ""
                    self.logger_cb("[AUTH] PowerShell stdout not found", "WARN")
            
            # Log stderr nếu có lỗi
            if hasattr(r, "std_err"):
                stderr = r.std_err.decode(errors="ignore") if isinstance(r.std_err, (bytes, bytearray)) else str(r.std_err)
                if stderr:
                    self.logger_cb(f"[AUTH] PowerShell stderr: {stderr}", "WARN")
            
            return out
        except Exception as e:
            # Log lỗi khi chạy script
            self.logger_cb(f"[AUTH] WinRM run_ps exception: {e}", "ERROR")
            import traceback
            self.logger_cb(f"[AUTH] Traceback: {traceback.format_exc()}", "ERROR")
            return ""

    def get_installed_software(self) -> List[Tuple[str, str]]:
        """
        Attempts to read installed apps via registry and Win32_Product fallback.
        Returns list of (name, version)
        """
        self.logger_cb("[AUTH] Starting Windows software enumeration...", "INFO")
        scripts = []

        # Try registry uninstall keys (both 64-bit and 32-bit)
        reg_script = r"""
        $keys = @(
          'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
          'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
        )
        $out = @()
        foreach ($k in $keys) {
          Get-ItemProperty $k -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.DisplayName) {
              $out += "{0}|||{1}" -f $_.DisplayName, ($_.DisplayVersion -replace '\r|\n','')
            }
          }
        }
        $out -join "`n"
        """
        scripts.append(("Registry", reg_script))

        # fallback to Win32_Product if registry empty (note: slow)
        win32 = r"""
        Try {
          Get-WmiObject -Class Win32_Product | ForEach-Object {
            "{0}|||{1}" -f $_.Name, ($_.Version -replace '\r|\n','')
          }
        } Catch {}
        """
        scripts.append(("WMI", win32))

        results = []
        for method, script in scripts:
            self.logger_cb(f"[AUTH] Trying {method} to enumerate software...", "INFO")
            out = self.run_ps(script)
            
            # Log output
            self.logger_cb(f"[AUTH] {method} output length: {len(out)} bytes", "INFO")
            if out:
                self.logger_cb(f"[AUTH] {method} output (first 500 chars):\n{out[:500]}", "INFO")
                
            if out:
                line_count = len(out.splitlines())
                self.logger_cb(f"[AUTH] {method} output has {line_count} lines", "INFO")
                
                for idx, line in enumerate(out.splitlines()):
                    if "|||" in line:
                        try:
                            name, ver = line.split("|||", 1)
                            name = name.strip()
                            ver = ver.strip()
                            if name:
                                results.append((name, ver or "unknown"))
                                if idx < 5:  # Log first 5 entries
                                    self.logger_cb(f"[AUTH] Parsed: {name} v{ver}", "INFO")
                        except Exception as e:
                            self.logger_cb(f"[AUTH] Failed to parse line: {line} - {e}", "WARN")
                    else:
                        if idx < 3:  # Log first few unparsed lines
                            self.logger_cb(f"[AUTH] Line missing '|||': {line}", "WARN")
                
            if results:
                self.logger_cb(f"[AUTH] Found {len(results)} software via {method}", "SUCCESS")
                break
            else:
                self.logger_cb(f"[AUTH] {method} output was empty or no parseable lines", "WARN")

        if not results:
            self.logger_cb("[AUTH] No software found via registry or WMI", "WARN")
        
        self.logger_cb(f"[AUTH] Final software list: {results}", "INFO")
        return results
