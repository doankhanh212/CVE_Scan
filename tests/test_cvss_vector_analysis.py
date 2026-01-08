import pytest

from modules.cve.cvss_vector_analysis import (
    parse_vector,
    analyze_vector,
    analyze_cvss_for_cve,
)


def test_parse_vector_v4():
    vec = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:L/SI:L/SA:L"
    parsed = parse_vector(vec)
    assert parsed["AV"] == "N"
    assert parsed["AC"] == "L"
    assert parsed["AT"] == "N"
    assert parsed["PR"] == "N"
    assert parsed["UI"] == "N"
    assert parsed["VC"] == "H"
    assert parsed["SC"] == "L"


def test_analyze_vector_groups_v4():
    vec = "CVSS:4.0/AV:A/AC:H/AT:P/PR:L/UI:R/VC:L/VI:L/VA:L/SC:H/SI:H/SA:H"
    result = analyze_vector(vec)
    assert result["cvss_version_used"].startswith("4")
    # Exploitability metrics should include keys such as AV, AC, AT, PR, UI
    exploit_keys = {i["parameter"] for i in result["exploitability"]}
    assert {"AV", "AC", "AT", "PR", "UI"}.issubset(exploit_keys)
    # Lateral impact present due to SC/SI/SA
    lat_params = {i["parameter"] for i in result["lateral_impact"]}
    assert {"SC", "SI", "SA"}.issubset(lat_params)


def test_analyze_vector_v3():
    vec = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    result = analyze_vector(vec)
    assert result["cvss_version_used"].startswith("3")
    tech_params = {i["parameter"] for i in result["technical_impact"]}
    assert {"C", "I", "A"}.issubset(tech_params)
    # Summary should mention Attack Vector
    assert "Attack Vector" in result["summary_explanation"]


def test_analyze_vector_v2():
    vec = "AV:N/AC:L/Au:N/C:C/I:C/A:C"
    result = analyze_vector(vec)
    assert result["cvss_version_used"].startswith("2")
    tech_params = {i["parameter"] for i in result["technical_impact"]}
    assert {"C", "I", "A"}.issubset(tech_params)


def test_analyze_cvss_for_cve_priority_v4():
    cve = {
        "id": "CVE-TEST-0001",
        "cvss4": {"vector": "CVSS:4.0/AV:P/AC:H/AT:P/PR:H/UI:R/VC:L/VI:L/VA:L/SC:N/SI:N/SA:N"},
        "severity": {"version": "3.1", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L"},
    }
    result = analyze_cvss_for_cve(cve)
    assert result["cvss_version_used"] == "4.0"
    assert result["vector"].startswith("CVSS:4.0")


def test_analyze_cvss_for_cve_fallback_v3():
    cve = {
        "id": "CVE-TEST-0002",
        "severity": {"version": "3.1", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"},
    }
    result = analyze_cvss_for_cve(cve)
    assert result["cvss_version_used"].startswith("3")
    assert result["vector"].startswith("CVSS:3.1")
