import tempfile
import gzip
import json
from pathlib import Path
from modules.cve import db_importer
from modules.cve.db_importer import init_db, parse_json_gz, save_to_db


def make_sample_feed(path: Path):
    payload = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-TEST-1000",
                    "published": "2025-01-01T00:00:00Z",
                    "descriptions": [{"lang": "en", "value": "Sample vuln"}],
                    "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 5.0, "vectorString": ""}}]},
                    "configurations": {"nodes": [{"cpeMatch": [{"cpe23Uri": "cpe:2.3:a:example:product:1.2:*:*:*:*:*:*:*"}]}]}
                }
            }
        ]
    }

    raw = json.dumps(payload).encode('utf-8')
    with gzip.open(path, 'wb') as f:
        f.write(raw)


def test_import_feed_and_query(tmp_path):
    feed_dir = tmp_path / "nvd"
    feed_dir.mkdir()
    feed_file = feed_dir / "nvdcve-2.0-sample.json.gz"
    make_sample_feed(feed_file)

    db = tmp_path / "nvd_test.db"
    db_path = str(db)

    init_db(db_path)

    entries = parse_json_gz(str(feed_file))
    save_to_db(db_path, entries)

    # verify row exists
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, description FROM cve WHERE id=?", ("CVE-TEST-1000",))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "CVE-TEST-1000"
    assert "Sample vuln" in (row[1] or "")
