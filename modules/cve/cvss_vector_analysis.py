"""
CVSS Vector Analysis Layer
--------------------------
Purpose: Deterministic parsing and explainability of CVSS vectors (2.0, 3.x, 4.0)
Constraints: No score calculation; prioritize clarity; auditable output.
"""

from typing import Dict, List, Optional, Tuple


# =========================
# Mapping Tables
# =========================

# Human-friendly names per metric key
METRIC_NAMES = {
    # Common
    "AV": "Attack Vector",
    "AC": "Attack Complexity",
    "PR": "Privileges Required",
    "UI": "User Interaction",
    # CVSS v4-only
    "AT": "Attack Requirements",
    "VC": "Vulnerable System: Confidentiality",
    "VI": "Vulnerable System: Integrity",
    "VA": "Vulnerable System: Availability",
    "SC": "Subsequent System: Confidentiality",
    "SI": "Subsequent System: Integrity",
    "SA": "Subsequent System: Availability",
    # CVSS v3.x-only
    "C": "Confidentiality",
    "I": "Integrity",
    "A": "Availability",
    # CVSS v2.0-only
    "Au": "Authentication",
}


# Value meanings by version
VALUE_MEANINGS_V4 = {
    "AV": {
        "N": ("Network", "Attack can be performed remotely over a network."),
        "A": ("Adjacent", "Attack requires access to the same logical network or segment."),
        "L": ("Local", "Attack requires local access to the system or device."),
        "P": ("Physical", "Attack requires physical interaction with the device or system."),
    },
    "AC": {
        "L": ("Low", "Attack is straightforward; few preconditions or steps."),
        "H": ("High", "Attack is difficult; significant preconditions or steps required."),
    },
    "AT": {
        "N": ("None", "No additional environmental requirements beyond the stated metrics."),
        "P": ("Present", "Specific environmental or configuration requirements must be met."),
    },
    "PR": {
        "N": ("None", "No privileges required; any user can attempt the attack."),
        "L": ("Low", "Low privileges required; basic or limited account."),
        "H": ("High", "High privileges required; administrative or equivalent access."),
    },
    "UI": {
        "N": ("None", "No user interaction is required."),
        "R": ("Required", "Successful attack depends on a user action."),
    },
    # Impact (Vulnerable System)
    "VC": {
        "N": ("None", "No loss of confidentiality on the vulnerable system."),
        "L": ("Low", "Limited disclosure of information."),
        "H": ("High", "Severe information disclosure on the vulnerable system."),
    },
    "VI": {
        "N": ("None", "No modification of data on the vulnerable system."),
        "L": ("Low", "Limited modification of data."),
        "H": ("High", "Severe modification or corruption of data."),
    },
    "VA": {
        "N": ("None", "No disruption of service on the vulnerable system."),
        "L": ("Low", "Limited disruption of service."),
        "H": ("High", "Severe service disruption or downtime."),
    },
    # Subsequent System impact
    "SC": {
        "N": ("None", "No confidentiality impact to downstream/connected systems."),
        "L": ("Low", "Limited confidentiality impact to subsequent systems."),
        "H": ("High", "Severe confidentiality impact to subsequent systems."),
    },
    "SI": {
        "N": ("None", "No integrity impact to downstream/connected systems."),
        "L": ("Low", "Limited integrity impact to subsequent systems."),
        "H": ("High", "Severe integrity impact to subsequent systems."),
    },
    "SA": {
        "N": ("None", "No availability impact to downstream/connected systems."),
        "L": ("Low", "Limited availability impact to subsequent systems."),
        "H": ("High", "Severe availability impact to subsequent systems."),
    },
}


VALUE_MEANINGS_V3 = {
    "AV": VALUE_MEANINGS_V4["AV"],
    "AC": VALUE_MEANINGS_V4["AC"],
    "PR": VALUE_MEANINGS_V4["PR"],
    "UI": VALUE_MEANINGS_V4["UI"],
    "C": {
        "N": ("None", "No loss of confidentiality."),
        "L": ("Low", "Limited information disclosure."),
        "H": ("High", "Severe information disclosure."),
    },
    "I": {
        "N": ("None", "No modification of data."),
        "L": ("Low", "Limited modification of data."),
        "H": ("High", "Severe data modification or corruption."),
    },
    "A": {
        "N": ("None", "No disruption of service."),
        "L": ("Low", "Limited disruption of service."),
        "H": ("High", "Severe service disruption or downtime."),
    },
}


