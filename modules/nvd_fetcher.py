import nvdlib  # Thư viện tương tác với NVD API (nvdlib cung cấp các hàm searchCVE, getCVE,...)
from modules.cve_db import ExploitDBFetcher  # Lớp xử lý việc tìm PoC/Exploit từ Exploit-DB


def get_base_score(detail):
    """
    Trích xuất điểm CVSS (base score) từ đối tượng `detail` trả về bởi nvdlib.getCVE.

    Chi tiết:
    - Một CVE có thể có nhiều metric (CVSS v3.1, v3.0, v2). Ta ưu tiên lấy theo
      thứ tự: cvssMetricV31 -> cvssMetricV30 -> cvssMetricV2.
    - Hàm này dùng `hasattr` và `getattr` để truy cập an toàn các thuộc tính có thể không tồn tại.
    - Trả về `raw_score` (số) hoặc `None` nếu không tìm thấy.
    """
    raw_score = None  # Giá trị khởi tạo cho điểm CVSS

    # Kiểm tra xem detail có chứa thuộc tính 'metrics' hay không
    if hasattr(detail, 'metrics'):
        # Danh sách tên metric theo thứ tự ưu tiên
        metrics_order = ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']
        idx = 0
        # Dùng while để duyệt qua danh sách metrics
        while idx < len(metrics_order):
            metric_name = metrics_order[idx]
            # Lấy ra list metric nếu có (getattr sẽ trả về None nếu không có)
            metric_list = getattr(detail.metrics, metric_name, None)
            if metric_list:
                # metric_list kỳ vọng là list; lấy baseScore của mục đầu tiên
                # (thông thường NVD trả về list các metric phiên bản)
                raw_score = metric_list[0].cvssData.baseScore
                break  # đã lấy được score, thoát vòng while
            idx += 1
    return raw_score


class NVDFetcher:
    """
    Lớp NVDFetcher: tìm CVE từ NVD và bổ sung các link exploit từ Exploit-DB.

    - __init__(api_key): nhận API key (có thể là None nếu không có key);
      nvdlib dùng key nếu cần để tăng giới hạn truy vấn.
    - search_cves(keyword, results_per_page): tìm CVE theo từ khóa và trả về
      danh sách dict có các trường: id, severity, score, desc, exploits.
    """

    def __init__(self, api_key=None):
        # Lưu API key (nếu có) vào instance
        self.api_key = api_key
        # Khởi tạo ExploitDBFetcher để bổ sung PoC/Exploit URL từ exploit-db
        self.exploit_fetcher = ExploitDBFetcher()

    def search_cves(self, keyword, results_per_page=5):
        """
        Tìm CVE theo keyword.

        Tham số:
        - keyword (str): chuỗi tìm kiếm (ví dụ: "apache 2.4.49" hoặc "nginx")
        - results_per_page (int): số lượng bản ghi trả về tối đa từ NVD

        Trả về:
        - list các dict, mỗi dict có keys: 'id', 'severity', 'score', 'desc', 'exploits'
        """
        # Validate input: keyword nên có ít nhất 3 ký tự
        if not keyword or len(keyword.strip()) < 3:
            print("[ERROR] Keyword quá ngắn hoặc rỗng.")
            return []

        cves = []  # Danh sách kết quả sẽ trả về
        try:
            # Log debug
            print(f"[DEBUG] Querying NVD for: {keyword}")

            # Gọi nvdlib.searchCVE để tìm các entry phù hợp với keyword
            # Tham số key=self.api_key sẽ truyền API key nếu có
            entries = nvdlib.searchCVE(
                keywordSearch=keyword,
                key=self.api_key,
                limit=results_per_page
            )

            # Duyệt danh sách entries bằng while (theo tiêu chí của bạn là tránh for lồng nhau)
            idx_entry = 0
            while idx_entry < len(entries):
                e = entries[idx_entry]

                # Một số entry trả về từ searchCVE đã chứa đầy đủ thông tin, nhưng
                # để đảm bảo có được các chi tiết như CVSS, ta cố gắng gọi getCVE.
                try:
                    detail = nvdlib.getCVE(e.id, key=self.api_key)
                except Exception:
                    # Nếu getCVE lỗi (ví dụ rate-limit hoặc dữ liệu không tìm thấy),
                    # fallback về object entry ban đầu `e` (có thể ít thông tin hơn).
                    detail = e

                # Lấy điểm CVSS base (nếu có)
                raw_score = get_base_score(detail)
                print(f"[DEBUG] CVE {e.id} raw_score: {raw_score}")

                # Chuyển đổi raw_score thành severity theo thang CVSS
                if isinstance(raw_score, (int, float)):
                    score = raw_score
                    if score >= 9.0:
                        severity = 'Critical'
                    elif score >= 7.0:
                        severity = 'High'
                    elif score >= 4.0:
                        severity = 'Medium'
                    else:
                        severity = 'Low'
                else:
                    # Nếu không có điểm số, thử lấy severity trực tiếp từ detail
                    # Một số đối tượng detail có thể có thuộc tính v3severity hoặc v2severity
                    severity = getattr(detail, 'v3severity', None) or getattr(detail, 'v2severity', 'N/A')
                    score = 'N/A'

                # Lấy mô tả CVE: detail.descriptions thường là list các objects
                # Mỗi object có `.value` chứa đoạn mô tả (lấy phần tử đầu nếu có)
                desc = detail.descriptions[0].value if getattr(detail, 'descriptions', None) else ''

                # Lấy các URL tham khảo có sẵn trong detail.references
                exploits = []
                refs = getattr(detail, 'references', [])
                j = 0
                # Dùng while để duyệt danh sách references
                while j < len(refs):
                    url = getattr(refs[j], 'url', '')
                    # Nếu reference chứa exploit-db, thêm vào danh sách exploits
                    if 'exploit-db.com' in url:
                        exploits.append(url)
                    j += 1

                # Nếu e.id là dạng CVE (bắt đầu bằng 'CVE-'), gọi ExploitDBFetcher
                # để tìm thêm PoC/exploit URL từ trang exploit-db (scraping hoặc API)
                if e.id.upper().startswith("CVE-"):
                    try:
                        exploits += self.exploit_fetcher.fetch(e.id)
                    except Exception as _ex:
                        # Nếu Fetcher lỗi, in debug nhưng không dừng toàn bộ flow
                        print(f"[WARN] ExploitDB fetch failed for {e.id}: {_ex}")

                # Loại trùng exploit bằng cách duyệt và giữ các URL unique
                unique_exploits = []
                k = 0
                while k < len(exploits):
                    if exploits[k] not in unique_exploits:
                        unique_exploits.append(exploits[k])
                    k += 1

                # Thêm đối tượng CVE đã chuẩn hoá vào danh sách kết quả
                cves.append({
                    'id': detail.id,
                    'severity': severity,
                    'score': score,
                    'desc': desc if desc else "(No description)",
                    'exploits': unique_exploits
                })

                # Tăng chỉ số để duyệt sang entry tiếp theo
                idx_entry += 1
        except Exception as ex:
            # Bắt lỗi tổng quát khi gọi NVD (network, rate limit, v.v.)
            print(f"[ERROR] NVD fetch fail for {keyword}: {ex}")

        # Trả về danh sách CVE đã thu thập (có thể rỗng nếu không tìm thấy)
        return cves


# Nếu chạy file này trực tiếp (dùng để test nhanh)
if __name__ == "__main__":
    fetcher = NVDFetcher()
    results = fetcher.search_cves("apache", results_per_page=2)
    for cve in results:
        print(cve)
