"""
Module AuthLinuxScanner: Quét phần mềm cài đặt trên Linux qua SSH.
- Kết nối tới Linux host qua SSH (port 22, mặc định)
- Chạy command để lấy OS info (tên, version) từ /etc/os-release hoặc uname
- Chạy dpkg hoặc rpm để lấy danh sách package cài đặt
- Parse output để extract package name và version
"""

import paramiko        # Thư viện SSH client (kết nối SSH, exec command remote)
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
        timeout: int = 10
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
        # Tạo SSH client object
        self.ssh = paramiko.SSHClient()
        # Policy: tự động chấp nhận unknown hosts (không hỏi)
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Kết nối SSH
            if self.keyfile:
                # Dùng SSH key authentication
                self.ssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.keyfile,
                    timeout=self.timeout
                )
            else:
                # Dùng password authentication
                self.ssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout
                )
            return True
        except Exception as e:
            # Log lỗi kết nối
            logger.error(f"SSH connect failed {self.host}: {e}")
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
            return ""
        
        try:
            # Chạy command qua SSH (trả về stdin, stdout, stderr)
            _, stdout, _ = self.ssh.exec_command(cmd, timeout=self.timeout)
            # Đọc stdout (bytes), decode thành string (ignore decode errors)
            return stdout.read().decode(errors="ignore")
        except Exception as e:
            # Log lỗi
            logger.error("SSH command error: %s", e)
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

        # Return dict với fallback values
        return {
            "os_name": name or "linux",
            "os_version": version or "unknown"
        }

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
        pkgs = []

        # === Phase 1: Debian / Ubuntu (dpkg) ===
        # Lấy danh sách package từ dpkg (chỉ lấy installed: '^ii')
        out = self._run("dpkg -l 2>/dev/null | grep '^ii' || true")
        if out:
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
                return pkgs

        # === Phase 2: RHEL / CentOS / Fedora (rpm) ===
        # Lấy danh sách package từ rpm -qa
        out = self._run("rpm -qa 2>/dev/null || true")
        if out:
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
                return pkgs

        # Nếu cả dpkg và rpm đều không tìm thấy, return list rỗng
        return pkgs

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
