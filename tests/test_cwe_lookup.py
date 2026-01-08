import pytest
import os
import tempfile
import sqlite3
from modules.cve.cwe_lookup import CWELookup


@pytest.fixture
def test_db():
    """Create a minimal test database."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript(
        """
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

        INSERT INTO cwe VALUES ('CWE-79', 'Cross-site Scripting', 'XSS attack description');
        INSERT INTO cwe_consequence VALUES (1, 'CWE-79', 'Confidentiality', 'Data Breach');
        INSERT INTO cwe_consequence VALUES (2, 'CWE-79', 'Integrity', 'Unauthorized Modification');
        INSERT INTO cwe_mitigation VALUES (1, 'CWE-79', 'Design', 'Input validation');
        INSERT INTO cwe_mitigation VALUES (2, 'CWE-79', 'Implementation', 'Output encoding');
        """
    )
    conn.commit()
    conn.close()

    yield db_path

    os.unlink(db_path)


def test_get_cwe(test_db):
    lookup = CWELookup(test_db)
    cwe = lookup.get_cwe("CWE-79")
    assert cwe is not None
    assert cwe["cwe_id"] == "CWE-79"
    assert cwe["name"] == "Cross-site Scripting"
    assert "XSS" in cwe["extended_description"]
    lookup.close()


def test_get_cwe_without_prefix(test_db):
    lookup = CWELookup(test_db)
    cwe = lookup.get_cwe("79")
    assert cwe is not None
    assert cwe["cwe_id"] == "CWE-79"
    lookup.close()


def test_get_cwe_not_found(test_db):
    lookup = CWELookup(test_db)
    cwe = lookup.get_cwe("CWE-9999")
    assert cwe is None
    lookup.close()


def test_get_consequences(test_db):
    lookup = CWELookup(test_db)
    consequences = lookup.get_consequences("CWE-79")
    assert len(consequences) == 2
    assert consequences[0]["scope"] == "Confidentiality"
    assert consequences[0]["impact"] == "Data Breach"
    lookup.close()


def test_get_mitigations(test_db):
    lookup = CWELookup(test_db)
    mitigations = lookup.get_mitigations("CWE-79")
    assert len(mitigations) == 2
    assert mitigations[0]["phase"] == "Design"
    assert mitigations[0]["description"] == "Input validation"
    lookup.close()


def test_get_full_explanation(test_db):
    lookup = CWELookup(test_db)
    explanation = lookup.get_full_explanation("CWE-79")
    assert explanation is not None
    assert "cwe" in explanation
    assert "consequences" in explanation
    assert "mitigations" in explanation
    assert len(explanation["consequences"]) == 2
    assert len(explanation["mitigations"]) == 2
    lookup.close()
