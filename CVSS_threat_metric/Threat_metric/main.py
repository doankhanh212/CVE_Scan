import sys
from cvss4 import build_cvss4_vector

BASE_VECTOR = (
    "CVSS:4.0/"
    "AV:N/AC:L/AT:N/PR:N/UI:N/"
    "VC:H/VI:H/VA:H"
)

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <CVE-ID>")
        sys.exit(1)

    cve_id = sys.argv[1]
    vector = build_cvss4_vector(BASE_VECTOR, cve_id)

    print(f"CVE: {cve_id}")
    print(f"CVSS 4.0 Vector: {vector}")

if __name__ == "__main__":
    main()
