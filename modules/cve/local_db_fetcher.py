import sqlite3
import json
from typing import List, Dict, Optional


class LocalDBFetcher:
    """Fetch CVE entries from a local SQLite DB produced by V1 scripts.

    Expected DB FILE: SQLite with table `cve` and columns:
      - id, published, last_modified, cvss_base_score, cvss_severity,
        description, raw_json, cve_cpe

    This fetcher returns a list of NVD-style items compatible with CVEMatcher._normalize()
    (each item is a dict with key 'cve' containing minimal fields).
    """

    def __init__(self, db_path: str = "modules/cve/nvd_cve.db"):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_nvd_item(self, row: sqlite3.Row) -> Dict:
        # raw_json may exist and contains the full NVD structure
        try:
            raw = json.loads(row["raw_json"]) if row["raw_json"] else None
        except Exception:
            raw = None

        # Build minimal 'cve' dict expected by CVEMatcher
        cve = {
            "id": row["id"],
            "descriptions": [{"lang": "en", "value": row["description"] or ""}],
            "metrics": {}
        }

        # Try to synthesize CVSS v3 structure if base score present
        score = row["cvss_base_score"]
        sev = row["cvss_severity"]
        if score is not None:
            # Put into cvssMetricV31 shape so CVEMatcher can parse it
            cve["metrics"] = {
                "cvssMetricV31": [
                    {"cvssData": {"baseScore": score, "vectorString": None, "baseSeverity": sev}}
                ]
            }

        # If raw NVD exists and contains cve info, prefer its 'cve' object
        if raw and isinstance(raw, dict):
            # In V2 feed structure, top-level item contains 'cve' key
            nested = raw.get("cve") if isinstance(raw.get("cve"), dict) else None
            if nested:
                # Let the nested structure override minimal fields
                cve = nested

        return {"cve": cve}

    def get_cve_by_cpe(self, cpe: str, max_results: int = 50, min_year: Optional[int] = None) -> List[Dict]:
        if not cpe:
            return []

        conn = self._connect()
        cur = conn.cursor()

        like = f"%\"{cpe}\"%"

        # Determine available columns for ordering and year filter
        try:
            cur.execute("PRAGMA table_info(cve)")
            cols = [r[1] for r in cur.fetchall()]
        except Exception:
            cols = []

        has_published = "published" in cols
        has_last_mod = "last_modified" in cols

        year_clause = ""
        params = [like]
        if min_year and (has_published or has_last_mod):
            col = "published" if has_published else "last_modified"
            year_clause = f" AND CAST(strftime('%Y', {col}) AS INTEGER) >= ?"
            params.append(min_year)

        order_col = "published" if has_published else ("last_modified" if has_last_mod else None)

        sql = "SELECT id, description, cvss_base_score, cvss_severity, raw_json FROM cve WHERE cve_cpe LIKE ?" + year_clause
        if order_col:
            sql += f" ORDER BY {order_col} DESC"
        sql += " LIMIT ?"
        params.append(int(max_results))

        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()

        return [self._row_to_nvd_item(r) for r in rows]

    def search_cve_keyword(self, keyword: str, max_results: int = 50) -> List[Dict]:
        if not keyword:
            return []

        conn = self._connect()
        cur = conn.cursor()

        kw = f"%{keyword}%"
        sql = "SELECT id, description, cvss_base_score, cvss_severity, raw_json FROM cve WHERE description LIKE ? OR id LIKE ? LIMIT ?"
        cur.execute(sql, (kw, kw, max_results))
        rows = cur.fetchall()
        conn.close()

        return [self._row_to_nvd_item(r) for r in rows]

    # ==================================================
    # FUZZY / REBUILD HELPERS
    # ==================================================
    def fuzzy_match_cpe_to_cve(self, cpe: str, max_results: int = 50, min_year: Optional[int] = None) -> List[Dict]:
        """Use fuzzy matcher to find related CPEs and return CVE items.

        Respects `max_results` and optional `min_year` to avoid oversized, stale result sets.
        """
        if not cpe:
            return []

        conn = self._connect()
        cur = conn.cursor()
        try:
            from modules.cve.fuzzy_matcher import fuzzy_find_related_cpe
        except Exception:
            conn.close()
            return []

        related = fuzzy_find_related_cpe(cur, cpe)
        if not related:
            conn.close()
            return []

        # Determine available columns for year filtering and ordering
        try:
            cur.execute("PRAGMA table_info(cve)")
            cols = [r[1] for r in cur.fetchall()]
        except Exception:
            cols = []

        has_published = "published" in cols
        has_last_mod = "last_modified" in cols

        year_clause = ""
        year_param = []
        if min_year and (has_published or has_last_mod):
            col = "published" if has_published else "last_modified"
            year_clause = f" AND CAST(strftime('%Y', {col}) AS INTEGER) >= ?"
            year_param = [min_year]

        # cve_cpe is stored as a JSON array string; perform LIKE on each related CPE
        conditions = " OR ".join(["cve_cpe LIKE ?"] * len(related))
        params = [f'%"{r}"%' for r in related]
        params.extend(year_param)

        order_col = "published" if has_published else ("last_modified" if has_last_mod else None)

        sql = f"SELECT id, description, cvss_base_score, cvss_severity, raw_json FROM cve WHERE {conditions}{year_clause}"
        if order_col:
            sql += f" ORDER BY {order_col} DESC"
            if "cvss_base_score" in cols:
                sql += ", cvss_base_score DESC"
        sql += " LIMIT ?"
        params.append(int(max_results))

        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()

        return [self._row_to_nvd_item(r) for r in rows]

    def rebuild_db_from_feeds(self, feed_dir: str, progress_cb=None):
        """Rebuild database by importing feeds from a feed directory (delegates to db_importer).

        progress_cb(filename, idx, total) will be forwarded to importer.
        """
        try:
            from modules.cve.db_importer import import_feeds, init_db
        except Exception as e:
            raise RuntimeError("db_importer not available: %s" % e)

        init_db(self.db_path)
        import_feeds(feed_dir, self.db_path, progress_cb=progress_cb)

        return True

    def prune_db_by_year_range(self, start_year: int, end_year: int, backup: bool = True) -> int:
        """Prune CVE rows outside the inclusive year range [start_year, end_year].

        - Creates a timestamped backup (if backup=True).
        - Returns the number of rows deleted.
        """
        import shutil
        import os
        from datetime import datetime

        # ensure DB exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"DB not found: {self.db_path}")

        if backup:
            bak_name = f"{self.db_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S') }"
            shutil.copy2(self.db_path, bak_name)

        conn = self._connect()
        cur = conn.cursor()

        # delete rows where published year is outside the inclusive window
        # published is expected to be an ISO date/time string like '2021-03-10T...'
        sql = (
            "DELETE FROM cve WHERE (published IS NULL) OR "
            "(CAST(strftime('%Y', published) AS INTEGER) < ?) OR "
            "(CAST(strftime('%Y', published) AS INTEGER) > ?)")
        cur.execute("SELECT COUNT(1) FROM cve")
        before = cur.fetchone()[0]

        cur.execute(sql, (start_year, end_year))
        conn.commit()

        cur.execute("SELECT COUNT(1) FROM cve")
        after = cur.fetchone()[0]

        conn.close()

        deleted = before - after
        return deleted
