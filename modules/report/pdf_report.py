import os
import datetime
from typing import Dict, Any, List


def _normalize_results(results: Dict[str, Any]):
    """Extract rows and summary from GUI-style results dict."""
    rows: List[Dict[str, Any]] = []
    hosts = len(results or {})
    open_services = 0
    cves_found = 0
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    def _version_from_cpe(cpe: str | None) -> str:
        if not cpe or not isinstance(cpe, str):
            return ""
        parts = cpe.split(":")
        if len(parts) >= 6:
            candidate = parts[5]
            if candidate and candidate not in {"*", "-"}:
                return candidate
        return ""

    for host, host_result in (results or {}).items():
        ports = host_result.get("gui", {}).get("ports", [])
        open_services += len(ports)
        for p in ports:
            cves = p.get("cves", [])
            if cves:
                for c in cves:
                    sev = c.get("severity")
                    label = sev if isinstance(sev, str) else (sev.get("label") if isinstance(sev, dict) else "")
                    if label in sev_counts:
                        sev_counts[label] += 1
                    cves_found += 1 if c.get("id") else 0
                    rows.append({
                        "host": host,
                        "port": p.get("port"),
                        "protocol": p.get("protocol"),
                        "service": p.get("service") or "",
                        "product": p.get("product") or "",
                        "version": p.get("version") or _version_from_cpe(c.get("cpe")),
                        "severity": label or "",
                        "cve_id": c.get("id") or "",
                        "description": c.get("description") or "",
                        "cvss_v2": c.get("cvss_v2"),
                        "cvss_v3": c.get("cvss_v3"),
                        "cvss_v4": c.get("cvss_v4"),
                        "cpe": c.get("cpe") or ""
                    })
            else:
                rows.append({
                    "host": host,
                    "port": p.get("port"),
                    "protocol": p.get("protocol"),
                    "service": p.get("service") or "",
                    "product": p.get("product") or "",
                    "version": p.get("version") or "",
                    "severity": "",
                    "cve_id": "",
                    "description": "",
                    "cvss_v2": None,
                    "cvss_v3": None,
                    "cvss_v4": None,
                    "cpe": ""
                })

    summary = {
        "hosts": hosts,
        "open_services": open_services,
        "cves_found": cves_found,
        "severity": sev_counts
    }
    return rows, summary


def export_pdf(results: Dict[str, Any], path: str) -> bool:
    """Export GUI-style `results` to a PDF report using reportlab.
    Returns True on success, False otherwise.
    """
    if not path:
        raise ValueError("No path provided")

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
    except Exception:
        # reportlab not installed
        return False

    rows, summary = _normalize_results(results or {})
    generated = datetime.datetime.utcnow().isoformat() + "Z"

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None

        doc = SimpleDocTemplate(
            path,
            pagesize=landscape(letter),
            leftMargin=0.4 * inch,
            rightMargin=0.4 * inch,
            topMargin=0.4 * inch,
            bottomMargin=0.4 * inch,
        )
        elements = []
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        normal = styles["Normal"]
        subtitle = styles["Heading2"]
        small = styles["BodyText"]
        small.fontSize = 9

        elements.append(Paragraph("CVE Scan Report", title_style))
        elements.append(Paragraph(f"Generated: {generated}", normal))
        elements.append(Spacer(1, 12))

        # Summary cards (as paragraphs)
        elements.append(Paragraph(
            f"Hosts: {summary['hosts']} • Open Services: {summary['open_services']} • CVEs Found: {summary['cves_found']}",
            subtitle
        ))
        sev = summary.get("severity", {})
        elements.append(Paragraph(
            f"Severity — CRITICAL {sev.get('CRITICAL',0)} | HIGH {sev.get('HIGH',0)} | MEDIUM {sev.get('MEDIUM',0)} | LOW {sev.get('LOW',0)}",
            normal
        ))
        elements.append(Spacer(1, 12))

        # Table header
        data = [[
            "Host", "Port/Proto", "Service", "Product", "Version", "CVE", "Severity", "CVSS v4", "Description"
        ]]

        # Wrap most textual columns to prevent clipping
        for r in rows:
            port_proto = f"{r.get('port') or ''}/{r.get('protocol') or ''}"
            desc = Paragraph((r.get("description") or ""), small)
            host_p = Paragraph(str(r.get("host") or ""), small)
            service_p = Paragraph(str(r.get("service") or ""), small)
            product_p = Paragraph(str(r.get("product") or ""), small)
            version_p = Paragraph(str(r.get("version") or ""), small)
            cve_p = Paragraph(str(r.get("cve_id") or ""), small)
            sev_p = Paragraph(str(r.get("severity") or ""), small)
            cvss4 = "" if r.get("cvss_v4") is None else r.get("cvss_v4")
            data.append([
                host_p,
                port_proto,
                service_p,
                product_p,
                version_p,
                cve_p,
                sev_p,
                cvss4,
                desc
            ])

        # Balanced column widths + dynamic description width
        page_width = doc.pagesize[0] - doc.leftMargin - doc.rightMargin
        # Tighter widths to fit on landscape: Host 1.8" + Port 0.9" + Service 1.0" + Product 1.2" + Version 0.9" + CVE 1.3" + Sev 0.8" + CVSS4 0.7" = 8.6"
        fixed = [1.8*inch, 0.9*inch, 1.0*inch, 1.2*inch, 0.9*inch, 1.3*inch, 0.8*inch, 0.7*inch]
        desc_w = max(2.5*inch, page_width - sum(fixed))
        col_widths = fixed + [desc_w]
        table = Table(data, repeatRows=1, colWidths=col_widths)
        table_style = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("ALIGN", (0,0), (-1,-1), "LEFT"),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 11),
            ("BOTTOMPADDING", (0,0), (-1,0), 6),
            ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
            ("TEXTCOLOR", (0,1), (-1,-1), colors.HexColor("#0b1220")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor("#e5e7eb")]),
            ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ])
        table.setStyle(table_style)

        elements.append(table)

        doc.build(elements)
        return True
    except Exception:
        return False
