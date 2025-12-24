from typing import Dict, Any, List
from datetime import datetime


def generate_cpe_html_report(data: Dict[str, List[tuple]], output: str) -> bool:
    """Generate an HTML report like previous `final_cvss.py`.

    data: mapping cpe -> list of tuples (id, description, cvss_score, published)
    """
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CPE Vulnerability Report</title>
    <style>body{{font-family:Arial,Helvetica,sans-serif;margin:20px}} table{{width:100%;border-collapse:collapse}} th,td{{padding:8px;border:1px solid #ddd}}</style>
</head>
<body>
    <h1>CPE Vulnerability Report</h1>
    <p>Generated at: {time_now}</p>
"""

    for cpe, vulns in data.items():
        html += f"<h2>{cpe}</h2>\n"
        if not vulns:
            html += "<p>No vulnerabilities found.</p>\n"
            continue

        html += "<table><thead><tr><th>CVE ID</th><th>Description</th><th>CVSS</th><th>Published</th></tr></thead><tbody>\n"
        for cve_id, desc, cvss, pub in vulns:
            html += f"<tr><td>{cve_id}</td><td>{desc}</td><td>{cvss or 'N/A'}</td><td>{pub}</td></tr>\n"
        html += "</tbody></table>\n"

    html += "</body></html>"

    try:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(html)
        return True
    except Exception:
        return False
