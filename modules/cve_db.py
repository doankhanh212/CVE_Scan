import requests  # Thư viện HTTP
from bs4 import BeautifulSoup  # Thư viện phân tích HTML
import re

def is_valid_cve_id(cve_id):
    # Kiểm tra định dạng CVE-YYYY-NNNN+
    return re.match(r"^CVE-\d{4}-\d{4,}$", cve_id, re.IGNORECASE) is not None

class ExploitDBFetcher:
    BASE_URL = 'https://www.exploit-db.com/search?cve='  # URL cơ bản để tìm kiếm theo CVE ID

    def fetch(self, cve_id):
        """
        Trả về danh sách URL exploit từ Exploit-DB cho CVE_ID
        """
        # Kiểm tra hợp lệ CVE ID
        if not is_valid_cve_id(cve_id):
            print(f"[ERROR] Invalid CVE ID: {cve_id}")
            return []

        # 1. Xây dựng URL truy vấn từ BASE_URL và CVE ID
        url = f"{self.BASE_URL}{cve_id}"

        # 2. Cấu hình header để tránh bị chặn (fake User-Agent)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # 3. Gửi HTTP GET và xử lý lỗi
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()  # nếu code >=400, ném exception
        except requests.RequestException as e:
            print(f"[ERROR] Cannot fetch {url}: {e}")
            return []

        # 4. Phân tích HTML bằng BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 5. Tìm các thẻ <a> chứa data-exploit-id và thu link
        elements = soup.select('table#search-results a[data-exploit-id]')
        links = []
        idx = 0
        while idx < len(elements):
            a_tag = elements[idx]
            href = a_tag.get('href')  # đường dẫn tương đối
            if href:
                full_url = 'https://www.exploit-db.com' + href
                links.append(full_url)
            idx += 1

        # 6. Nếu không có exploit nào, thông báo
        if len(links) == 0:
            print(f"[INFO] No exploits found for {cve_id}")

        # 7. Trả về danh sách URL (có thể là rỗng)
        return links
