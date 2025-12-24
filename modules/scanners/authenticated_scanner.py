# modules/scanners/authenticated_scanner.py

from typing import Dict, Any
import logging

from modules.scanners.auth_linux_scanner import AuthLinuxScanner
from modules.scanners.auth_windows_scanner import AuthWindowsScanner

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AuthenticatedScanner:
    """
    AuthenticatedScanner (Adapter for new engine)
    ----------------------------------------------
    - Giữ logic cũ
    - Adapt interface cho engine mới
    """

    def __init__(self, timeout: int = 30, logger=None):
        self.timeout = timeout
        self.logger = logger or (lambda msg, lvl="INFO": None)

        self.logger("AuthenticatedScanner initialized", "SYSTEM")

    # ==================================================
    # ENGINE ENTRYPOINT (ENGINE MỚI GỌI HÀM NÀY)
    # ==================================================
    def scan(self, target: str, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapter method cho engine mới
        """
        return self.scan_host(target, auth_data)

    # ==================================================
    # LOGIC CŨ (GIỮ NGUYÊN)
    # ==================================================
    def scan_host(
        self,
        target: str,
        auth: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.logger(">>> ENTER AuthenticatedScanner.scan_host()", "SYSTEM")

        os_type = auth.get("os")
        self.logger(f"[AUTH] Detected os_type: {os_type}", "INFO")
        self.logger(f"[AUTH] Auth keys: {list(auth.keys())}", "INFO")
        
        if not os_type:
            raise ValueError("auth.os is required ('linux' or 'windows')")

        scanner = None

        try:
            # =========================
            # LINUX
            # =========================
            if os_type == "linux":
                self.logger("[AUTH] ENTERING LINUX SECTION", "SYSTEM")
                self.logger("[AUTH] Linux scan selected", "SYSTEM")
                self.logger(f"[AUTH] Auth data: username={auth.get('username')}, password={bool(auth.get('password'))}, keyfile={auth.get('keyfile')}", "INFO")

                scanner = AuthLinuxScanner(
                    host=target,
                    username=auth["username"],
                    password=auth.get("password"),
                    keyfile=auth.get("keyfile"),
                    port=auth.get("port", 22),
                    timeout=auth.get("timeout", self.timeout),
                    logger_cb=self.logger
                )

                self.logger(f"[AUTH] Kết nối SSH: {target}:{auth.get('port', 22)}", "SYSTEM")
                self.logger("[AUTH] Calling SSH connect()", "SYSTEM")
                if not scanner.connect():
                    self.logger(f"[AUTH] SSH connect FAILED: {target}", "ERROR")
                    return {}
                self.logger("[AUTH] Đăng nhập thành công (Linux)", "SUCCESS")

                os_info = scanner.get_os_info()
                software = scanner.get_installed_software()
                if software:
                    self.logger(f"[AUTH] Phát hiện {len(software)} packages cài đặt", "INFO")
                else:
                    self.logger(f"[AUTH] Không tìm thấy packages, có thể do quyền hoặc distro không hỗ trợ", "WARN")

            # =========================
            # WINDOWS
            # =========================
            elif os_type == "windows":
                self.logger("[AUTH] ENTERING WINDOWS SECTION", "SYSTEM")
                self.logger("[AUTH] Windows scan selected", "SYSTEM")
                self.logger(f"[AUTH] Auth data: username={auth.get('username')}, password={bool(auth.get('password'))}", "INFO")

                scanner = AuthWindowsScanner(
                    host=target,
                    username=auth["username"],
                    password=auth.get("password"),
                    transport=auth.get("transport", "ntlm"),
                    port=auth.get("port", 5985),
                    use_ssl=auth.get("use_ssl", False),
                    timeout=auth.get("timeout", self.timeout),
                    logger_cb=self.logger
                )

                self.logger("[AUTH] BEFORE WinRM connect()", "SYSTEM")

                ok = scanner.connect()

                self.logger("[AUTH] AFTER WinRM connect()", "SYSTEM")

                if not ok:
                    self.logger("[AUTH] WinRM connect FAILED", "ERROR")
                    return {}

                self.logger("[AUTH] WinRM connect OK", "SUCCESS")


                os_info = {
                    "os_name": "windows",
                    "os_version": "unknown"
                }

                software = scanner.get_installed_software()
                self.logger(f"[AUTH] Software returned: {len(software) if software else 0} items", "INFO")
                if software:
                    self.logger(f"[AUTH] Sample software: {software[:3]}", "INFO")
                else:
                    self.logger("[AUTH] No software found from Windows!", "WARN")

            else:
                self.logger("[AUTH] ELSE SECTION - UNKNOWN OS TYPE!", "ERROR")
                raise ValueError("auth.os must be 'linux' or 'windows'")

            self.logger(f"[AUTH] Final result - os_info: {os_info}, software count: {len(software) if software else 0}", "INFO")
            return {
                "os": os_info,
                "software": software
            }

        except KeyError as e:
            self.logger(f"Missing auth field: {e}", "ERROR")
            import traceback
            self.logger(f"KeyError traceback: {traceback.format_exc()}", "ERROR")
            return {}

        except ValueError as e:
            self.logger(f"ValueError in scan_host: {e}", "ERROR")
            import traceback
            self.logger(f"ValueError traceback: {traceback.format_exc()}", "ERROR")
            return {}

        except Exception as e:
            self.logger(f"Authenticated scan failed for {target}: {e}", "ERROR")
            import traceback
            self.logger(f"Exception traceback: {traceback.format_exc()}", "ERROR")
            return {}

        finally:
            try:
                if scanner and hasattr(scanner, "close"):
                    scanner.close()
            except Exception:
                pass
            