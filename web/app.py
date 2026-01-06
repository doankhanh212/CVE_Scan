# web/app.py
"""
Flask entry point
"""

from flask import Flask, render_template, redirect, url_for
from web.routes.scan import scan_bp
from web.routes.scan_page import scan_page_bp  
from web.routes.status import status_bp
from web.routes.export import export_bp
from web.routes.dashboard import dashboard_bp
from web.routes.vulnerabilities import vuln_bp
from web.routes.vulnerabilities_page import vuln_page_bp
from web.routes.results import results_bp
from web.routes.settings import settings_bp
from web.routes.security_standards import security_bp
from web.routes.security_standards_page import security_page_bp
from web.routes.cve_detail import cve_detail_bp
app = Flask(__name__)

# Register blueprints
app.register_blueprint(scan_bp)
app.register_blueprint(scan_page_bp)
app.register_blueprint(status_bp)
app.register_blueprint(export_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(vuln_bp)
app.register_blueprint(vuln_page_bp)
app.register_blueprint(results_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(security_bp)
app.register_blueprint(security_page_bp)
app.register_blueprint(cve_detail_bp)

@app.route('/')
def root_dashboard():
    """Redirect to enterprise dashboard"""
    return redirect(url_for('dashboard.dashboard'))


@app.route('/scan')
def scan_page():
    """Trang quét"""
    return render_template('scan.html')


@app.route('/result/<scan_id>')
def result_page(scan_id):
    """Trang kết quả"""
    return render_template('result.html', scan_id=scan_id)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

