import csv
from modules.report.csv_report import export_csv


def make_report_for_host(target="1.2.3.4"):
    return {
        "meta": {},
        "hosts": [
            {
                "target": target,
                "scan_type": "basic",
                "summary": {},
                "services": [
                    {"name": "http:80", "product": "nginx", "version": "1.18", "port": 80, "protocol": "tcp", "os": None}
                ],
                "vulnerabilities": [
                    {"cve_id": "CVE-2023-1234", "service": "http:80", "cpe": "cpe:...", "description": "desc", "severity": {"label": "HIGH", "score": 7.5}, "cvss4": {}, "references": [], "evidence": {"product": "nginx", "version": "1.18", "os": None}}
                ]
            }
        ],
        "gui": {
            "ports": [
                {"port": 80, "service": "http:80", "version": "1.18", "cves": [{"id": "CVE-2023-1234", "severity": {"label": "HIGH", "score": 7.5}, "score": 7.5, "description": "desc"}]}
            ]
        }
    }


def test_export_csv(tmp_path):
    report = make_report_for_host()
    out = tmp_path / "out.csv"
    assert export_csv(report, str(out)) is True
    with open(out, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    # header + one row expected
    assert rows[0][0] == "Host"
    joined = "\n".join(
        [",".join([str(i) for i in row]) for row in rows]
    )
    assert "CVE-2023-1234" in joined
