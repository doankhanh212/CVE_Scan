"""
Module CPEBuilder: Xây dựng CPE (Common Platform Enumeration) string từ tên sản phẩm và phiên bản.

CPE là định dạng chuẩn để mô tả phần mềm/hệ điều hành trong các database CVE/NVD.
Ví dụ: "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"
    - a = application
    - apache = vendor
    - http_server = product
    - 2.4.49 = version

Module này cung cấp:
1. Hàm normalize tên sản phẩm (xóa ký tự đặc biệt, lowercase)
2. Lớp CPEBuilder dùng heuristic để tạo CPE khi không có CPE Dictionary

Lưu ý: Đã loại bỏ việc phụ thuộc vào CPE DB và NVD CPE API theo yêu cầu.
"""

import logging        # Thư viện logging (ghi log debug/warning/error)
import re             # Thư viện regex (biểu thức chính quy)
import os             # Path operations
from typing import List, Optional  # Type hints cho type checking

# Thiết lập logger (để ghi log debug/info/warning)
logger = logging.getLogger(__name__)
# NullHandler: không in ra console (lên client quản lý)
logger.addHandler(logging.NullHandler())





# =============================================================================
# VENDOR/PRODUCT SYNONYM MAPPING
# =============================================================================
# Map: product name (from nmap) → correct NVD vendor name
VENDOR_MAPPING = {
    # Common mismatches found in real scans
    "tinyproxy": "banu",
    "dropbear": "dropbear_ssh_project",
    "dropbear sshd": "dropbear_ssh_project",
    "mini_httpd": "acme",
    "busybox": "busybox",
    "dnsmasq": "thekelleys",
    "apache": "apache",
    "apache httpd": "apache",
    "nginx": "f5",
    "microsoft": "microsoft",
    "cisco": "cisco",
    "vmware": "vmware",
    "openssh": "openbsd",
    "openssl": "openssl",
    "mysql": "oracle",
    "mariadb": "mariadb",
    "postgresql": "postgresql",
    "redis": "redis",
    "mongodb": "mongodb",
    "php": "php",
    "python": "python",
    "java": "oracle",
}

# Product name normalization: nmap product → NVD product
PRODUCT_MAPPING = {
    "dropbear sshd": "dropbear_ssh",
    "apache httpd": "http_server",
    "microsoft sql server": "sql_server",
    "microsoft windows rpc": "windows",  # Skip generic RPC
    "microsoft httpapi httpd": "http_api",
}


def _normalize_name(name: str) -> str:
    """
    Normalize tên sản phẩm để dùng trong CPE string.
    
    Tham số:
    - name (str): tên sản phẩm (ví dụ: "Apache HTTP Server", "nginx_1.18.0")
    
    Trả về: str - tên đã normalize (lowercase, xóa ký tự đặc biệt, whitespace)
    
    Quy trình:
    1. Lấy string, xóa leading/trailing whitespace, chuyển lowercase
    2. Thay thế 1+ underscore/_/space thành 1 space (ví dụ: "http__server" -> "http server")
    3. Xóa tất cả ký tự không phải alphanumeric/space/dot/hyphen
       (chỉ giữ lại: a-z, 0-9, space, '.', '-')
    4. Trả về kết quả
    
    Ví dụ:
    - "Apache HTTP Server" -> "apache http server"
    - "nginx_1.18.0" -> "nginx 1 18 0"
    - "PHP@5.6" -> "php 5 6"
    """
    # Handle None/empty
    name = name or ""
    # Step 1: strip whitespace, convert to lowercase
    name = name.strip().lower()
    # Step 2: replace 1+ underscore/space với 1 space
    # \s = whitespace, + = 1 hoặc nhiều lần
    name = re.sub(r"[_\s]+", " ", name)
    # Step 3: xóa tất cả ký tự không phải [a-zA-Z0-9 .-]
    # \w = [a-zA-Z0-9_], nên re.sub(r"[^\w\s\.\-]", "", name) giữ lại word char/space/dot/hyphen
    name = re.sub(r"[^\w\s\.\-]", "", name)
    return name


