import os
import gzip
import json
import sqlite3
from typing import List, Optional


BASE_URL = "https://nvd.nist.gov/feeds/json/cve/2.0"


def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS cve (
            id TEXT PRIMARY KEY,
            published TEXT,
            last_modified TEXT,
            cvss_base_score REAL,
            cvss_severity TEXT,
            description TEXT,
            raw_json TEXT,
            cve_cpe TEXT
        )
    """)

    # Index for faster searches on cpe JSON
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_cve_cpe ON cve(cve_cpe)")
    except Exception:
        pass

    conn.commit()
    conn.close()


def parse_json_gz(path: str) -> List[dict]:
    """Parse a .json.gz NVD feed and return list of vulnerability items."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("vulnerabilities", [])


def extract_cpe_list(item: dict) -> List[str]:
    cpe_list = []
    cve = item.get("cve", {})

    configs = cve.get("configurations", {})

    if isinstance(configs, dict):
        for node in configs.get("nodes", []):
            for match in node.get("cpeMatch", []):
                cpe = match.get("criteria") or match.get("cpe23Uri")
                if cpe:
                    cpe_list.append(cpe)

    elif isinstance(configs, list):
        for cfg in configs:
            if not isinstance(cfg, dict):
                continue
            for node in cfg.get("nodes", []):
                for match in node.get("cpeMatch", []):
                    cpe = match.get("criteria") or match.get("cpe23Uri")
                    if cpe:
                        cpe_list.append(cpe)

    if not cpe_list and "affects" in cve:
        vendor_data = (
            cve.get("affects", {}).get("vendor", {}).get("vendor_data", [])
        )
        for vendor in vendor_data:
            products = vendor.get("product", {}).get("product_data", [])
            for product in products:
                vendor_name = vendor.get("vendor_name")
                product_name = product.get("product_name")
                versions = product.get("version", {}).get("version_data", [])
                for ver in versions:
                    version = ver.get("version_value")
                    if vendor_name and product_name and version:
                        cpe = f"cpe:2.3:a:{vendor_name}:{product_name}:{version}:*:*:*:*:*:*:*"
                        cpe_list.append(cpe)

    return list(set(cpe_list))


def save_to_db(db_path: str, entries: List[dict]):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for item in entries:
        cve = item.get("cve", {})
        cve_id = cve.get("id")
        if not cve_id:
            continue

        published = cve.get("published")
        last_modified = cve.get("lastModified")

        metrics = cve.get("metrics", {})
        cvss = None
        if "cvssMetricV40" in metrics:
            cvss = metrics["cvssMetricV40"][0]
        elif "cvssMetricV31" in metrics:
            cvss = metrics["cvssMetricV31"][0]
        elif "cvssMetricV30" in metrics:
            cvss = metrics["cvssMetricV30"][0]

        base_score = None
        severity = None
        if cvss:
            try:
                base_score = cvss["cvssData"].get("baseScore")
                severity = cvss["cvssData"].get("baseSeverity")
            except Exception:
                pass

        descriptions = cve.get("descriptions", [])
        desc = descriptions[0].get("value") if descriptions else ""

        cpe_list = extract_cpe_list(item)
        cpe_json = json.dumps(cpe_list)

        c.execute(
            """
            INSERT OR REPLACE INTO cve
            (id, published, last_modified, cvss_base_score, cvss_severity, description, raw_json, cve_cpe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cve_id, published, last_modified, base_score, severity, desc, json.dumps(item), cpe_json),
        )

    conn.commit()
    conn.close()


def import_feeds(feed_dir: str, db_path: str, limit_files: Optional[List[str]] = None, progress_cb=None):
    """Import all .json.gz files in feed_dir into db_path. Optionally provide a list of filenames to limit.

    progress_cb(filename, index, total) will be called per-file if provided.
    """
    init_db(db_path)

    files = [f for f in os.listdir(feed_dir) if f.endswith('.json.gz')]
    files.sort()

    if limit_files:
        files = [f for f in files if f in limit_files]

    total = len(files)

    for idx, f in enumerate(files, start=1):
        path = os.path.join(feed_dir, f)
        try:
            if progress_cb:
                try:
                    progress_cb(f, idx, total)
                except Exception:
                    pass

            entries = parse_json_gz(path)
            save_to_db(db_path, entries)

            if progress_cb:
                try:
                    progress_cb(None, idx, total)
                except Exception:
                    pass

        except Exception as e:
            # continue on error per-file
            print(f"[!] Failed to import {path}: {e}")
            if progress_cb:
                try:
                    progress_cb(f, idx, total)
                except Exception:
                    pass


if __name__ == '__main__':
    # CLI convenience
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--feed-dir', default='modules/cve/nvd_data')
    p.add_argument('--db', default='modules/cve/nvd_cve.db')
    args = p.parse_args()

    import_feeds(args.feed_dir, args.db)
