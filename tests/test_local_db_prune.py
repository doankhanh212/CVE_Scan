import sqlite3
import tempfile
import json
import os
from modules.cve.local_db_fetcher import LocalDBFetcher


def make_db_with_years(path):
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

    def ins(id, published):
        item = {"cve": {"id": id, "descriptions": [{"lang": "en", "value": "desc"}]}}
        raw = json.dumps(item)
        cpe_json = json.dumps([])
        c.execute("INSERT OR REPLACE INTO cve (id, published, last_modified, cvss_base_score, cvss_severity, description, raw_json, cve_cpe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (id, published, published, None, None, "desc", raw, cpe_json))

    ins("CVE-2018-0001", "2018-05-01")
    ins("CVE-2021-0001", "2021-07-02")
    ins("CVE-2024-0001", "2024-11-11")

    conn.commit()
    conn.close()


def test_prune_db_by_year_range(tmp_path):
    db = tmp_path / "prune.db"
    make_db_with_years(str(db))

    f = LocalDBFetcher(db_path=str(db))
    deleted = f.prune_db_by_year_range(2020, 2025, backup=True)

    # deleted should be 1 (the 2018 CVE)
    assert deleted == 1

    # remaining entries should be 2
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT id FROM cve ORDER BY id")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()

    assert rows == ["CVE-2021-0001", "CVE-2024-0001"]

    # backup file exists
    bak_files = [p for p in os.listdir(str(tmp_path)) if p.startswith('prune.db.bak.')]
    assert bak_files
