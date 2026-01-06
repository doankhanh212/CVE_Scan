from flask import Blueprint, render_template
from web.services.scan_service import scan_service
from datetime import datetime, timedelta
from collections import defaultdict

dashboard_bp = Blueprint("dashboard", __name__)

def _extract_top_ports(scan_results):
    """Extract top vulnerable ports from scan results"""
    port_count = defaultdict(int)
    port_services = {}
    
    if not scan_results:
        return [], []
    
    # scan_results is a dict: { "host_label": { "hosts": [...], ... }, ... }
    if not isinstance(scan_results, dict):
        return [], []
    
    # Count CVEs per port across all hosts
    for host_label, host_data in scan_results.items():
        if not isinstance(host_data, dict):
            continue
        
        # NEW: Handle nested 'hosts' structure
        hosts_list = host_data.get("hosts", [])
        if not isinstance(hosts_list, list):
            continue
        
        for host in hosts_list:
            if not isinstance(host, dict):
                continue
            
            # Get vulnerabilities from this host
            vulnerabilities = host.get("vulnerabilities", [])
            if not isinstance(vulnerabilities, list):
                continue
            
            # Count CVEs by service (e.g., "ssh:22")
            for vuln in vulnerabilities:
                if not isinstance(vuln, dict):
                    continue
                
                service_name = vuln.get("service", "unknown")  # e.g., "ssh:22"
                
                # Extract port number from service name
                if ":" in service_name:
                    service_label, port_str = service_name.rsplit(":", 1)
                    try:
                        port_num = int(port_str)
                    except:
                        port_num = port_str
                else:
                    service_label = service_name
                    port_num = "unknown"
                
                port_services[port_num] = service_label
                port_count[port_num] += 1  # Count each CVE
    
    # Sort by CVE count descending - show top 10 ports (or all if less than 10)
    sorted_ports = sorted(port_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Format labels with service:port format
    labels = []
    for p in sorted_ports:
        port_num = p[0]
        service = port_services.get(port_num, "unknown")
        labels.append(f"{service}:{port_num}")
    
    values = [p[1] for p in sorted_ports]
    
    return labels, values

def _extract_critical_cves(scan_results, limit=5):
    """Extract critical/high CVEs from scan results"""
    cves = []
    
    if not scan_results:
        return cves
    
    # scan_results is a dict: { "host_label": { "ports": [...], ... }, ... }
    if not isinstance(scan_results, dict):
        return cves
    
    # Iterate through each host
    for host_label, host_data in scan_results.items():
        if not isinstance(host_data, dict):
            continue
        
        ports = host_data.get("ports", [])
        if not isinstance(ports, list):
            continue
        
        # Iterate through ports on this host
        for port_info in ports:
            if not isinstance(port_info, dict):
                continue
            
            port = port_info.get("port", "unknown")
            service = port_info.get("service", "unknown")
            cves_list = port_info.get("cves", [])
            
            if not isinstance(cves_list, list):
                continue
            
            # Iterate through CVEs on this port
            for cve in cves_list:
                if not isinstance(cve, dict):
                    continue
                
                severity = cve.get("severity", {})
                if isinstance(severity, dict):
                    severity_label = severity.get("label", "unknown")
                else:
                    severity_label = str(severity)
                
                # Only collect critical and high (case-insensitive)
                if severity_label.upper() in ["CRITICAL", "HIGH"]:
                    # Handle CVSS score
                    cvss = 0
                    if isinstance(cve.get("cvss_v3"), (int, float)):
                        cvss = float(cve.get("cvss_v3", 0))
                    elif isinstance(cve.get("cvss_v2"), (int, float)):
                        cvss = float(cve.get("cvss_v2", 0))
                    elif isinstance(cve.get("severity"), dict):
                        cvss = float(cve.get("severity", {}).get("score", 0))
                    
                    cves.append({
                        "id": cve.get("id", "unknown"),
                        "host": host_label,
                        "port": port,
                        "service": service,
                        "severity": severity_label.capitalize(),
                        "cvss": cvss,
                        "description": cve.get("description", "")[:100]
                    })
    
    # Sort by CVSS score descending
    cves.sort(key=lambda x: x.get("cvss", 0), reverse=True)
    return cves[:limit]

def _calculate_security_posture(stats, severity):
    """Calculate security posture score (0-100)"""
    if stats["total_cves"] == 0:
        return 100
    
    # Simple formula: penalize based on critical/high count
    critical = severity.get("critical", 0)
    high = severity.get("high", 0)
    
    # Each critical = -10 points, each high = -5 points, max penalty = -50
    penalty = min(50, (critical * 10) + (high * 5))
    return max(0, 100 - penalty)

def _extract_host_risk(scan_results):
    """Extract host risk assessment data with deduplication by IP"""
    from collections import defaultdict
    import re
    
    if not scan_results or not isinstance(scan_results, dict):
        return []
    
    # Dictionary to aggregate by IP address
    host_aggregated = defaultdict(lambda: {
        "host_label": "",
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "total": 0
    })
    
    # Group and aggregate by IP
    for host_label, host_data in scan_results.items():
        if not isinstance(host_data, dict):
            continue
        
        severity_count = host_data.get("severity_count", {})
        total_cves = sum(severity_count.values()) if severity_count else 0
        
        # Include all hosts, even those with 0 CVEs for comprehensive view
        # Extract IP from host_label (supports "IP" or "hostname (IP)" format)
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', host_label)
        if ip_match:
            ip = ip_match.group(1)
        else:
            ip = host_label  # Use as-is if no IP found
        
        # Support both uppercase and lowercase keys
        critical = (severity_count.get("CRITICAL", 0) or 
                   severity_count.get("Critical", 0) or 
                   severity_count.get("critical", 0))
        high = (severity_count.get("HIGH", 0) or 
               severity_count.get("High", 0) or 
               severity_count.get("high", 0))
        medium = (severity_count.get("MEDIUM", 0) or 
                 severity_count.get("Medium", 0) or 
                 severity_count.get("medium", 0))
        low = (severity_count.get("LOW", 0) or 
              severity_count.get("Low", 0) or 
              severity_count.get("low", 0))
        
        # Aggregate counts for same IP
        host_aggregated[ip]["critical"] += critical
        host_aggregated[ip]["high"] += high
        host_aggregated[ip]["medium"] += medium
        host_aggregated[ip]["low"] += low
        host_aggregated[ip]["total"] += total_cves
        
        # Prefer hostname (IP) format over plain IP
        if not host_aggregated[ip]["host_label"] or "(" in host_label:
            host_aggregated[ip]["host_label"] = host_label
    
    # Convert to list and determine risk levels
    host_risk = []
    for ip, data in host_aggregated.items():
        # Only include hosts with CVEs
        if data["total"] > 0:
            # Determine risk level based on highest severity present
            if data["critical"] > 0:
                risk_level = "CRITICAL"
            elif data["high"] > 0:
                risk_level = "HIGH"
            elif data["medium"] > 0:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            host_risk.append({
                "host": data["host_label"],
                "critical": data["critical"],
                "high": data["high"],
                "medium": data["medium"],
                "low": data["low"],
                "total": data["total"],
                "risk_level": risk_level
            })
    
    # Sort by total CVEs descending
    host_risk.sort(key=lambda x: x["total"], reverse=True)
    return host_risk  # Return all hosts, not just top 5

def _get_trend_data(scans_list, days=7):
    """Generate trend data from scan history"""
    now = datetime.now()
    labels = []
    values = []
    
    # Create empty buckets for last N days
    for i in range(days - 1, -1, -1):
        date = now - timedelta(days=i)
        labels.append(date.strftime("%a"))  # "Mon", "Tue", etc.
        values.append(0)
    
    # Populate with actual scan data
    for scan in scans_list[:30]:  # Look at recent scans
        end_time_str = scan.get("end_time", "")
        if not end_time_str:
            continue
        
        try:
            scan_date = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            scan_date = scan_date.replace(tzinfo=None)  # Make naive
            
            days_ago = (now.date() - scan_date.date()).days
            if 0 <= days_ago < days:
                idx = days - 1 - days_ago
                values[idx] += scan.get("summary", {}).get("total_cves", 0)
        except:
            continue
    
    return {"labels": labels, "values": values}

@dashboard_bp.route("/dashboard")
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

    severity = summary.get("severity", default_severity)
    
    stats = {
        "hosts_scanned": summary.get("hosts_scanned", 0),
        "open_ports": summary.get("open_ports", 0),
        "total_cves": summary.get("total_cves", 0),
        "critical": severity.get("critical", 0),
        **changes
    }
    
    # NEW: Extract top ports, critical CVEs, and other real data
    top_ports_labels = []
    top_ports_values = []
    critical_cves = []
    host_risk_data = []
    trend_data = {"labels": [], "values": []}
    
    # Get all scans with results (not just latest) for comprehensive host risk assessment
    scans_with_results = [
        s for s in completed 
        if s.get("scan_id")
    ]
    
    # Aggregate data from all scans by actually counting CVEs from ports (like vulnerabilities page)
    all_scan_results = {}
    total_cve_count = 0
    severity_totals = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for scan in scans_with_results:
        scan_id = scan.get("scan_id")
        if scan_id:
            scan_results = scan_service.get_scan_results(scan_id)
            if scan_results and isinstance(scan_results, dict):
                # Count CVEs properly by iterating through ports
                for host, host_data in scan_results.items():
                    # Handle different data structures
                    if isinstance(host_data, dict) and "gui" in host_data:
                        ports = host_data.get("gui", {}).get("ports", [])
                    elif isinstance(host_data, dict) and "ports" in host_data:
                        ports = host_data.get("ports", [])
                    else:
                        ports = []
                    
                    # Count CVEs from ports
                    host_severity_count = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
                    for port_data in ports:
                        for cve in port_data.get("cves", []):
                            total_cve_count += 1
                            
                            # Extract severity
                            severity = cve.get("severity")
                            if isinstance(severity, dict):
                                severity_label = severity.get("label", "UNKNOWN").upper()
                            elif isinstance(severity, str):
                                severity_label = severity.upper()
                            else:
                                severity_label = "UNKNOWN"
                            
                            if severity_label in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                                host_severity_count[severity_label] += 1
                                severity_totals[severity_label.lower()] += 1
                    
                    # Merge results for deduplication
                    if host not in all_scan_results:
                        all_scan_results[host] = host_data
                        all_scan_results[host]["severity_count"] = host_severity_count
                    else:
                        # Merge severity counts if host exists in multiple scans
                        existing_severity = all_scan_results[host].get("severity_count", {})
                        for sev_key, sev_count in host_severity_count.items():
                            existing_severity[sev_key] = existing_severity.get(sev_key, 0) + sev_count
                        all_scan_results[host]["severity_count"] = existing_severity
    
    # Update stats with accurate counts from all scans
    stats.update({
        "total_cves": total_cve_count,
        "critical": severity_totals["critical"],
    })
    
    severity.update(severity_totals)
    
    # Extract data from aggregated results
    if all_scan_results:
        top_ports_labels, top_ports_values = _extract_top_ports(all_scan_results)
        critical_cves = _extract_critical_cves(all_scan_results, limit=50)
        host_risk_data = _extract_host_risk(all_scan_results)
    elif latest:
        # Fallback to latest scan only if aggregation fails
        latest_id = latest.get("scan_id")
        if latest_id:
            scan_results = scan_service.get_scan_results(latest_id)
            if scan_results:
                top_ports_labels, top_ports_values = _extract_top_ports(scan_results)
                critical_cves = _extract_critical_cves(scan_results, limit=50)
                host_risk_data = _extract_host_risk(scan_results)
    
    # Get trend data from historical scans
    trend_data = _get_trend_data(completed, days=7)
    
    # Calculate security posture
    security_posture = _calculate_security_posture(stats, severity)
    
    return render_template(
        "dashboard.html",
        stats=stats,
        severity=severity,
        last_scan_time=latest.get("end_time") if latest else "Never",
        recent_scans=completed[:5],
        username="Admin",
        # NEW DATA
        top_ports_labels=top_ports_labels,
        top_ports_values=top_ports_values,
        critical_cves=critical_cves,
        host_risk_data=host_risk_data,
        trend_data=trend_data,
        security_posture=security_posture
    )
