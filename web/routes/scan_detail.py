from flask import Blueprint, jsonify
from web.services.scan_service import scan_service

scan_detail_bp = Blueprint("scan_detail", __name__)

@scan_detail_bp.route("/scan/<scan_id>", methods=["GET"])
def get_scan_detail(scan_id):
    scan = scan_service.get_scan(scan_id)

    if not scan:
        return jsonify({"error": "Scan không tồn tại"}), 404

    response = {
        "scan_id": scan["scan_id"],
        "status": scan["status"],
        "progress": scan["progress"],
        "message": scan["message"],
        "start_time": scan.get("start_time"),
        "end_time": scan.get("end_time"),
        "summary": scan.get("summary", {}),
        "hosts": scan.get("results", {})
    }

    if scan.get("error"):
        response["error"] = scan["error"]

    return jsonify(response), 200
