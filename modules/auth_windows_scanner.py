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
        timeout: int = 30
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

    def connect(self) -> bool:
        """
        Kết nối tới Windows target qua WinRM.
        
        Trả về: bool
        - True nếu kết nối thành công
        - False nếu lỗi (WinRM không cài, kết nối fail, test command fail)
        
        Quy trình:
        1. Kiểm tra winrm library cài đặt
        2. Xây dựng endpoint URL: http(s)://host:port/wsman
        3. Tạo WinRM Session object (chứa credentials)
        4. Test kết nối: chạy 'hostname' command (PowerShell hoặc cmd)
        5. Nếu status_code=0 -> return True
        6. Nếu error -> log error, return False
        """
        # Kiểm tra winrm library có sẵn không
        if winrm is None:
            logger.error("pywinrm not installed")
            return False
        
        # Xây dựng URL endpoint: http://host:5985/wsman hoặc https://host:5986/wsman
        scheme = "https" if self.use_ssl else "http"
        endpoint = f"{scheme}://{self.host}:{self.port}/wsman"
        
        try:
            # Tạo WinRM Session object (chứa connection info và credentials)
            # - endpoint: URL đầy đủ tới WinRM service
            # - auth: tuple (username, password) hoặc None
            # - transport: loại auth (ntlm, basic, kerberos)
            # - server_cert_validation: 'ignore' (không verify SSL cert, dùng cho self-signed)
            self.session = winrm.Session(
                endpoint,
                auth=(self.username, self.password),
                transport=self.transport,
                server_cert_validation='ignore'
            )

            # Test connection: chạy PowerShell "hostname" command
            r = self.session.run_ps("hostname")
            # Kiểm tra status code = 0 (success)
            if getattr(r, "status_code", 1) == 0:
                return True

            # Fallback: thử cmd command nếu PowerShell fail
            r2 = self.session.run_cmd("hostname")
            if getattr(r2, "status_code", 1) == 0:
                return True

            # Cả 2 command đều fail
            logger.error("WinRM test returned non-zero status codes")
            return False
        except Exception as e:
            # Exception khi kết nối (network error, auth fail, timeout, v.v.)
            logger.error("WinRM connect failed %s: %s", self.host, e)
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
            return ""
        
        try:
            # Chạy PowerShell script qua WinRM
            r = self.session.run_ps(ps_script)
            out = ""
            
            # Parse stdout từ result object
            if hasattr(r, "std_out"):
                try:
                    # Kiểm tra std_out là bytes hay str
                    out = r.std_out.decode(errors="ignore") if isinstance(r.std_out, (bytes, bytearray)) else str(r.std_out)
                except Exception:
                    # Fallback nếu decode fail
                    out = str(r.std_out)
            else:
                # Fallback: một số phiên bản winrm có cách khác
                try:
                    out = r.std_out.decode(errors="ignore")
                except Exception:
                    out = ""
            
            return out
        except Exception as e:
            # Log lỗi khi chạy script
            logger.error("WinRM run_ps error: %s", e)
            return ""

    def get_installed_software(self) -> List[Tuple[str, str]]:
        """
        Attempts to read installed apps via registry and Win32_Product fallback.
        Returns list of (name, version)
        """
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
        scripts.append(reg_script)

        # fallback to Win32_Product if registry empty (note: slow)
        win32 = r"""
        Try {
          Get-WmiObject -Class Win32_Product | ForEach-Object {
            "{0}|||{1}" -f $_.Name, ($_.Version -replace '\r|\n','')
          }
        } Catch {}
        """
        scripts.append(win32)

        results = []
        for s in scripts:
            out = self.run_ps(s)
            if out:
                for line in out.splitlines():
                    if "|||" in line:
                        name, ver = line.split("|||", 1)
                        name = name.strip()
                        ver = ver.strip()
                        if name:
                            results.append((name, ver or "unknown"))
            if results:
                break

        return results
