"""
CVE Matcher Module (OpenVAS-style)
---------------------------------
Nhiệm vụ:
- Nhận CPE string
- Query CVE từ NVD (qua NVDFetcherPRO)
- Chuẩn hóa dữ liệu CVE dùng chung cho scanner / GUI / report

Chuẩn output (enterprise-ready):

{
    "id": "CVE-2023-12345",
    "description": {
        "short": "...",
        "full": "..."
    },
    "severity": {
        "label": "HIGH",
        "score": 7.8,
        "vector": "CVSS:3.1/AV:N/AC:L/...",
        "version": "3.1"
    },
    "cvss4": {
        "score": null,
        "vector": null
    },
    "references": [...],
    "source": "NVD"
}
"""

from typing import List, Dict, Optional
import logging

try:
    from modules.cve.nvd_fetcher import NVDFetcherPRO
except Exception:
    try:
        from nvd_fetcher import NVDFetcherPRO
    except Exception:
        NVDFetcherPRO = None


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CVEMatcher:
    """
    CVEMatcher
    ----------
    - Normalize CVE từ nhiều nguồn
    - Hiện tại hỗ trợ: NVD
    - KHÔNG được làm crash pipeline
    """

    def __init__(self, api_key: Optional[str] = None, local_db_path: Optional[str] = None):
        self.fetcher = None

        # Prefer local DB fetcher when provided
        if local_db_path:
            try:
                from modules.cve.local_db_fetcher import LocalDBFetcher
                self.fetcher = LocalDBFetcher(db_path=local_db_path)
                logger.info("Using LocalDBFetcher: %s", local_db_path)
                return
            except Exception as e:
                logger.error("Init LocalDBFetcher failed: %s", e)
                self.fetcher = None

        if NVDFetcherPRO is None:
            logger.warning("NVDFetcherPRO import failed — CVE disabled")
            return

        try:
            self.fetcher = NVDFetcherPRO(api_key=api_key)
        except Exception as e:
            logger.error("Init NVDFetcherPRO failed: %s", e)
            self.fetcher = None

    # ==================================================
    # PUBLIC
    # ==================================================
    def match_by_cpe(self, cpe: str, max_results: int = 50) -> List[Dict]:
        if not cpe or cpe == "N/A":
            return []

        if not self.fetcher:
            # 🔥 CHỐT: KHÔNG ĐƯỢC CRASH
            return []

        try:
            raw_cves = self.fetcher.get_cve_by_cpe(
                cpe,
                max_results=max_results
            )
        except Exception as e:
            logger.error("Fetch CVE failed for %s: %s", cpe, e)
            raw_cves = []

        # If no exact matches and we have a local DB fetcher with fuzzy capabilities,
        # attempt fuzzy matching to increase recall.
        if not raw_cves:
            try:
                # LocalDBFetcher exposes fuzzy_match_cpe_to_cve or the matcher may do fuzzy itself
                if hasattr(self.fetcher, 'fuzzy_match_cpe_to_cve'):
                    logger.info("No exact CVEs for %s — trying fuzzy DB lookup", cpe)
                    raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe)
                else:
                    # As a fallback, import matcher and run fuzzy against a cursor if possible
                    try:
                        from modules.cve.local_db_fetcher import LocalDBFetcher
                        if isinstance(self.fetcher, LocalDBFetcher):
                            logger.info("Using LocalDBFetcher fuzzy matcher for %s", cpe)
                            raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe)
                    except Exception:
                        raw_cves = []
            except Exception as e:
                logger.debug("Fuzzy lookup failed for %s: %s", cpe, e)
                raw_cves = []

        return self._normalize(raw_cves)

    # ==================================================
    # INTERNAL
    # ==================================================
    def _normalize(self, raw_cves: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []

        for item in raw_cves:
            try:
                cve = item.get("cve", {}) if isinstance(item, dict) else {}

                cve_id = self._extract_id(cve)
                description = self._extract_description(cve)
                severity = self._extract_cvss(cve)
                references = self._extract_references(cve)

                normalized.append({
                    "id": cve_id,
                    "description": description,
                    "severity": severity,
                    # 🔮 chuẩn bị cho CVSS 4.0
                    "cvss4": self._extract_cvss4(cve),
                    "references": references,
                    "source": "NVD"
                })

            except Exception as e:
                logger.debug("Normalize CVE failed: %s", e)
                continue

        return normalized

    # ==================================================
    # EXTRACTORS
    # ==================================================
    def _extract_id(self, cve: Dict) -> str:
        return (
            cve.get("id")
            or cve.get("CVE_data_meta", {}).get("ID")
            or "N/A"
        )

    def _extract_description(self, cve: Dict) -> Dict:
        full = ""
        for d in cve.get("descriptions", []):
            if d.get("lang") in ("en", None):
                full = d.get("value", "")
                break

        return {
            "short": full[:200] if full else "",
            "full": full
        }

    def _extract_cvss(self, cve: Dict) -> Dict:
        metrics = cve.get("metrics", {}) or {}

        # Priority: CVSS 3.1 > 3.0 > 2.0
        if "cvssMetricV31" in metrics:
            return self._parse_cvss(metrics["cvssMetricV31"][0], "3.1")
        if "cvssMetricV30" in metrics:
            return self._parse_cvss(metrics["cvssMetricV30"][0], "3.0")
        if "cvssMetricV2" in metrics:
            return self._parse_cvss(metrics["cvssMetricV2"][0], "2.0")

        return {
            "label": "INFO",
            "score": None,
            "vector": None,
            "version": None
        }

    def _extract_cvss4(self, cve: Dict) -> Dict:
        """Extract CVSS v4 score/vector if present in raw NVD metrics.

        Handles keys: cvssMetricV40 / cvssMetricV4 / cvssMetricV41
        """
        metrics = cve.get("metrics", {}) or {}
        for key in ("cvssMetricV40", "cvssMetricV4", "cvssMetricV41"):
            try:
                if key in metrics and isinstance(metrics[key], list) and metrics[key]:
                    data = metrics[key][0].get("cvssData", {}) or {}
                    return {
                        "score": data.get("baseScore"),
                        "vector": data.get("vectorString")
                    }
            except Exception:
                continue
        return {"score": None, "vector": None}

    def _parse_cvss(self, metric: Dict, version: str) -> Dict:
        data = metric.get("cvssData", {}) or {}

        score = data.get("baseScore")
        vector = data.get("vectorString")

        return {
            "label": self._score_to_severity(score),
            "score": score,
            "vector": vector,
            "version": version
        }

    def _extract_references(self, cve: Dict) -> List[str]:
        refs = []
        for r in cve.get("references", []):
            if isinstance(r, dict) and "url" in r:
                refs.append(r["url"])
        return refs

    # ==================================================
    # HELPERS
    # ==================================================
    def _score_to_severity(self, score: Optional[float]) -> str:
        if score is None:
            return "INFO"
        try:
            s = float(score)
        except Exception:
            return "INFO"

        if s >= 9.0:
            return "CRITICAL"
        if s >= 7.0:
            return "HIGH"
        if s >= 4.0:
            return "MEDIUM"
        if s > 0:
            return "LOW"
        return "INFO"


# ==================================================
# Shortcut helper
# ==================================================
def match_cve_by_cpe(cpe: str, api_key: Optional[str] = None) -> List[Dict]:
    try:
        matcher = CVEMatcher(api_key=api_key)
        return matcher.match_by_cpe(cpe)
    except Exception:
        return []
