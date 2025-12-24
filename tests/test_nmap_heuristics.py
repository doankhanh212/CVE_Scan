import pytest

from modules.scanners.nmap_scanner import NmapScanner


def test_normalize_port_only_name():
    s = NmapScanner()
    svc = {"name": "port32922", "product": "", "version": ""}
    name, product, version = s._normalize_service(svc, 32922)
    assert name == "port32922"
    assert product == "port32922"
    assert version == ""


def test_normalize_well_known_port():
    s = NmapScanner()
    svc = {"name": "", "product": "", "version": ""}
    name, product, version = s._normalize_service(svc, 22)
    assert name == "ssh"
    assert product == "ssh"


def test_parse_extrainfo_openssh():
    s = NmapScanner()
    svc = {"name": "", "product": "", "extrainfo": "OpenSSH 7.4p1"}
    name, product, version = s._normalize_service(svc, 22)
    assert product.lower().startswith("openssh")
    assert version.startswith("7.4")


def test_parse_extrainfo_apache():
    s = NmapScanner()
    svc = {"name": "http", "product": "", "extrainfo": "Apache httpd 2.4.49"}
    name, product, version = s._normalize_service(svc, 80)
    assert name == "http"
    assert product.lower().startswith("apache")
    assert version.startswith("2.4")


def test_filter_placeholder_syn_ack():
    s = NmapScanner()
    svc = {"name": "", "product": "syn-ack", "extrainfo": "syn-ack"}
    name, product, version = s._normalize_service(svc, 80)
    # port 80 is known -> should fallback to http
    assert name == "http"
    assert product == "http"


def test_filter_placeholder_reset_unknown_port():
    s = NmapScanner()
    svc = {"name": "", "product": "reset", "extrainfo": "reset"}
    name, product, version = s._normalize_service(svc, 44188)
    # unknown port -> name should default to port44188 and product follow name
    assert name == "port44188"
    assert product == "port44188"


def test_filter_placeholder_reset_well_known_port():
    s = NmapScanner()
    svc = {"name": "", "product": "reset", "extrainfo": "reset"}
    name, product, version = s._normalize_service(svc, 80)
    # port 80 known -> should fallback to http
    assert name == "http"
    assert product == "http"
