from flask import Blueprint, render_template
from web.services.scan_service import scan_service

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def dashboard():
    # Get lightweight scan list (summary only, no heavy results)
    scans = scan_service.list_scans(include_results=False)
    
    # Default empty stats
    default_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    default_summary = {
        "hosts_scanned": 0,
        "open_ports": 0,
        "total_cves": 0,
        "severity": default_severity
    }
    
    # Get completed scans only
    completed = [s for s in scans if s.get("status") == "completed"]
    
    if completed and len(completed) >= 1:
        # Sort by end_time to get latest
        completed.sort(key=lambda s: s.get("end_time") or "", reverse=True)
        latest = completed[0]
        summary = latest.get("summary", default_summary)
        
        # Calculate changes from previous scan if available
        changes = {
            "hosts_change": 0,
            "ports_change": 0,
            "cves_change": 0,
            "critical_change": 0
        }
        
        if len(completed) >= 2:
            prev = completed[1]
            prev_summary = prev.get("summary", default_summary)
            
            changes["hosts_change"] = summary.get("hosts_scanned", 0) - prev_summary.get("hosts_scanned", 0)
            changes["ports_change"] = summary.get("open_ports", 0) - prev_summary.get("open_ports", 0)
            changes["cves_change"] = summary.get("total_cves", 0) - prev_summary.get("total_cves", 0)
            changes["critical_change"] = summary.get("severity", {}).get("critical", 0) - prev_summary.get("severity", {}).get("critical", 0)
    else:
        summary = default_summary
        latest = None
        changes = {
            "hosts_change": 0,
            "ports_change": 0,
            "cves_change": 0,
            "critical_change": 0
        }

    stats = {
        "hosts_scanned": summary.get("hosts_scanned", 0),
        "open_ports": summary.get("open_ports", 0),
        "total_cves": summary.get("total_cves", 0),
        "critical": summary.get("severity", {}).get("critical", 0),
        **changes
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        severity=summary.get("severity", default_severity),
        last_scan_time=latest.get("end_time") if latest else "Never",
        recent_scans=completed[:5],
        username="Admin"
    )