VALUE_MEANINGS_V2 = {
    "AV": {
        "N": ("Network", "Attack can be performed over a network."),
        "A": ("Adjacent Network", "Attack requires same broadcast or logical network."),
        "L": ("Local", "Attack requires local system access."),
    },
    "AC": {
        "L": ("Low", "Attack is straightforward; few preconditions."),
        "M": ("Medium", "Attack requires some conditions or steps."),
        "H": ("High", "Attack is difficult; significant preconditions."),
    },
    "Au": {
        "N": ("None", "No authentication required."),
        "S": ("Single", "A single authentication instance is required."),
        "M": ("Multiple", "Multiple authentication instances are required."),
    },
    "C": {
        "N": ("None", "No loss of confidentiality."),
        "P": ("Partial", "Partial information disclosure."),
        "C": ("Complete", "Complete information disclosure."),
    },
    "I": {
        "N": ("None", "No modification of data."),
        "P": ("Partial", "Partial modification of data."),
        "C": ("Complete", "Complete modification or corruption of data."),
    },
    "A": {
        "N": ("None", "No disruption of service."),
        "P": ("Partial", "Partial disruption of service."),
        "C": ("Complete", "Complete service disruption or downtime."),
    },
}


# =========================
# Core API
# =========================

def select_vector(cve: Dict) -> Tuple[Optional[str], Optional[str]]:
    """Select a single CVSS vector by priority (4.0 → 3.1 → 3.0 → 2.0).

    Accepts a normalized CVE dict (as produced by your matcher) or any dict
    containing potential vector locations:
    - cve.get('cvss4', {}).get('vector')
    - cve.get('severity', {}).get('vector') for v3.x or v2.0
    - cve.get('cvss_v3_vector') / cve.get('cvss_v2_vector') if present

    Returns: (vector_string, version_string)
    """
    v4 = (cve or {}).get("cvss4") or {}
    if isinstance(v4, dict) and v4.get("vector"):
        return v4.get("vector"), "4.0"

    sev = (cve or {}).get("severity") or {}
    vector = sev.get("vector")
    ver = str(sev.get("version") or "").strip()
    if vector and ver.startswith("3.1"):
        return vector, "3.1"
    if vector and ver.startswith("3.0"):
        return vector, "3.0"

    # explicit fields fallback
    if cve.get("cvss_v3_vector"):
        return cve.get("cvss_v3_vector"), "3.x"
    if cve.get("cvss_v2_vector"):
        return cve.get("cvss_v2_vector"), "2.0"

    # sometimes severity.version is missing; infer by prefix
    if vector and vector.startswith("CVSS:3."):
        return vector, "3.x"
    if vector and vector.startswith("AV:"):
        # CVSS v2.0 often lacks the 'CVSS:2.0' prefix
        return vector, "2.0"

    return None, None


def parse_vector(vector: str) -> Dict[str, str]:
    """Parse a CVSS vector string into {metric: value} pairs.
    Does not modify the original string. Supports v2.0, v3.x, v4.0 formats.
    """
    if not vector:
        return {}

    parts = [p for p in vector.split('/') if p]
    kvs: Dict[str, str] = {}

    # skip leading 'CVSS:x.y' token
    if parts and parts[0].startswith("CVSS:"):
        parts = parts[1:]

    for token in parts:
        if ':' in token:
            k, v = token.split(':', 1)
            kvs[k.strip()] = v.strip()

    return kvs


def classify_parameters(parsed: Dict[str, str], version: str) -> Dict[str, List[Dict[str, str]]]:
    """Classify parsed metrics into exploitability, technical impact, lateral impact."""
    exploit_keys = ["AV", "AC", "AT", "PR", "UI"]
    impact_v3 = ["C", "I", "A"]
    impact_v4_vuln = ["VC", "VI", "VA"]
    impact_v4_subseq = ["SC", "SI", "SA"]

    exploitability = []
    technical = []
    lateral = []

    for k, v in parsed.items():
        if k in exploit_keys:
            exploitability.append({"key": k, "value": v})
        elif version.startswith("4") and k in impact_v4_vuln:
            technical.append({"key": k, "value": v})
        elif version.startswith("4") and k in impact_v4_subseq:
            lateral.append({"key": k, "value": v})
        elif (version.startswith("3") or version.startswith("2")) and k in impact_v3:
            technical.append({"key": k, "value": v})

    return {
        "exploitability": exploitability,
        "technical_impact": technical,
        "lateral_impact": lateral,
    }


