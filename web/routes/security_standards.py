"""
Security Standards Analysis API Routes
OWASP Top 10, MITRE ATT&CK, Secure Coding Practices
"""

from flask import Blueprint, jsonify, request
from web.security_standards import UnifiedSecurityMapper, OWASPMapper, MITREMapper, SecureCodeMapper

security_bp = Blueprint('security_standards', __name__, url_prefix='/api/security')


# =====================================================================
# UNIFIED ANALYSIS
# =====================================================================
@security_bp.route('/analyze/cve', methods=['POST'])
def analyze_cve():
    """
    Comprehensive CVE analysis against all security standards
    
    POST /api/security/analyze/cve
    {
        "cve_id": "CVE-2023-12345",
        "cwe_ids": [79, 80],
        "description": "XSS vulnerability...",
        "severity": "HIGH"
    }
    """
    data = request.get_json() or {}
    
    analysis = UnifiedSecurityMapper.analyze_cve(
        cve_id=data.get('cve_id'),
        cwe_ids=data.get('cwe_ids', []),
        description=data.get('description', ''),
        severity=data.get('severity', 'MEDIUM')
    )
    
    return jsonify(analysis), 200


@security_bp.route('/analyze/batch', methods=['POST'])
def analyze_batch():
    """
    Batch analyze multiple CVEs
    
    POST /api/security/analyze/batch
    {
        "findings": [
            {"id": "CVE-2023-1", "cwe_ids": [...], "severity": "HIGH"},
            ...
        ]
    }
    """
    data = request.get_json() or {}
    findings = data.get('findings', [])
    
    if not findings:
        return jsonify({"error": "findings is required"}), 400
    
    analysis = UnifiedSecurityMapper.analyze_multiple_cves(findings)
    
    return jsonify(analysis), 200


# =====================================================================
# OWASP TOP 10
# =====================================================================
@security_bp.route('/owasp/categories', methods=['GET'])
def get_owasp_categories():
    """Get all OWASP Top 10 categories"""
    categories = OWASPMapper.get_all_categories()
    
    return jsonify({
        "total": len(categories),
        "categories": {
            code: {
                "code": cat.code,
                "name": cat.name,
                "description": cat.description,
                "risk_weight": cat.risk_weight,
                "cwe_count": len(cat.cwe_ids)
            }
            for code, cat in categories.items()
        }
    }), 200


@security_bp.route('/owasp/by-cwe/<int:cwe_id>', methods=['GET'])
def get_owasp_by_cwe(cwe_id: int):
    """Get OWASP category for specific CWE"""
    owasp_code, category = OWASPMapper.get_by_cwe(cwe_id)
    
    if not category:
        return jsonify({"error": f"CWE {cwe_id} not mapped to OWASP"}), 404
    
    return jsonify({
        "cwe_id": cwe_id,
        "owasp_code": owasp_code,
        "owasp_name": category.name,
        "description": category.description,
        "risk_weight": category.risk_weight
    }), 200


@security_bp.route('/owasp/by-cve/<cve_id>', methods=['GET'])
def get_owasp_by_cve(cve_id: str):
    """Get OWASP mappings for CVE"""
    cwe_ids = request.args.getlist('cwe_ids', type=int)
    
    result = OWASPMapper.get_by_cve_id(cve_id, cwe_ids)
    
    return jsonify(result), 200


# =====================================================================
# MITRE ATT&CK
# =====================================================================
@security_bp.route('/mitre/tactics', methods=['GET'])
def get_mitre_tactics():
    """Get all MITRE ATT&CK tactics"""
    tactics = MITREMapper.get_all_tactics()
    
    return jsonify({
        "total": len(tactics),
        "tactics": {
            tactic_id: {
                "id": tactic.id,
                "name": tactic.name,
                "description": tactic.description,
                "technique_count": len(tactic.techniques)
            }
            for tactic_id, tactic in tactics.items()
        }
    }), 200


@security_bp.route('/mitre/reconnaissance', methods=['GET'])
def get_mitre_reconnaissance():
    """Get reconnaissance techniques (critical for ASM)"""
    techniques = MITREMapper.get_reconnaissance_threats()
    
    technique_details = [
        {
            "id": tech_id,
            "name": MITREMapper.get_technique(tech_id).name,
            "description": MITREMapper.get_technique(tech_id).description
        }
        for tech_id in techniques
    ]
    
    return jsonify({
        "tactic": "Reconnaissance",
        "technique_count": len(techniques),
        "techniques": technique_details
    }), 200


@security_bp.route('/mitre/initial-access', methods=['GET'])
def get_mitre_initial_access():
    """Get initial access techniques"""
    techniques = MITREMapper.get_initial_access_threats()
    
    technique_details = [
        {
            "id": tech_id,
            "name": MITREMapper.get_technique(tech_id).name,
            "description": MITREMapper.get_technique(tech_id).description
        }
        for tech_id in techniques
    ]
    
    return jsonify({
        "tactic": "Initial Access",
        "technique_count": len(techniques),
        "techniques": technique_details
    }), 200


@security_bp.route('/mitre/by-cve/<cve_id>', methods=['GET'])
def get_mitre_by_cve(cve_id: str):
    """Get MITRE ATT&CK mappings for CVE"""
    cwe_ids = request.args.getlist('cwe_ids', type=int)
    
    result = MITREMapper.get_by_cve(cve_id, cwe_ids)
    
    return jsonify(result), 200


# =====================================================================
# SECURE CODING PRACTICES
# =====================================================================
@security_bp.route('/scp/categories', methods=['GET'])
def get_scp_categories():
    """Get all Secure Coding Practice categories"""
    categories = SecureCodeMapper.get_all_categories()
    
    return jsonify({
        "total": len(categories),
        "categories": {
            cat_name: {
                "name": cat_name,
                "practice_count": len(practices),
                "practices": [
                    {
                        "id": p.id,
                        "practice": p.practice,
                        "severity": p.severity
                    }
                    for p in practices
                ]
            }
            for cat_name, practices in categories.items()
        }
    }), 200


@security_bp.route('/scp/by-category/<category>', methods=['GET'])
def get_scp_by_category(category: str):
    """Get practices for specific category"""
    practices = SecureCodeMapper.get_by_category(category)
    
    if not practices:
        return jsonify({"error": f"Category '{category}' not found"}), 404
    
    return jsonify({
        "category": category,
        "practice_count": len(practices),
        "practices": [
            {
                "id": p.id,
                "practice": p.practice,
                "description": p.description,
                "severity": p.severity,
                "remediation": p.remediation
            }
            for p in practices
        ]
    }), 200


@security_bp.route('/scp/by-cve/<cve_id>', methods=['GET'])
def get_scp_by_cve(cve_id: str):
    """Get Secure Coding Practices for CVE"""
    cwe_ids = request.args.getlist('cwe_ids', type=int)
    
    result = SecureCodeMapper.get_by_cve(cve_id, cwe_ids)
    
    return jsonify(result), 200


# =====================================================================
# HEALTH CHECK
# =====================================================================
@security_bp.route('/health', methods=['GET'])
def health():
    """Health check for security standards API"""
    return jsonify({
        "status": "operational",
        "frameworks": {
            "owasp_top_10": True,
            "mitre_attack": True,
            "secure_coding_practices": True
        },
        "total_mappings": {
            "owasp_categories": len(OWASPMapper.get_all_categories()),
            "mitre_tactics": len(MITREMapper.get_all_tactics()),
            "scp_practices": len(SecureCodeMapper.get_all_categories())
        }
    }), 200
