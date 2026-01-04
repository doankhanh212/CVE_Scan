"""
CVE Detail Analysis with Security Standards Mapping
Provides comprehensive CVE analysis with OWASP, MITRE, CVSS details
"""

from flask import Blueprint, jsonify, request
from web.security_standards import UnifiedSecurityMapper
from web.services.scan_service import scan_service

cve_detail_bp = Blueprint('cve_detail', __name__, url_prefix='/api')


@cve_detail_bp.route('/cve/<cve_id>/detail', methods=['GET'])
def get_cve_detail(cve_id: str):
    """
    Get detailed CVE information including security standards mapping
    
    GET /api/cve/CVE-2023-12345/detail
    
    Query params:
    - scan_id: (optional) Filter to specific scan
    - host: (optional) Filter to specific host
    """
    scan_id = request.args.get('scan_id')
    host = request.args.get('host')
    
    # Get CVE from all scans
    cve_data = _find_cve_in_scans(cve_id, scan_id, host)
    
    if not cve_data:
        return jsonify({"error": f"CVE {cve_id} not found"}), 404
    
    # Extract CWE IDs from CVE data
    cwe_ids = _extract_cwe_ids(cve_data)
    
    # Get security standards mapping
    analysis = UnifiedSecurityMapper.analyze_cve(
        cve_id=cve_id,
        cwe_ids=cwe_ids,
        description=cve_data.get('description', ''),
        severity=cve_data.get('severity', {}).get('label', 'UNKNOWN') if isinstance(cve_data.get('severity'), dict) else cve_data.get('severity', 'UNKNOWN')
    )
    
    # Build comprehensive response
    response = {
        "cve_id": cve_id,
        "cwe_ids": cwe_ids,
        
        # Basic info
        "description": cve_data.get('description', 'N/A'),
        "severity": _extract_severity(cve_data),
        
        # CVSS Scores
        "cvss": {
            "v2": cve_data.get('cvss_v2'),
            "v3": cve_data.get('cvss_v3'),
            "v4": cve_data.get('cvss_v4'),
            "vector_v3": _extract_cvss_vector(cve_data)
        },
        
        # Security Standards Mapping
        "security_standards": {
            "owasp": analysis["owasp"],
            "mitre_attack": analysis["mitre_attack"],
            "secure_coding": analysis["secure_coding"],
            "risk_score": analysis["risk_score"]
        },
        
        # Context
        "attack_context": analysis["attack_context"],
        "recommendations": analysis["recommendations"],
        
        # Source info
        "cpe": cve_data.get('cpe'),
        "found_in": {
            "scan_id": scan_id,
            "host": host,
            "port": request.args.get('port'),
            "service": request.args.get('service')
        }
    }
    
    return jsonify(response), 200


@cve_detail_bp.route('/cve/<cve_id>/analysis', methods=['POST'])
def cve_analysis(cve_id: str):
    """
    Get detailed CVE analysis for modal display
    POST /api/cve/CVE-2023-12345/analysis
    
    Returns: {
        cve_id, title, description, cvss, owasp, mitre, scp, affected_cpes, recommendations, risk_score
    }
    """
    # Find CVE in scans
    cve_data = _find_cve_in_scans(cve_id)
    
    if not cve_data:
        return jsonify({"error": f"CVE {cve_id} not found"}), 404
    
    # Extract CWE IDs
    cwe_ids = _extract_cwe_ids(cve_data)
    
    # DEBUG: Log CWE extraction
    import sys
    print(f"[CVE_DETAIL] CVE: {cve_id}, CWE_IDs extracted: {cwe_ids}", file=sys.stderr)
    print(f"[CVE_DETAIL] Full CVE data keys: {cve_data.keys()}", file=sys.stderr)
    
    # Get unified analysis
    analysis = UnifiedSecurityMapper.analyze_cve(
        cve_id=cve_id,
        cwe_ids=cwe_ids,
        description=cve_data.get('description', ''),
        severity=_extract_severity_label(cve_data)
    )
    
    # Extract CVSS details
    cvss_response = _extract_cvss_details(cve_data)
    
    # Format OWASP for modal (from owasp.mappings array)
    owasp_list = []
    if analysis.get("owasp"):
        for mapping in analysis["owasp"].get("mappings", []):
            owasp_list.append({
                "category": mapping.get("owasp_code"),
                "name": mapping.get("owasp_name"),
                "risk_rating": _score_to_severity(mapping.get("risk_weight", 5.0)),
                "description": mapping.get("description", "")
            })
    
    # Format MITRE for modal (from mitre_attack.techniques)
    mitre_dict = {}
    if analysis.get("mitre_attack"):
        for technique in analysis["mitre_attack"].get("techniques", []):
            tactic = technique.get("tactic_name", "Reconnaissance")
            if tactic not in mitre_dict:
                mitre_dict[tactic] = []
            mitre_dict[tactic].append(f"{technique.get('technique_id', '')} - {technique.get('technique_name', '')}")
    
    # Format SCP for modal (from secure_coding.practices)
    scp_list = []
    if analysis.get("secure_coding"):
        for practice in analysis["secure_coding"].get("practices", []):
            scp_list.append({
                "category": practice.get("category", ""),
                "practice": practice.get("practice", ""),
                "severity": practice.get("severity", "MEDIUM"),
                "description": practice.get("description", "")
            })
    
    # Build modal response
    response = {
        "cve_id": cve_id,
        "title": cve_data.get('name') or f"{cve_id} Vulnerability",
        "description": cve_data.get('description', 'No description available'),
        "cvss": cvss_response,
        "owasp": owasp_list,
        "mitre": mitre_dict,
        "scp": scp_list,
        "affected_cpes": cve_data.get('cpe', []) if isinstance(cve_data.get('cpe'), list) else [cve_data.get('cpe', 'N/A')],
        "recommendations": analysis.get("recommendations", []),
        "risk_score": analysis.get("risk_score", 5.0)
    }
    
    return jsonify(response), 200


