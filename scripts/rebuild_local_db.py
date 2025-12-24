"""Rebuild the local CVE DB at modules/cve/nvd_cve.db from feeds in modules/cve/nvd_data."""
import os
import sys
import sqlite3

# Ensure project root is on sys.path when run as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.cve.local_db_fetcher import LocalDBFetcher

FEED_DIR = os.path.join('modules', 'cve', 'nvd_data')
DB_PATH = os.path.join('modules', 'cve', 'nvd_cve.db')


def progress_cb(filename, idx, total):
    if filename:
        print(f"[IMPORT] {idx}/{total}: {filename}")
    else:
        print(f"[IMPORT] Completed {idx}/{total}")


if __name__ == '__main__':
    print(f"Rebuilding DB at {DB_PATH} from feeds in {FEED_DIR}")
    fetcher = LocalDBFetcher(db_path=DB_PATH)
    fetcher.rebuild_db_from_feeds(FEED_DIR, progress_cb=progress_cb)

    # verify DB row count
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM cve')
        count = cur.fetchone()[0]
        conn.close()
        print(f"[VERIFY] total CVE rows: {count}")
    except Exception as e:
        print(f"[VERIFY] DB verify failed: {e}")
        raise

    print("Rebuild finished.")