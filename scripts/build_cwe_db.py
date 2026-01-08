#!/usr/bin/env python3
import argparse
import datetime
import os
import sqlite3
import xml.etree.ElementTree as ET


NS = {"cwe": "http://cwe.mitre.org/cwe-7", "xhtml": "http://www.w3.org/1999/xhtml"}


def extract_text(elem):
    """Extract and clean text from element, preserving original wording."""
    if elem is None:
        return None
    text = "".join(elem.itertext()).strip()
    text = " ".join(text.split())
    return text if text else None


def init_database(db_path):
    """Create database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript(
        """
        DROP TABLE IF EXISTS cwe;
        DROP TABLE IF EXISTS cwe_consequence;
        DROP TABLE IF EXISTS cwe_mitigation;
        DROP TABLE IF EXISTS cwe_metadata;

        CREATE TABLE cwe (
            cwe_id TEXT PRIMARY KEY,
            name TEXT,
            extended_description TEXT
        );

        CREATE TABLE cwe_consequence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cwe_id TEXT,
            scope TEXT,
            impact TEXT
        );

        CREATE TABLE cwe_mitigation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cwe_id TEXT,
            phase TEXT,
            description TEXT
        );

        CREATE TABLE cwe_metadata (
            version TEXT,
            imported_at TEXT
        );
        """
    )

    conn.commit()
    return conn


def extract_consequences(weakness_elem, cwe_id):
    """Parse Common_Consequences/Consequence elements."""
    consequences = []
    for consequence in weakness_elem.findall("cwe:Common_Consequences/cwe:Consequence", NS):
        scope_elems = consequence.findall("cwe:Scope", NS)
        impact_elems = consequence.findall("cwe:Impact", NS)

        scopes = [extract_text(e) for e in scope_elems]
        impacts = [extract_text(e) for e in impact_elems]

        scopes = [s for s in scopes if s]
        impacts = [i for i in impacts if i]

        for scope in scopes:
            for impact in impacts:
                consequences.append((cwe_id, scope, impact))

    return consequences


def extract_mitigations(weakness_elem, cwe_id):
    """Parse Potential_Mitigations/Mitigation elements."""
    mitigations = []
    for mitigation in weakness_elem.findall(
        "cwe:Potential_Mitigations/cwe:Mitigation", NS
    ):
        phase_elems = mitigation.findall("cwe:Phase", NS)
        desc_elem = mitigation.find("cwe:Description", NS)

        phases = [extract_text(e) for e in phase_elems]
        desc = extract_text(desc_elem)

        phases = [p for p in phases if p]

        if not desc:
            continue

        if phases:
            for phase in phases:
                mitigations.append((cwe_id, phase, desc))
        else:
            mitigations.append((cwe_id, None, desc))

    return mitigations


def import_cwe_catalog(xml_path, conn):
    """Parse XML and insert CWE data into database."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    version = root.attrib.get("Version", "unknown")
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cwe_metadata (version, imported_at) VALUES (?, ?)",
        (version, timestamp),
    )

    for weakness in root.findall(".//cwe:Weakness", NS):
        wid = weakness.attrib.get("ID")
        name = weakness.attrib.get("Name")

        if not wid:
            continue

        cwe_id = f"CWE-{wid}"
        ext_desc = extract_text(weakness.find("cwe:Extended_Description", NS))

        cursor.execute(
            "INSERT INTO cwe (cwe_id, name, extended_description) VALUES (?, ?, ?)",
            (cwe_id, name, ext_desc),
        )

        consequences = extract_consequences(weakness, cwe_id)
        if consequences:
            cursor.executemany(
                "INSERT INTO cwe_consequence (cwe_id, scope, impact) VALUES (?, ?, ?)",
                consequences,
            )

        mitigations = extract_mitigations(weakness, cwe_id)
        if mitigations:
            cursor.executemany(
                "INSERT INTO cwe_mitigation (cwe_id, phase, description) VALUES (?, ?, ?)",
                mitigations,
            )

    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Import MITRE CWE catalog XML into SQLite database"
    )
    parser.add_argument("xml_path", help="Path to cwec_v4.x.xml")
    parser.add_argument(
        "--db",
        default=os.path.join("modules", "cve", "cwe.db"),
        help="Output database path (default: modules/cve/cwe.db)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.xml_path):
        print(f"Error: XML file not found: {args.xml_path}")
        return 1

    db_dir = os.path.dirname(args.db)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    print(f"Initializing database: {args.db}")
    conn = init_database(args.db)

    print(f"Parsing XML: {args.xml_path}")
    import_cwe_catalog(args.xml_path, conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cwe")
    cwe_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cwe_consequence")
    consequence_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cwe_mitigation")
    mitigation_count = cursor.fetchone()[0]

    conn.close()

    print(f"✓ Imported {cwe_count} CWEs")
    print(f"✓ Imported {consequence_count} consequences")
    print(f"✓ Imported {mitigation_count} mitigations")
    print(f"✓ Database saved to: {args.db}")

    return 0


if __name__ == "__main__":
    exit(main())