def _looks_like_version(token: str, version: Optional[str]) -> bool:
    """Detect tokens that are version-like (e.g., 1.18.0 or match provided version)."""
    if not token:
        return False
    if version and token == version:
        return True
    return bool(re.fullmatch(r"\d+[0-9A-Za-z\.\-]*", token))


def _version_in_cpe(cpe: str, version: Optional[str]) -> bool:
    """
    Kiểm tra xem version có nằm trong CPE string hay không.
    
    Tham số:
    - cpe (str): CPE string (ví dụ: "cpe:2.3:a:apache:http_server:2.4.49:...")
    - version (str|None): version cần kiểm tra (ví dụ: "2.4.49")
    
    Trả về: bool
    - True nếu version không rỗng và nằm trong CPE string (substring match)
    - False nếu version là None/rỗng hoặc không nằm trong CPE
    
    Ví dụ:
    - _version_in_cpe("cpe:2.3:a:apache:http_server:2.4.49:*:*:*", "2.4.49") -> True
    - _version_in_cpe("cpe:2.3:a:apache:http_server:2.4.50:*:*:*", "2.4.49") -> False
    - _version_in_cpe("cpe:2.3:a:apache:http_server:*:*:*", None) -> False
    """
    # Nếu version rỗng hoặc None, trả về False (không thể match)
    if not version:
        return False
    # Kiểm tra version có substring trong CPE hay không
    return version in cpe


