# web/routes/status.py
"""
Routes: /scan/<id>/status, /scan/latest
"""

from flask import Blueprint, jsonify
from web.services.scan_service import scan_service

status_bp = Blueprint('status', __name__)


@status_bp.route('/scan/latest', methods=['GET'])
def get_latest_scan():
    """
    GET /scan/latest
    Lấy scan gần nhất đã completed để hiển thị trên dashboard
    """
    # Get scans WITHOUT results first (lightweight)
    all_scans = scan_service.list_scans(include_results=False)
    
    # Filter scans đã completed, sắp xếp theo end_time mới nhất
    completed_scans = [s for s in all_scans if s['status'] == 'completed' and s.get('end_time')]
    
    if not completed_scans:
        return jsonify({"status": "no_scan"}), 200
    
    # Sort by end_time descending (newest first)
    completed_scans.sort(key=lambda x: x['end_time'], reverse=True)
    latest = completed_scans[0]
    
    # Use pre-computed summary if available (fast path)
    if 'summary' in latest:
        summary = latest['summary']
    else:
        # Fallback: Load full scan with results and compute (slow path)
        latest_full = scan_service.get_scan_status(latest['scan_id'])
        
        if not latest_full or 'results' not in latest_full:
            return jsonify({"status": "no_scan"}), 200
        
        # Build summary from results
        summary = {
            "hosts_scanned": len(latest_full.get('results', {})),
            "open_ports": 0,
            "total_cves": 0,
            "severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
        
        # Count ports and CVEs from results
        for host_label, host_result in latest_full.get('results', {}).items():
            if isinstance(host_result, dict):
                ports = host_result.get('ports', [])
                summary["open_ports"] += len(ports)
                
                # Count CVEs from each port
                for port_data in ports:
                    cves = port_data.get('cves', [])
                    summary["total_cves"] += len(cves)
                    
                    # Count by severity
                    for cve in cves:
                        severity = cve.get('severity', 'low')
                        if isinstance(severity, dict):
                            severity = severity.get('label', 'low')
                        severity = str(severity).lower()
                        if severity in summary["severity"]:
                            summary["severity"][severity] += 1
    
    return jsonify({
        "scan_id": latest['scan_id'],
        "status": latest['status'],
        "start_time": latest.get('start_time'),
        "end_time": latest.get('end_time'),
        "summary": summary,
        "message": latest.get('message')
    }), 200


@status_bp.route('/scan/<scan_id>/status', methods=['GET'])
def get_scan_status(scan_id):
    """
    GET /scan/<scan_id>/status
    Lấy status của scan (lightweight, không có results)
    """
    scan_info = scan_service.get_scan_status(scan_id)
    
    if not scan_info:
        return jsonify({"error": "Scan không tồn tại"}), 404
    
    # Chỉ trả về status info, không có results
    status_info = {
        "scan_id": scan_info["scan_id"],
        "status": scan_info["status"],
        "progress": scan_info["progress"],
        "message": scan_info["message"],
        "start_time": scan_info.get("start_time"),
        "end_time": scan_info.get("end_time"),
        "error": scan_info.get("error"),
        "hosts_count": len(scan_info.get("hosts", []))
    }
    
    return jsonify(status_info), 200

