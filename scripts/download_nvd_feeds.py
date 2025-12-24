"""Download NVD feed .json.gz files into a local directory.

Usage:
  python scripts/download_nvd_feeds.py --dest modules/cve/nvd_data --start 2002 --end 2025
"""
import os
import sys
import time
import requests
from pathlib import Path

BASE_URL = "https://nvd.nist.gov/feeds/json/cve/2.0"
DEFAULT_DEST = Path("modules/cve/nvd_data")

FEED_SUFFIXES = [
    # standard year feeds
] + ["nvdcve-2.0-modified.json.gz", "nvdcve-2.0-recent.json.gz"]


def download_file(url: str, dst: Path, max_retries: int = 3, backoff: float = 1.5):
    tmp = dst.with_suffix(dst.suffix + ".part")
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            tmp.replace(dst)
            return True
        except Exception as e:
            print(f"[DOWNLOAD] attempt {attempt} failed: {e}")
            time.sleep(backoff * attempt)
    return False


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--dest", default=str(DEFAULT_DEST))
    p.add_argument("--start", type=int, default=2002)
    p.add_argument("--end", type=int, default=2025)
    p.add_argument("--force", action="store_true", help="re-download even if file exists")
    args = p.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    years = list(range(args.start, args.end + 1))
    feed_files = [f"nvdcve-2.0-{y}.json.gz" for y in years] + ["nvdcve-2.0-modified.json.gz", "nvdcve-2.0-recent.json.gz"]

    for f in feed_files:
        url = f"{BASE_URL}/{f}"
        dst = dest / f
        if dst.exists() and not args.force:
            print(f"[SKIP] {f} already present")
            continue
        print(f"[DOWNLOAD] {f} from {url}")
        ok = download_file(url, dst)
        if ok:
            print(f"[DONE] {f}")
        else:
            print(f"[FAIL] {f}")

    print("Download finished.")