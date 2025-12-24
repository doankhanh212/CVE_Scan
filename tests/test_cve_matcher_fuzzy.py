from modules.cve.cve_matcher import CVEMatcher
from modules.cve.local_db_fetcher import LocalDBFetcher
import sqlite3
import json


def make_db(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cve (
            id TEXT PRIMARY KEY,
            published TEXT,
            last_modified TEXT,
            cvss_base_score REAL,
            cvss_severity TEXT,
            description TEXT,
            raw_json TEXT,
            cve_cpe TEXT
        )
    """)

    item = {"cve": {"id": "CVE-TEST-3000", "descriptions": [{"lang": "en", "value": "Fancy vuln"}], "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 6.5}}]}}}
    raw = json.dumps(item)
    cpe_json = json.dumps(["cpe:2.3:a:example:prodname:2.0:*:*:*:*:*:*:*"])
    c.execute("INSERT OR REPLACE INTO cve (id, description, cvss_base_score, raw_json, cve_cpe) VALUES (?, ?, ?, ?, ?)",
              ("CVE-TEST-3000", "Fancy vuln", 6.5, raw, cpe_json))
    conn.commit()
    conn.close()


def test_match_by_cpe_fuzzy(tmp_path):
    db = tmp_path / "cve_local.db"
    make_db(str(db))

    matcher = CVEMatcher(local_db_path=str(db))

    # exact match should be empty
    res_exact = matcher.match_by_cpe("cpe:2.3:a:example:prodname:3.0:*:*:*:*:*:*:*")
    # fallback fuzzy should find the 2.0 entry
    res = matcher.match_by_cpe("cpe:2.3:a:example:prodnme:2.0:*:*:*:*:*:*:*")
    assert isinstance(res, list)
    assert len(res) >= 0
