from kev_db import is_in_kev

def cvss4_exploit_maturity(cve_id: str) -> str:
    """
    CVSS 4.0 Exploit Maturity
    A = Attacked (KEV)
    U = Unproven
    """
    return "A" if is_in_kev(cve_id) else "U"

def inject_e_metric(base_vector: str, cve_id: str) -> str:
    E = cvss4_exploit_maturity(cve_id)
    return f"{base_vector}/E:{E}"
