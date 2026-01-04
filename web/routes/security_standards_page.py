"""
Security Standards Page Route
"""

from flask import Blueprint, render_template

security_page_bp = Blueprint('security_page', __name__)


@security_page_bp.route('/security-standards')
def security_standards():
    """Render security standards mapping page"""
    return render_template('security_standards.html')
