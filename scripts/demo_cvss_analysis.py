import json
from modules.cve.cvss_vector_analysis import analyze_vector, analyze_cvss_for_cve


def demo_vectors():
    samples = [
        # CVSS v4.0 example
        "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:L/SI:L/SA:L",
        # CVSS v3.1 example
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        # CVSS v2.0 example (no prefix typical)
        "AV:N/AC:L/Au:N/C:C/I:C/A:C",
    ]

    for v in samples:
        print("=== Vector:", v)
        result = analyze_vector(v)
        print(json.dumps(result, indent=2))


def demo_cve_dict():
    cve = {
        "id": "CVE-XXXX-YYYY",
        "severity": {"version": "3.1", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"},
    }
    result = analyze_cvss_for_cve(cve)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    demo_vectors()
    demo_cve_dict()
