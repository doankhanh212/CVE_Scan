import requests  # Thư viện gửi HTTP (GET/POST...), đơn giản và phổ biến
from bs4 import BeautifulSoup  # Dùng để parse HTML (trích xuất thẻ, selector, v.v.)
import re  # Thư viện regex (biểu thức chính quy) để kiểm tra định dạng CVE ID

# -------------------------
# Hàm kiểm tra định dạng CVE
# -------------------------
def is_valid_cve_id(cve_id):
    """
    Kiểm tra xem chuỗi cve_id có đúng định dạng "CVE-YYYY-NNNN..." hay không.
    - ^CVE-      : bắt đầu bằng "CVE-"
    - \d{4}      : 4 chữ số cho năm (YYYY)
    - -\d{4,}$   : một dấu '-' rồi ít nhất 4 chữ số (Số định danh CVE có thể dài hơn 4 chữ số)
    - re.IGNORECASE : cho phép CVE hoặc cve (không phân biệt hoa thường)
    Trả về True nếu hợp lệ, False nếu không.
    """
    return re.match(r"^CVE-\d{4}-\d{4,}$", cve_id, re.IGNORECASE) is not None


# --------------------------------
# Hàm trích xuất link từ HTML trả về
# --------------------------------
def parse_exploit_links(html):
    """
    Phân tích HTML (string) và trả về danh sách URL exploit đầy đủ.
    - Sử dụng BeautifulSoup với parser 'html.parser'.
    - Dùng CSS selector 'table#search-results a[data-exploit-id]' để
      tìm các thẻ <a> trong bảng kết quả có attribute data-exploit-id.
      (Giả sử cấu trúc trang exploit-db có table id="search-results" và các
       link exploit có attribute data-exploit-id).
    - Ghép href với domain 'https://www.exploit-db.com' nếu href tồn tại.
    Trả về list các URL (có thể rỗng nếu không tìm thấy).
    """
    soup = BeautifulSoup(html, 'html.parser')  # Parse HTML thành DOM để truy vấn
    # Lấy tất cả thẻ <a> bên trong table#search-results có attribute data-exploit-id
    elements = soup.select('table#search-results a[data-exploit-id]')
    links = []
    for a_tag in elements:
        href = a_tag.get('href')  # lấy giá trị thuộc tính href
        if href:
            # Nếu href là đường dẫn tương đối, nối với domain chính
            links.append('https://www.exploit-db.com' + href)
    return links


# --------------------------------
# Lớp lấy exploit từ exploit-db
# --------------------------------
class ExploitDBFetcher:
    # URL cơ sở để tìm theo CVE (có thể thay đổi nếu exploit-db đổi query param)
    BASE_URL = 'https://www.exploit-db.com/search?cve='

    def fetch(self, cve_id, limit=None, verbose=True):
        """
        Tìm và trả về danh sách URL exploit từ Exploit-DB cho một CVE ID.

        Tham số:
        - cve_id (str): ví dụ "CVE-2023-23397"
        - limit (int|None): số exploit tối đa muốn lấy (None = lấy tất cả)
        - verbose (bool): nếu True in thông báo lỗi/info ra console

        Quy trình:
        1. Kiểm tra định dạng CVE (tránh gửi request vô nghĩa)
        2. Tạo URL truy vấn
        3. Gửi GET request với header (User-Agent giả) và timeout
        4. Nếu response OK -> parse HTML để tìm links
        5. Trả về danh sách links (có thể rỗng)
        """
        # 0. Kiểm tra định dạng CVE trước khi gửi request
        if not is_valid_cve_id(cve_id):
            if verbose:
                print(f"[ERROR] Invalid CVE ID: {cve_id}")
            return []  # trả về list rỗng nếu CVE không hợp lệ

        # 1. Xây dựng URL truy vấn từ BASE_URL và CVE ID
        url = f"{self.BASE_URL}{cve_id}"

        # 2. Header để giả làm trình duyệt thực, giảm khả năng bị chặn
        #    (Lưu ý: scraping vẫn phải tuân thủ robots.txt và điều khoản trang web)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # 3. Gửi HTTP GET và xử lý các lỗi kết nối/timeout/HTTP error
        try:
            # timeout=10 gián đoạn request nếu server không phản hồi trong 10s
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()  # ném exception nếu HTTP status >= 400
        except requests.RequestException as e:
            # Bắt mọi lỗi liên quan tới request (kể cả timeout, connection error, HTTPError)
            if verbose:
                print(f"[ERROR] Cannot fetch {url}: {e}")
            return []  # trả về list rỗng khi có lỗi

        # 4. Nếu thành công, parse HTML để lấy các link exploit
        links = parse_exploit_links(resp.text)

        # 5. Áp dụng giới hạn nếu có
        if limit:
            links = links[:limit]

        # 6. Nếu không tìm thấy exploit nào, in thông báo (nếu verbose)
        if verbose and len(links) == 0:
            print(f"[INFO] No exploits found for {cve_id}")

        # 7. Trả về danh sách URL (có thể rỗng)
        return links


# -------------------------
# Ví dụ sử dụng khi chạy trực tiếp file
# -------------------------
if __name__ == "__main__":
    fetcher = ExploitDBFetcher()
    cve = "CVE-2023-50071"  # CVE ví dụ
    links = fetcher.fetch(cve, limit=5)
    print(f"Found {len(links)} exploits for {cve}:")
    for link in links:
        print(link)
