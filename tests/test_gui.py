import os
import tempfile
import json

import pytest

from modules.gui import results_to_rows, write_scan_results_to_csv


def test_results_to_rows():
    results = {
        "127.0.0.1": {
            "gui": {"ports": [{"port": 32922, "protocol": "tcp", "service": "port32922", "product": "", "version": "", "cves": []}]}
        }
    }

    r, kpi, sev = results_to_rows(results)
    assert len(r) == 1
    assert r[0][0] == "127.0.0.1"
    assert "32922" in r[0][1]


def test_write_scan_results_to_csv(tmp_path):
    results = {
        "192.168.1.10": {
            "gui": {"ports": [{
                "port": 22,
                "protocol": "tcp",
                "service": "ssh",
                "product": "OpenSSH",
                "version": "7.4",
                "cves": [{
                    "id": "CVE-2025-0001",
                    "cpe": "cpe:2.3:a:openssh:openssh:7.4:*:*:*:*:*:*:*",
                    "description": "Example vuln",
                    "cvss_v3": 7.5,
                    "severity": "HIGH"
                }]
            }]}
        }
    }

    out = tmp_path / "out.csv"
    write_scan_results_to_csv(results, str(out))

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "CVE-2025-0001" in content
    assert "OpenSSH" in content
    assert "HIGH" in content
