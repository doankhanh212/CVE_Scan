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
import datetime
import re

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

    def __init__(self, api_key: Optional[str] = None, local_db_path: Optional[str] = None, year_window: Optional[int] = None):
        self.fetcher = None
        self.year_window = year_window
        self.fetcher_type = None  # Track which fetcher is used

        # Prefer local DB fetcher when provided
        if local_db_path:
            try:
                from modules.cve.local_db_fetcher import LocalDBFetcher
                self.fetcher = LocalDBFetcher(db_path=local_db_path)
                self.fetcher_type = "LocalDB"
                logger.info("✅ Using LocalDBFetcher: %s", local_db_path)
                return
            except Exception as e:
                logger.error("❌ Init LocalDBFetcher failed: %s", e)
                self.fetcher = None

        if NVDFetcherPRO is None:
            logger.warning("⚠️ NVDFetcherPRO import failed — CVE disabled")
            return

        try:
            self.fetcher = NVDFetcherPRO(api_key=api_key)
            self.fetcher_type = "NVD_API"
            logger.info("✅ Using NVDFetcherPRO with API key: %s", "Yes" if api_key else "No")
        except Exception as e:
            logger.error("❌ Init NVDFetcherPRO failed: %s", e)
            self.fetcher = None

    # ==================================================
    # PUBLIC
    # ==================================================
    def match_by_cpe(self, cpe: str, max_results: int = 50, year_window: Optional[int] = None) -> List[Dict]:
        if not cpe or cpe == "N/A":
            logger.debug("🔍 CPE is empty or N/A, skipping CVE lookup")
            return []

        if not self.fetcher:
            # 🔥 CHỐT: KHÔNG ĐƯỢC CRASH
            logger.warning("⚠️ No fetcher available (DB or API) — CVE lookup disabled")
            return []
        
        logger.debug("🔍 Searching CVE for CPE: %s (fetcher: %s)", cpe, self.fetcher_type or "Unknown")

        # Determine min_year based on window (prefer explicit arg, else instance default)
        window = year_window if year_window is not None else self.year_window
        min_year = None
        try:
            if window and window > 0:
                current_year = datetime.datetime.utcnow().year
                min_year = current_year - window + 1
                logger.debug("📅 Year window: %d (min_year=%d)", window, min_year)
        except Exception:
            min_year = None

        try:
            if min_year is not None:
                try:
                    raw_cves = self.fetcher.get_cve_by_cpe(
                        cpe,
                        max_results=max_results,
                        min_year=min_year
                    )
                except TypeError:
                    raw_cves = self.fetcher.get_cve_by_cpe(
                        cpe,
                        max_results=max_results
                    )
            else:
                raw_cves = self.fetcher.get_cve_by_cpe(
                    cpe,
                    max_results=max_results
                )
            
            logger.debug("📊 Found %d exact matches for CPE: %s", len(raw_cves), cpe)
        except Exception as e:
            logger.error("❌ Fetch CVE failed for %s: %s", cpe, e)
            raw_cves = []

        # If no exact matches and we have a local DB fetcher with fuzzy capabilities,
        # attempt fuzzy matching to increase recall.
        if not raw_cves:
            try:
                # LocalDBFetcher exposes fuzzy_match_cpe_to_cve; pass through max_results when supported
                if hasattr(self.fetcher, 'fuzzy_match_cpe_to_cve'):
                    logger.info("🔍 No exact CVEs for %s — trying fuzzy DB lookup", cpe)
                    try:
                        if min_year is not None:
                            raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe, max_results=max_results, min_year=min_year)
                        else:
                            raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe, max_results=max_results)
                        logger.debug("📊 Fuzzy match found %d CVEs", len(raw_cves))
                    except TypeError:
                        # Backward compatibility with older signature
                        raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe)
                        logger.debug("📊 Fuzzy match (legacy) found %d CVEs", len(raw_cves))
                else:
                    # As a fallback, import matcher and run fuzzy against a cursor if possible
                    try:
                        from modules.cve.local_db_fetcher import LocalDBFetcher
                        if isinstance(self.fetcher, LocalDBFetcher):
                            logger.info("🔍 Using LocalDBFetcher fuzzy matcher for %s", cpe)
                            try:
                                if min_year is not None:
                                    raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe, max_results=max_results, min_year=min_year)
                                else:
                                    raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe, max_results=max_results)
                            except TypeError:
                                raw_cves = self.fetcher.fuzzy_match_cpe_to_cve(cpe)
                            logger.debug("📊 Fuzzy fallback found %d CVEs", len(raw_cves))
                    except Exception:
                        raw_cves = []
            except Exception as e:
                logger.debug("⚠️ Fuzzy lookup failed for %s: %s", cpe, e)
                raw_cves = []
        
        if not raw_cves:
            logger.info("ℹ️ No CVEs found for CPE: %s", cpe)

        normalized = self._normalize(raw_cves)

        # Apply year filter locally if fetcher doesn't support it
        # Ensures older CVEs are excluded even when using NVD API without min_year.
        try:
            if min_year is not None:
                normalized = [c for c in normalized if (self._cve_year(c.get("id")) or 0) >= min_year]
        except Exception:
            pass

        # Sort newest-first by CVE year, then by CVSS score to prefer fresh/high-impact CVEs
        def _sort_key(c):
            year = self._cve_year(c.get("id")) or 0
            sev = c.get("severity") or {}
            score = sev.get("score") if isinstance(sev, dict) else None
            score_val = score if isinstance(score, (int, float)) else 0
            return (year, score_val)

        try:
            normalized.sort(key=_sort_key, reverse=True)
        except Exception:
            pass

        # Enforce max_results after sorting to keep newest slice
        return normalized[:max_results]

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
        Optionally enriches vector with E (Exploit Maturity) metric from KEV.
        """
        metrics = cve.get("metrics", {}) or {}
        for key in ("cvssMetricV40", "cvssMetricV4", "cvssMetricV41"):
            try:
                if key in metrics and isinstance(metrics[key], list) and metrics[key]:
                    data = metrics[key][0].get("cvssData", {}) or {}
                    score = data.get("baseScore")
                    vector = data.get("vectorString")
                    
                    # Optionally enrich with E metric (Exploit Maturity) from threat_metric
                    if vector:
                        try:
                            from modules.threat_metric import enrich_cvss4_vector
                            cve_id = self._extract_id(cve)
                            if cve_id and cve_id != "N/A":
                                vector = enrich_cvss4_vector(vector, cve_id) or vector
                        except Exception:
                            pass
                    
                    return {
                        "score": score,
                        "vector": vector
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

    def _cve_year(self, cve_id: Optional[str]) -> Optional[int]:
        if not cve_id:
            return None
        try:
            m = re.search(r"CVE-(\d{4})-", cve_id)
            if m:
                return int(m.group(1))
        except Exception:
            return None
        return None


# ==================================================
# Shortcut helper
# ==================================================
def match_cve_by_cpe(cpe: str, api_key: Optional[str] = None) -> List[Dict]:
    try:
        matcher = CVEMatcher(api_key=api_key)
        return matcher.match_by_cpe(cpe)
    except Exception:
        return []