def _explain_one(key: str, val: str, version: str) -> Dict[str, str]:
    name = METRIC_NAMES.get(key, key)
    label = ""
    meaning = ""

    if version.startswith("4"):
        table = VALUE_MEANINGS_V4.get(key, {})
        label, meaning = table.get(val, (val, ""))
    elif version.startswith("3"):
        table = VALUE_MEANINGS_V3.get(key, {})
        label, meaning = table.get(val, (val, ""))
    else:
        table = VALUE_MEANINGS_V2.get(key, {})
        label, meaning = table.get(val, (val, ""))

    return {
        "parameter": key,
        "raw_value": val,
        "name": name,
        "technical_meaning": label,
        "explanation": meaning,
    }


def explain_groups(groups: Dict[str, List[Dict[str, str]]], version: str) -> Dict[str, List[Dict[str, str]]]:
    return {
        "exploitability": [_explain_one(i["key"], i["value"], version) for i in groups.get("exploitability", [])],
        "technical_impact": [_explain_one(i["key"], i["value"], version) for i in groups.get("technical_impact", [])],
        "lateral_impact": [_explain_one(i["key"], i["value"], version) for i in groups.get("lateral_impact", [])],
    }


def summarize_explanation(version: Optional[str], parsed: Dict[str, str]) -> str:
    """Business-friendly one-liner summary derived from key exploitability metrics."""
    if not version:
        return "No CVSS vector available for analysis."

    av = parsed.get("AV")
    ui = parsed.get("UI")
    pr = parsed.get("PR")

    def _label(table: Dict[str, Tuple[str, str]], code: Optional[str]) -> Optional[str]:
        if not code:
            return None
        return table.get(code, (code, ""))[0]

    if version.startswith("4"):
        table = VALUE_MEANINGS_V4
    elif version.startswith("3"):
        table = VALUE_MEANINGS_V3
    else:
        table = VALUE_MEANINGS_V2

    av_l = _label(table.get("AV", {}), av)
    ui_l = _label(table.get("UI", {}), ui)
    pr_l = _label(table.get("PR", {}), pr)

    parts = []
    if av_l:
        parts.append(f"Attack Vector: {av_l}")
    if pr_l:
        parts.append(f"Privileges Required: {pr_l}")
    if ui_l:
        parts.append(f"User Interaction: {ui_l}")

    return ", ".join(parts) if parts else "CVSS vector parsed; see details."


def analyze_cvss_for_cve(cve: Dict) -> Dict[str, object]:
    """High-level API: select vector, parse, classify, explain, summarize."""
    vector, version = select_vector(cve)
    parsed = parse_vector(vector) if vector else {}
    groups = classify_parameters(parsed, version or "") if parsed else {"exploitability": [], "technical_impact": [], "lateral_impact": []}
    explained = explain_groups(groups, version or "") if parsed else groups

    return {
        "cvss_version_used": version,
        "vector": vector,
        "exploitability": explained.get("exploitability", []),
        "technical_impact": explained.get("technical_impact", []),
        "lateral_impact": explained.get("lateral_impact", []),
        "summary_explanation": summarize_explanation(version, parsed),
    }


# Convenience API for direct vector strings
def analyze_vector(vector: str) -> Dict[str, object]:
    version = None
    if vector and vector.startswith("CVSS:4"):
        version = "4.0"
    elif vector and vector.startswith("CVSS:3"):
        version = "3.x"
    elif vector:
        version = "2.0"

    parsed = parse_vector(vector)
    groups = classify_parameters(parsed, version or "")
    explained = explain_groups(groups, version or "")
    return {
        "cvss_version_used": version,
        "vector": vector,
        "exploitability": explained.get("exploitability", []),
        "technical_impact": explained.get("technical_impact", []),
        "lateral_impact": explained.get("lateral_impact", []),
        "summary_explanation": summarize_explanation(version, parsed),
    }
