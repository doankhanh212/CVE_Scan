# modules/nvd_fetcher.py
import requests
import time
import json
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Base URL (no prefilled query)
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

class NVDFetcherPRO:
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_file: str = "nvd_cache.json",
        max_retries: int = 5,
        cooldown: int = 6,
    ):
        self.api_key = api_key
        self.cache_file = cache_file
        self.max_retries = max_retries
        self.cooldown = cooldown

        # Load cache
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        else:
            self.cache = {}

    def _api_call(self, params: dict) -> dict:
        headers = {"User-Agent": "CVE-Scanner/1.0"}
        if self.api_key:
            headers["apiKey"] = self.api_key.strip()

        for attempt in range(1, self.max_retries + 1):
            try:
                res = requests.get(NVD_API_URL, headers=headers, params=params, timeout=30)
                if res.status_code == 200:
                    try:
                        return res.json()
                    except Exception as e:
                        logger.error("[NVD] JSON decode error: %s", e)
                        return {}
                if res.status_code == 429:
                    wait = min(60, 2 * attempt)
                    logger.warning("[NVD] 429 Too Many Requests — waiting %ss (attempt %s)", wait, attempt)
                    time.sleep(wait)
                    continue
                res.raise_for_status()
                return {}
            except Exception as e:
                logger.error("[NVD] API request error (attempt %s): %s", attempt, e)
                time.sleep(self.cooldown)

        logger.error("[NVD] API call failed after retries.")
        return {}

    def _cache_key(self, key: str) -> str:
        return key.lower().strip()

    def _load_from_cache(self, key: str):
        return self.cache.get(self._cache_key(key))

    def _save_to_cache(self, key: str, data):
        self.cache[self._cache_key(key)] = data
        try:
            tmp = self.cache_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
            os.replace(tmp, self.cache_file)
        except Exception as e:
            logger.warning("Cannot write cache file: %s", e)

    def get_cve_by_cpe(self, cpe: str, max_results: int = 50) -> List[Dict]:
        key = f"cpe::{cpe}"
        cached = self._load_from_cache(key)
        if cached:
            return cached

        params = {
            "cpeName": cpe,
            "resultsPerPage": max_results,
        }

        data = self._api_call(params)
        cves = data.get("vulnerabilities", [])

        self._save_to_cache(key, cves)
        return cves

    def search_cve_keyword(self, keyword: str, max_results: int = 50) -> List[Dict]:
        if not keyword:
            return []

        cache_key = f"keyword::{keyword}"
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        params = {
            "keywordSearch": keyword,
            "resultsPerPage": max_results,
        }

        data = self._api_call(params)
        vulns = data.get("vulnerabilities", [])

        output = []
        for v in vulns:
            try:
                cve_obj = v.get("cve", {}) if isinstance(v, dict) else {}
                cve_id = cve_obj.get("id") or cve_obj.get("CVE_data_meta", {}).get("ID")
                desc = ""
                if "descriptions" in cve_obj:
                    for d in cve_obj.get("descriptions", []):
                        if d.get("lang") in ("en", None):
                            desc = d.get("value", "")
                            break
                else:
                    # fallback older structure
                    desc = cve_obj.get("descriptions", [{}])[0].get("value", "")

                score = None
                severity = None
                metrics = cve_obj.get("metrics", {}) or {}
                if "cvssMetricV31" in metrics:
                    try:
                        m = metrics["cvssMetricV31"][0]["cvssData"]
                        score = m.get("baseScore")
                        severity = m.get("baseSeverity")
                    except Exception:
                        pass
                elif "cvssMetricV30" in metrics:
                    try:
                        m = metrics["cvssMetricV30"][0]["cvssData"]
                        score = m.get("baseScore")
                        severity = m.get("baseSeverity")
                    except Exception:
                        pass
                elif "cvssMetricV2" in metrics:
                    try:
                        m = metrics["cvssMetricV2"][0].get("cvssData", {})
                        score = m.get("baseScore")
                    except Exception:
                        pass

                entry = {
                    "id": cve_id or "N/A",
                    "score": score,
                    "severity": severity,
                    "desc": desc or "",
                    "exploits": []
                }
                output.append(entry)
            except Exception:
                continue

        self._save_to_cache(cache_key, output)
        return output

# Backwards-compatible function
def get_cve_by_cpe(cpe: str):
    fetcher = NVDFetcherPRO()
    return fetcher.get_cve_by_cpe(cpe)
