from flask import Blueprint, request, jsonify
from web.services.scan_service import scan_service
from web.utils.cache import stats_cache, list_cache

scan_bp = Blueprint("scan", __name__, url_prefix="/api")


def _compute_scan_stats(scan_info):
    """Compute lightweight stats from scan results without returning heavy payload."""
    hosts_scanned = 0
    ports_found = 0
    cves_found = 0
    critical_cves = 0

    results = scan_info.get("results", {}) or {}
    for host_label, host_result in results.items():
        if not isinstance(host_result, dict):
            continue
        hosts_scanned += 1

        # Prefer normalized GUI structure if present
        ports = host_result.get("gui", {}).get("ports", [])
        if not ports:
            ports = host_result.get("ports", [])

        ports_found += len(ports)

        for port_data in ports:
            cves = port_data.get("cves", []) or []
            cves_found += len(cves)

            for cve in cves:
                severity = cve.get("severity", "low")
                if isinstance(severity, dict):
                    severity = severity.get("label", "low")
                if str(severity).lower() == "critical":
                    critical_cves += 1

    return {
        "hosts_scanned": hosts_scanned,
        "ports_found": ports_found,
        "cves_found": cves_found,
        "critical_cves": critical_cves,
    }


@scan_bp.route("/scan", methods=["POST"])
def create_scan():
    data = request.get_json() or {}

    hosts = data.get("hosts", [])
    if not hosts:
        return jsonify({"error": "hosts là bắt buộc"}), 400

    authenticated = data.get("authenticated", False)
    auth_data = data.get("auth_data")
    input_mode = data.get("input_mode", "IP/CIDR")

    if input_mode not in ("IP/CIDR", "Hostname (Domain)"):
        return jsonify({"error": "input_mode không hợp lệ"}), 400

    if authenticated and not auth_data:
        return jsonify({"error": "auth_data là bắt buộc khi authenticated=true"}), 400

    scan_id = scan_service.create_and_start_scan(
        hosts=hosts,
        authenticated=authenticated,
        auth_data=auth_data,
        input_mode=input_mode
    )

    return jsonify({
        "scan_id": scan_id,
        "status": "running"
    }), 201


@scan_bp.route("/scan/<scan_id>", methods=["GET"])
def get_scan(scan_id):
    """
    GET /api/scan/<scan_id>
    Return lightweight status only (no results) to reduce network overhead
    """
    # Try cache for completed scans (immutable)
    scan_info = scan_service.get_scan_status(scan_id)
    if not scan_info:
        return jsonify({"error": "Scan không tồn tại"}), 404
    
    if scan_info["status"] == "completed":
        cache_key = f"scan_stats_{scan_id}"
        cached = stats_cache.get(cache_key)
        if cached:
            return jsonify(cached), 200
    
    stats = _compute_scan_stats(scan_info)

    # Return only lightweight status, not heavy results
    response = {
        "scan_id": scan_info["scan_id"],
        "status": scan_info["status"],
        "progress": scan_info.get("progress", 0),
        "message": scan_info.get("message", ""),
        "start_time": scan_info.get("start_time"),
        "end_time": scan_info.get("end_time"),
        "error": scan_info.get("error"),
        "hosts_scanned": stats["hosts_scanned"],
        "ports_found": stats["ports_found"],
        "cves_found": stats["cves_found"],
        "critical_cves": stats["critical_cves"],
        "logs": scan_info.get("logs", [])  # Include logs for live update
    }
    
    # Cache completed scans
    if scan_info["status"] == "completed":
        stats_cache.set(f"scan_stats_{scan_id}", response)
    
    return jsonify(response), 200


@scan_bp.route("/scan/<scan_id>/logs", methods=["GET"])
def get_scan_logs(scan_id):
    logs = scan_service.get_scan_logs(scan_id)
    if logs is None:
        return jsonify({"error": "Scan không tồn tại"}), 404
    return jsonify({"logs": logs}), 200


@scan_bp.route("/scan/<scan_id>", methods=["DELETE"])
def stop_scan(scan_id):
    scan_service.stop_scan(scan_id)
    return jsonify({"message": "Scan đã được dừng"}), 200


@scan_bp.route("/scan/<scan_id>/purge", methods=["DELETE"])
def delete_scan(scan_id):
    """Xóa scan khỏi bộ nhớ và tệp lưu trữ."""
    try:
        scan_service.delete_scan(scan_id)
        return jsonify({"message": "Scan đã bị xóa"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@scan_bp.route("/scans", methods=["GET"])
def list_scans():
    # Try cache first (reduces load for repeated requests)
    cache_key = "scans_list"
    cached = list_cache.get(cache_key)
    if cached:
        return jsonify({"scans": cached}), 200
    
    # Get lightweight scan list (no results/logs)
    scans = scan_service.list_scans(include_results=False) or []

    enriched = []
    for scan in scans:
        # Compute stats only from summary if available (faster)
        if "summary" in scan:
            summary = scan["summary"]
            stats = {
                "hosts_scanned": summary.get("hosts_scanned", 0),
                "ports_found": summary.get("open_ports", 0),
                "cves_found": summary.get("total_cves", 0),
                "critical_cves": summary.get("severity", {}).get("critical", 0),
            }
        else:
            # Fallback: load results and compute (slower)
            full_scan = scan_service.get_scan_status(scan["scan_id"])
            stats = _compute_scan_stats(full_scan) if full_scan else {}
        
        enriched.append({
            "scan_id": scan.get("scan_id"),
            "status": scan.get("status"),
            "progress": scan.get("progress", 0),
            "message": scan.get("message", ""),
            "start_time": scan.get("start_time"),
            "end_time": scan.get("end_time"),
            "hosts": scan.get("hosts", []),
            **stats,
        })
    
    # Cache for 3 seconds
    list_cache.set(cache_key, enriched)
    
    return jsonify({"scans": enriched}), 200


@scan_bp.route("/scan/reload", methods=["POST"])
def reload_scans():
    """Reload all scans from disk (useful after external modifications)"""
    try:
        scan_service.reload_scans_from_disk()
        return jsonify({"message": "Scans reloaded from disk successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
