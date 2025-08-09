import nvdlib  # Thư viện tương tác với NVD API
from modules.cve_db import ExploitDBFetcher  # Lấy PoC từ Exploit-DB

def get_base_score(detail):
    """
    Trích xuất điểm CVSS từ detail object của nvdlib.getCVE.
    """
    raw_score = None  # Giá trị khởi tạo cho điểm CVSS
    # Kiểm tra xem detail có chứa metrics không
    if hasattr(detail, 'metrics'):
        metrics_order = ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']
        idx = 0
        # Dùng while duyệt qua thứ tự ưu tiên của các metric
        while idx < len(metrics_order):
            metric_name = metrics_order[idx]
            metric_list = getattr(detail.metrics, metric_name, None)
            if metric_list:
                # Lấy baseScore đầu tiên của metric
                raw_score = metric_list[0].cvssData.baseScore
                break
            idx += 1
    return raw_score

class NVDFetcher:
    def __init__(self, api_key=None):
        # API key để truy cập NVD
        self.api_key = api_key
        # Khởi tạo ExploitDBFetcher để bổ sung PoC
        self.exploit_fetcher = ExploitDBFetcher()

    def search_cves(self, keyword, results_per_page=5):
        """
        Tìm CVE theo keyword, trả về list dict các CVE:
        {id, severity, score, desc, exploits}
        """
        if not keyword or len(keyword.strip()) < 3:
            print("[ERROR] Keyword quá ngắn hoặc rỗng.")
            return []
        cves = []
        try:
            print(f"[DEBUG] Querying NVD for: {keyword}")
            # Lấy danh sách CVE cơ bản
            entries = nvdlib.searchCVE(
                keywordSearch=keyword,
                key=self.api_key,
                limit=results_per_page
            )
            idx_entry = 0
            # Dùng while để duyệt entries
            while idx_entry < len(entries):
                e = entries[idx_entry]
                # Lấy detail để có CVSS score
                try:
                    detail = nvdlib.getCVE(e.id, key=self.api_key)
                except Exception:
                    detail = e

                # Trích xuất điểm CVSS
                raw_score = get_base_score(detail)
                print(f"[DEBUG] CVE {e.id} raw_score: {raw_score}")

                # Xác định severity
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
                    severity = getattr(detail, 'v3severity', None) or getattr(detail, 'v2severity', 'N/A')
                    score = 'N/A'

                # Lấy mô tả CVE
                desc = detail.descriptions[0].value if getattr(detail, 'descriptions', None) else ''

                # Lấy PoC từ references của NVD
                exploits = []
                refs = getattr(detail, 'references', [])
                j = 0
                while j < len(refs):
                    url = getattr(refs[j], 'url', '')
                    if 'exploit-db.com' in url:
                        exploits.append(url)
                    j += 1
                # Bổ sung PoC từ Exploit-DB (chỉ khi là CVE ID hợp lệ)
                if e.id.upper().startswith("CVE-"):
                    exploits += self.exploit_fetcher.fetch(e.id)

                # Loại trùng exploit
                unique_exploits = []
                k = 0
                while k < len(exploits):
                    if exploits[k] not in unique_exploits:
                        unique_exploits.append(exploits[k])
                    k += 1

                # Đưa vào kết quả
                cves.append({
                    'id': detail.id,
                    'severity': severity,
                    'score': score,
                    'desc': desc if desc else "(No description)",
                    'exploits': unique_exploits
                })
                idx_entry += 1
        except Exception as ex:
            print(f"[ERROR] NVD fetch fail for {keyword}: {ex}")
        return cves

if __name__ == "__main__":
    fetcher = NVDFetcher()
    results = fetcher.search_cves("apache", results_per_page=2)
    for cve in results:
        print(cve)
