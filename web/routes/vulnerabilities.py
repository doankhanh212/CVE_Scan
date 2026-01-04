from flask import Blueprint, jsonify, render_template
from web.services.scan_service import scan_service

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
                    
                    vulns.append({
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
                    })

    return jsonify({
        "scan_id": latest.get("scan_id"),
        "generated_at": latest.get("end_time") or latest.get("start_time"),
        "status": latest.get("status"),
        "total": len(vulns),
        "vulnerabilities": vulns
    })
