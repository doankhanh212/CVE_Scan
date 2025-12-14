"""
Module CVEDatabase/ExploitDB: Tìm kiếm exploit từ Exploit-DB website.
- Cung cấp hàm kiểm tra định dạng CVE ID
- Cung cấp hàm parse HTML response để tìm exploit links
- Cung cấp lớp ExploitDBFetcher để truy vấn exploit-db.com
"""

import requests    # Thư viện gửi HTTP GET/POST request
from bs4 import BeautifulSoup  # Thư viện parse HTML và trích xuất dữ liệu
import re          # Thư viện biểu thức chính quy (regex) để validation

# -------------------------
# Hàm kiểm tra định dạng CVE
# -------------------------
def is_valid_cve_id(cve_id):
    """
    Kiểm tra xem chuỗi có phải CVE ID hợp lệ (dạng "CVE-YYYY-NNNN...").
    
    Quy trình:
    1. Match với regex pattern: ^CVE-\d{4}-\d{4,}$
       - ^CVE-      : bắt đầu bằng "CVE-"
       - \d{4}      : 4 chữ số cho năm (YYYY)
       - -\d{4,}$   : dấu '-' rồi ít nhất 4 chữ số cho ID
    2. Không phân biệt hoa/thường (re.IGNORECASE)
    3. Trả về True nếu match, False nếu không
    """
    return re.match(r"^CVE-\d{4}-\d{4,}$", cve_id, re.IGNORECASE) is not None


# --------------------------------
# Hàm trích xuất link từ HTML trả về
# --------------------------------
def parse_exploit_links(html):
    """
    Parse HTML response từ Exploit-DB và trích xuất danh sách exploit URLs.
    
    Tham số:
    - html (str): HTML content từ response của exploit-db.com/search
    
    Trả về: list URLs exploit (có thể rỗng nếu không tìm thấy)
    
    Quy trình:
    1. Parse HTML string thành BeautifulSoup DOM object
    2. Dùng CSS selector 'table#search-results a[data-exploit-id]' để tìm links:
       - 'table#search-results'     : bảng chứa kết quả tìm kiếm
       - 'a[data-exploit-id]'       : thẻ <a> có attribute data-exploit-id
    3. Với mỗi thẻ <a> tìm được, lấy href attribute
    4. Nếu href tương đối, nối với domain https://www.exploit-db.com
    5. Trả về danh sách URLs đầy đủ
    """
    # Parse HTML string thành DOM tree
    soup = BeautifulSoup(html, 'html.parser')
    # Dùng CSS selector để tìm tất cả exploit links trong bảng kết quả
    elements = soup.select('table#search-results a[data-exploit-id]')
    links = []
    # Duyệt từng thẻ <a> tìm được
    for a_tag in elements:
        # Lấy giá trị href attribute từ thẻ <a>
        href = a_tag.get('href')
        if href:
            # Nếu href là đường dẫn tương đối (/exploit/...), nối với domain
            links.append('https://www.exploit-db.com' + href)
    return links


# --------------------------------
# Lớp lấy exploit từ exploit-db
# --------------------------------
class ExploitDBFetcher:
    """
    Lớp tìm kiếm exploit từ Exploit-DB (exploit-db.com).
    - Truy vấn exploit-db.com qua HTTP
    - Parse HTML response để trích xuất exploit URLs
    """
    
    # URL cơ sở để tìm kiếm theo CVE ID (có thể thay đổi nếu exploit-db đổi query param)
    BASE_URL = 'https://www.exploit-db.com/search?cve='

    def fetch(self, cve_id, limit=None, verbose=True):
        """
        Tìm kiếm và trả về danh sách exploit URLs từ Exploit-DB cho một CVE ID.

        Tham số:
        - cve_id (str): CVE ID cần tìm (ví dụ: "CVE-2023-23397")
        - limit (int|None): số exploit tối đa muốn lấy (None = lấy tất cả)
        - verbose (bool): nếu True sẽ in thông báo debug/error ra console

        Trả về: list URLs exploit (có thể rỗng nếu không tìm thấy hoặc lỗi)

        Quy trình:
        1. Kiểm tra CVE ID hợp lệ bằng is_valid_cve_id()
        2. Xây dựng URL truy vấn từ BASE_URL + CVE ID
        3. Gửi HTTP GET request với User-Agent header (giả làm trình duyệt)
        4. Xử lý exception: connection error, timeout, HTTP error
        5. Nếu thành công, parse HTML bằng parse_exploit_links()
        6. Áp dụng giới hạn số exploit nếu có
        7. Trả về danh sách URLs
        """
        # 0. Kiểm tra định dạng CVE ID trước khi gửi request
        if not is_valid_cve_id(cve_id):
            if verbose:
                print(f"[ERROR] Invalid CVE ID: {cve_id}")
            return []  # Trả về list rỗng nếu CVE format không hợp lệ

        # 1. Xây dựng URL truy vấn
        url = f"{self.BASE_URL}{cve_id}"

        # 2. Header User-Agent để giả làm trình duyệt thực
        #    (Giảm khả năng bị server chặn, tuân thủ robots.txt)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # 3. Gửi HTTP GET request
        try:
            # timeout=10: gián đoạn request nếu server không phản hồi trong 10 giây
            resp = requests.get(url, headers=headers, timeout=10)
            # raise_for_status(): ném exception nếu HTTP status >= 400 (404, 403, 500, etc.)
            resp.raise_for_status()
        except requests.RequestException as e:
            # Bắt tất cả requests exceptions: connection error, timeout, HTTPError, etc.
            if verbose:
                print(f"[ERROR] Cannot fetch {url}: {e}")
            return []  # Trả về list rỗng khi có lỗi

        # 4. Nếu thành công, parse HTML để lấy danh sách exploit URLs
        links = parse_exploit_links(resp.text)

        # 5. Áp dụng giới hạn số exploit nếu user chỉ định limit
        if limit:
            links = links[:limit]

        # 6. Log nếu không tìm thấy exploit nào (nếu verbose=True)
        if verbose and len(links) == 0:
            print(f"[INFO] No exploits found for {cve_id}")

        # 7. Trả về danh sách URLs
        return links


# -------------------------
# Ví dụ sử dụng khi chạy trực tiếp file
# -------------------------
if __name__ == "__main__":
    # Khởi tạo ExploitDBFetcher instance
    fetcher = ExploitDBFetcher()
    # CVE ID ví dụ để test
    cve = "CVE-2023-50071"
    # Tìm exploit URLs cho CVE này, tối đa 5 kết quả
    links = fetcher.fetch(cve, limit=5)
    # In kết quả
    print(f"Found {len(links)} exploits for {cve}:")
    for link in links:
        print(link)