@cve_detail_bp.route('/cve/<cve_id>/remediation', methods=['GET'])
def get_cve_remediation(cve_id: str):
    """Get remediation guidance for CVE"""
    cwe_ids = request.args.getlist('cwe_ids', type=int)
    
    if not cwe_ids:
        return jsonify({"error": "cwe_ids required"}), 400
    
    analysis = UnifiedSecurityMapper.analyze_cve(
        cve_id=cve_id,
        cwe_ids=cwe_ids
    )
    
    return jsonify({
        "cve_id": cve_id,
        "recommendations": analysis["recommendations"],
        "owasp_remediation": [
            {
                "code": m.get("owasp_code"),
                "name": m.get("owasp_name"),
                "guidance": _get_owasp_guidance(m.get("owasp_code"))
            }
            for m in analysis["owasp"]["mappings"]
        ],
        "secure_coding_practices": analysis["secure_coding"]["practices"]
    }), 200


@cve_detail_bp.route('/cve/batch-analysis', methods=['POST'])
def batch_cve_analysis():
    """Analyze multiple CVEs at once"""
    data = request.get_json() or {}
    cves = data.get('cves', [])
    
    if not cves:
        return jsonify({"error": "cves array required"}), 400
    
    results = []
    for cve_item in cves:
        analysis = UnifiedSecurityMapper.analyze_cve(
            cve_id=cve_item.get('id'),
            cwe_ids=cve_item.get('cwe_ids', []),
            severity=cve_item.get('severity', 'MEDIUM')
        )
        results.append(analysis)
    
    return jsonify({
        "total": len(results),
        "analyses": results
    }), 200


# =====================================================================
# Helper Functions
# =====================================================================

def _find_cve_in_scans(cve_id: str, scan_id: str = None, host: str = None) -> dict:
    """Find CVE data in scan results"""
    scans = scan_service.list_scans(include_results=True)
    
    for scan in scans:
        if scan_id and scan.get('scan_id') != scan_id:
            continue
        
        results = scan.get('results', {})
        
        for host_label, host_data in results.items():
            if host and host_label != host:
                continue
            
            ports = host_data.get('ports', [])
            
            for port_data in ports:
                for cve in port_data.get('cves', []):
                    cve_check_id = cve.get('cve_id') or cve.get('id')
                    if cve_check_id == cve_id:
                        return cve
    
    return None


def _extract_cwe_ids(cve_data: dict) -> list:
    """Extract CWE IDs from CVE data or infer from description"""
    import re
    
    # Try various possible locations
    cwe_ids = cve_data.get('cwe_ids', [])
    if not cwe_ids:
        cwe_ids = cve_data.get('cwe', [])
    
    if cwe_ids:
        return cwe_ids if isinstance(cwe_ids, list) else [cwe_ids]
    
    # If no explicit CWE found, try to infer from description
    description = (cve_data.get('description') or '').lower()
    product = (cve_data.get('product') or '').lower()
    
    # CWE inference rules based on keywords
    cwe_mapping = {
        'buffer overflow': 120,  # CWE-120: Buffer Copy without Checking Size of Input
        'heap overflow': 122,    # CWE-122: Heap-based Buffer Overflow
        'stack overflow': 674,   # CWE-674: Uncontrolled Recursion
        'integer overflow': 190, # CWE-190: Integer Overflow or Wraparound
        'sql injection': 89,     # CWE-89: SQL Injection
        'xss': 79,              # CWE-79: Improper Neutralization of Input During Web Page Generation
        'cross-site scripting': 79,
        'command injection': 78, # CWE-78: OS Command Injection
        'path traversal': 22,    # CWE-22: Path Traversal
        'directory traversal': 22,
        'authentication': 287,   # CWE-287: Improper Authentication
        'authorization': 285,    # CWE-285: Improper Access Control
        'cryptographic': 327,    # CWE-327: Use of Broken Crypto
        'weak encryption': 327,
        'arbitrary file': 434,   # CWE-434: Unrestricted Upload of File with Dangerous Type
        'upload': 434,
        'xxe': 611,             # CWE-611: Improper Restriction of XML External Entity Reference
        'xml external entity': 611,
        'insecure deserialization': 502, # CWE-502: Deserialization of Untrusted Data
        'deserialization': 502,
        'race condition': 362,   # CWE-362: Concurrent Execution using Shared Resource with Improper Synchronization
        'use after free': 416,   # CWE-416: Use After Free
        'null pointer': 476,     # CWE-476: Null Pointer Dereference
        'format string': 134,    # CWE-134: Use of Externally-Controlled Format String
    }
    
    inferred_cwe = set()
    for keyword, cwe_id in cwe_mapping.items():
        if keyword in description or keyword in product:
            inferred_cwe.add(cwe_id)
    
    if inferred_cwe:
        return list(inferred_cwe)
    
    # Default: return common CWE for general vulnerabilities
    # This is a fallback for unknown vulnerabilities
    return [79, 89, 434]  # XSS, SQL Injection, File Upload


