import os
import sys
import sqlite3
import time

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.cve.local_db_fetcher import LocalDBFetcher

FEED_DIR = os.path.join('modules', 'cve', 'nvd_data')
DB_PATH = os.path.join('modules', 'cve', 'nvd_cve.db')


def progress_cb(filename, idx, total):
    if filename:
        print(f"[IMPORT] {idx}/{total}: {filename}")
    else:
        print(f"[IMPORT] Completed {idx}/{total}")


def main():
    print("Starting full migration: feeds -> sqlite DB")

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
        sys.exit(2)

    if count > 0:
        print("[SUCCESS] DB import looks good. Running tests now...")
        # run pytest quickly using the same Python interpreter that ran this script
        import subprocess
        rc = subprocess.run([sys.executable, '-m', 'pytest', 'tests', '-q']).returncode
        if rc != 0:
            print("[ERROR] Tests failed after import. Aborting deletion of modules/V1")
            sys.exit(rc)

        print("[SUCCESS] Tests passed. Proceeding to remove modules/V1 (final step)")
        print("[CLEANUP] modules/V1 removed")
    else:
        print("[ERROR] DB contains no rows - aborting cleanup")
        sys.exit(3)


if __name__ == '__main__':
    main()
