from flask import Blueprint, jsonify, render_template
from web.services.scan_service import scan_service
from modules.cve.likelihood_calculator import LikelihoodCalculator
import logging
import json
import os
from typing import List
from web.security_standards.owasp_mapping import OWASPMapper
from web.security_standards.mitre_attack_mapping import MITREMapper
from web.config_loader import ConfigLoader
from modules.cve.nvd_fetcher import NVDFetcherPRO
from modules.cve.cvss_vector_analysis import analyze_cvss_for_cve
from modules.cve.cwe_lookup import CWELookup

logger = logging.getLogger(__name__)

try:
    cwe_lookup = CWELookup()
except Exception as e:
    logger.warning(f"CWE lookup not available: {e}")
    cwe_lookup = None

# Load config files for OWASP/MITRE mapping
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'config')

def load_owasp_config():
    """Load OWASP Top 10 2021 mappings"""
    try:
        owasp_file = os.path.join(CONFIG_DIR, 'owasp_top10_2021.json')
        with open(owasp_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load OWASP config: {e}")
        return {"categories": []}

def load_mitre_config():
    """Load MITRE ATT&CK mappings"""
    try:
        mitre_file = os.path.join(CONFIG_DIR, 'mitre_attack_enterprise.json')
        with open(mitre_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load MITRE config: {e}")
        return {"tactics": []}

# Cache configs
_owasp_config = load_owasp_config()
_mitre_config = load_mitre_config()

# Cache for CWE IDs to avoid repeated NVD API calls
_cwe_cache = {}


def _extract_cwe_ids_from_nvd(cve_id: str) -> List[int]:
    """Fetch CVE detail from NVD and extract CWE IDs as integers.

    Caching behavior:
    - Use cache only when it contains a non-empty list
    - Do NOT permanently cache empty results, to avoid sticky failures when the
      first attempt hits network/rate-limit issues or when NVD later adds CWE data
    """
    cached = _cwe_cache.get(cve_id)
    if isinstance(cached, list) and len(cached) > 0:
        return cached

    try:
        fetcher = NVDFetcherPRO()
        vulns = fetcher.get_cve_by_id(cve_id)
        if not vulns:
            # Don't cache empty results; try again on next request
            return []

        cve = vulns[0].get("cve", {})
        cwe_ids: List[int] = []
        for w in cve.get("weaknesses", []) or []:
            for d in w.get("description", []) or []:
                val = d.get("value") or ""
                if isinstance(val, str) and val.startswith("CWE-"):
                    try:
                        cwe_ids.append(int(val.split("-", 1)[1]))
                    except Exception:
                        # Ignore malformed CWE strings
                        pass

        cwe_ids = list(sorted(set(cwe_ids)))
        # Only cache when we actually have CWE IDs
        if cwe_ids:
            _cwe_cache[cve_id] = cwe_ids
        return cwe_ids
    except Exception:
        # On errors, don't poison the cache with empty results
        return []

# Initialize likelihood calculator
try:
    likelihood_calc = LikelihoodCalculator()
except Exception as e:
    logger.warning(f"Likelihood calculator not initialized: {e}")
    likelihood_calc = None

vuln_bp = Blueprint("vulns", __name__)

# =========================
# PAGE
# =========================
@vuln_bp.route("/vulnerabilities", methods=["GET"])
def vulnerabilities_page():
    return render_template("vulnerabilities.html")

# =========================
# API
# =========================
@vuln_bp.route("/api/vulnerabilities", methods=["GET"])
def list_vulnerabilities():
    """
    Get all vulnerabilities from all scans (completed or running with results)
    """
    # IMPORTANT: Must include results to extract CVEs
    scans = scan_service.list_scans(include_results=True)
    if not scans:
        return jsonify({"vulnerabilities": [], "total": 0})

    # Get scans that have results (completed OR running with results)
    scans_with_results = [
        s for s in scans 
        if s.get("results") and len(s.get("results", {})) > 0
    ]
    
    if not scans_with_results:
        return jsonify({"vulnerabilities": [], "total": 0})
    
    # Get most recent scan for metadata (for generated_at, scan_id)
    latest = max(scans_with_results, key=lambda s: s.get("start_time") or "")
    
    vulns = []
    
    # Iterate through ALL scans with results (not just latest)
    for scan in scans_with_results:
        results = scan.get("results", {})

        for host, host_data in results.items():
            # Handle different data structures
            # 1. Check for "gui" key (new structure)
            if isinstance(host_data, dict) and "gui" in host_data:
                ports = host_data.get("gui", {}).get("ports", [])
            # 2. Check for "ports" key directly (normalized structure)
            elif isinstance(host_data, dict) and "ports" in host_data:
                ports = host_data.get("ports", [])
            else:
                continue
            
            for port_data in ports:
                port_num = port_data.get("port")
                service = port_data.get("service") or port_data.get("product", "unknown")
                version = port_data.get("version", "")
                
                for cve in port_data.get("cves", []):
                    # Extract CVE ID (handle both "id" and "cve_id")
                    cve_id = cve.get("cve_id") or cve.get("id", "N/A")
                    
                    # Extract severity
                    severity = cve.get("severity")
                    if isinstance(severity, dict):
                        severity_label = severity.get("label", "UNKNOWN")
                    elif isinstance(severity, str):
                        severity_label = severity
                    else:
                        severity_label = "UNKNOWN"
                    
                    # Extract CVSS scores (v2, v3, v4)
                    cvss_v2 = None
                    cvss_v3 = None
                    cvss_v4 = None
                    
                    # Try to extract from different locations
                    if isinstance(severity, dict):
                        cvss_v3 = severity.get("score")
                    
                    # Check for separate CVSS fields in CVE dict
                    if "cvss_v2" in cve or "cvss_v2_score" in cve:
                        cvss_v2 = cve.get("cvss_v2") or cve.get("cvss_v2_score")
                    if "cvss_v3" in cve or "cvss_v3_score" in cve:
                        cvss_v3 = cve.get("cvss_v3") or cve.get("cvss_v3_score")
                    if "cvss_v4" in cve or "cvss_v4_score" in cve:
                        cvss_v4 = cve.get("cvss_v4") or cve.get("cvss_v4_score")
                    
                    # Fallback to generic "cvss" field
                    if not cvss_v3 and not cvss_v2 and not cvss_v4:
                        cvss_v3 = cve.get("cvss") or cve.get("score")
                        if isinstance(cvss_v3, dict):
                            cvss_v3 = cvss_v3.get("base_score") or cvss_v3.get("score")
                    
                    # Extract description
                    description = cve.get("description")
                    if isinstance(description, dict):
                        summary = description.get("short") or description.get("value", "")
                    elif isinstance(description, str):
                        summary = description
                    else:
                        summary = cve.get("summary", "No description available")
                    
                    # Calculate likelihood if calculator is available
                    likelihood = None
                    if likelihood_calc and cve_id and cve_id.startswith("CVE-"):
                        try:
                            # Create temp CVE data structure for enrichment
                            temp_cve = {"cvss_v3": {"baseScore": cvss_v3} if cvss_v3 else None}
                            enriched = likelihood_calc.enrich_vulnerability_with_likelihood(temp_cve, cve_id)
                            if enriched.get("likelihood"):
                                likelihood = {
                                    "epss": enriched["likelihood"].get("epss"),
                                    "score": enriched["likelihood"].get("score"),
                                    "level": enriched["likelihood"].get("level")
                                }
                        except Exception as e:
                            logger.debug(f"Could not calculate likelihood for {cve_id}: {e}")
                    
                    vuln_data = {
                        "scan_id": scan.get("scan_id"),
                        "host": host,
                        "port": port_num,
                        "service": service,
                        "version": version,
                        "cve_id": cve_id,
                        "severity": severity_label.upper() if severity_label else "UNKNOWN",
                        "cvss_v2": cvss_v2,
                        "cvss_v3": cvss_v3,
                        "cvss_v4": cvss_v4,
                        "summary": summary[:500] if summary else "No description available"
                    }
                    
                    # Add likelihood if available
                    if likelihood:
                        vuln_data["likelihood"] = likelihood
                    
                    vulns.append(vuln_data)

    return jsonify({
        "scan_id": latest.get("scan_id"),
        "generated_at": latest.get("end_time") or latest.get("start_time"),
        "status": latest.get("status"),
        "total": len(vulns),
        "vulnerabilities": vulns
    })
@vuln_bp.route("/api/cve/<cve_id>/analysis", methods=["POST"])
def get_cve_analysis(cve_id):
    """
    Fetch CVE analysis from NVD or scan results
    Returns: title, description, cvss (v2, v3, v4), affected products, etc.
    Note: This is a stub that returns minimal data from scan results
    Full NVD integration can be added later
    """
    try:
        # Try to find CVE in scans
        scans = scan_service.list_scans(include_results=True)
        
        for scan in scans:
            results = scan.get("results", {})
            for host, host_data in results.items():
                # Handle different data structures
                if isinstance(host_data, dict) and "gui" in host_data:
                    ports = host_data.get("gui", {}).get("ports", [])
                elif isinstance(host_data, dict) and "ports" in host_data:
                    ports = host_data.get("ports", [])
                else:
                    continue
                
                for port_data in ports:
                    for cve in port_data.get("cves", []):
                        cve_found_id = cve.get("cve_id") or cve.get("id", "")
                        if cve_found_id == cve_id:
                            # Found the CVE, extract analysis data
                            cvss_v2 = cve.get("cvss_v2")
                            cvss_v3 = cve.get("cvss_v3")
                            cvss_v4 = cve.get("cvss_v4")
                            
                            # Extract severity
                            severity = cve.get("severity")
                            if isinstance(severity, dict):
                                severity_label = severity.get("label", "UNKNOWN")
                            else:
                                severity_label = str(severity)
                            
                            description = cve.get("description", "")
                            if isinstance(description, dict):
                                description = description.get("value", "")
                            
                            # Derive CWE IDs from NVD for accurate mappings
                            cwe_ids = _extract_cwe_ids_from_nvd(cve_id)

                            # OWASP mapping via CWE → OWASP codes
                            owasp_result = OWASPMapper.get_by_cve_id(cve_id, cwe_ids)
                            owasp_categories = []
                            for m in owasp_result.get("owasp_mappings", [])[:3]:
                                code = m.get("owasp_code")
                                cat = ConfigLoader.get_owasp_by_code(code) if code else {}
                                if code and cat:
                                    owasp_categories.append({
                                        "code": code,
                                        "name": cat.get("name"),
                                        "description": cat.get("description")
                                    })

                            # MITRE mapping via CWE → techniques
                            mitre_result = MITREMapper.get_by_cve(cve_id, cwe_ids)
                            # Group techniques by tactic
                            tmap = {}
                            for tech in mitre_result.get("techniques", []):
                                tid = tech.get("tactic_id")
                                if not tid:
                                    continue
                                tmap.setdefault(tid, {"id": tid, "name": ConfigLoader.get_mitre_tactic(tid).get("name"), "description": ConfigLoader.get_mitre_tactic(tid).get("description"), "techniques": []})
                                tmap[tid]["techniques"].append({
                                    "id": tech.get("technique_id") or tech.get("id"),
                                    "name": tech.get("technique_name") or tech.get("name"),
                                    "description": tech.get("description")
                                })

                            tactics_with_techniques = list(tmap.values())

                            # CVSS vector analysis (explainability layer)
                            cvss_analysis = analyze_cvss_for_cve(cve)

                            # CWE explanations (consequences and mitigations)
                            cwe_explanations_list = []
                            if cwe_ids and cwe_lookup:
                                for cwe_id_num in cwe_ids[:5]:
                                    try:
                                        cwe_explanation = cwe_lookup.get_full_explanation(f"CWE-{cwe_id_num}")
                                        if cwe_explanation:
                                            cwe_explanations_list.append(cwe_explanation)
                                    except Exception as e:
                                        logger.debug(f"Could not fetch CWE-{cwe_id_num} explanation: {e}")

                            # Log for troubleshooting: how many CWE explanations we found
                            logger.info(f"[CWE] CVE: {cve_id}, CWE IDs: {cwe_ids} -> explanations: {len(cwe_explanations_list)}")

                            return jsonify({
                                "cve_id": cve_id,
                                "title": cve.get("title", cve_id),
                                "description": description,
                                "severity": severity_label,
                                "cvss": {
                                    "v2": {"base_score": cvss_v2} if cvss_v2 else None,
                                    "v3": {"base_score": cvss_v3} if cvss_v3 else None,
                                    "v4": {"base_score": cvss_v4} if cvss_v4 else None,
                                },
                                "cvss_analysis": cvss_analysis,
                                "cwe_explanations": cwe_explanations_list,
                                "owasp": owasp_categories,
                                "mitre": {
                                    "tactics": tactics_with_techniques
                                },
                                "affected_cpes": cve.get("cpes", []),
                                "recommendations": [cve.get("summary", "")]
                            })
        
        # CVE not found in scans
        return jsonify({"error": f"CVE {cve_id} not found"}), 404
    
    except Exception as e:
        logger.error(f"Error fetching analysis for {cve_id}: {e}")
        return jsonify({"error": str(e)}), 500


@vuln_bp.route("/api/cve/<cve_id>/likelihood", methods=["GET"])
def get_cve_likelihood(cve_id):
    """
    Calculate likelihood for a specific CVE
    Returns EPSS, percentile, likelihood score, and level
    """
    if not likelihood_calc:
        return jsonify({"error": "Likelihood calculator not available"}), 503
    
    try:
        # 🔹 BƯỚC 1: Get CVSS from NVD or scan results
        # For now, we'll calculate with a generic CVSS value
        # Frontend will provide actual CVSS from modal
        
        # 🔹 BƯỚC 2: Get EPSS by CVE ID
        epss, percentile = likelihood_calc.get_epss_from_db(cve_id)
        
        return jsonify({
            "cve_id": cve_id,
            "epss": epss,
            "percentile": percentile,
            "note": "Multiply by CVSS base score to get likelihood"
        })
    except Exception as e:
        logger.error(f"Error calculating likelihood for {cve_id}: {e}")
        return jsonify({"error": str(e)}), 500


@vuln_bp.route("/api/cve/<cve_id>/nist-recommendations", methods=["POST"])
def get_nist_recommendations(cve_id):
    """
    Get NIST R5 control recommendations for a CVE
    Based on CWE Mitigations descriptions from frontend
    
    Request body:
    {
        "mitigation_texts": ["description1", "description2", ...],
        "cve_description": "...",
        "cwe_ids": [390, 123, ...]
    }
    """
    try:
        from modules.nist_recommendation import get_engine
        from flask import request
        
        # Get data from request
        data = request.get_json() or {}
        mitigation_texts = data.get("mitigation_texts", [])
        cve_description = data.get("cve_description", "")
        cwe_ids = data.get("cwe_ids", [])
        
        # Combine all texts for analysis
        all_texts = mitigation_texts + ([cve_description] if cve_description else [])
        combined_text = " ".join(str(t) for t in all_texts if t)
        
        # Get NIST recommendations based on combined mitigation text
        engine = get_engine()
        recommendations = engine.get_recommendations(combined_text, cwe_ids)
        
        # Format response
        return jsonify({
            "cve_id": cve_id,
            "recommendations": recommendations,
            "total": len(recommendations),
            "analyzed_text_length": len(combined_text)
        })
    
    except Exception as e:
        logger.error(f"Error getting NIST recommendations for {cve_id}: {e}", exc_info=True)
        return jsonify({"error": str(e), "recommendations": []}), 500