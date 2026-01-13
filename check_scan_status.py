#!/usr/bin/env python
"""Check scan file status and summary"""
import json
from pathlib import Path

scans_dir = Path("data/scans")
for scan_file in scans_dir.glob("scan_*.json"):
    try:
        with open(scan_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"File: {scan_file.name}")
        print(f"  Status: {data.get('status')}")
        print(f"  Has summary: {'summary' in data}")
        print(f"  End time: {data.get('end_time')}")
        print(f"  Message: {data.get('message')}")
        print(f"  Hosts in results: {len(data.get('results', {}))}")
        if data.get('summary'):
            print(f"  Summary CVEs: {data['summary'].get('total_cves')}")
        print()
    except Exception as e:
        print(f"File: {scan_file.name} - ERROR: {e}\n")
