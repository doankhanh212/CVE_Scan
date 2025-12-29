from __future__ import annotations

"""
Lightweight adapter to query CISA KEV membership using the
sqlite database provided in CVSS_threat_metric.

Search order for kev.db:
- CVSS_threat_metric/kev_module/kev.db
- CVSS_threat_metric/Threat_metric/kev.db

APIs:
- is_kev(cve_id) -> bool
- get_metadata(cve_id) -> dict | None
"""

import os
import sqlite3
from typing import Optional, Dict

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

DB_CANDIDATES = [
    os.path.join(WORKSPACE_ROOT, "CVSS_threat_metric", "kev_module", "kev.db"),
    os.path.join(WORKSPACE_ROOT, "CVSS_threat_metric", "Threat_metric", "kev.db"),
]


def _find_db_path() -> Optional[str]:
    for p in DB_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def is_kev(cve_id: Optional[str]) -> bool:
    if not cve_id:
        return False
    db_path = _find_db_path()
    if not db_path:
        return False
    try:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute(
                "SELECT 1 FROM kev_vulnerabilities WHERE cve_id = ? LIMIT 1",
                (cve_id.upper(),)
            )
            return cur.fetchone() is not None
        finally:
            conn.close()
    except Exception:
        return False


def get_metadata(cve_id: Optional[str]) -> Optional[Dict]:
    if not cve_id:
        return None
    db_path = _find_db_path()
    if not db_path:
        return None
    try:
        conn = sqlite3.connect(db_path)
        try:
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
                "is_exploited": True,
            }
        finally:
            conn.close()
    except Exception:
        return None
