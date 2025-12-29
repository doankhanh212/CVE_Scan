import sqlite3
from config import DB_PATH

def is_in_kev(cve_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT 1 FROM kev_vulnerabilities WHERE cve_id = ? LIMIT 1",
            (cve_id.upper(),)
        )
        return cur.fetchone() is not None
    finally:
        conn.close()
