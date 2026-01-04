# web/routes/export.py
"""
Routes: /export/csv, /export/html, /export/pdf
"""

import os
import sys
from flask import Blueprint, jsonify, send_file, request
from io import BytesIO
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from web.services.scan_service import scan_service
from modules.report import html_report, pdf_report
from modules.gui import write_scan_results_to_csv

export_bp = Blueprint('export', __name__)


@export_bp.route('/export/<format_type>', methods=['GET'])
def export_scan(format_type):
    """
    GET /export/<format_type>?scan_id=<scan_id>
    
    format_type: csv, html, pdf
    """
    scan_id = request.args.get('scan_id')
    if not scan_id:
        return jsonify({"error": "scan_id là bắt buộc"}), 400
    
    results = scan_service.get_scan_results(scan_id)
    if not results:
        scan_info = scan_service.get_scan_status(scan_id)
        if not scan_info:
            return jsonify({"error": "Scan không tồn tại"}), 404
        if scan_info["status"] != "completed":
            return jsonify({"error": f"Scan chưa hoàn tất (status: {scan_info['status']})"}), 400
        results = scan_info.get("results", {})
    
    if not results:
        return jsonify({"error": "Không có kết quả để xuất"}), 400
    
    try:
        if format_type == "csv":
            # Tạo temporary file
            fd, path = tempfile.mkstemp(suffix='.csv', delete=False)
            os.close(fd)
            try:
                write_scan_results_to_csv(results, path)
                return send_file(
                    path,
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=f'scan_results_{scan_id}.csv'
                )
            finally:
                # Cleanup sau khi send
                try:
                    os.unlink(path)
                except:
                    pass
        
        elif format_type == "html":
            fd, path = tempfile.mkstemp(suffix='.html', delete=False)
            os.close(fd)
            try:
                if html_report.export_html(results, path):
                    return send_file(
                        path,
                        mimetype='text/html',
                        as_attachment=True,
                        download_name=f'scan_results_{scan_id}.html'
                    )
                else:
                    return jsonify({"error": "Xuất HTML thất bại"}), 500
            finally:
                try:
                    os.unlink(path)
                except:
                    pass
        
        elif format_type == "pdf":
            fd, path = tempfile.mkstemp(suffix='.pdf', delete=False)
            os.close(fd)
            try:
                if pdf_report.export_pdf(results, path):
                    return send_file(
                        path,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=f'scan_results_{scan_id}.pdf'
                    )
                else:
                    return jsonify({"error": "Xuất PDF thất bại. Yêu cầu thư viện 'reportlab'"}), 500
            finally:
                try:
                    os.unlink(path)
                except:
                    pass
        
        else:
            return jsonify({"error": f"Format không hỗ trợ: {format_type}"}), 400
    
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất file: {str(e)}"}), 500

