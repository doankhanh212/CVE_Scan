"""
Module AuthLinuxScanner: Quét phần mềm cài đặt trên Linux qua SSH.
- Kết nối tới Linux host qua SSH (port 22, mặc định)
- Chạy command để lấy OS info (tên, version) từ /etc/os-release hoặc uname
- Chạy dpkg hoặc rpm để lấy danh sách package cài đặt
- Parse output để extract package name và version
"""

try:
    import paramiko
except Exception:
    paramiko = None  # paramiko optional for unit tests / CI environments
import re             # Thư viện regex (parse output command)
import logging        # Thư viện logging
from typing import List, Tuple  # Type hints

# Thiết lập logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AuthLinuxScanner:
    """
    Lớp quét phần mềm cài đặt trên Linux qua SSH.
    
    Phương pháp:
    1. Kết nối SSH (dùng password hoặc SSH key)
    2. Chạy command lấy OS info từ /etc/os-release (Debian/RHEL) hoặc uname
    3. Chạy command enumerate packages:
       - dpkg (Debian/Ubuntu): dpkg -l
       - rpm (RHEL/CentOS/Fedora): rpm -qa
    4. Parse output, extract package name và version
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str = None,
        keyfile: str = None,
        port: int = 22,
        timeout: int = 10,
        logger_cb=None
    ):
        """
        Khởi tạo AuthLinuxScanner instance.
        
        Tham số:
        - host (str): địa chỉ IP/hostname Linux target (ví dụ: "192.168.1.50", "app.example.com")
        - username (str): tên user SSH (ví dụ: "root", "ubuntu", "admin")
        - password (str|None): mật khẩu SSH (dùng nếu keyfile không có)
        - keyfile (str|None): đường dẫn tới SSH private key (ví dụ: "~/.ssh/id_rsa")
                              Nếu có, ưu tiên hơn password
        - port (int): cổng SSH (mặc định 22)
        - timeout (int): timeout cho connection và command (giây, mặc định 10)
        - logger_cb (callable|None): callback(msg, level) để output logs tới GUI
        
        Hành động:
        - Lưu các tham số kết nối
        - Khởi tạo self.ssh = None (sẽ được set khi connect())
        """
        self.host = host
        self.username = username
        self.password = password
        self.keyfile = keyfile
        self.port = port
        self.timeout = timeout
        self.logger_cb = logger_cb or (lambda msg, lvl="INFO": None)
        self.ssh = None  # Paramiko SSHClient object (khởi tạo sau khi connect)

    def connect(self) -> bool:
        """
        Kết nối tới Linux target qua SSH.
        
        Trả về: bool
        - True nếu kết nối thành công
        - False nếu lỗi (auth fail, network error, timeout, v.v.)
        
        Quy trình:
        1. Tạo Paramiko SSHClient object
        2. Thiết lập policy: AutoAddPolicy (tự thêm unknown hosts vào known_hosts)
        3. Gọi ssh.connect() với:
           - Nếu keyfile có: dùng SSH key (priority cao hơn)
           - Nếu không: dùng password
        4. Return True/False dựa vào kết quả
        """
        # If paramiko not present, fail gracefully (useful for CI/tests)
        if paramiko is None:
            logger.error("paramiko not installed")
            return False

        # Tạo SSH client object
        self.ssh = paramiko.SSHClient()
        # Policy: tự động chấp nhận unknown hosts (không hỏi)
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Kết nối SSH
            self.logger_cb(f"[AUTH] Connecting to {self.host}:{self.port} (user={self.username})", "SYSTEM")
            if self.keyfile:
                # Dùng SSH key authentication
                self.logger_cb(f"[AUTH] Using key auth: {self.keyfile}", "INFO")
                self.ssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.keyfile,
                    timeout=self.timeout
                )
            else:
                # Dùng password authentication
                self.logger_cb(f"[AUTH] Using password auth", "INFO")
                self.ssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout
                )
            self.logger_cb(f"[AUTH] SSH connection successful: {self.host}", "SUCCESS")
            return True
        except Exception as e:
            # Log lỗi kết nối
            self.logger_cb(f"[AUTH] SSH connect failed {self.host}: {e}", "ERROR")
            return False

    def _run(self, cmd: str) -> str:
        """
        Tiện ích: chạy shell command trên remote Linux host.
        
        Tham số:
        - cmd (str): shell command (ví dụ: "dpkg -l", "cat /etc/os-release")
        
        Trả về: str - stdout output từ command (hoặc "" nếu lỗi)
        
        Quy trình:
        1. Kiểm tra SSH session tồn tại
        2. Exec command qua ssh.exec_command()
        3. Lấy stdout file-like object
        4. Đọc output (bytes), decode thành string
        5. Return output (hoặc "" nếu lỗi)
        """
        # Nếu SSH session chưa khởi tạo
        if not self.ssh:
            self.logger_cb("SSH session not initialized", "WARN")
            return ""
        
        try:
            # Chạy command qua SSH (trả về stdin, stdout, stderr)
            _, stdout, _ = self.ssh.exec_command(cmd, timeout=self.timeout)
            # Đọc stdout (bytes), decode thành string (ignore decode errors)
            output = stdout.read().decode(errors="ignore")
            return output
        except Exception as e:
            # Log lỗi
            self.logger_cb(f"SSH command error: {e}", "ERROR")
            return ""

    def get_os_info(self) -> dict:
        """
        Lấy thông tin OS (tên, version) từ Linux target.
        
        Trả về: dict
        {
            "os_name": str (ví dụ: "ubuntu", "centos", "debian", "linux"),
            "os_version": str (ví dụ: "20.04", "8.5", "unknown")
        }
        
        Quy trình:
        1. Chạy command: cat /etc/os-release (standard) hoặc uname -a (fallback)
        2. Parse output bằng regex:
           - NAME="Ubuntu" -> os_name="ubuntu"
           - VERSION_ID="20.04" -> os_version="20.04"
        3. Fallback: os_name="linux", os_version="unknown" nếu parse fail
        
        Example output /etc/os-release:
        ```
        NAME="Ubuntu"
        VERSION="20.04.1 LTS (Focal Fossa)"
        ID=ubuntu
        VERSION_ID="20.04"
        ...
        ```
        """
        self.logger_cb("[AUTH] Fetching OS information...", "INFO")
        # Chạy command lấy OS info
        out = self._run("cat /etc/os-release 2>/dev/null || uname -a")
        name = None
        version = None

        # Parse NAME="..." line
        m_name = re.search(r'^NAME="?([^"\n]+)"?', out, re.MULTILINE)
        # Parse VERSION_ID="..." line
        m_ver = re.search(r'^VERSION_ID="?([^"\n]+)"?', out, re.MULTILINE)

        # Extract groups từ regex matches
        if m_name:
            name = m_name.group(1)
        if m_ver:
            version = m_ver.group(1)

        # Get kernel version via uname -r (fallback if available)
        kernel_out = self._run("uname -r 2>/dev/null || true")
        kernel = kernel_out.strip().splitlines()[0] if kernel_out else "unknown"

        # Return dict với fallback values
        result = {
            "os_name": name or "linux",
            "os_version": version or "unknown",
            "kernel": kernel
        }
        self.logger_cb(f"[AUTH] OS info: {result.get('os_name')} {result.get('os_version')}", "INFO")
        return result

    def get_installed_packages(self) -> List[Tuple[str, str]]:
        """
        Enumerate danh sách package cài đặt trên remote Linux host.
        
        Trả về: list[tuple[str, str]]
        - Danh sách (package_name, version) tuples
        - Ví dụ: [("curl", "7.68.0"), ("openssh-server", "1:8.2"), ...]
        - Return [] nếu không tìm thấy hoặc lỗi
        
        Quy trình:
        1. Thử Debian/Ubuntu (dpkg):
           - Command: dpkg -l | grep '^ii'
           - Format: ii  curl  7.68.0-1  amd64
           - Extract: package name (column 2), version (column 3)
        
        2. Nếu Debian fail, thử RHEL/CentOS/Fedora (rpm):
           - Command: rpm -qa
           - Format: curl-7.68.0-1.el8.x86_64
           - Parse: name-version-release.arch
           - Regex: ^(.+)-([0-9][^-]*)-(.+)$
           - Extract: package name (group 1), version (group 2)
        
        3. Fallback: split package-version-release bằng rsplit("-", 2)
        4. Return danh sách packages (hoặc [] nếu cả 2 fail)
        
        Note:
        - Dpkg output format: "ii  name  version  arch  description"
        - Rpm output format: "name-version-release.arch"
        """
        self.logger_cb("[AUTH] Starting package enumeration...", "INFO")
        pkgs = []

        # === Phase 1: Debian / Ubuntu (dpkg) ===
        # Lấy danh sách package từ dpkg (chỉ lấy installed: '^ii')
        self.logger_cb("[AUTH] Trying dpkg (Debian/Ubuntu)...", "INFO")
        out = self._run("dpkg -l 2>/dev/null | grep '^ii' || true")
        if out:
            self.logger_cb(f"[AUTH] dpkg output found, {len(out)} bytes", "INFO")
            # Parse từng line
            for line in out.splitlines():
                # Split by whitespace: ii  name  version  arch  ...
                parts = line.split()
                # Expected format: [ii, package_name, version, arch, ...]
                if len(parts) >= 3:
                    pkg = parts[1].strip()
                    ver = parts[2].strip()
                    pkgs.append((pkg, ver))
            # Nếu dpkg tìm thấy package, return ngay (không cần rpm fallback)
            if pkgs:
                self.logger_cb(f"[AUTH] Found {len(pkgs)} packages via dpkg", "SUCCESS")
                return pkgs
            else:
                self.logger_cb("[AUTH] dpkg output was empty", "WARN")

        # === Phase 2: RHEL / CentOS / Fedora (rpm) ===
        # Lấy danh sách package từ rpm -qa
        self.logger_cb("[AUTH] Trying rpm (RHEL/CentOS/Fedora)...", "INFO")
        out = self._run("rpm -qa 2>/dev/null || true")
        if out:
            self.logger_cb(f"[AUTH] rpm output found, {len(out)} bytes", "INFO")
            # Parse từng line
            for line in out.splitlines():
                line = line.strip()
                # Try to parse package-version-release.arch pattern
                # Example: curl-7.68.0-1.el8.x86_64
                # Regex: ^(.+)-([0-9][^-]*)-(.+)$
                #        name      version    release
                m = re.match(r"^(.+)-([0-9][^-]*)-(.+)$", line)
                if m:
                    pkg = m.group(1)
                    ver = m.group(2)
                    pkgs.append((pkg, ver))
                else:
                    # Fallback: rsplit by '-' từ phải sang (lấy 2 parts cuối)
                    # Example: curl-7.68.0 -> [curl, 7.68.0]
                    parts = line.rsplit("-", 2)
                    if len(parts) >= 2:
                        pkg = parts[0]
                        ver = parts[1]
                        pkgs.append((pkg, ver))
            # Nếu rpm tìm thấy package, return
            if pkgs:
                self.logger_cb(f"[AUTH] Found {len(pkgs)} packages via rpm", "SUCCESS")
                return pkgs
            else:
                self.logger_cb("[AUTH] rpm output was empty", "WARN")

        # Nếu cả dpkg và rpm đều không tìm thấy, return list rỗng
        self.logger_cb("[AUTH] No packages found via dpkg or rpm", "WARN")
        return pkgs

    # Backwards compatibility: some callers expect get_installed_software()
    def get_installed_software(self) -> List[Tuple[str, str]]:
        """
        Backwards compatible wrapper used by AuthenticatedScanner.
        """
        return self.get_installed_packages()

    def close(self):
        """
        Đóng SSH connection.
        
        Hành động:
        - Nếu SSH session tồn tại, gọi close() để đóng connection
        - Silent fail nếu lỗi (pass exception)
        
        Note: Nên gọi hàm này khi không cần scanner nữa (cleanup resource)
        """
        if self.ssh:
            try:
                self.ssh.close()
            except Exception:
                # Silent fail: bất kỳ exception nào cũng pass
                pass