class CPEBuilder:
    """
    Lớp xây dựng CPE (Common Platform Enumeration) string từ tên/version sản phẩm.
    
    Phương pháp: Heuristic generation dựa trên tên và version sản phẩm.
    
    CPE format: "cpe:2.3:{type}:{vendor}:{product}:{version}:{update}:..."
    - type: a (application), o (operating system), h (hardware)
    - vendor: tên nhà cung cấp (lowercase)
    - product: tên sản phẩm (lowercase, underscore thay space)
    - version: phiên bản sản phẩm (hoặc '*' nếu any version)
    """
    
    def __init__(self, api_key: Optional[str] = None, cpe_db_path: Optional[str] = None):
        """
        Khởi tạo CPEBuilder instance.
        
        Lưu ý: Tham số api_key và cpe_db_path được giữ để tương thích ngược,
        nhưng không được sử dụng. Builder chỉ dùng heuristic generation.
        """
        # Không sử dụng; giữ để tương thích API
        self.api_key = None
        self.cpe_db_path = None
    


    def find_cpe_candidates(
        self,
        product_name: str,
        version: Optional[str] = None,
        max_results: int = 10,
        use_remote: bool = True
    ) -> List[str]:
        """
        Tìm CPE candidates từ tên/version sản phẩm.
        
        Tham số:
        - product_name (str): tên sản phẩm (ví dụ: "Apache", "nginx 1.18.0")
        - version (str|None): phiên bản (ví dụ: "1.18.0", mặc định None)
        - max_results (int): số CPE tối đa trả về (mặc định 10)
        - use_remote (bool): có query NVD API hay không (mặc định True)
        
        Trả về: list[str] - danh sách CPE strings, ưu tiên những có chính xác version
        
        Quy trình:
        
        1. Normalize tên sản phẩm
        2. Extract vendor và product từ tên (dùng VENDOR_MAPPING và PRODUCT_MAPPING)
        3. Generate CPE templates:
           - cpe:2.3:a:{vendor}:{product}:{version}:*:*:*:*:*:*:*  (app, exact version)
           - cpe:2.3:a:{vendor}:{product}:*:*:*:*:*:*:*:*         (app, any version)
           - cpe:2.3:o:{vendor}:{product}:{version}:*:*:*:*:*:*:*  (OS, exact version)
        4. Return top max_results
        - product_name="Apache", version="2.4.49"
          -> DB/NVD return: ["cpe:2.3:a:apache:http_server:2.4.49:..."]
        - product_name="unknown_app", version=None
          -> Heuristic return: ["cpe:2.3:a:unknown:unknown_app:*:...", ...]
        """
        # Normalize product name (lowercase, remove special chars, etc)
        name_norm = _normalize_name(product_name)
        candidates = []

        # === Heuristic Fallback ===
        # Split normalized name thành từng từ và loại bỏ token giống version
        parts = name_norm.split()
        core_parts = [p for p in parts if not _looks_like_version(p, version)] or parts or [name_norm]

        # Use vendor/product mapping for better accuracy
        base_product = "_".join(core_parts[:2]) if len(core_parts) >= 2 else (core_parts[0] if core_parts else name_norm.replace(" ", "_"))
        
        # Check product mapping first (more specific)
        mapped_product = PRODUCT_MAPPING.get(name_norm) or PRODUCT_MAPPING.get(base_product)
        
        # Check vendor mapping
        vendor_key = name_norm.split()[0] if name_norm else ""
        mapped_vendor = VENDOR_MAPPING.get(name_norm) or VENDOR_MAPPING.get(vendor_key) or VENDOR_MAPPING.get(base_product)
        
        # Use mapped values or fallback to parsed values
        if mapped_vendor and mapped_product:
            vendor, product = mapped_vendor, mapped_product
        elif mapped_vendor:
            vendor = mapped_vendor
            product = mapped_product or base_product
        elif mapped_product:
            vendor = core_parts[0] if core_parts else name_norm
            product = mapped_product
        else:
            # Fallback to heuristic
            vendor = core_parts[0] if core_parts else name_norm
            product = base_product

        # Generate heuristic CPE templates
        heuristics = [
            # Template 1: Application, explicit version
            f"cpe:2.3:a:{vendor}:{product}:{version or '*'}:*:*:*:*:*:*:*",
            # Template 2: Application, any version (generic)
            f"cpe:2.3:a:{vendor}:{product}:*:*:*:*:*:*:*:*",
            # Template 3: Operating System, explicit version (nếu là OS)
            f"cpe:2.3:o:{vendor}:{product}:{version or '*'}:*:*:*:*:*:*:*",
        ]

        # Clean up heuristic CPEs (remove "None" strings, fix double colons)
        final = []
        for h in heuristics:
            h = h.replace("None", "*").replace("::", ":")
            if h not in final:
                final.append(h)

        return final[:max_results]


def build_cpe(product_name: str, version: Optional[str] = None, use_remote: bool = False) -> str:
    """
    Tiện ích: xây dựng 1 CPE string từ tên và version (quick interface).

    Tham số:
    - product_name (str): tên sản phẩm (ví dụ: "Apache HTTP Server")
    - version (str|None): phiên bản (ví dụ: "2.4.49")
    - use_remote (bool): (deprecated) không còn được sử dụng

    Trả về: str - CPE string (hoặc "N/A" nếu lỗi)

    Quy trình:
    1. Tạo CPEBuilder instance (không API key)
    2. Gọi find_cpe_candidates(use_remote=use_remote) để tìm CPE
    3. Return CPE đầu tiên từ danh sách (best match)
    4. Nếu không có kết quả hoặc exception, return "N/A"
    """
    try:
        # Tạo CPEBuilder instance (heuristic-only)
        cb = CPEBuilder()
        # Tìm CPE candidates (heuristic)
        r = cb.find_cpe_candidates(product_name, version, use_remote=False)
        # Return CPE đầu tiên (best match), hoặc "N/A" nếu danh sách rỗng
        return r[0] if r else "N/A"
    except Exception:
        # Nếu có lỗi, return "N/A" (silent fail)
        return "N/A"
