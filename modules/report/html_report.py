import os
import datetime
from string import Template
from typing import Dict, Any, List


def _normalize_results(results: Dict[str, Any]):
    """Extract rows and summary from GUI-style results dict.

    Accepts either:
    - GUI cache shape: {host: {"gui": {"ports": [...]}, ...}}
    - JSONReport shape: {"hosts": [{"target": ..., "services": [...], "vulnerabilities": [...]}]}
    """

    rows: List[Dict[str, Any]] = []
    hosts = len(results or {}) if isinstance(results, dict) else 0
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

    # Path 1: GUI cache (host -> gui.ports)
    for host, host_result in (results or {}).items():
        ports = host_result.get("gui", {}).get("ports", [])
        if ports:
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

    # Path 2: JSONReport shape (if provided instead of GUI cache)
    if not rows and isinstance(results, dict) and isinstance(results.get("hosts"), list):
        for host_block in results.get("hosts", []):
            host = host_block.get("target") or ""
            services = {s.get("name"): s for s in host_block.get("services", [])}
            vulns = host_block.get("vulnerabilities", [])
            for v in vulns:
                svc_name = v.get("service")
                svc = services.get(svc_name, {})
                sev = v.get("severity")
                label = sev if isinstance(sev, str) else (sev.get("label") if isinstance(sev, dict) else "")
                if label in sev_counts:
                    sev_counts[label] += 1
                if v.get("cve_id"):
                    cves_found += 1
                rows.append({
                    "host": host,
                    "port": svc.get("port"),
                    "protocol": svc.get("protocol"),
                    "service": svc_name or "",
                    "product": svc.get("product") or "",
                    "version": svc.get("version") or _version_from_cpe(v.get("cpe")),
                    "severity": label or "",
                    "cve_id": v.get("cve_id") or "",
                    "description": v.get("description") or "",
                    "cvss_v2": None,
                    "cvss_v3": None,
                    "cvss_v4": (v.get("cvss4") or {}).get("score"),
                    "cpe": v.get("cpe") or ""
                })
        hosts = max(hosts, len(results.get("hosts", [])))
        open_services = max(open_services, sum(len(h.get("services", [])) for h in results.get("hosts", [])))

    summary = {
        "hosts": hosts,
        "open_services": open_services,
        "cves_found": cves_found,
        "severity": sev_counts
    }
    return rows, summary


def export_html(results: Dict[str, Any], path: str) -> bool:
    """Export GUI-style `results` to an HTML report (Nessus-like table)."""
    if not path:
        raise ValueError("No path provided")

    try:
        rows, summary = _normalize_results(results or {})
    except Exception as e:
        print(f"HTML normalization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    generated = datetime.datetime.utcnow().isoformat() + "Z"

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        template = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CVE Scan Report</title>
<style>
:root {
    --bg: #0b1220;
    --panel: #0f172a;
    --card: #111827;
    --text: #e5e7eb;
    --sub: #9ca3af;
    --accent: #38bdf8;
    --accent2: #22d3ee;
    --danger: #ef4444;
    --warn: #f59e0b;
    --ok: #10b981;
    --muted: #334155;
    --table-border: #1f2937;
}
* { box-sizing: border-box; }
body { margin:0; font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--text); }
header { background: linear-gradient(90deg, #0b1220, #0e1a2e); padding: 20px 24px; border-bottom: 1px solid var(--muted); }
h1 { margin: 0; font-size: 22px; letter-spacing: 0.5px; }
.subtitle { color: var(--sub); margin-top: 4px; }
.container { padding: 18px 20px 28px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0; }
.card { background: var(--card); border: 1px solid var(--table-border); border-radius: 10px; padding: 12px 14px; }
.card .label { color: var(--sub); font-size: 12px; text-transform: uppercase; letter-spacing: 0.6px; }
.card .value { font-size: 24px; margin-top: 6px; }
.table-wrap { background: var(--panel); border: 1px solid var(--table-border); border-radius: 10px; padding: 12px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--table-border); }
th { background: #162033; color: var(--text); font-weight: 600; }
tr:hover { background: rgba(56, 189, 248, 0.08); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge.CRITICAL { background: rgba(239,68,68,0.16); color: var(--danger); }
.badge.HIGH { background: rgba(249,115,22,0.18); color: #f97316; }
.badge.MEDIUM { background: rgba(245,158,11,0.18); color: var(--warn); }
.badge.LOW { background: rgba(16,185,129,0.18); color: var(--ok); }
.footer { margin-top: 14px; color: var(--sub); font-size: 12px; }
</style>
</head>
<body>
<header>
    <h1>CVE Scan Report</h1>
    <div class="subtitle">Generated at ${generated} • Hosts: ${hosts} • CVEs: ${cves_found}</div>
</header>
<div class="container">
    <div class="cards">
        <div class="card"><div class="label">Hosts</div><div class="value">${hosts}</div></div>
        <div class="card"><div class="label">Open Services</div><div class="value">${open_services}</div></div>
        <div class="card"><div class="label">CVEs Found</div><div class="value">${cves_found}</div></div>
        <div class="card"><div class="label">Severity</div><div class="value">CRIT ${crit} | HIGH ${high} | MED ${med} | LOW ${low}</div></div>
    </div>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Host</th><th>Port/Proto</th><th>Service</th><th>Product</th><th>Version</th><th>CVE</th><th>Severity</th><th>CVSS v4</th><th>Description</th>
                </tr>
            </thead>
            <tbody>
""")
        
        header_html = template.substitute(
            generated=generated,
            hosts=summary["hosts"],
            cves_found=summary["cves_found"],
            open_services=summary["open_services"],
            crit=summary["severity"].get("CRITICAL", 0),
            high=summary["severity"].get("HIGH", 0),
            med=summary["severity"].get("MEDIUM", 0),
            low=summary["severity"].get("LOW", 0),
        )

        with open(path, "w", encoding="utf-8") as f:
            f.write(header_html)

            for row in rows:
                f.write("      <tr>\n")
                f.write("        <td>%s</td>\n" % (row["host"] or ""))
                port_proto = "{}/{}".format(row.get("port") or "", row.get("protocol") or "")
                f.write("        <td>%s</td>\n" % port_proto)
                f.write("        <td>%s</td>\n" % (row["service"] or ""))
                f.write("        <td>%s</td>\n" % (row["product"] or ""))
                f.write("        <td>%s</td>\n" % (row["version"] or ""))
                f.write("        <td>%s</td>\n" % (row["cve_id"] or ""))
                sev = row.get("severity") or ""
                sev_badge = f"<span class='badge {sev}'>" + sev + "</span>" if sev else ""
                f.write("        <td>%s</td>\n" % sev_badge)
                cvss4 = row.get("cvss_v4")
                f.write("        <td>%s</td>\n" % ("" if cvss4 is None else cvss4))
                desc = (row.get("description") or "").replace("<", "&lt;").replace(">", "&gt;")
                f.write("        <td>%s</td>\n" % desc)
                f.write("      </tr>\n")

            f.write("""      </tbody>
        </table>
    </div>
    <div class="footer">Report generated by CVE Scanner • Nessus-like HTML export</div>
</div>
</body>
</html>
""")
        return True
    except Exception as e:
        print(f"HTML export failed: {e}")
        import traceback
        traceback.print_exc()
        return False
