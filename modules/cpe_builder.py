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
2. Lớp CPEBuilder để tìm CPE từ NVD API
3. Heuristic CPE generation nếu NVD API không có kết quả
"""

import logging        # Thư viện logging (ghi log debug/warning/error)
import re             # Thư viện regex (biểu thức chính quy)
from typing import List, Optional  # Type hints cho type checking

# Cố gắng import nvdlib (library Python để query NVD API)
try:
    import nvdlib
    # Config: delay để không quá tải server NVD
    try:
        nvdlib.config.delay = 1.5  # Delay 1.5s giữa các request (nếu không dùng API key)
    except Exception:
        pass
except Exception:
    # Nếu nvdlib không cài đặt, set thành None (sẽ dùng heuristic fallback)
    nvdlib = None

# Thiết lập logger (để ghi log debug/info/warning)
logger = logging.getLogger(__name__)
# NullHandler: không in ra console (lên client quản lý)
logger.addHandler(logging.NullHandler())


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
    
    Phương pháp:
    1. Nếu nvdlib có sẵn + use_remote=True: query NVD API để tìm CPE chính xác
    2. Nếu NVD API không có kết quả: dùng heuristic để generate CPE
    
    CPE format: "cpe:2.3:{type}:{vendor}:{product}:{version}:{update}:..."
    - type: a (application), o (operating system), h (hardware)
    - vendor: tên nhà cung cấp (lowercase)
    - product: tên sản phẩm (lowercase, underscore thay space)
    - version: phiên bản sản phẩm (hoặc '*' nếu any version)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Khởi tạo CPEBuilder instance.
        
        Tham số:
        - api_key (str|None): NVD API key để tăng rate limit
                              (mặc định None: free tier 1 request/6s)
        
        Hành động:
        - Lưu api_key
        - Nếu nvdlib có sẵn + api_key được cung cấp: config nvdlib
          - Set API key
          - Set delay=0.8s (free tier không cần delay dài nếu có API key)
        """
        self.api_key = api_key
        # Nếu nvdlib cài đặt và có API key, config với API key
        if nvdlib and api_key:
            try:
                nvdlib.config.apikey = api_key
                # Delay ngắn hơn khi dùng API key (high rate limit)
                nvdlib.config.delay = 0.8
            except Exception:
                # Nếu config fail, pass silently (nvdlib có thể không support)
                pass

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
        
        === Phase 1: Query NVD API (nếu use_remote=True và nvdlib có sẵn) ===
        1. Normalize tên sản phẩm
        2. Query NVD API bằng nvdlib.searchCPE()
        3. Với mỗi kết quả:
           - Nếu normalized tên nằm trong CPE -> thêm vào candidates
           - Nếu version match trong CPE -> insert vào đầu (ưu tiên)
        4. Loại bỏ duplicate, return top max_results
        
        === Phase 2: Heuristic fallback (nếu NVD trả rỗng hoặc error) ===
        1. Extract vendor (từ đầu tiên) và product (2 từ đầu) từ name
        2. Generate 3 CPE template:
           - cpe:2.3:a:{vendor}:{product}:{version}:*:*:*:*:*:*:*  (app, exact version)
           - cpe:2.3:a:{vendor}:{product}:*:*:*:*:*:*:*:*         (app, any version)
           - cpe:2.3:o:{vendor}:{product}:{version}:*:*:*:*:*:*:*  (OS, exact version)
        3. Return top max_results
        
        Ví dụ:
        - product_name="Apache", version="2.4.49"
          -> NVD return: ["cpe:2.3:a:apache:http_server:2.4.49:..."]
        - product_name="unknown_app", version=None
          -> Heuristic return: ["cpe:2.3:a:unknown:unknown_app:*:...", ...]
        """
        # Normalize product name (lowercase, remove special chars, etc)
        name_norm = _normalize_name(product_name)
        candidates = []

        # === Phase 1: Query NVD API ===
        if use_remote and nvdlib is not None:
            try:
                # Log: tìm CPE từ NVD
                logger.info(f"Querying NVD for CPE: '{name_norm}'")
                # Query NVD API: searchCPE(keywordSearch=...)
                # Trả về list CPE objects
                results = nvdlib.searchCPE(keywordSearch=name_norm)
                # Duyệt từng kết quả
                for item in results:
                    # Lấy cpeName attribute từ item (CPE string)
                    cpe = getattr(item, "cpeName", None)
                    if not cpe:
                        # Skip nếu không có cpeName
                        continue
                    # Nếu normalized tên nằm trong CPE (case-insensitive)
                    if name_norm in cpe.lower():
                        candidates.append(cpe)
                    # Nếu version được cung cấp và version nằm trong CPE
                    if version and _version_in_cpe(cpe.lower(), version):
                        # Insert vào đầu (ưu tiên version chính xác)
                        candidates.insert(0, cpe)
                
                # Loại bỏ duplicate (giữ thứ tự)
                output = []
                for x in candidates:
                    if x not in output:
                        output.append(x)
                
                # Nếu có kết quả, return top max_results
                if output:
                    return output[:max_results]
            except Exception as e:
                # Log warning nếu NVD query fail
                logger.warning(f"NVD searchCPE error: {e}")

        # === Phase 2: Heuristic Fallback ===
        # Split normalized name thành từng từ
        parts = name_norm.split()
        # Vendor: từ đầu tiên (ví dụ: "apache http server" -> vendor="apache")
        vendor = parts[0] if parts else name_norm
        # Product: 2 từ đầu nối bằng underscore
        # (ví dụ: "apache http server" -> product="apache_http")
        product = "_".join(parts[:2]) if len(parts) >= 2 else name_norm.replace(" ", "_")

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


def build_cpe(product_name: str, version: Optional[str] = None) -> str:
    """
    Tiện ích: xây dựng 1 CPE string từ tên và version (quick interface).
    
    Tham số:
    - product_name (str): tên sản phẩm (ví dụ: "Apache HTTP Server")
    - version (str|None): phiên bản (ví dụ: "2.4.49")
    
    Trả về: str - CPE string (hoặc "N/A" nếu lỗi)
    
    Quy trình:
    1. Tạo CPEBuilder instance (không API key)
    2. Gọi find_cpe_candidates() để tìm CPE
    3. Return CPE đầu tiên từ danh sách (best match)
    4. Nếu không có kết quả hoặc exception, return "N/A"
    
    Ví dụ:
    - build_cpe("Apache", "2.4.49")
      -> "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*"
    - build_cpe("unknown_product", None)
      -> "cpe:2.3:a:unknown:unknown_product:*:*:*:*:*:*:*:*" (heuristic)
    - build_cpe("") -> "N/A" (lỗi hoặc không tìm thấy)
    """
    try:
        # Tạo CPEBuilder instance (mặc định: use NVD API nếu có)
        cb = CPEBuilder()
        # Tìm CPE candidates
        r = cb.find_cpe_candidates(product_name, version)
        # Return CPE đầu tiên (best match), hoặc "N/A" nếu danh sách rỗng
        return r[0] if r else "N/A"
    except Exception:
        # Nếu có lỗi, return "N/A" (silent fail)
        return "N/A"
