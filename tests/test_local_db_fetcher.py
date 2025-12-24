import sqlite3
import tempfile
import json
from modules.cve.local_db_fetcher import LocalDBFetcher


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

    item = {
        "cve": {"id": "CVE-TEST-0001", "descriptions": [{"lang": "en", "value": "Test desc"}], "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 7.5, "vectorString": ""}}]}}}
    raw = json.dumps(item)
    cpe_json = json.dumps(["cpe:2.3:a:example:product:1.0:*:*:*:*:*:*:*"])

    c.execute("INSERT OR REPLACE INTO cve (id, published, last_modified, cvss_base_score, cvss_severity, description, raw_json, cve_cpe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              ("CVE-TEST-0001", "2025-01-01", "2025-01-01", 7.5, "HIGH", "Test desc", raw, cpe_json))

    conn.commit()
    conn.close()


def test_get_cve_by_cpe(tmp_path):
    db = tmp_path / "test.db"
    make_db(str(db))

    f = LocalDBFetcher(db_path=str(db))
    res = f.get_cve_by_cpe("cpe:2.3:a:example:product:1.0:*:*:*:*:*:*:*")
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["cve"]["id"] == "CVE-TEST-0001"


def test_search_cve_keyword(tmp_path):
    db = tmp_path / "test2.db"
    make_db(str(db))
    f = LocalDBFetcher(db_path=str(db))
    res = f.search_cve_keyword("TEST-0001")
    assert res and res[0]["cve"]["id"] == "CVE-TEST-0001"
