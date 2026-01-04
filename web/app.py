# web/app.py
"""
Flask entry point
"""

from flask import Flask, render_template
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
def dashboard():
    """Dashboard - trang chủ"""
    # TODO: Get real data from scan_service
    # For now, provide sample data structure
    stats = {
        'hosts_scanned': 0,
        'open_ports': 0,
        'total_cves': 0,
        'critical': 0
    }
    
    severity = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    recent_scans = []
    
    # Try to get real data from scan_service
    try:
        from web.services.scan_service import scan_service
        scans = scan_service.list_scans()
        
        # Calculate stats from scans
        total_hosts = 0
        total_cves = 0
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for scan in scans:
            if scan.get('status') == 'completed':
                results = scan.get('results', {})
                for host, host_result in results.items():
                    ports = host_result.get('gui', {}).get('ports', [])
                    total_hosts += 1
                    for port in ports:
                        cves = port.get('cves', [])
                        total_cves += len(cves)
                        for cve in cves:
                            sev = cve.get('severity', '')
                            if isinstance(sev, str):
                                sev_lower = sev.lower()
                                if sev_lower in severity_counts:
                                    severity_counts[sev_lower] += 1
                            elif isinstance(sev, dict):
                                sev_label = sev.get('label', '').lower()
                                if sev_label in severity_counts:
                                    severity_counts[sev_label] += 1
        
        stats = {
            'hosts_scanned': total_hosts,
            'open_ports': sum(len(s.get('results', {}).get('gui', {}).get('ports', [])) for s in scans if s.get('status') == 'completed'),
            'total_cves': total_cves,
            'critical': severity_counts['critical']
        }
        
        severity = severity_counts
        
        # Get recent scans (last 10)
        recent_scans = sorted(
            scans,
            key=lambda x: x.get('start_time', ''),
            reverse=True
        )[:10]
        
        # Format recent scans
        for scan in recent_scans:
            scan['target_name'] = f"Scan {scan['scan_id'][:8]}"
            scan['network_range'] = ', '.join(scan.get('hosts', [])[:3])
            if len(scan.get('hosts', [])) > 3:
                scan['network_range'] += '...'
            scan['timestamp'] = scan.get('start_time', 'N/A')
            if scan['timestamp'] != 'N/A':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(scan['timestamp'].replace('Z', '+00:00'))
                    scan['timestamp'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
    
    except Exception as e:
        # If scan_service fails, use defaults
        pass
    
    return render_template(
        'dashboard.html',
        stats=stats,
        severity=severity,
        recent_scans=recent_scans,
        username='Admin',  # TODO: Get from session/auth
        last_scan_time=None  # TODO: Get from most recent scan
    )


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

