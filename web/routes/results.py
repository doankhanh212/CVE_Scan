# web/routes/results.py
from flask import Blueprint, render_template
from web.services.scan_service import scan_service

results_bp = Blueprint('results', __name__)

@results_bp.route('/results')
def results():
    """Scan results page"""
    scans = scan_service.list_scans()
    return render_template('results.html', scans=scans)
