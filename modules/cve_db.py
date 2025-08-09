import requests  # Thư viện HTTP
from bs4 import BeautifulSoup  # Thư viện phân tích HTML
import re

def is_valid_cve_id(cve_id):
    # Kiểm tra định dạng CVE-YYYY-NNNN+
    return re.match(r"^CVE-\d{4}-\d{4,}$", cve_id, re.IGNORECASE) is not None

def parse_exploit_links(html):
    """Phân tích HTML và trả về danh sách link exploit."""
    soup = BeautifulSoup(html, 'html.parser')
    elements = soup.select('table#search-results a[data-exploit-id]')
    links = []
    for a_tag in elements:
        href = a_tag.get('href')
        if href:
            links.append('https://www.exploit-db.com' + href)
    return links

class ExploitDBFetcher:
    BASE_URL = 'https://www.exploit-db.com/search?cve='  # URL cơ bản để tìm kiếm theo CVE ID

    def fetch(self, cve_id, limit=None, verbose=True):
        """
        Trả về danh sách URL exploit từ Exploit-DB cho CVE_ID

        limit: số lượng exploit tối đa trả về (None = không giới hạn)
        verbose: in log ra màn hình nếu True
        """
        # Kiểm tra hợp lệ CVE ID
        if not is_valid_cve_id(cve_id):
            if verbose:
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
            if verbose:
                print(f"[ERROR] Cannot fetch {url}: {e}")
            return []

        # 4. Phân tích HTML và lấy link exploit
        links = parse_exploit_links(resp.text)
        if limit:
            links = links[:limit]

        # 5. Nếu không có exploit nào, thông báo
        if verbose and len(links) == 0:
            print(f"[INFO] No exploits found for {cve_id}")

        # 6. Trả về danh sách URL (có thể là rỗng)
        return links

if __name__ == "__main__":
    fetcher = ExploitDBFetcher()
    cve = "CVE-2023-23397"
    links = fetcher.fetch(cve, limit=5)
    print(f"Found {len(links)} exploits for {cve}:")
    for link in links:
        print(link)
