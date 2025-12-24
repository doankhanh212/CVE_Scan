"""Simple smoke runner for BasicPipeline to reproduce scan failures.

Run with the project's venv:
  C:/.../venv/Scripts/python.exe scripts/smoke_run_scan.py
"""
import logging
import json
import os
import sys

# ensure project root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.pipelines.basic_pipeline import BasicPipeline

logging.basicConfig(level=logging.DEBUG)

config = {
    "nvd_api_key": "",
    "use_local_db": True,
    "local_db_path": "modules/cve/nvd_cve.db",
    "rustscan_timeout": 60,
    "rustscan_ulimit": 1000,
    "nmap_timeout": 30
}

pipeline = BasicPipeline(config, logger=lambda m, lvl="INFO": print(f"[{lvl}] {m}"))

print("Running smoke BasicPipeline scan against 127.0.0.1 (may require rustscan/wsl and nmap installed)")
try:
    report = pipeline.execute("127.0.0.1")
    print(json.dumps(report, indent=2, ensure_ascii=False)[:1000])
    print("...output truncated")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("FAILED: ", e)
