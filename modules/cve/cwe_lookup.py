import sqlite3
import os
from typing import Optional, Dict, List, Any


class CWELookup:
    """Query CWE data from cwe.db for explainability."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "cwe.db")
        self.db_path = db_path
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        """Lazy-load and cache database connection."""
        if self._conn is None:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"CWE database not found: {self.db_path}")
            # Allow reuse across Flask request threads (read-only workload)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_cwe(self, cwe_id: str) -> Optional[Dict[str, Any]]:
        """Fetch CWE metadata and extended description."""
        if not cwe_id.startswith("CWE-"):
            cwe_id = f"CWE-{cwe_id}"

        cursor = self._get_conn().cursor()
        cursor.execute(
            "SELECT cwe_id, name, extended_description FROM cwe WHERE cwe_id = ?",
            (cwe_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "cwe_id": row["cwe_id"],
            "name": row["name"],
            "extended_description": row["extended_description"],
        }

    def get_consequences(self, cwe_id: str) -> List[Dict[str, str]]:
        """Fetch all consequences for a CWE."""
        if not cwe_id.startswith("CWE-"):
            cwe_id = f"CWE-{cwe_id}"

        cursor = self._get_conn().cursor()
        cursor.execute(
            "SELECT scope, impact FROM cwe_consequence WHERE cwe_id = ? ORDER BY scope, impact",
            (cwe_id,),
        )
        rows = cursor.fetchall()

        return [{"scope": row["scope"], "impact": row["impact"]} for row in rows]

    def get_mitigations(self, cwe_id: str) -> List[Dict[str, Optional[str]]]:
        """Fetch all mitigations for a CWE."""
        if not cwe_id.startswith("CWE-"):
            cwe_id = f"CWE-{cwe_id}"

        cursor = self._get_conn().cursor()
        cursor.execute(
            "SELECT phase, description FROM cwe_mitigation WHERE cwe_id = ? ORDER BY phase, description",
            (cwe_id,),
        )
        rows = cursor.fetchall()

        return [{"phase": row["phase"], "description": row["description"]} for row in rows]

    def get_full_explanation(self, cwe_id: str) -> Optional[Dict[str, Any]]:
        """Fetch all CWE data in one call."""
        cwe_data = self.get_cwe(cwe_id)
        if cwe_data is None:
            return None

        return {
            "cwe": cwe_data,
            "consequences": self.get_consequences(cwe_id),
            "mitigations": self.get_mitigations(cwe_id),
        }

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()
