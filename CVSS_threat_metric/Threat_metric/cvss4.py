from kev_db import is_in_kev

def exploit_maturity(cve_id: str) -> str:
    """
    CVSS 4.0 Exploit Maturity (E)
    A = Attacked (CISA KEV)
    U = Unproven
    """
    return "A" if is_in_kev(cve_id) else "U"


def build_cvss4_vector(base_vector: str, cve_id: str) -> str:
    """
    Inject E metric into CVSS 4.0 vector
    """
    E = exploit_maturity(cve_id)

    if "/E:" in base_vector:
        base_vector = base_vector.split("/E:")[0]

    return f"{base_vector}/E:{E}"