def _extract_severity(cve_data: dict) -> dict:
    """Extract severity information"""
    severity = cve_data.get('severity')
    
    if isinstance(severity, dict):
        return {
            "label": severity.get('label', 'UNKNOWN'),
            "score": severity.get('score'),
            "vector": severity.get('vector'),
            "version": severity.get('version', '3.1')
        }
    elif isinstance(severity, str):
        return {
            "label": severity.upper(),
            "score": None,
            "vector": None,
            "version": None
        }
    else:
        return {
            "label": "UNKNOWN",
            "score": None,
            "vector": None,
            "version": None
        }


def _extract_severity_label(cve_data: dict) -> str:
    """Extract severity label as string"""
    severity = cve_data.get('severity')
    
    if isinstance(severity, dict):
        return severity.get('label', 'UNKNOWN').upper()
    elif isinstance(severity, str):
        return severity.upper()
    else:
        return 'UNKNOWN'


def _extract_cvss_details(cve_data: dict) -> dict:
    """Extract CVSS score and vector details"""
    response = {}
    
    # CVSS v2
    cvss_v2 = cve_data.get('cvss_v2')
    if cvss_v2:
        if isinstance(cvss_v2, dict):
            response['v2'] = {
                'base_score': cvss_v2.get('base_score'),
                'vector': cvss_v2.get('vector')
            }
        else:
            response['v2'] = {
                'base_score': cvss_v2,
                'vector': None
            }
    
    # CVSS v3
    cvss_v3 = cve_data.get('cvss_v3')
    if cvss_v3:
        if isinstance(cvss_v3, dict):
            response['v3'] = {
                'base_score': cvss_v3.get('base_score'),
                'vector': cvss_v3.get('vector')
            }
        else:
            response['v3'] = {
                'base_score': cvss_v3,
                'vector': None
            }
    
    # CVSS v4
    cvss_v4 = cve_data.get('cvss_v4')
    if cvss_v4:
        if isinstance(cvss_v4, dict):
            response['v4'] = {
                'base_score': cvss_v4.get('base_score'),
                'vector': cvss_v4.get('vector')
            }
        else:
            response['v4'] = {
                'base_score': cvss_v4,
                'vector': None
            }
    
    return response


def _extract_cvss_vector(cve_data: dict) -> str:
    """Extract CVSS vector string"""
    severity = cve_data.get('severity')
    
    if isinstance(severity, dict):
        return severity.get('vector', '')
    
    return ''


def _get_owasp_guidance(owasp_code: str) -> str:
    """Get remediation guidance for OWASP category"""
    guidance_map = {
        "A01": "Implement proper access control checks. Use deny-by-default principle. Verify user permissions on every protected operation.",
        "A02": "Use strong cryptography (AES-256, TLS 1.2+). Implement secure key management and rotation.",
        "A03": "Validate all input using whitelist approach. Use parameterized queries. Escape output based on context.",
        "A04": "Threat model during design. Implement security controls early. Regular security reviews.",
        "A05": "Harden configuration. Remove unnecessary services. Apply security patches. Use strong authentication.",
        "A06": "Keep dependencies updated. Monitor vulnerabilities. Use dependency scanning tools.",
        "A07": "Implement strong password policies. Use MFA. Secure session management.",
        "A08": "Use digital signatures and checksums. Implement integrity verification.",
        "A09": "Implement comprehensive logging. Monitor for security events. Have incident response plan.",
        "A10": "Validate and sanitize URLs. Use allowlist for domains. Implement network segmentation."
    }
    
    return guidance_map.get(owasp_code, "Implement appropriate security controls")


def _score_to_severity(score: float) -> str:
    """Convert numeric score to severity label"""
    if score >= 8.5:
        return "CRITICAL"
    elif score >= 7.0:
        return "HIGH"
    elif score >= 4.0:
        return "MEDIUM"
    elif score >= 1.0:
        return "LOW"
    else:
        return "INFO"
