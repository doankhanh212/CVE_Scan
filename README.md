# CVE_Scan v1.0.0

Desktop GUI tool (Tkinter) to discover hosts, map services to CPEs, and match CVEs using NVD feeds or a local database.

## Features
- Input Mode: IP/CIDR or Hostname routing
- Host discovery via threaded ping; optional nmap probes
- Fast port discovery (RustScan), service detection (Nmap)
- CPE building with heuristics; CVE matching via NVD or local DB
- CSV/JSON/PDF report exports; GUI logs with severity tags

## Requirements
- Python 3.10+
- On Windows: Npcap (for advanced discovery)
- Dependencies: see `requirements.txt`

## Quick Start
```bash
pip install -r requirements.txt
python app.py
```

## Tests
```bash
python -m pytest -q
```

## Notes
- Local NVD DB can be rebuilt via `scripts/rebuild_local_db.py`.
- CSV layout and helpers live in `modules/gui.py`.
- Keep long-running tasks off the UI thread; GUI uses a log queue.

