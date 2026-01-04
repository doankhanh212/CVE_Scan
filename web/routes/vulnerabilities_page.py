from flask import Blueprint, render_template

vuln_page_bp = Blueprint("vuln_page", __name__)

@vuln_page_bp.route("/vulnerabilities")
def vulnerabilities_page():
    return render_template("vulnerabilities.html")
