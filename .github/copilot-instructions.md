# Copilot instructions for CVE_Scan

This file contains short, practical tips for an AI agent making code changes in this repository. Focus on specific, discoverable patterns and reproducible developer workflows.

## Big picture (what the app does)
- Desktop GUI tool (Tkinter) for scanning hosts and mapping services to CVEs using NVD feeds and CPE matching.
- Two main surfaces:
  - GUI (single-entrypoint `app.py` → `modules/gui.py`) which collects hosts and credentials, displays progress and results
  - Engine modules (`modules/scan_manager.py`, `modules/cve/*`, `modules/scanners/*`) that perform discovery, scanning and CVE matching
- Results shape used across the app: a mapping of host → result dict where `result['gui']['ports']` is a list of port dicts; each port has `cves` (list of CVE dicts). CVE dicts commonly include `id`, `severity` (string or dict with `label`), `description`, `cvss_v2|v3|v4`, and `cpe`.

## Key files & responsibilities
- `app.py` — processes entrypoint that starts the GUI
- `modules/gui.py` — UI code; uses background threads for scans and a `log_queue` to update a `scrolledtext` widget; UI helpers like `results_to_rows`, `write_scan_results_to_csv` are intentionally testable and independent of UI objects
- `modules/scan_manager.py` — orchestrates discovery and scanning, exposes `scan(targets, authenticated, auth_data, host_result_cb)`; prefer calling this when adding scan features
- `modules/config_manager.py` — central config load/save; configuration keys to know: `nvd_api_key`, `use_local_db`, `local_db_path`
- `modules/cve/*` — CPE building, fuzzy matching, local DB fetcher, NVD fetcher. Look at `nvd_fetcher.py` and `local_db_fetcher.py` for feed ingestion and DB rebuild patterns
- `modules/scanners/*` — platform-specific scanners (e.g., `auth_linux_scanner.py`, `auth_windows_scanner.py`) and helpers like `nmap_scanner.py` and `rustscan_scanner.py`
- `scripts/` — utility scripts (e.g., `rebuild_local_db.py`, `download_nvd_feeds.py`, `full_migration_runner.py`)
- `tests/` — lots of unit tests for logic (CSV export, fuzzy matching, GUI helpers). Use these as examples for writing small, focused tests (no heavy UI automation expected)

## Developer workflows & commands
- Virtual environment and deps: install via `pip install -r requirements.txt` in your virtualenv
- Run GUI: `python app.py` (starts Tkinter main loop)
- Run tests: `pytest -q` or `python -m pytest` from repository root (tests are designed to be fast/unit-level)
- Rebuild local CVE DB (interactive from GUI settings or via `scripts/rebuild_local_db.py`) — DB path defaults to `modules/cve/nvd_cve.db` or `modules/cve/nvd_data` for raw feed files

## Patterns and conventions to follow
- Prefer pure helpers for logic (e.g., `results_to_rows`, `write_scan_results_to_csv`) rather than embedding logic directly into GUI code; tests rely on these helpers
- Threading & UI: all long-running work must run in background threads; UI updates must use `root.after(0, ...)` or queue-based patterns used in `GUIController` to stay thread-safe
- Logging: GUI uses a `log_queue` to send `(text, tag)` tuples. Tags are `INFO|SUCCESS|WARN|ERROR|SYSTEM` with color styling in `gui.py` — prefer these tags when emitting logs from engine modules via provided `logger` callbacks
- CVE severity may be a string or a dict: code frequently checks `cve.get('severity')` and then handles both forms — replicate this defensively
- Import style: modules attempt `from modules.xxx import Y`; maintain relative/absolute imports consistent with package layout when adding new modules

## Tests & examples to reference when editing code
- `tests/test_csv_report.py` and `modules/gui.py::write_scan_results_to_csv` — example of CSV layout and expected columns
- `tests/test_cve_matcher_fuzzy.py` and `modules/cve/fuzzy_matcher.py` — examples for matching heuristics and expected behavior
- `tests/test_gui.py` and `tests/test_gui_host_updates.py` — examples for testing `GUIController` helpers synchronously using `sync=True` hooks
- Look for small helper functions that are intentionally separated for testability (follow that style)

## Integration points & external dependencies
- NVD feeds: used by `modules/cve/nvd_fetcher.py`; the repo supports both remote NVD API access (requires `nvd_api_key`) and a local SQLite DB (`use_local_db` config)
- Scanners depend on `python-nmap`, `paramiko` (Linux auth), `pywinrm` (Windows auth) and optionally `rustscan`/`nmap` external tools for port discovery

## PR guidance for AI edits (do this in PRs)
- Small, focused PRs that change one module or behavior are preferred
- Add unit tests for new logic (follow the `tests/` pattern) and ensure `pytest` passes
- Preserve GUI-friendly helper functions for testability (avoid mixing UI and core logic directly)
- When updating data structures (result shapes), update both helpers in `modules/gui.py` and relevant tests in `tests/`

---
If you'd like, I can add quick checklist items or a couple of concrete code snippets (e.g., a recommended `ScanManager` usage example) to the file. Any sections missing or unclear that you want me to expand? Please tell me which parts to refine.