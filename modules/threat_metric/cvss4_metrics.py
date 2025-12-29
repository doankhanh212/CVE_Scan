"""
CVSS 4.0 Metrics — Exploit Maturity Injection
"""
from typing import Optional
from .kev_db import is_in_kev


def exploit_maturity(cve_id: Optional[str]) -> str:
    """
    CVSS 4.0 Exploit Maturity (E)
    A = Attacked (CISA KEV)
    U = Unproven
    """
    if not cve_id:
        return "U"
    return "A" if is_in_kev(cve_id) else "U"


def build_cvss4_vector(base_vector: Optional[str], cve_id: Optional[str]) -> Optional[str]:
    """
    Inject E metric into CVSS 4.0 vector.
    If base_vector is None, return None.
    """
    if not base_vector or not cve_id:
        return base_vector
    
    E = exploit_maturity(cve_id)
    
    # Remove existing E metric if present
    if "/E:" in base_vector:
        base_vector = base_vector.split("/E:")[0]
    
    return f"{base_vector}/E:{E}"
