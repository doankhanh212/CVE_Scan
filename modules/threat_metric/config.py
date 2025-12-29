"""
Threat Metric Configuration
"""
import os

# DB Path: prefer workspace root CVSS_threat_metric, fallback to local
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DB_CANDIDATES = [
    os.path.join(WORKSPACE_ROOT, "CVSS_threat_metric", "kev_module", "kev.db"),
    os.path.join(WORKSPACE_ROOT, "CVSS_threat_metric", "Threat_metric", "kev.db"),
    "kev.db"  # Local fallback
]

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CACHE_FILE = "kev_cache.json"
CACHE_TTL = 6 * 60 * 60  # 6 hours

DB_PATH = None
for path in DB_CANDIDATES:
    if os.path.exists(path):
        DB_PATH = path
        break
if DB_PATH is None:
    DB_PATH = DB_CANDIDATES[-1]  # Use local fallback as default
