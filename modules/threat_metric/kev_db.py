"""
KEV Database Query
"""
import sqlite3
from typing import Optional
from datetime import datetime
from .config import DB_PATH


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
            vuln.get("cveID"),
            vuln.get("vendorProject"),
            vuln.get("product"),
            vuln.get("dateAdded"),
            vuln.get("dueDate"),
            vuln.get("knownRansomwareCampaignUse"),
            datetime.utcnow().isoformat()
        ))


def is_in_kev(cve_id: Optional[str]) -> bool:
    if not cve_id:
        return False
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "SELECT 1 FROM kev_vulnerabilities WHERE cve_id = ? LIMIT 1",
                (cve_id.upper(),)
            )
            return cur.fetchone() is not None
    except Exception:
        return False


def get_kev_metadata(cve_id: Optional[str]) -> Optional[dict]:
    if not cve_id:
        return None
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "SELECT cve_id, vendor, product, date_added, due_date, ransomware_use FROM kev_vulnerabilities WHERE cve_id = ? LIMIT 1",
                (cve_id.upper(),)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "cve_id": row[0],
                "vendor_project": row[1],
                "product": row[2],
                "date_added": row[3],
                "due_date": row[4],
                "known_ransomware_campaign_use": row[5],
            }
    except Exception:
        return None
