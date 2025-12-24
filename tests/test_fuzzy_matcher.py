import sqlite3
from modules.cve.fuzzy_matcher import fuzzy_find_related_cpe, fuzzy_match_cpe_to_cve


def make_db(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cve (
            id TEXT PRIMARY KEY,
            description TEXT,
            cvss_base_score REAL,
            cve_cpe TEXT
        )
    """)
    # insert a cve with a cpe
    cpe_json = '["cpe:2.3:a:example:product:1.2:*:*:*:*:*:*:*"]'
    c.execute("INSERT OR REPLACE INTO cve (id, description, cvss_base_score, cve_cpe) VALUES (?, ?, ?, ?)",
              ("CVE-TEST-2000", "Example vuln", 7.5, cpe_json))
    conn.commit()


def test_fuzzy_find(tmp_path):
    db = tmp_path / "fuzzy.db"
    conn = sqlite3.connect(str(db))
    make_db(conn)
    cur = conn.cursor()

    related = fuzzy_find_related_cpe(cur, "cpe:2.3:a:example:product:1.2:*:*:*:*:*:*:*")
    assert related and "cpe:2.3:a:example:product:1.2:*:*:*:*:*:*:*" in related

    rows = fuzzy_match_cpe_to_cve(cur, "cpe:2.3:a:example:product:1.2:*:*:*:*:*:*:*")
    assert rows and rows[0][0] == "CVE-TEST-2000"
    conn.close()
