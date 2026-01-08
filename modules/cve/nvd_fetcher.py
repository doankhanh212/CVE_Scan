import requests
import time
import json
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ==================================================
# NVD API CONFIG
# ==================================================
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class NVDFetcherPRO:
    """
    Fetch RAW CVE data from NVD API (v2.0)

    ⚠️ Responsibilities:
    - Call NVD API
    - Handle rate limit (429)
    - Cache raw responses
    - DO NOT normalize CVE data
    """

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

    # ==================================================
    # INTERNAL HELPERS
    # ==================================================
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
            logger.warning("[NVD] Cannot write cache file: %s", e)

    def _api_call(self, params: dict) -> dict:
        headers = {
            "User-Agent": "CVE-Scanner/1.0"
        }

        if self.api_key:
            headers["apiKey"] = self.api_key.strip()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(
                    NVD_API_URL,
                    headers=headers,
                    params=params,
                    timeout=30
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    wait = min(60, 2 * attempt)
                    logger.warning(
                        "[NVD] 429 Too Many Requests — waiting %ss (attempt %s)",
                        wait,
                        attempt
                    )
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return {}

            except Exception as e:
                logger.error(
                    "[NVD] API request error (attempt %s): %s",
                    attempt,
                    e
                )
                time.sleep(self.cooldown)

        logger.error("[NVD] API call failed after max retries.")
        return {}

    # ==================================================
    # PUBLIC METHODS
    # ==================================================
    def get_cve_by_cpe(self, cpe: str, max_results: int = 50) -> List[Dict]:
        """
        Fetch CVEs by exact CPE name

        Return: RAW NVD vulnerabilities list
        """
        if not cpe:
            return []

        cache_key = f"cpe::{cpe}"
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        params = {
            "cpeName": cpe,
            "resultsPerPage": max_results,
        }

        data = self._api_call(params)
        vulns = data.get("vulnerabilities", [])

        self._save_to_cache(cache_key, vulns)
        return vulns

    def get_cve_by_id(self, cve_id: str) -> List[Dict]:
        """Fetch CVE by CVE ID (v2.0 API supports cveId parameter).

        Return: RAW NVD vulnerabilities list for the specific CVE ID
        """
        if not cve_id:
            return []

        cache_key = f"cveid::{cve_id}"
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        params = {
            "cveId": cve_id,
            "resultsPerPage": 1,
        }

        data = self._api_call(params)
        vulns = data.get("vulnerabilities", [])

        self._save_to_cache(cache_key, vulns)
        return vulns

    def search_cve_keyword(self, keyword: str, max_results: int = 50) -> List[Dict]:
        """
        Search CVEs by keyword (service / product / version)

        Return: RAW NVD vulnerabilities list
        """
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

        self._save_to_cache(cache_key, vulns)
        return vulns


# ==================================================
# BACKWARD COMPATIBILITY
# ==================================================
def get_cve_by_cpe(cpe: str):
    fetcher = NVDFetcherPRO()
    return fetcher.get_cve_by_cpe(cpe)
