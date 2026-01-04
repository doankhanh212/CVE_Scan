from flask import Blueprint, render_template

scan_page_bp = Blueprint("scan_page", __name__)

@scan_page_bp.route("/scan", methods=["GET"])
def scan_page():
    return render_template(
        "scan.html",
        active="scan"
    )
