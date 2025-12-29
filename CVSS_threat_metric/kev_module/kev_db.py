import sqlite3
from datetime import datetime
from config import DB_PATH

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS kev_vulnerabilities (
            cve_id TEXT PRIMARY KEY,
            vendor TEXT,
            product TEXT,
            date_added TEXT,
            due_date TEXT,
            ransomware_use TEXT,
            last_updated TEXT
        )
        """)

def upsert_kev(vuln: dict):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO kev_vulnerabilities
        (cve_id, vendor, product, date_added, due_date, ransomware_use, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cve_id) DO UPDATE SET
            vendor=excluded.vendor,
            product=excluded.product,
            date_added=excluded.date_added,
            due_date=excluded.due_date,
            ransomware_use=excluded.ransomware_use,
            last_updated=excluded.last_updated
        """, (
            vuln["cveID"],
            vuln.get("vendorProject"),
            vuln.get("product"),
            vuln.get("dateAdded"),
            vuln.get("dueDate"),
            vuln.get("knownRansomwareCampaignUse"),
            datetime.utcnow().isoformat()
        ))

def is_in_kev(cve_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM kev_vulnerabilities WHERE cve_id=?",
            (cve_id,)
        )
        return cur.fetchone() is not None
