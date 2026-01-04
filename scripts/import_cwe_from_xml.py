#!/usr/bin/env python3
"""Import CWE catalog from cwec_latest.xml into config/cwe_mapping.json."""
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import re

ROOT = Path(__file__).resolve().parents[1]
XML_PATH = ROOT / "cwec_latest.xml" / "cwec_v4.19.xml"
JSON_PATH = ROOT / "config" / "cwe_mapping.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def _detect_namespace(root: ET.Element) -> str:
    """Extract XML namespace from root tag if present."""
    match = re.match(r"\{(.+)}", root.tag)
    return match.group(1) if match else ""


def main() -> int:
    if not XML_PATH.exists():
        print(f"[ERROR] CWE XML not found: {XML_PATH}")
        return 1
    if not JSON_PATH.exists():
        print(f"[ERROR] JSON mapping not found: {JSON_PATH}")
        return 1

    data = load_json(JSON_PATH)
    mappings = data.get("mappings", [])
    by_id = {m["cwe_id"]: m for m in mappings if "cwe_id" in m}

    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    ns = _detect_namespace(root)
    weak_xpath = ".//{*}Weakness" if not ns else f".//{{{ns}}}Weakness"

    added = 0
    updated = 0
    for weakness in root.findall(weak_xpath):
        try:
            cid = int(weakness.attrib.get("ID"))
        except (TypeError, ValueError):
            continue
        name = weakness.attrib.get("Name", "").strip()
        if cid not in by_id:
            by_id[cid] = {
                "cwe_id": cid,
                "cwe_name": name,
                "owasp_codes": [],
                "mitre_techniques": [],
                "severity": "MEDIUM",
            }
            added += 1
        else:
            entry = by_id[cid]
            if not entry.get("cwe_name") and name:
                entry["cwe_name"] = name
                updated += 1

    data["mappings"] = sorted(by_id.values(), key=lambda m: m["cwe_id"])
    save_json(JSON_PATH, data)

    print(f"[INFO] Added {added} new CWEs, updated {updated} existing names")
    print(f"[INFO] Total CWEs in mapping: {len(data['mappings'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
