import json
import os
import time
import requests
from config import KEV_URL, CACHE_FILE, CACHE_TTL
from kev_db import upsert_kev

def cache_valid():
    if not os.path.exists(CACHE_FILE):
        return False
    return time.time() - os.path.getmtime(CACHE_FILE) < CACHE_TTL

def load_from_cache():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def fetch_kev(force=False):
    if not force and cache_valid():
        return load_from_cache()

    r = requests.get(KEV_URL, timeout=15)
    r.raise_for_status()
    data = r.json()

    save_cache(data)
    return data

def update_db_from_kev(force=False):
    data = fetch_kev(force)
    for vuln in data.get("vulnerabilities", []):
        upsert_kev(vuln)
