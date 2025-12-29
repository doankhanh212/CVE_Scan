"""
Threat Metric Public API

Provides:
- check_kev(cve_id) -> bool
- enrich_cvss4_vector(vector, cve_id) -> vector with E metric
- get_kev_metadata(cve_id) -> dict
"""

from typing import Optional
from .kev_db import is_in_kev, get_kev_metadata
from .cvss4_metrics import build_cvss4_vector


def check_kev(cve_id: Optional[str]) -> bool:
    """Check if CVE is in CISA KEV."""
    return is_in_kev(cve_id)


def enrich_cvss4_vector(base_vector: Optional[str], cve_id: Optional[str]) -> Optional[str]:
    """Inject E (Exploit Maturity) metric into CVSS 4.0 vector."""
    return build_cvss4_vector(base_vector, cve_id)


def get_kev_info(cve_id: Optional[str]) -> Optional[dict]:
    """Get full KEV metadata for a CVE."""
    return get_kev_metadata(cve_id)
